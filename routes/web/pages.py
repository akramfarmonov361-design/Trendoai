import re
import threading
import time
from datetime import datetime
from flask import current_app, flash, redirect, render_template, request, url_for
from utils.logger import setup_logger
logger = setup_logger("pages")


from extensions import db
from models.order import Order
from models.post import Post
from routes.web._blueprint import web_bp
from routes.web.services_routes import PUBLIC_SERVICE_PRICING
from config import POSTS_PER_PAGE, SITE_URL

ORDER_RATE_LIMIT = 3
ORDER_RATE_WINDOW_SECONDS = 10 * 60
_order_submissions = {}
_order_rate_lock = threading.Lock()

def _client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'

@web_bp.route('/')
def index():
    """Bosh sahifa — xizmatlar sahifasi"""
    return render_template('services.html', pricing=PUBLIC_SERVICE_PRICING)

@web_bp.route('/search')
def search():
    """Qidiruv sahifasi"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)

    if query:
        posts = Post.query.filter(
            Post.is_published == True,
            (Post.title.contains(query) | Post.content.contains(query) | Post.keywords.contains(query))
        ).order_by(Post.created_at.desc()).paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    else:
        posts = None

    return render_template('search.html', posts=posts, query=query)

@web_bp.route('/about')
def about():
    """Biz haqimizda sahifasi"""
    post_count = Post.query.filter_by(is_published=True).count()
    return render_template('about.html', post_count=post_count)

@web_bp.route('/maxfiylik')
@web_bp.route('/privacy')
def privacy():
    """Maxfiylik siyosati sahifasi"""
    return render_template('privacy.html')

@web_bp.route('/shartlar')
@web_bp.route('/terms')
def terms():
    """Foydalanish shartlari va Kafolat sahifasi"""
    return render_template('terms.html')

@web_bp.route('/tma')
@web_bp.route('/app')
def telegram_mini_app():
    """Telegram Mini App (TMA) interfeysi"""
    return render_template('tma.html')

@web_bp.route('/order')
def order_page():
    """Alohida buyurtma sahifasi"""
    return render_template('order.html')

@web_bp.route('/submit-order', methods=['POST'])
def submit_order():
    """Xizmatga yozilish formasi"""
    if (request.form.get('website') or '').strip():
        return redirect(url_for('web.index'), code=303)

    name = (request.form.get('name') or '').strip()
    phone = (request.form.get('phone') or '').strip()
    service = (request.form.get('service') or '').strip()
    budget = (request.form.get('budget') or '').strip()
    message = (request.form.get('message') or '').strip()

    allowed_services = {
        'ai_content', 'telegram_bot', 'web_site', 'consulting',
        'smm', 'ai_chatbot', 'target_ads', 'other',
    }

    if len(name) < 2 or len(name) > 100:
        flash("Ismingizni 2–100 belgi oralig'ida kiriting.", 'error')
        return redirect(request.referrer or url_for('web.order_page'), code=303)
    if not re.fullmatch(r'\+?[0-9\s()\-]{7,20}', phone):
        flash("Telefon raqamini to'g'ri formatda kiriting.", 'error')
        return redirect(request.referrer or url_for('web.order_page'), code=303)
    if service not in allowed_services:
        flash("Xizmat turini tanlang.", 'error')
        return redirect(request.referrer or url_for('web.order_page'), code=303)
    if len(budget) > 50 or len(message) > 2000:
        flash("Byudjet yoki loyiha tavsifi juda uzun.", 'error')
        return redirect(request.referrer or url_for('web.order_page'), code=303)

    ip = _client_ip()
    with _order_rate_lock:
        now = time.time()
        recent_submissions = [
            submitted_at
            for submitted_at in _order_submissions.get(ip, [])
            if now - submitted_at < ORDER_RATE_WINDOW_SECONDS
        ]
        rate_limited = len(recent_submissions) >= ORDER_RATE_LIMIT
        if not rate_limited:
            recent_submissions.append(now)
        _order_submissions[ip] = recent_submissions

    if rate_limited:
        flash("Juda ko'p ariza yuborildi. 10 daqiqadan so'ng qayta urinib ko'ring.", 'error')
        return render_template('order.html'), 429

    service_names = {
        'ai_content': 'AI Kontent Generatsiya',
        'telegram_bot': 'Telegram Bot',
        'web_site': 'Web Sayt',
        'consulting': 'IT Konsalting',
        'smm': 'SMM Avtomatlashtirish',
        'ai_chatbot': 'AI Chatbot',
        'target_ads': 'Target Reklama',
        'other': 'Boshqa xizmat',
    }
    service_name = service_names.get(service, service)

    new_order = Order(
        name=name,
        phone=phone,
        service=service,
        service_name=service_name,
        budget=budget,
        message=message,
        status='new'
    )
    try:
        db.session.add(new_order)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Buyurtmani saqlashda xato: %s", exc)
        flash("Arizani saqlashda vaqtinchalik xato yuz berdi. Iltimos, qayta urinib ko'ring.", 'error')
        return redirect(request.referrer or url_for('web.order_page'), code=303)

    try:
        from telegram_poster import send_to_admin
        budget_text = budget if budget else "Ko'rsatilmagan"
        message_text = message if message else "Yo'q"
        time_text = datetime.now().strftime('%d.%m.%Y %H:%M')

        order_message = f"""
🆕 *Yangi Buyurtma #{new_order.id}*

👤 *Ism:* {name}
📞 *Telefon:* {phone}
🛠️ *Xizmat:* {service_name}
💰 *Byudjet:* {budget_text}

💬 *Xabar:*
{message_text}

📅 *Vaqt:* {time_text}

🔗 Admin panel: /admin/orders
"""
        if send_to_admin(order_message):
            logger.info(f"✅ Order #{new_order.id} sent to Admin")
        else:
            logger.error(f"❌ Failed to send Order #{new_order.id} to Admin")
    except Exception as e:
        logger.info(f"Telegram yuborishda xato: {e}")

    try:
        from services.meta_capi import track_meta_event
        track_meta_event(
            event_name="Lead",
            user_data={"name": name, "phone": phone},
            custom_data={"service_name": service_name, "currency": "UZS", "value": 500000},
            event_source_url=request.referrer or f"{SITE_URL}/order"
        )
    except Exception as e:
        current_app.logger.warning("Meta CAPI Lead event error: %s", e)

    flash(f'Rahmat, {name}! Arizangiz qabul qilindi. Tez orada siz bilan boglanamiz!', 'success')
    return redirect(url_for('web.index'), code=303)

@web_bp.route('/set-lang/<lang_code>')
def set_language(lang_code):
    """Foydalanuvchi tilini o'zgartirish (uz, ru, en)"""
    from flask import session
    if lang_code in ('uz', 'ru', 'en'):
        session['lang'] = lang_code
    referer = request.referrer or url_for('web.index')
    return redirect(referer)
