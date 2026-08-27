"""
TrendoAI REST API, AI Chatbot, Live Audio, Webhook va Cron marshrutlari.
"""
import base64
from datetime import datetime
import os
import random
import re
import threading
import time

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
)
from config import (
    CATEGORIES,
    CRON_SECRET,
    GEMINI_API_KEY,
    GEMINI_LIVE_MODEL,
    GEMINI_MODEL,
    SITE_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
)
from extensions import csrf, db
from models.order import BotOrder, Order
from models.interaction import Lead, PushSubscription
from models.post import Post
from routes.admin import login_required
from services.crm_service import capture_lead_from_message
from services.push_service import notify_all_subscribers
from services.voice_service import (
    friendly_audio_error,
    get_gemini_api_key_candidates,
    get_live_audio_reply,
)

api_bp = Blueprint('api', __name__)

TELEGRAM_WEBHOOK_SECRET = CRON_SECRET[:256] if CRON_SECRET else 'trendoai_super_secret_123'


def _cron_secret_error():
    return jsonify({'error': 'Unauthorized', 'message': 'Invalid secret key'}), 401


def _has_valid_cron_secret():
    secret = request.args.get('secret') or request.headers.get('X-Cron-Secret')
    expected = current_app.config.get('CRON_SECRET') or CRON_SECRET
    return bool(secret and secret == expected)


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


# ========== PUBLIC API ROUTES ==========

@api_bp.route('/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'TrendoAI',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat()
    })


