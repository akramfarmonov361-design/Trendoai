import telebot
import google.generativeai as genai
from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, GEMINI_MODEL, SITE_URL
from datetime import datetime
from flask import request, Blueprint

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# Create bot instance safely
bot = None
if TELEGRAM_BOT_TOKEN:
    try:
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        print("✅ Telegram bot instansiyasi yaratildi.")
    except Exception as e:
        print(f"⚠️ Telegram bot initialization error: {e}")
else:
    print("⚠️ TELEGRAM_BOT_TOKEN topilmadi. Bot xizmatlari o'chirildi.")

# Create Blueprint for webhook
bot_blueprint = Blueprint('bot', __name__)

SYSTEM_PROMPT = """
Sen TrendoAI kompaniyasining professional AI assistentisan.
Isming: TrendoBot.
Vazifang: Foydalanuvchilarga texnologiya, AI, dasturlash va TrendoAI xizmatlari haqida to'liq va tushunarli javoblar berish.
Muloqot tili: O'zbek tili (Lotin yozuvi).

MUHIM QOIDALAR:
1. Javoblaringni BATAFSIL va TUSHUNARLI yoz - qisqa emas!
2. Har doim misollar va tushuntirishlar bilan javob ber.
3. Agar dasturlash savoli bo'lsa - kod misoli bilan javob ber.
4. Agar TrendoAI xizmatlari haqida so'rashsa - to'liq ma'lumot ber.
5. Savol noaniq bo'lsa - aniqlashtirish so'ra.
6. Javobni strukturali qil: raqamlar, punktlar, sarlavhalar ishlat.
7. MIJOZ BUYURTMA BERSA: Agar suhbat davomida foydalanuvchi o'z ismini va telefon raqamini (+998...) qilsa, javobingning eng oxirida FAQAT ushbu formatda maxfiy kod qoldir:
   [LEAD: Ism, Nomer, Xizmat]
   Misol: [LEAD: Ali, +998901234567, Web Sayt yaratish]

TRENDOAI HAQIDA:
- Kompaniya: TrendoAI - O'zbekistondagi texnologiya va AI yechimlari kompaniyasi
- Sayt: trendoai.uz
- Telegram: @TrendoAibot
- Rahbar: Akbarjon

XIZMATLAR VA NARXLAR:
1. Telegram Botlar - $100 dan
2. Web Saytlar - $150 dan
3. AI Chatbotlar - $200 dan
4. Mini App ishlab chiqish - $300 dan
5. SMM va Marketing - $50/oy dan

MUHIM KONTEKST:
- Eng so'nggi AI modellari: Google Gemini 2.5 Flash, OpenAI GPT-4o, Claude 3.5 Sonnet
- Sen bu yangiliklardan xabardorsan

Esla: Javoblar BATAFSIL, TUSHUNARLI va FOYDALI bo'lsin!
"""

def get_ai_response(user_message):
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        dynamic_prompt = f"{SYSTEM_PROMPT}\nBugungi sana: {current_date}"
        
        chat = model.start_chat(history=[
            {"role": "user", "parts": [dynamic_prompt]}
        ])
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        print(f"❌ Gemini AI Error: {e}")
        return "Uzr, hozirda serverda xatolik yuz berdi. Birozdan so'ng urinib ko'ring."

@bot.message_handler(commands=['start', 'help']) if bot else lambda f: f
def send_welcome(message):
    print(f"🤖 Bot Handler: /start or /help triggered by {message.from_user.id}")
    try:
        welcome_text = """
🔥 **Assalomu alaykum!** Men TrendoAI assistentiman.

🤖 **Men sizga yordam bera olaman:**
• Sun'iy intellekt va AI haqida savollar
• Dasturlash va kod yozish
• Web sayt, Telegram bot buyurtma berish
• Texnologiya yangiliklari

📱 **Quyidagi tugmalardan foydalaning:**
🌐 Mini App - Saytni Telegramda oching
📋 Xizmatlar - Narxlar va xizmatlar ro'yxati

💬 Yoki savolingizni yozing, men javob beraman! 🚀
        """
        
        # Create inline keyboard with Mini App button
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        
        # Mini App button
        web_app = telebot.types.WebAppInfo(url="https://trendoai.uz")
        mini_app_btn = telebot.types.InlineKeyboardButton(
            text="🌐 Mini App", 
            web_app=web_app
        )
        
        # Other buttons
        services_btn = telebot.types.InlineKeyboardButton(
            text="📋 Xizmatlar", 
            callback_data="services"
        )
        site_btn = telebot.types.InlineKeyboardButton(
            text="🔗 Saytga o'tish", 
            url="https://trendoai.uz"
        )
        
        markup.add(mini_app_btn)
        markup.add(services_btn, site_btn)
        
        bot.reply_to(message, welcome_text, reply_markup=markup, parse_mode='Markdown')
        print(f"✅ Bot reply sent to {message.from_user.id}")
    except Exception as e:
        print(f"❌ Bot Handler Error: {e}")
        import traceback
        traceback.print_exc()



