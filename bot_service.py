import telebot
import json
import re
from datetime import datetime
import time
import google.generativeai as genai
from flask import Blueprint
from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, GEMINI_MODEL, SITE_URL, TELEGRAM_ADMIN_ID
from app import app, db, TelegramUser, Order, MenuItem, MenuCategory, BotOrder

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

bot_blueprint = Blueprint('bot', __name__)

# --- STATE MACHINE ---
user_states = {}
# Structure: { 123456: {'state': 'idle', 'cart': [], 'data': {}, 'last_time': 0} }

def get_user_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = {'state': 'idle', 'cart': [], 'data': {}, 'last_time': 0}
    return user_states[user_id]

def update_user_state(user_id, state):
    if user_id not in user_states:
        user_states[user_id] = {'state': 'idle', 'cart': [], 'data': {}, 'last_time': 0}
    user_states[user_id]['state'] = state

def get_price_range(cat_name):
    if not cat_name: return "Kelishilgan narx"
    cat_name = cat_name.lower()
    if 'bot' in cat_name:
        return "300,000 - 3,000,000 so'm"
    elif 'veb' in cat_name or 'sayt' in cat_name:
        return "500,000 - 3,000,000 so'm"
    elif 'ai' in cat_name:
        return "1,000,000 - 5,000,000 so'm"
    elif 'target' in cat_name:
        return "600,000 - 1,000,000 so'm"
    return "Kelishilgan narx"

# --- GEMINI PROMPT ---
SYSTEM_PROMPT = """
Sen TrendoAI kompaniyasining professional AI assistentisan.
Vazifang: Mijozlarga menyudan xarid qilishda yoki IT xizmatlari bo'yicha maslahat berish.
Agar ular nimadir buyurtma qilmoqchi bo'lishsa, ularga "📋 Menyu" tugmasini bosishni yoki xarid bo'limidan foydalanishni taklif qil.
O'zbek tilida, professional va samimiy javob ber. Emojilar ishlat!
"""

def get_ai_response(user_message):
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        dynamic_prompt = f"{SYSTEM_PROMPT}\nBugungi sana: {current_date}"
        
        chat = model.start_chat(history=[{"role": "user", "parts": [dynamic_prompt]}])
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        print(f"❌ Gemini AI Error: {e}")
        return "Uzr, hozirda serverda xatolik yuz berdi. Birozdan so'ng urinib ko'ring."

# --- KEYBOARDS ---
def get_main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        telebot.types.KeyboardButton("📋 Menyu"),
        telebot.types.KeyboardButton("🛒 Savat"),
        telebot.types.KeyboardButton("💬 AI Assistent"),
        telebot.types.KeyboardButton("📦 Buyurtmalarim")
    )
    return markup

# --- HANDLERS ---
@bot.message_handler(commands=['start', 'help']) if bot else lambda f: f
def send_welcome(message):
    user_id = message.from_user.id
    update_user_state(user_id, 'idle')
    
    # Save user to DB
    try:
        with app.app_context():
            user = TelegramUser.query.filter_by(tg_id=user_id).first()
            if not user:
                user = TelegramUser(
                    tg_id=user_id,
                    username=message.from_user.username,
                    full_name=f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
                )
                db.session.add(user)
            else:
                user.last_interaction = db.func.now()
            db.session.commit()
    except Exception as e:
        print(f"Error saving user: {e}")

    welcome_text = (
        f"👋 **Salom, {message.from_user.first_name}!** TrendoAI botiga xush kelibsiz.\n\n"
        f"🚀 **Bu bot orqali siz nimalar qila olasiz?**\n"
        f"1️⃣ **📋 Menyu:** Bizning xizmatlar yoki mahsulotlarni tanlab, oson buyurtma berasiz.\n"
        f"2️⃣ **💬 AI Assistent:** Assistent (ChatGPT) bilan suhbatlashasiz — u har qanday savolingizga yordam beradi.\n"
        f"3️⃣ **📦 Buyurtmalarim:** O'zingizning xarid va statuslaringizni kuzatasiz.\n\n"
        f"👇 **Pastdagi klaviaturadan tugmalarni tanlang!**"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text == "📋 Menyu") if bot else lambda f: f
def show_categories(message):
    update_user_state(message.from_user.id, 'idle')
    with app.app_context():
        cats = MenuCategory.query.filter_by(is_active=True).order_by(MenuCategory.order_index).all()
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        
        for cat in cats:
            markup.add(telebot.types.InlineKeyboardButton(f"{cat.emoji} {cat.name}", callback_data=f"cat_{cat.id}"))
            
        bot.send_message(message.chat.id, "Kategoriyalardan birini tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🛒 Savat") if bot else lambda f: f
