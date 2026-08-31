import base64
from flask import jsonify, request, current_app
from config import GEMINI_API_KEY, GEMINI_LIVE_MODEL
from services.crm_service import capture_lead_from_message
from services.voice_service import friendly_audio_error, get_gemini_api_key_candidates, get_live_audio_reply
from routes.api._blueprint import api_bp, _client_ip, _check_rate_limit
from utils.logger import setup_logger
logger = setup_logger("chat")


def _is_ai_capacity_error(exc):
    message = str(exc).lower()
    return any(part in message for part in ["quota", "429", "resourceexhausted", "denied access", "403", "1008"])


def _local_chat_fallback(user_message, exc=None):
    message = (user_message or "").lower()
    prefix = ""
    if exc and _is_ai_capacity_error(exc):
        prefix = "Gemini API limiti yoki project access sabab hozir live javob sekinlashgan. "

    if any(word in message for word in ["salom", "assalom", "hello", "hi"]):
        return prefix + "Salom! TrendoAI web saytlar, Telegram botlar, AI chatbotlar va SMM bo'yicha yordam beradi. Qaysi xizmat sizga kerak?"

    if any(word in message for word in ["narx", "qancha", "price", "sum", "so'm"]):
        return prefix + (
            "Narx loyiha murakkabligiga bog'liq. Telegram botlar 300 000 so'mdan, "
            "web saytlar 500 000 so'mdan, AI chatbotlar 1 000 000 so'mdan boshlanadi. "
            "Aniq hisoblash uchun Telegram username yoki telefon raqamingizni qoldiring."
        )

    if any(word in message for word in ["bot", "telegram"]):
        return prefix + "Telegram bot uchun buyurtma, to'lov, admin panel, CRM va xabar avtomatlashtirish funksiyalarini qilib beramiz. Qanday biznes uchun bot kerak?"

    if any(word in message for word in ["sayt", "website", "web", "landing"]):
        return prefix + "Web sayt uchun landing page, korporativ sayt yoki internet do'kon tayyorlaymiz. Mobilga mos, tez va SEO asoslari bilan qilinadi. Qaysi turdagi sayt kerak?"

    if any(word in message for word in ["ai", "chatbot", "sun'iy", "suniy"]):
        return prefix + "AI chatbot mijoz savollariga 24/7 javob berishi, lead yig'ishi va Telegram yoki saytga ulanishi mumkin. Qaysi soha uchun kerakligini yozing."

    return prefix + "Savolingizni oldim. TrendoAI xizmatlari bo'yicha yordam beraman: web sayt, Telegram bot, AI chatbot yoki SMM. Batafsilroq yozsangiz, mos yechimni tavsiya qilaman."


# ========== AI CHATBOT & AUDIO ==========