# Callback handler for inline buttons
@bot.callback_query_handler(func=lambda call: call.data == "services") if bot else lambda f: f
def callback_services(call):
    services_text = """
🚀 **TrendoAI Xizmatlari va Narxlar:**

🔥 **YANGI! 1-fevralgacha 30% CHEGIRMA:**
1. 📞 **AI Ovozli Assistent** - Call-markaz o'rniga
2. ⚙️ **CRM Integratsiya** - Biznes avtomatlashtirish
3. 🛍️ **Marketpleys Botlar** - Uzum/Wildberries uchun
4. 📊 **Data Analitika** - Dashboardlar
5. 🎓 **AI Ta'lim** - Xodimlar uchun trening

💼 **ASOSIY XIZMATLAR:**
6. 📱 **Telegram Botlar** - $100 dan
7. 🌐 **Web Saytlar** - $150 dan
8. 🧠 **AI Chatbotlar** - $200 dan
9. 📢 **SMM Marketing** - $50/oy dan

📞 Bog'lanish: @Akramjon1984
🌐 Batafsil: trendoai.uz/services
    """
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, services_text, parse_mode='Markdown')


@bot.message_handler(commands=['services']) if bot else lambda f: f
def send_services(message):
    services_text = """
🚀 **TrendoAI Xizmatlari:**

1. **Telegram Botlar:** Biznesingiz uchun mukammal botlar.
2. **Web Saytlar:** Zamonaviy va tezkor saytlar.
3. **AI Integratsiya:** Ish jarayonlarini avtomatlashtirish.
4. **SMM Dizayn:** Brendingizni rivojlantirish.

Buyurtma berish uchun saytimizga o'ting: trendoai.uz/services
Yoki menga "Web sayt kerak" deb yozing.
    """
    bot.reply_to(message, services_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True) if bot else lambda f: f
def echo_all(message):
    import re
    from config import TELEGRAM_ADMIN_ID
    
    # 1. Foydalanuvchini bazaga qo'shish yoki yangilash
    try:
        from app import app, db, TelegramUser, Order
        with app.app_context():
            user = TelegramUser.query.filter_by(tg_id=message.from_user.id).first()
            if not user:
                user = TelegramUser(
                    tg_id=message.from_user.id,
                    username=message.from_user.username,
                    full_name=f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
                )
                db.session.add(user)
            else:
                user.last_interaction = db.func.now()
            db.session.commit()
    except Exception as e:
        print(f"User track error: {e}")

    bot.send_chat_action(message.chat.id, 'typing')
    ai_reply = get_ai_response(message.text)
    
    # 2. Lead (Mijoz) ma'lumotlarini ajratib olish
    lead_match = re.search(r'\[LEAD:\s*(.*?),\s*(.*?),\s*(.*?)\]', ai_reply)
    if lead_match:
        name, phone, service = lead_match.groups()
        # Maxfiy kodni foydalanuvchiga bormaydigan javobdan o'chirib tashlaymiz
        ai_reply = ai_reply.replace(lead_match.group(0), "").strip()
        
        try:
            with app.app_context():
                new_order = Order(
                    name=name,
                    phone=phone,
                    service="telegram_bot_lead",
                    service_name=service,
                    message=f"Telegram Chatbot orqali qabul qilindi. Mijoz: @{message.from_user.username or message.from_user.id}"
                )
                db.session.add(new_order)
                db.session.commit()
                
                # Adminga xabar yuborish
                if TELEGRAM_ADMIN_ID:
                    admin_msg = f"🔥 **YANGI MIJOZ (Bot orqali)**\n\n👤 **Ism:** {name}\n📞 **Raqam:** {phone}\n🛠 **Xizmat:** {service}\n💬 **Chatdan usti:** @{message.from_user.username or message.from_user.id}"
                    bot.send_message(TELEGRAM_ADMIN_ID, admin_msg, parse_mode='Markdown')
                    print(f"✅ Lead qabul qilindi va adminga yuborildi: {phone}")
        except Exception as e:
            print(f"Failed to process lead: {e}")
    
    try:
        bot.reply_to(message, ai_reply, parse_mode='Markdown')
    except Exception as e:
        try:
            bot.reply_to(message, ai_reply, parse_mode=None)
        except Exception as e2:
            bot.reply_to(message, "Uzr, xatolik yuz berdi.")

# ========== WEBHOOK SETUP ==========
def setup_webhook(app):
    """Webhook ni sozlash (faqat URL ni Telegramga yuborish)"""
    if not bot:
        print("⚠️ Bot sozlanmagan, webhook o'rnatilmadi.")
        return

    webhook_url = f"{SITE_URL}/webhook"
    
    def _set_hook():
        import time
        time.sleep(1) # Wait for app to fully start
        try:
            # Eski webhook ni o'chirish
            bot.remove_webhook()
            time.sleep(0.5)
            
            # Yangi webhook o'rnatish
            bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook o'rnatildi: {webhook_url}")
        except Exception as e:
            print(f"⚠️ Webhook o'rnatishda xatolik: {e}")

    # Run in background thread
    import threading
    threading.Thread(target=_set_hook, daemon=True).start()