def show_cart(message):
    user_state = get_user_state(message.from_user.id)
    cart = user_state['cart']
    
    if not cart:
        bot.send_message(message.chat.id, "🛒 Savatingiz bo'sh. Marhamat, menyudan mahsulot tanlang.")
        return
        
    total = sum([item['price'] * item['qty'] for item in cart])
    text = "🛒 **Sizning savatingiz:**\n\n"
    for i, item in enumerate(cart):
        p_range = get_price_range(item.get('category', ''))
        text += f"{i+1}. {item['name']} x {item['qty']} ({p_range} oralig'ida)\n"
        
    text += f"\n💰 **Taxminiy minimal jami: {total} so'm**\n*(Aniq narx loyiha murakkabligiga qarab belgilanadi)*"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🗑 Savatni tozalash", callback_data="clear_cart"))
    markup.add(telebot.types.InlineKeyboardButton("✅ Buyurtma berish", callback_data="checkout"))
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📦 Buyurtmalarim") if bot else lambda f: f
def my_orders(message):
    with app.app_context():
        orders = BotOrder.query.filter_by(tg_id=message.from_user.id).order_by(BotOrder.created_at.desc()).limit(5).all()
        if not orders:
            bot.send_message(message.chat.id, "Sizda hozircha buyurtmalar yo'q.")
            return
            
        text = "📦 **So'nggi buyurtmalaringiz:**\n\n"
        for o in orders:
            text += f"🔖 #{o.order_number} — {o.total_amount} so'm\nStatus: {o.status}\n\n"
        bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "💬 AI Assistent") if bot else lambda f: f
def ai_assistant_mode(message):
    update_user_state(message.from_user.id, 'ai_chat')
    bot.send_message(message.chat.id, "🤖 AI Assistent holatiga o'tdingiz. Menga savolingizni yozib qoldiring.")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_')) if bot else lambda f: f
def category_clicked(call):
    cat_id = int(call.data.split('_')[1])
    with app.app_context():
        cat = MenuCategory.query.get(cat_id)
        items = MenuItem.query.filter_by(category=cat.name, is_available=True).order_by(MenuItem.order_index).all()
        
        if not items:
            bot.answer_callback_query(call.id, "Bu kategoriyada mahsulot yo'q.")
            return
            
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for item in items:
            p_range = get_price_range(cat.name)
            markup.add(telebot.types.InlineKeyboardButton(f"{item.emoji} {item.name} - {p_range}", callback_data=f"item_{item.id}"))
            
        bot.edit_message_text(f"📋 **{cat.name}** bo'limi", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('item_')) if bot else lambda f: f
def item_clicked(call):
    item_id = int(call.data.split('_')[1])
    with app.app_context():
        item = MenuItem.query.get(item_id)
        if not item:
            bot.answer_callback_query(call.id, "Mahsulot topilmadi.")
            return
            
        p_range = get_price_range(item.category)
        text = f"{item.emoji} **{item.name}**\n\nNarxi: {p_range}\n"
        if item.description:
            text += f"Ta'rif: {item.description}\n"
            
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("➕ Savatga qo'shish", callback_data=f"add_{item.id}"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 Orqaga", callback_data="menyu_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "menyu_back") if bot else lambda f: f
def menyu_back(call):
    show_categories(call.message)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_')) if bot else lambda f: f
def add_to_cart(call):
    item_id = int(call.data.split('_')[1])
    user_state = get_user_state(call.from_user.id)
    
    with app.app_context():
        item = MenuItem.query.get(item_id)
        if not item:
            bot.answer_callback_query(call.id, "Xatolik.")
            return
            
        # Check if already in cart
        found = False
        for cart_item in user_state['cart']:
            if cart_item['id'] == item.id:
                cart_item['qty'] += 1
                found = True
                break
        
        if not found:
            user_state['cart'].append({
                'id': item.id,
                'name': item.name,
                'price': item.price,
                'category': item.category,
                'qty': 1
            })
            
        bot.answer_callback_query(call.id, f"✅ {item.name} savatga qo'shildi!")

