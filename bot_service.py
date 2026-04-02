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
Sen haqiqiy inson kabi samimiy, do'stona va professional gaplashassan.
Vazifang: Foydalanuvchilarga texnologiya, AI, dasturlash va TrendoAI xizmatlari haqida yordam berish, shuningdek ularni mijozga aylantirish.
Muloqot tili: O'zbek tili (Lotin yozuvi).

SENING XULQ-ATVORING:
1. Doimo samimiy va iliq munosabatda bo'l — do'stingga gaplashayotgandek.
2. Javoblaringni BATAFSIL va TUSHUNARLI yoz — qisqa emas!
3. Har doim misollar va tushuntirishlar bilan javob ber.
4. Agar dasturlash savoli bo'lsa — kod misoli bilan javob ber.
5. Agar TrendoAI xizmatlari haqida so'rashsa — to'liq ma'lumot ber va buyurtma berishga undovchi chiroyli taklif qil.
6. Suhbatni davom ettirish uchun oxirida savol qo'y yoki taklif ber.
7. Javobni strukturali qil: emoji, raqamlar, punktlar ishlat.
8. Agar foydalanuvchi oddiy savol bersa (masalan, "salom", "nima yangilik") — iliq javob ber va xizmatlarimiz haqida qisqacha eslatib o'tib, "Sizga qanday yordam bera olaman?" deb so'ra.

MIJOZ LEAD QOIDASI (MAXFIY!):
9. Agar suhbat davomida foydalanuvchi o'z ismini VA telefon raqamini (+998...) aytsa, javobingning eng oxirida FAQAT ushbu formatda maxfiy kod qoldir (bu foydalanuvchiga ko'rinmaydi):
   [LEAD: Ism, Nomer, Xizmat]
   Misol: [LEAD: Ali, +998901234567, Web Sayt yaratish]
10. Agar mijoz buyurtma berishga tayyor bo'lsa lekin raqam bermagan bo'lsa — "Raqamingizni qoldirsangiz, mutaxassisimiz 5 daqiqa ichida aloqaga chiqadi!" deb so'ra.

TRENDOAI HAQIDA:
- Kompaniya: TrendoAI — O'zbekistondagi yetakchi IT va AI yechimlari kompaniyasi
- Sayt: trendoai.uz
- Telegram kanal: @TrendoAI
- Bot: @TrendoAibot
- Rahbar: Akbarjon
- Manzil: Toshkent, O'zbekiston