@api_bp.route('/api/posts')
def api_posts():
    """Barcha postlar API"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', None)

    query = Post.query.filter_by(is_published=True)
    if category:
        query = query.filter_by(category=category)

    pagination = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=min(per_page, 50), error_out=False
    )

    return jsonify({
        'posts': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    })


@api_bp.route('/api/posts/<int:post_id>')
def api_post(post_id):
    """Bitta post API"""
    p = Post.query.get_or_404(post_id)
    return jsonify(p.to_dict())


@api_bp.route('/api/stats')
def api_stats():
    """Statistika API"""
    return jsonify({
        'total_posts': Post.query.count(),
        'published_posts': Post.query.filter_by(is_published=True).count(),
        'total_views': db.session.query(db.func.sum(Post.views)).scalar() or 0,
        'categories': CATEGORIES
    })


@api_bp.route('/api/lead', methods=['POST'])
@csrf.exempt
def submit_lead():
    """Lead Magnet yoki Chatbot orqali kelgan ma'lumotni saqlash"""
    data = request.json
    if not data or not data.get('contact'):
        return jsonify({'status': 'error', 'message': "Iltimos, aloqa ma'lumotini kiriting."}), 400

    try:
        new_lead = Lead(
            name=data.get('name', "Noma'lum"),
            contact=data['contact'],
            source=data.get('source', 'Sayt Orqali')
        )
        db.session.add(new_lead)
        db.session.commit()

        from telegram_poster import send_admin_alert
        msg = f"🎯 <b>YANGI MIJOZ (LEAD)!</b>\n\n👤 <b>Ismi:</b> {new_lead.name}\n📞 <b>Aloqa:</b> {new_lead.contact}\n📍 <b>Manba:</b> {new_lead.source}"
        send_admin_alert(msg)

        return jsonify({'status': 'success', 'message': "Ma'lumot muvaffaqiyatli qabul qilindi!"})
    except Exception as e:
        print(f"[api] Lead error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ========== AI CHATBOT & AUDIO ==========

@api_bp.route('/api/chat', methods=['POST'])
def api_chat():
    """AI chatbot yordamchisi API"""
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

        from ai_helpers import generate_text
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
        print(f"[api] Chat error: {e}")
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
    try:
        data = request.get_json(silent=True) or {}
        audio_base64 = data.get('audio', '')
        mime_type = data.get('mime_type') or data.get('mimeType') or 'audio/webm'

        if not audio_base64:
            return jsonify({'error': 'Audio topilmadi'}), 400

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
        print(f"[api] Audio chatbot error: {e}")
        return jsonify({
            'error': "Ovozni tushunib bo'lmadi",
            'response': friendly_audio_error(e),
            'model': GEMINI_LIVE_MODEL,
        }), 500


# ========== PUSH NOTIFICATION ROUTES ==========

@api_bp.route('/api/push/subscribe', methods=['POST'])
def push_subscribe():
    """Web Push obunasini saqlash yoki yangilash"""
    data = request.json
    if not data or not data.get('endpoint'):
        return jsonify({'error': 'Invalid data'}), 400

    endpoint = data['endpoint']
    keys = data.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not p256dh or not auth:
        return jsonify({'error': 'Missing keys'}), 400

    subscription = PushSubscription.query.filter_by(endpoint=endpoint).first()
    created = False

    if not subscription:
        subscription = PushSubscription(
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth
        )
        db.session.add(subscription)
        created = True
    else:
        subscription.p256dh = p256dh
        subscription.auth = auth

    db.session.commit()
    print(f"[push] Subscription {'yaratildi' if created else 'yangilandi'}: {endpoint[:80]}")
    return jsonify({'success': True, 'message': 'Obuna saqlandi', 'created': created})


@api_bp.route('/api/push/send', methods=['POST'])
@login_required
def push_send():
    """Push xabar yuborish (Admin)"""
    data = request.json or {}
    title = data.get('title', 'TrendoAI')
    message = data.get('message', 'Yangi xabar!')
    url = data.get('url', '/')

    sent_count = notify_all_subscribers(title=title, message=message, url=url)
    return jsonify({'success': sent_count > 0, 'sent_count': sent_count})


# ========== ADMIN / BOT STATUS APIS ==========

@api_bp.route('/api/bot-order-status', methods=['POST'])
@login_required
def update_bot_order_status():
    """Bot buyurtma statusini o'zgartirish"""
    try:
        order_id = (request.json or {}).get('order_id') or request.form.get('order_id')
        status = (request.json or {}).get('status') or request.form.get('status')
        order = BotOrder.query.get(order_id)
        if order:
            order.status = status
            db.session.commit()

            from telegram_poster import bot
            if bot and order.tg_id:
                status_text = {
                    'confirmed': "✅ Qabul qilindi",
                    'preparing': "👨‍🍳 Tayyorlanmoqda",
                    'delivering': "🛵 Yetkazilmoqda",
                    'done': "🎉 Yetkazib berildi",
                    'cancelled': "❌ Bekor qilindi"
                }.get(status, status)

                msg = f"📋 Buyurtma {order.order_number} yangilandi!\n📦 Status: *{status_text}*"
                try:
                    bot.send_message(order.tg_id, msg, parse_mode='Markdown')
                except Exception as e:
                    print(f"Failed to send status update to customer: {e}")

            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/admin/crm/update-status', methods=['POST'])
@login_required
@csrf.exempt
def api_crm_update_status():
    """AJAX status update for Kanban Board items"""
    data = request.json or {}
    item_type = data.get('type')
    item_id = data.get('id')
    new_status = data.get('status')

    valid_statuses = ['new', 'contacted', 'in_progress', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        return jsonify({'error': 'Yaroqsiz status'}), 400

    try:
        if item_type == 'order':
            order = Order.query.get(item_id)
            if order:
                order.status = new_status
                db.session.commit()
                return jsonify({'success': True, 'message': f'Order #{item_id} statusi yangilandi.'})
        elif item_type == 'lead':
            lead = Lead.query.get(item_id)
            if lead:
                lead.status = new_status
                db.session.commit()
                return jsonify({'success': True, 'message': f'Lead #{item_id} statusi yangilandi.'})

        return jsonify({'error': 'Topilmadi'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/admin/crm/update-note', methods=['POST'])
@login_required
@csrf.exempt
def api_crm_update_note():
    """AJAX endpoint for saving follow-up notes on Kanban items"""
    data = request.json or {}
    item_type = data.get('type')
    item_id = data.get('id')
    note = (data.get('note') or '').strip()

    try:
        if item_type == 'order':
            order = Order.query.get(item_id)
            if order:
                order.admin_note = note
                db.session.commit()
                return jsonify({'success': True, 'message': 'Eslatma saqlandi.'})
        elif item_type == 'lead':
            lead = Lead.query.get(item_id)
            if lead:
                lead.admin_note = note
                db.session.commit()
                return jsonify({'success': True, 'message': 'Eslatma saqlandi.'})

        return jsonify({'error': 'Element topilmadi'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/api/generate-portfolio')
@login_required
def api_generate_portfolio():
    """AI yordamida portfolio kontent generatsiya qilish"""
    from ai_generator import generate_portfolio_content
    title = request.args.get('title', '')
    category = request.args.get('category', 'web')

    if not title:
        return jsonify({'error': 'Title kerak'}), 400

    try:
        result = generate_portfolio_content(title, category)
        if result:
            return jsonify(result)
        return jsonify({'error': 'AI generatsiya muvaffaqiyatsiz'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== TELEGRAM WEBHOOK ==========

@api_bp.route('/webhook', methods=['POST'])
@csrf.exempt
def telegram_webhook():
    """Telegram webhook handler"""
    try:
        from bot_service import bot
        import telebot

        secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if secret_token and secret_token != TELEGRAM_WEBHOOK_SECRET:
            return 'Unauthorized', 403

        if bot and request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        else:
            return 'Bot not configured', 400
    except Exception as e:
        print(f"[api] Webhook error: {e}")
        return 'Error', 500


# ========== CRON ROUTES ==========

@api_bp.route('/api/init-db')
def api_init_database():
    """Database jadvallarini tekshirish"""
    if not _has_valid_cron_secret():
        return _cron_secret_error()

    try:
        db.create_all()
        order_count = Order.query.count()
        post_count = Post.query.count()
        return jsonify({
            'status': 'success',
            'message': 'Database jadvallar muvaffaqiyatli yaratildi/yangilandi',
            'tables': {
                'orders': order_count,
                'posts': post_count
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@api_bp.route('/api/cron/status')
def cron_status():
    """Cron vazifalar statusi"""
    try:
        from scheduler import get_scheduled_jobs
        jobs = get_scheduled_jobs()
        return jsonify({
            'status': 'ok',
            'scheduled_jobs': len(jobs),
            'jobs': jobs,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/api/cron/generate', methods=['GET', 'POST'])
def cron_generate_post():
    """Tashqi cron xizmatlari uchun post generatsiya qilish"""
    if not _has_valid_cron_secret():
        return _cron_secret_error()

    topic = request.args.get('topic')
    category = request.args.get('category')

    from scheduler import generate_and_publish_post
    thread = threading.Thread(target=generate_and_publish_post, args=(topic, category))
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Post generation started in background',
        'timestamp': datetime.now().isoformat()
    })


@api_bp.route('/api/cron/keep-alive')
def cron_keep_alive():
    """Serverni uyg'oq saqlash"""
    status_data = {
        'status': 'alive',
        'time': datetime.now().isoformat()
    }
    try:
        from scheduler import get_scheduled_jobs
        jobs = get_scheduled_jobs()
        status_data['scheduler_status'] = 'running' if len(jobs) > 0 else 'stopped'
        status_data['active_jobs_count'] = len(jobs)
    except Exception as e:
        status_data['scheduler_error'] = str(e)

    return jsonify(status_data)


@api_bp.route('/api/cron/debug-generate')
def cron_debug_generate():
    """Sinxron debug endpoint"""
    if not _has_valid_cron_secret():
        return _cron_secret_error()

    import traceback as tb
    result = {'steps': [], 'success': False}

    try:
        result['gemini_api_key_exists'] = bool(GEMINI_API_KEY)
        result['gemini_model'] = GEMINI_MODEL
        if not GEMINI_API_KEY:
            result['error'] = "GEMINI_API_KEY muhit o'zgaruvchisi topilmadi!"
            return jsonify(result), 500

        result['steps'].append('1. Gemini API oddiy test...')
        try:
            from google import genai
            test_client = genai.Client(api_key=GEMINI_API_KEY)
            test_response = test_client.models.generate_content(model=GEMINI_MODEL, contents="Salom, 1+1 nechta?")
            resp_text = (getattr(test_response, "text", "") or "")[:100]
            result['steps'].append(f'✅ Gemini API ishlaydi! Javob: {resp_text}')
            result['gemini_test'] = 'OK'
        except Exception as gemini_err:
            result['steps'].append(f'❌ Gemini API xatosi: {str(gemini_err)}')
            result['gemini_error'] = str(gemini_err)
            return jsonify(result), 500

        result['steps'].append('2. AI post generatsiya boshlanmoqda...')
        from ai_generator import generate_post_for_seo
        from scheduler import TOPICS
        topic = request.args.get('topic') or random.choice(TOPICS)
        result['topic'] = topic

        post_data = generate_post_for_seo(topic)
        if not post_data:
            result['error'] = 'generate_post_for_seo None qaytardi'
            return jsonify(result), 500

        result['steps'].append(f'✅ AI generatsiya muvaffaqiyatli: {post_data.get("title", "?")}')

        from image_fetcher import get_image_for_topic, build_image_prompt
        existing_urls = [
            row[0] for row in db.session.query(Post.image_url)
            .filter(Post.image_url.isnot(None), Post.image_url.contains('images.unsplash.com')).all()
        ]
        image_url = get_image_for_topic(topic, exclude_image_urls=existing_urls)
        image_prompt = build_image_prompt(topic=topic, title=post_data.get('title'), category=request.args.get('category'))

        selected_category = request.args.get('category') or random.choice(CATEGORIES)
        new_post = Post(
            title=post_data['title'],
            content=post_data['content'],
            topic=topic,
            category=selected_category,
            keywords=post_data.get('keywords', ''),
            image_url=image_url,
            image_prompt=image_prompt,
            is_published=True
        )
        new_post.reading_time = new_post.calculate_reading_time()
        db.session.add(new_post)
        db.session.commit()

        new_post.slug = new_post.generate_slug()
        db.session.commit()

        result['steps'].append(f'✅ Bazaga saqlandi: ID={new_post.id}, slug={new_post.slug}')
        result['post_id'] = new_post.id
        result['post_url'] = f'{SITE_URL}/blog/{new_post.slug}'
        result['success'] = True
        return jsonify(result)
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = tb.format_exc()
        return jsonify(result), 500


@api_bp.route('/api/cron/test-ai')
def cron_test_ai():
    """Tezkor Gemini API test"""
    if not _has_valid_cron_secret():
        return _cron_secret_error()

    result = {
        'api_key_exists': bool(GEMINI_API_KEY),
        'model': GEMINI_MODEL,
    }
    if not GEMINI_API_KEY:
        result['error'] = 'GEMINI_API_KEY topilmadi'
        return jsonify(result), 500

    try:
        from google import genai
        test_client = genai.Client(api_key=GEMINI_API_KEY)
        resp = test_client.models.generate_content(model=GEMINI_MODEL, contents="1+1=?")
        result['gemini_status'] = 'OK'
        result['gemini_response'] = (getattr(resp, "text", "") or "")[:200]
    except Exception as e:
        result['gemini_status'] = 'ERROR'
        result['gemini_error'] = str(e)

    try:
        result['db_status'] = 'OK'
        result['total_posts'] = Post.query.count()
    except Exception as e:
        result['db_status'] = 'ERROR'
        result['db_error'] = str(e)

    result['telegram_token_exists'] = bool(TELEGRAM_BOT_TOKEN)
    result['telegram_channel_exists'] = bool(TELEGRAM_CHANNEL_ID)
    return jsonify(result)


@api_bp.route('/api/webhook/facebook-leads', methods=['GET', 'POST'])
def facebook_lead_webhook():
    """
    Meta Instant Lead Forms Webhook.
    Instagram / Facebook ichida to'ldirilgan arizalarni qabul qilib,
    avtomatik bazaga (Order) saqlaydi va Telegramga tezkor xabar beradi.
    """
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        expected_token = os.getenv('FB_LEAD_VERIFY_TOKEN', 'trendoai_lead_secret_2026')
        if mode == 'subscribe' and token == expected_token:
            return challenge or 'OK', 200
        return jsonify({'error': 'Invalid verification token'}), 403

    data = request.get_json(silent=True) or {}
    try:
        from config import FB_CONVERSIONS_API_TOKEN
        import requests
        from telegram_poster import send_admin_alert

        entries = data.get('entry', [])
        for entry in entries:
            changes = entry.get('changes', [])
            for change in changes:
                if change.get('field') == 'leadgen':
                    leadgen_id = change.get('value', {}).get('leadgen_id')
                    form_id = change.get('value', {}).get('form_id')

                    if leadgen_id and FB_CONVERSIONS_API_TOKEN:
                        url = f"https://graph.facebook.com/v19.0/{leadgen_id}?access_token={FB_CONVERSIONS_API_TOKEN}"
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            lead_data = resp.json()
                            field_data = {f.get('name'): f.get('values', [''])[0] for f in lead_data.get('field_data', [])}

                            full_name = field_data.get('full_name') or field_data.get('name') or 'Instagram Mijoz'
                            phone = field_data.get('phone_number') or field_data.get('phone') or 'Kiritilmagan'
                            service_choice = field_data.get('service') or field_data.get('xizmat') or 'Meta Instant Form'

                            order = Order(
                                name=full_name,
                                phone=phone,
                                service='meta_lead_form',
                                service_name=service_choice,
                                message=f"Instagram Instant Form #{form_id} orqali keldi",
                                status='new'
                            )
                            db.session.add(order)
                            db.session.commit()

                            time_str = datetime.now().strftime('%d.%m.%Y %H:%M')
                            alert_msg = f"""🔥 <b>YANGI INSTAGRAM INSTANT FORM ARIZASI!</b>

👤 <b>Mijoz:</b> {full_name}
📞 <b>Telefon:</b> {phone}
🛠 <b>Xizmat:</b> {service_choice}
📱 <b>Manba:</b> Instagram Lead Form #{form_id}
⏰ <b>Vaqt:</b> {time_str}
"""
                            send_admin_alert(alert_msg)
    except Exception as exc:
        current_app.logger.warning("Facebook Lead Webhook error: %s", exc)

    return jsonify({'status': 'received'}), 200