@bot.callback_query_handler(func=lambda call: call.data == "clear_cart") if bot else lambda f: f
def clear_cart(call):
    user_state = get_user_state(call.from_user.id)
    user_state['cart'] = []
    user_state['data'] = {}
    update_user_state(call.from_user.id, 'idle')
    bot.edit_message_text("🗑 Savat tozalandi.", call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Asosiy menyuga qaytdingiz.", reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "checkout") if bot else lambda f: f
def checkout_cart(call):
    user_id = call.from_user.id
    user_state = get_user_state(user_id)
    
    if not user_state['cart']:
        bot.answer_callback_query(call.id, "Savat bo'sh!")
        return
        
    update_user_state(user_id, 'waiting_name')
    bot.send_message(call.message.chat.id, "Iltimos, ism va familiyangizni kiriting:", reply_markup=telebot.types.ReplyKeyboardRemove())

# --- ORDER FLOW STATE HANDLER ---
@bot.message_handler(content_types=['text', 'contact'], func=lambda message: True) if bot else lambda f: f
def handle_all(message):
    user_id = message.from_user.id
    user_state = get_user_state(user_id)
    
    # Rate Limiting (Anti-Spam) Check: Maksimum 1 so'rov har 3 soniyada
    now = time.time()
    if now - user_state.get('last_time', 0) < 3:
        bot.send_message(message.chat.id, "⏳ Iltimos, biroz sekinroq yozing. AI javob tayyorlamoqda...")
        return
    user_state['last_time'] = now
    
    state = user_state['state']
    
    if state == 'waiting_name':
        if not user_state['cart']:
            update_user_state(user_id, 'idle')
            bot.send_message(message.chat.id, "⚠️ Savatingiz bo'sh. Avval menyudan xizmat tanlang.", reply_markup=get_main_menu())
            return
        user_state['data']['name'] = message.text
        update_user_state(user_id, 'waiting_phone')
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
        bot.send_message(message.chat.id, "Telefon raqamingizni kiriting yoki pastdagi tugmani bosing:", reply_markup=markup)
        
    elif state == 'waiting_phone':
        if message.contact:
            user_state['data']['phone'] = message.contact.phone_number
        else:
            user_state['data']['phone'] = message.text
            
        update_user_state(user_id, 'waiting_address')
        bot.send_message(message.chat.id, "Yetkazib berish manzilini kiriting (yoki mo'ljal):", reply_markup=telebot.types.ReplyKeyboardRemove())
        
    elif state == 'waiting_address':
        if not user_state['cart']:
            update_user_state(user_id, 'idle')
            bot.send_message(message.chat.id, "⚠️ Savatingiz bo'sh. Buyurtma bekor qilindi.", reply_markup=get_main_menu())
            return
        user_state['data']['address'] = message.text
        
        # Save order
        cart = user_state['cart']
        total = sum([item['price'] * item['qty'] for item in cart])
        order_num = f"TRD-{datetime.now().strftime('%y%m%d%H%M%S')}"
        
        with app.app_context():
            new_order = BotOrder(
                order_number=order_num,
                tg_id=user_id,
                tg_username=message.from_user.username,
                customer_name=user_state['data']['name'],
                phone=user_state['data']['phone'],
                address=user_state['data']['address'],
                items_json=json.dumps(cart),
                total_amount=total
            )
            db.session.add(new_order)
            db.session.commit()
            
            # Send to Admin
            admin_msg = f"🔥 **YANGI BUYURTMA #{order_num}** (Botdan)\n\n"
            admin_msg += f"👤 Ism: {user_state['data']['name']}\n"
            admin_msg += f"📞 Tel: {user_state['data']['phone']}\n"
            admin_msg += f"📍 Manzil: {user_state['data']['address']}\n\n"
            admin_msg += "🛒 **Savat:**\n"
            for item in cart:
                admin_msg += f" - {item['name']} x {item['qty']}\n"
            admin_msg += f"\n💰 **Jami:** {total} so'm"
            
            if TELEGRAM_ADMIN_ID:
                try:
                    bot.send_message(TELEGRAM_ADMIN_ID, admin_msg)
                except:
                    pass
        
        # Reset state
        user_state['cart'] = []
        user_state['data'] = {}
        update_user_state(user_id, 'idle')
        
        bot.send_message(message.chat.id, f"✅ Buyurtmangiz muvaffaqiyatli qabul qilindi!\nBuyurtma raqami: {order_num}\n\nTez orada siz bilan bog'lanamiz.", reply_markup=get_main_menu())
        
    elif state == 'ai_chat':
        if not message.text:
            bot.send_message(message.chat.id, "Iltimos, menga faqat matnli savol yuboring.")
            return
            
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_ai_response(message.text)
        bot.reply_to(message, ai_reply, parse_mode='Markdown')
        
    else:
        # Default AI Chat Fallback
        if not message.text:
            bot.send_message(message.chat.id, "Iltimos, faqat matn yuboring yoki menyudan kerakli bo'limni tanlang.")
            return
            
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_ai_response(message.text)
        try:
            bot.reply_to(message, ai_reply, parse_mode='Markdown')
        except:
            bot.reply_to(message, ai_reply)


# ========== WEBHOOK SETUP ==========
def setup_webhook(app):
    if not bot:
        return

    webhook_url = f"{SITE_URL}/webhook"
    
    def _set_hook():
        import time
        time.sleep(1)
        try:
            bot.remove_webhook()
            time.sleep(0.5)
            
            from config import CRON_SECRET
            secret = (CRON_SECRET or 'trendoai_super_secret_123')[:256]
            
            bot.set_webhook(url=webhook_url, secret_token=secret)
            print(f"✅ Webhook o'rnatildi: {webhook_url}")
        except Exception as e:
            print(f"⚠️ Webhook error: {e}")

    import threading
    threading.Thread(target=_set_hook, daemon=True).start()