XIZMATLAR VA NARXLAR:
1. 🤖 Telegram Botlar — $100 dan (Oddiy botlar, menyu botlar, to'lov bilan)
2. 🌐 Web Saytlar — $150 dan (Landing page, korporativ sayt, internet do'kon)
3. 🧠 AI Chatbotlar — $200 dan (Sun'iy intellekt bilan ishlaydigan aqlli botlar)
4. 📱 Mini App ishlab chiqish — $300 dan (Telegram ichida to'liq ilova)
5. 📢 SMM va Marketing — $50/oy dan (Kontent, dizayn, reklama)
6. 📊 Data Analitika — $250 dan (Dashboardlar, hisobotlar)
7. 🎓 AI Ta'lim — $100/guruh (Xodimlar uchun AI trening)

MUHIM KONTEKST:
- Eng so'nggi AI modellari: Google Gemini 2.5 Flash, OpenAI GPT-4o, Claude Sonnet 4
- Sen bu yangiliklardan xabardorsan va mijozlarga tushuntira olasan

Esla: Sen sotuvchi ham, maslahatchi ham, do'st hamsan. Javoblar FOYDALI, SAMIMIY va PROFESSIONAL bo'lsin!
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
        user_name = message.from_user.first_name or "do'stim"
        welcome_text = f"""
👋 **Salom, {user_name}!** Men TrendoAI sun'iy intellekt assistentiman.

🧠 **Men bilan xohlagan mavzuda gaplashishingiz mumkin:**
• _"Telegram bot qancha turadi?"_
• _"Menga web sayt kerak"_
• _"Python da loop qanday yoziladi?"_
• _"AI nima va u qanday ishlaydi?"_

✍️ **Shunchaki pastga xabar yozing — men darhol javob beraman!**

⬇️ Yoki quyidagi tugmalardan birini tanlang:
        """
        
        # Create inline keyboard
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        
        # AI Chat button - most prominent
        ai_chat_btn = telebot.types.InlineKeyboardButton(
            text="💬 AI bilan suhbatlashish",
            callback_data="ai_chat_start"
        )
        
        # Services button
        services_btn = telebot.types.InlineKeyboardButton(
            text="📋 Xizmatlar va Narxlar",
            callback_data="services"
        )
        
        # Mini App button
        web_app = telebot.types.WebAppInfo(url="https://trendoai.uz")
        mini_app_btn = telebot.types.InlineKeyboardButton(
            text="🌐 Saytni ochish",
            web_app=web_app
        )
        
        # Contact button
        contact_btn = telebot.types.InlineKeyboardButton(
            text="📞 Bog'lanish",
            callback_data="contact"
        )
        
        # Portfolio
        portfolio_btn = telebot.types.InlineKeyboardButton(
            text="🎯 Loyihalarimiz",
            url="https://trendoai.uz/portfolio"
        )

        markup.add(ai_chat_btn)
        markup.add(services_btn, mini_app_btn)
        markup.add(contact_btn, portfolio_btn)
        
        bot.reply_to(message, welcome_text, reply_markup=markup, parse_mode='Markdown')
        print(f"✅ Bot reply sent to {message.from_user.id}")
    except Exception as e:
        print(f"❌ Bot Handler Error: {e}")
        import traceback
        traceback.print_exc()



# Callback handler for inline buttons
@bot.callback_query_handler(func=lambda call: call.data == "ai_chat_start") if bot else lambda f: f
def callback_ai_chat(call):
    ai_text = """
🧠 **AI Assistent tayyor!**

Men sizga quyidagi mavzularda yordam bera olaman:

💻 **Dasturlash** — Python, JavaScript, va boshqa tillar
🤖 **Sun'iy intellekt** — ChatGPT, Gemini, neyrosetlar
📱 **Loyiha g'oyalari** — Bot, sayt, ilova yaratish
💡 **Biznes maslahat** — Raqamli marketing, SEO, SMM
📚 **Ta'lim** — Yangi texnologiyalarni o'rganish

✍️ **Shunchaki savolingizni yozing!**
_Misol: "Python da bot qanday yoziladi?"_
    """
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, ai_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "services") if bot else lambda f: f
def callback_services(call):
    services_text = """
🚀 **TrendoAI Xizmatlari va Narxlar:**

🤖 **Telegram Botlar** — $100 dan
   _Menyu bot, to'lov bot, sotuv bot_

🌐 **Web Saytlar** — $150 dan
   _Landing page, korporativ sayt, do'kon_

🧠 **AI Chatbotlar** — $200 dan
   _Aqlli assistent, avtomatik javob_

📱 **Mini App** — $300 dan
   _Telegram ichida to'liq ilova_

📢 **SMM Marketing** — $50/oy dan
   _Kontent, dizayn, reklama_

📊 **Data Analitika** — $250 dan
   _Dashboardlar, hisobotlar_

🎓 **AI Ta'lim** — $100/guruh
   _Xodimlar uchun AI trening_

💬 Buyurtma berish uchun shunchaki menga yozing:
_"Menga web sayt kerak, raqamim +998..."_

📞 Bevosita bog'lanish: @Akramjon1984
🌐 Sayt: trendoai.uz
    """
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, services_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "contact") if bot else lambda f: f
def callback_contact(call):
    contact_text = """
📞 **Biz bilan bog'laning:**

👤 **Rahbar:** Akbarjon
📱 **Telegram:** @Akramjon1984
🌐 **Sayt:** trendoai.uz
📧 **Email:** admin@trendoai.uz

💬 Yoki shu yerda menga xabar yozing — men AI assistent sifatida har qanday savolingizga javob beraman!

_Raqamingizni qoldirsangiz, mutaxassisimiz 5 daqiqa ichida aloqaga chiqadi!_
    """
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, contact_text, parse_mode='Markdown')

@bot.message_handler(commands=['services']) if bot else lambda f: f
def send_services(message):
    services_text = """
🚀 **TrendoAI Xizmatlari:**

🤖 Telegram Botlar — $100 dan
🌐 Web Saytlar — $150 dan
🧠 AI Chatbotlar — $200 dan
📱 Mini App — $300 dan
📢 SMM Marketing — $50/oy dan

💬 Buyurtma berish uchun menga "Web sayt kerak" deb yozing.
📞 Yoki @Akramjon1984 ga murojaat qiling.
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