@api_bp.route('/api/chat', methods=['POST'])
def api_chat():
    """AI chatbot yordamchisi API"""
    client_ip = _client_ip()
    if not _check_rate_limit(f"chat:{client_ip}", limit=30, window_seconds=60):
        return jsonify({'error': "Juda ko'p so'rov yuborildi. Iltimos, 1 daqiqadan so'ng qayta urinib ko'ring."}), 429

    data = request.get_json(silent=True) or {}
    messages = data.get('messages') or []
    raw_message = (data.get('message') or '').strip()

    if not messages and raw_message:
        messages = [{'role': 'user', 'content': raw_message}]

    if not messages:
        fallback = 'Qanday yordam bera olaman?'
        return jsonify({'success': True, 'reply': fallback, 'response': fallback})

    last_user_msg = ''
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            content = (msg.get('content') or '').strip()
            if content:
                last_user_msg = content
                break

    if not last_user_msg:
        last_user_msg = raw_message

    if not last_user_msg:
        fallback = 'Savolingizni qaytadan yozib yuboring.'
        return jsonify({'success': False, 'reply': fallback, 'response': fallback}), 400

    if len(last_user_msg) > 4000:
        return jsonify({'error': 'Xabar matni juda uzun (maksimal 4000 ta belgi)'}), 400

    api_key = current_app.config.get('GEMINI_API_KEY') or GEMINI_API_KEY
    if not api_key:
        fallback = _local_chat_fallback(last_user_msg)
        return jsonify({
            'success': True,
            'reply': fallback,
            'response': fallback,
            'ai_fallback': True,
            'error': 'AI provider sozlanmagan, lokal javob ishlatildi.',
        })

    try:
        system_prompt = """Siz TrendoAI kompaniyasining bosh AI Savdo va Avtomatlashtirish Konsultantisiz (AI Sales Manager).
TrendoAI — O'zbekistonda bizneslar uchun AI Agentlar, Telegram Botlar, CRM va Veb-saytlar ishlab chiquvchi yetakchi IT agentligi.

SIZNING VAZIFANGIZ VA SOTUV STRATEGIYANGIZ (SALES QUALIFICATION):
1. Mijozga juda do'stona, professional va qisqa javob bering (O'zbek lotin tilida).
2. Mijoz xizmat so'raganda, uning ehtiyojini aniqlang (Qualify):
   - Biznesingiz qaysi sohada? (Masalan: Restoran, O'quv markazi, Do'kon, Xizmat ko'rsatish)
   - Qaysi jarayonni avtomatlashtirmoqchisiz? (24/7 javob berish, buyurtma/to'lov qabul qilish, CRM hisobotlar)
   - Qanday byudjet rejalashtiryapsiz?
3. Mos keluvchi TrendoAI yechimini tavsiya qiling va taxminiy narxlarni ayting:
   - Telegram Bot & TMA: 1,000,000 - 4,000,000 so'm
   - AI Chatbot / AI Agent: 2,000,000 - 6,000,000 so'm
   - Veb-sayt / E-commerce: 2,000,000 - 7,000,000 so'm
   - Barcha loyihalarga 1 oylik bepul texnik kafolat va 24/7 monitoring beriladi.
4. Yakunda mijozdan aloqa ma'lumotini so'rang:
   "Sizga aniq Texnik Topshiriq (TZ) va smeta tayyorlab berishimiz uchun telefon raqamingiz yoki Telegram username'ingizni qoldiring, mutaxassisimiz 15 daqiqada bog'lanadi."
5. Hech qachon umumiy yoki quruq doston yozmang, qisqa va amaliy bo'ling."""

        history = []
        for msg in messages[-6:-1]:
            content = (msg.get('content') or '').strip()
            if not content:
                continue
            role = 'user' if msg.get('role') == 'user' else 'model'
            history.append({'role': role, 'parts': [content]})

        from services.ai_service import generate_text
        reply, _model_used = generate_text(
            prompt=last_user_msg,
            system_instruction=system_prompt,
            history=history,
        )

        if not reply:
            reply = "Uzr, hozir javobni shakllantirib bo'lmadi. Telegram orqali yozing: @trendoai"

        capture_lead_from_message(last_user_msg, source="AI Chat Vidjet", default_name="AI Chat Mijoz")
        return jsonify({'success': True, 'reply': reply, 'response': reply})

    except Exception as e:
        logger.error(f"[api] Chat error: {e}")
        fallback = _local_chat_fallback(last_user_msg, e)
        return jsonify({
            'success': True,
            'reply': fallback,
            'response': fallback,
            'ai_fallback': True,
            'error': 'AI provider vaqtincha limit yoki access sabab javob bermadi.',
        })


@api_bp.route('/api/chat/audio', methods=['POST'])
def api_chat_audio():
    """AI Chatbot audio endpoint - Gemini Live bilan."""
    client_ip = _client_ip()
    if not _check_rate_limit(f"audio:{client_ip}", limit=15, window_seconds=60):
        return jsonify({'error': "Juda ko'p audio so'rovi yuborildi. Iltimos, birozdan so'ng qayta urinib ko'ring."}), 429

    try:
        data = request.get_json(silent=True) or {}
        audio_base64 = data.get('audio', '')
        mime_type = data.get('mime_type') or data.get('mimeType') or 'audio/webm'

        if not audio_base64:
            return jsonify({'error': 'Audio topilmadi'}), 400

        # Maksimal 5MB base64 payload cheklovi
        if len(audio_base64) > 5 * 1024 * 1024:
            return jsonify({'error': 'Audio fayl hajmi juda katta (maksimal 5MB)'}), 400

        if not get_gemini_api_key_candidates():
            return jsonify({
                'error': 'GEMINI_API_KEY topilmadi',
                'response': "AI ovozli yordamchi hozircha sozlanmagan."
            }), 503

        if ',' in audio_base64:
            audio_base64 = audio_base64.split(',', 1)[1]

        audio_bytes = base64.b64decode(audio_base64)
        import sys
        live_reply_fn = getattr(sys.modules.get('app'), 'get_live_audio_reply', get_live_audio_reply)
        from services.voice_service import chat_audio_system_prompt
        live_reply = live_reply_fn(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            system_prompt=chat_audio_system_prompt(),
        )

        response_text = live_reply.get('text') or "Ovozli javob tayyor."
        transcription = live_reply.get('input_transcription') or response_text or ''
        capture_lead_from_message(transcription, source="Live Voice Call (Gemini)", default_name="Ovozli Muloqot Mijoz")

        return jsonify({
            'success': True,
            'response': response_text,
            'reply': response_text,
            'audio_base64': live_reply.get('audio_base64'),
            'input_transcription': live_reply.get('input_transcription'),
            'model': live_reply.get('model') or GEMINI_LIVE_MODEL,
        })
    except Exception as e:
        logger.error(f"[api] Audio chatbot error: {e}")
        return jsonify({
            'error': "Ovozni tushunib bo'lmadi",
            'response': friendly_audio_error(e),
            'model': GEMINI_LIVE_MODEL,
        }), 500
