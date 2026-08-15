"""
TrendoAI Web / Public sahifalar va SEO marshrutlari.
"""
from datetime import datetime
import re
import threading
import time
import xml.dom.minidom
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.sax.saxutils import escape as xml_escape

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
import markdown2

from config import (
    POSTS_PER_PAGE,
    SITE_DESCRIPTION,
    SITE_NAME,
    SITE_URL,
)
from extensions import db
from models.order import Order
from models.portfolio import Portfolio
from models.post import Post
from models.service import Service
from services.cache_service import cache_get, cache_set

web_bp = Blueprint('web', __name__)

PUBLIC_SERVICE_PRICING = {
    'telegram_bot': {'min_display': '300,000', 'max_display': "3,000,000 so'm"},
    'web_site': {'min_display': '500,000', 'max_display': "3,000,000 so'm"},
    'ai_chatbot': {'min_display': '1,000,000', 'max_display': "5,000,000 so'm"},
    'target_ads': {'min_display': '600,000', 'max_display': "1,000,000 so'm"},
}

SERVICES_DATA = {
    'ai_content': {
        'key': 'ai_content',
        'title': 'AI Kontent Generatsiya',
        'icon': '🤖',
        'description': "Sun'iy intellekt yordamida SEO-optimallashtirilgan blog maqolalari va marketing kontentlari.",
        'features': [
            'Avtomatik blog postlar va maqolalar',
            'SEO kalit so\'zlar tahlili va integratsiyasi',
            'Telegram kanallarga avtomatik yuborish',
            'Ko\'p tilli kontent yaratish (Uz, Ru, En)'
        ],
        'price': '500,000 so\'m/oy dan',
        'full_description': "TrendoAI taklif etayotgan AI Kontent Generatsiya xizmati sizning biznesingiz uchun avtomatik, sifatli va SEO-optimallashtirilgan kontent yaratishga yordam beradi. Bizning tizim Google-ning eng so'nggi Gemini AI texnologiyasi asosida ishlaydi va o'zbek tilidagi eng mukammal, inson tomonidan yozishga o'xshash kontentni taqdim etadi.",
        'meta_desc': "AI yordamida professional blog va marketing kontentlari yaratish. TrendoAI AI-agentlari biznesingiz uchun 24/7 ishlaydi."
    },
    'telegram_bot': {
        'key': 'telegram_bot',
        'title': 'Telegram Botlar',
        'icon': '📱',
        'description': "Biznesingiz uchun murakkab funksional va foydalanuvchilarga qulay Telegram botlar.",
        'features': [
            'Telegram Mini App (Web App) yaratish',
            'To\'lov tizimlari (Click, Payme) integratsiyasi',
            'Boshqaruv paneli (Admin Panel)',
            'Mijozlar bazasi va statistika'
        ],
        'price': "300,000 - 3,000,000 so'm",
        'full_description': "Sizning biznes jarayonlaringizni avtomatlashtirish uchun murakkab va foydali Telegram botlarni ishlab chiqamiz. Savdo botlari, mijozlarni qo'llab-quvvatlash botlari, e-commerce Mini Applar va maxsus tizimlar - barchasini TrendoAI jamoasi taqdim etadi.",
        'meta_desc': "Telegram botlar va Mini Applar ishlab chiqish. Biznesingizni Telegram orqali avtomatlashtiring va savdoni oshiring."
    },
    'web_site': {
        'key': 'web_site',
        'title': 'Web Saytlar',
        'icon': '🌐',
        'description': "Zamonaviy, o'ta tez va SEO-optimallashtirilgan professional veb-saytlar.",
        'features': [
            'Landing Page (Bir sahifali sayt)',
            'Korporativ va brend saytlari',
            'E-commerce (Internet do\'konlar)',
            'Zamonaviy UI/UX va mobil moslashuv'
        ],
        'price': "500,000 - 3,000,000 so'm",
        'full_description': "Biz zamonaviy texnologiyalar (Next.js, React, Flask, Node.js) yordamida har qanday murakkablikdagi veb-saytlarni yaratamiz. Saytlarimiz tezligi, Google qidiruv tizimi uchun to'liq optimalligi va brendingizga mos dizayni bilan ajralib turadi.",
        'meta_desc': "Professional veb-saytlar yaratish. Landing page, korporativ saytlar va internet do'konlar. SEO va mobil adaptiv."
    },
    'ai_chatbot': {
        'key': 'ai_chatbot',
        'title': 'AI Chatbot Yaratish',
        'icon': '🧠',
        'description': "Mijozlaringizga sun'iy intellekt orqali 24/7 xizmat ko'rsatish tizimi.",
        'features': [
            'Intellektual javoblar (LLM asosida)',
            'Mavjud ma\'lumotlar bazasi bilan integratsiya',
            'Telegram, WhatsApp va Sayt uchun yagona bot',
            'Mijozlar bilan insondek muloqot'
        ],
        'price': "1,000,000 - 5,000,000 so'm",
        'full_description': "Mijozlaringiz bilan kechayu-kunduz muloqot qiladigan, ularning savollariga aniq va aqlli javob beradigan AI chatbotlarni yarating. Gemini yoki ChatGPT asosidagi ushbu tizimlar xodimlar xarajatini kamaytiradi va mijozlar talabiga tezkor javob beradi.",
        'meta_desc': "Aqlli AI Chatbotlar va virtual assistentlar yaratish. Biznesingiz uchun sun'iy intellektli mijozlar xizmati."
    },
    'smm': {
        'key': 'smm',
        'title': 'SMM Avtomatlashtirish',
        'icon': '📢',
        'description': "Ijtimoiy tarmoqlar uchun AI agentlar yordamida avtomatik boshqaruv.",
        'features': [
            'Postlarni AI yordamida rejalashtirish',
            'Kreativ rasm va matnlar generatsiyasi',
            'Avtomatik ijtimoiy tarmoq tahlili',
            'Kross-platforma posting (TG, FB, IG)'
        ],
        'price': '800,000 so\'m/oy dan',
        'full_description': "Ijtimoiy tarmoqlardagi faolligingizni aqlli avtomatlashtirish orqali yanada samarali qiling. Bizning AI tizimlarimiz trendlarni kuzatadi, matn yozadi va brendingiz uchun foydali auditoriyani jalb qilishga yordam beradi.",
        'meta_desc': "AI SMM avtomatlashtirish xizmatlari. Kontent yaratish va ijtimoiy tarmoqlarni avtomatik boshqarish."
    },
    'consulting': {
        'key': 'consulting',
        'title': 'IT Konsalting',
        'icon': '💡',
        'description': "Raqamli transformatsiya va sun'iy intellektni joriy qilish bo'yicha maslahatlar.",
        'features': [
            'Biznes jarayonlarni texnik audit qilish',
            'AI texnologiyalarini rejalashtirish',
            'Dasturiy mahsulotlar arxitekturasi',
            'Top-menejment uchun texnik treninglar'
        ],
        'price': '500,000 so\'m/soat dan',
        'full_description': "Sizning g'oyangizni qanday qilib texnologiya orqali amalga oshirish yoki mavjud tizimingizni qanday optimallashtirish bo'yicha professional maslahat beramiz. AI asrida biznesingizni yangi bosqichga olib chiqishda yo'l ko'rsatamiz.",
        'meta_desc': "Professional IT konsalting va AI audit xizmatlari. Biznesingizni raqamli transformatsiya qiling."
    },
    'crm_integration': {
        'key': 'crm_integration',
        'title': 'CRM Integratsiya',
        'icon': '⚙️',
        'description': "Sotuv jarayonlarini avtomatlashtirish va mijozlar bazasini tartibga solish.",
        'features': [
            'AmoCRM / Bitrix24 integratsiyasi',
            'Telegram botdan CRM ga lidlar tushishi',
            'Sotuv voronkalarini avtomatlashtirish',
            'Menejerlar faoliyatini nazorat qilish'
        ],
        'price': '2,000,000 so\'m',
        'discount': {'percent': 30, 'until': '1-aprel'},
        'full_description': "Biznesingizda tartib o'rnating! Buyurtmalarni Excel yoki daftarda emas, zamonaviy CRM tizimlarida yuriting. Biz sizning Telegram botingiz, saytingiz va Instagram sahifangizni yagona CRM bazasiga ulab beramiz. Har bir mijoz nazoratda bo'ladi.",
        'meta_desc': "CRM tizimlarini (AmoCRM, Bitrix24) joriy qilish va integratsiya xizmatlari. Biznes jarayonlarni avtomatlashtirish."
    },
    'voice_ai': {
        'key': 'voice_ai',
        'title': 'AI Ovozli Assistent',
        'icon': '📞',
        'description': "Call-markazlar o'rniga sun'iy intellekt asosidagi aqlli ovozli operatorlar.",
        'features': [
            'Kiruvchi qo\'ng\'iroqlarga javob berish',
            'Mijozlarga avtomatik qo\'ng\'iroq qilish (Cold calling)',
            'Inson ovozidan farq qilmaydigan muloqot',
            '24/7 ish tartibi'
        ],
        'price': '3,000,000 so\'m dan',
        'discount': {'percent': 30, 'until': '1-aprel'},
        'full_description': "Endi katta call-markaz ushlash shart emas. Bizning AI ovozli assistentlarimiz mijozlaringiz bilan xuddi insondek gaplashadi, savollarga javob beradi va buyurtma qabul qiladi. Bu xarajatlarni 70% ga qisqartiradi.",
        'meta_desc': "AI ovozli assistentlar va virtual call-markaz xizmatlari. Sun'iy intellekt orqali mijozlar bilan ovozli muloqot."
    },
    'marketplace_auto': {
        'key': 'marketplace_auto',
        'title': 'Marketpleys Avtomatlashtirish',
        'icon': '🛍️',
        'description': "Uzum va Wildberries da savdo qiluvchilar uchun maxsus botlar va dasturlar.",
        'features': [
            'Tovarlarni avtomatik yuklash',
            'Raqobatchilar narxini kuzatish',
            'Sotuvlar analitikasi (Bot orqali)',
            'Ombor qoldiqlarini boshqarish'
        ],
        'price': '1,500,000 so\'m',
        'discount': {'percent': 30, 'until': '1-aprel'},
        'full_description': "E-tijoratda vaqt bu pul. Uzum Market yoki Wildberries do'koningizni boshqarishni avtomatlashtiring. Bizning yechimlarimiz orqali siz narxlarni tezkor o'zgartirishingiz va kunlik foydani telefoningizdan kuzatib borishingiz mumkin.",
        'meta_desc': "Uzum va Wildberries marketpleyslari uchun avtomatlashtirish xizmatlari. Savdoni oshirish uchun maxsus dasturlar."
    },
    'data_analytics': {
        'key': 'data_analytics',
        'title': 'Data Analitika',
        'icon': '📊',
        'description': "Biznes ko'rsatkichlarini real vaqtda kuzatib borish uchun Dashboardlar.",
        'features': [
            'Sotuv va xarajatlar Dashboardi',
            'Telegram orqali kunlik hisobotlar',
            'Power BI / Google Data Studio integratsiyasi',
            'Marketing samaradorligi tahlili'
        ],
        'price': '2,500,000 so\'m',
        'discount': {'percent': 30, 'until': '1-aprel'},
        'full_description': "Raqamlarga asoslanib qaror qabul qiling. Biz sizning barcha ma'lumotlaringizni (Excel, CRM, 1C) yagona tushunarli Dashboardga yig'ib beramiz. Endi biznesingiz holatini bir qarashda tushunasiz.",
        'meta_desc': "Biznes uchun Data Analitika va Dashboardlar yaratish. Power BI va Google Data Studio xizmatlari."
    },
}

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


@web_bp.route('/blog')
def blog():
    """Blog sahifasi — barcha postlar ro'yxati"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)

    cache_key = f"blog:{page}:{category or ''}"
    is_testing = bool(current_app.config.get('TESTING'))
    cached = cache_get(cache_key, is_testing=is_testing)

    if cached is not None:
        pagination, popular_posts = cached
    else:
        query = Post.query.filter_by(is_published=True)
        if category:
            query = query.filter_by(category=category)

        pagination = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=POSTS_PER_PAGE, error_out=False
        )
        popular_posts = Post.query.filter_by(is_published=True).order_by(
            Post.views.desc()
        ).limit(5).all()

        cache_set(cache_key, (pagination, popular_posts), ttl=60, is_testing=is_testing)

    return render_template('index.html',
                           posts=pagination.items,
                           pagination=pagination,
                           popular_posts=popular_posts)


@web_bp.route('/post/<int:post_id>')
def post(post_id):
    """ID orqali post sahifasi - slug ga redirect"""
    p = Post.query.get_or_404(post_id)
    if p.slug:
        return redirect(url_for('web.post_by_slug', slug=p.slug), code=301)

    p.views = (p.views or 0) + 1
    db.session.commit()

    related_posts = Post.query.filter(
        Post.id != p.id,
        Post.category == p.category,
        Post.is_published == True
    ).order_by(Post.created_at.desc()).limit(3).all()

    return render_template('post.html', post=p, related_posts=related_posts)


@web_bp.route('/blog/<slug>')
def post_by_slug(slug):
    """Slug orqali post sahifasi (SEO-friendly)"""
    p = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
    p.views = (p.views or 0) + 1
    db.session.commit()

    related_posts = Post.query.filter(
        Post.id != p.id,
        Post.category == p.category,
        Post.is_published == True
    ).order_by(Post.created_at.desc()).limit(3).all()

    return render_template('post.html', post=p, related_posts=related_posts)


@web_bp.route('/maxfiylik')
def privacy():
    """Maxfiylik siyosati sahifasi"""
    return render_template('privacy.html')


@web_bp.route('/rss')
def rss_feed():
    """Blog RSS 2.0 feed"""
    posts = Post.query.filter(
        Post.is_published == True,
        Post.slug.isnot(None)
    ).order_by(Post.created_at.desc()).limit(30).all()

    items = []
    for p in posts:
        link = f"{SITE_URL}/blog/{p.slug}"
        plain = re.sub(r'<[^>]+>', '', markdown2.markdown(p.content or ''))
        plain = re.sub(r'\s+', ' ', plain).strip()[:300]
        pub_date = (p.created_at or datetime.utcnow()).strftime('%a, %d %b %Y %H:%M:%S +0000')

        item = (
            "  <item>\n"
            f"    <title>{xml_escape(p.title)}</title>\n"
            f"    <link>{xml_escape(link)}</link>\n"
            f"    <guid isPermaLink=\"true\">{xml_escape(link)}</guid>\n"
            f"    <pubDate>{pub_date}</pubDate>\n"
            f"    <category>{xml_escape(p.category or 'Texnologiya')}</category>\n"
            f"    <description>{xml_escape(plain)}</description>\n"
        )
        if p.image_url:
            item += f"    <enclosure url=\"{xml_escape(p.image_url)}\" type=\"image/jpeg\"/>\n"
        item += "  </item>\n"
        items.append(item)

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '<channel>\n'
        f"  <title>{xml_escape(SITE_NAME)} — Blog</title>\n"
        f"  <link>{SITE_URL}/blog</link>\n"
        f"  <description>{xml_escape(SITE_DESCRIPTION)}</description>\n"
        "  <language>uz</language>\n"
        f"  <atom:link href=\"{SITE_URL}/rss\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        + "".join(items) +
        '</channel>\n'
        '</rss>\n'
    )
    return Response(xml, mimetype='application/rss+xml')


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


@web_bp.route('/tma')
@web_bp.route('/app')
def telegram_mini_app():
    """Telegram Mini App (TMA) interfeysi"""
    return render_template('tma.html')


@web_bp.route('/services')
def services():
    """Legacy xizmatlar URL'ini bosh sahifaga yo'naltirish"""
    return redirect(url_for('web.index'), code=301)


@web_bp.route('/services/<service_key>')
def service_detail(service_key):
    """Xizmat batafsil sahifasi"""
    service = Service.query.filter_by(slug=service_key).first_or_404()

    category_map = {
        'web_site': 'web',
        'telegram_bot': 'bot',
        'smm': 'smm',
        'design': 'design',
        'ai': 'ai'
    }
    cat = category_map.get(service.slug)
    if not cat:
        if 'bot' in service.slug:
            cat = 'bot'
        elif 'ai' in service.slug:
            cat = 'ai'

    related_portfolio = []
    if cat:
        related_portfolio = Portfolio.query.filter_by(category=cat, is_published=True).limit(3).all()

    all_services = Service.query.filter_by(is_active=True).order_by(Service.order.asc()).all()
    pricing = PUBLIC_SERVICE_PRICING.get(service.slug)
    public_price = (
        f"{pricing['min_display']} - {pricing['max_display']}"
        if pricing
        else service.price
    )

    return render_template('service_detail.html',
                           service=service,
                           related_portfolio=related_portfolio,
                           services=all_services,
                           public_price=public_price)


@web_bp.route('/portfolio')
def portfolio():
    """Portfolio sahifasi"""
    page = request.args.get('page', 1, type=int)
    category = (request.args.get('category') or '').strip().lower()
    allowed_categories = {'bot', 'web', 'ai', 'mobile'}

    if category not in allowed_categories:
        category = ''

    cache_key = f"portfolio:{page}:{category}"
    is_testing = bool(current_app.config.get('TESTING'))
    pagination = cache_get(cache_key, is_testing=is_testing)

    if pagination is None:
        query = Portfolio.query.filter_by(is_published=True)
        if category:
            query = query.filter_by(category=category)

        pagination = query.order_by(Portfolio.created_at.desc()).paginate(
            page=page,
            per_page=12,
            error_out=False,
        )
        cache_set(cache_key, pagination, ttl=60, is_testing=is_testing)

    return render_template(
        'portfolio.html',
        portfolios=pagination.items,
        pagination=pagination,
        active_category=category,
    )


@web_bp.route('/portfolio/project/<slug>')
def portfolio_item(slug):
    """Loyiha batafsil sahifasi"""
    item = Portfolio.query.filter_by(slug=slug, is_published=True).first_or_404()
    related_items = Portfolio.query.filter(
        Portfolio.id != item.id,
        Portfolio.category == item.category,
        Portfolio.is_published == True
    ).limit(3).all()

    return render_template('portfolio_detail.html', item=item, related_items=related_items)


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
            print(f"✅ Order #{new_order.id} sent to Admin")
        else:
            print(f"❌ Failed to send Order #{new_order.id} to Admin")
    except Exception as e:
        print(f"Telegram yuborishda xato: {e}")

    flash(f'Rahmat, {name}! Arizangiz qabul qilindi. Tez orada siz bilan boglanamiz!', 'success')
    return redirect(url_for('web.index'), code=303)


# ========== SEO, SITEMAP & FEEDS ==========

@web_bp.route('/robots.txt')
def robots_txt():
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /search",
        "Disallow: /search?",
        "Disallow: /login",
        "Disallow: /logout",
        "Allow: /static/img/",
        "Allow: /static/css/",
        "",
        "User-agent: Googlebot-Image",
        "Allow: /static/img/",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@web_bp.route('/sitemap.xml')
def sitemap_xml():
    today = datetime.now().strftime('%Y-%m-%d')
    latest_post = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).first()
    latest_portfolio = Portfolio.query.filter_by(is_published=True).order_by(Portfolio.created_at.desc()).first()
    candidates = [today]
    if latest_post:
        cand = latest_post.updated_at or latest_post.created_at
        if cand:
            candidates.append(cand.strftime('%Y-%m-%d'))
    if latest_portfolio and latest_portfolio.created_at:
        candidates.append(latest_portfolio.created_at.strftime('%Y-%m-%d'))
    site_lastmod = max(candidates)

    pages = []
    static_pages = [
        ('/', '1.0', 'weekly', site_lastmod),
        ('/portfolio', '0.8', 'weekly', site_lastmod),
        ('/blog', '0.9', 'daily', site_lastmod),
        ('/about', '0.7', 'monthly', '2026-01-01'),
        ('/order', '0.8', 'monthly', '2026-01-01'),
        ('/maxfiylik', '0.3', 'yearly', '2026-07-07'),
    ]
    for url, priority, changefreq, lastmod in static_pages:
        pages.append({
            'loc': f'{SITE_URL}{url}',
            'priority': priority,
            'changefreq': changefreq,
            'lastmod': lastmod,
        })

    services_list = Service.query.filter_by(is_active=True).all()
    for s in services_list:
        pages.append({
            'loc': f'{SITE_URL}/services/{s.slug}',
            'priority': '0.8',
            'changefreq': 'monthly',
            'lastmod': '2026-01-01',
        })

    posts = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).all()
    for p in posts:
        lastmod_dt = p.updated_at or p.created_at
        page_item = {
            'loc': f'{SITE_URL}/blog/{p.slug}' if p.slug else f'{SITE_URL}/post/{p.id}',
            'priority': '0.7',
            'changefreq': 'monthly',
            'lastmod': lastmod_dt.strftime('%Y-%m-%d') if lastmod_dt else today,
        }
        if p.image_url:
            page_item['image'] = {'loc': p.image_url, 'title': p.title}
        pages.append(page_item)

    portfolios = Portfolio.query.filter_by(is_published=True).all()
    for port in portfolios:
        if not port.slug:
            continue
        page_item = {
            'loc': f'{SITE_URL}/portfolio/project/{port.slug}',
            'priority': '0.6',
            'changefreq': 'monthly',
            'lastmod': port.created_at.strftime('%Y-%m-%d') if port.created_at else today,
        }
        if port.image_url:
            page_item['image'] = {'loc': port.image_url, 'title': port.title}
        pages.append(page_item)

    parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    parts.append(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
    )
    for page_item in pages:
        parts.append('  <url>')
        parts.append(f'    <loc>{xml_escape(page_item["loc"])}</loc>')
        parts.append(f'    <lastmod>{page_item["lastmod"]}</lastmod>')
        parts.append(f'    <changefreq>{page_item["changefreq"]}</changefreq>')
        parts.append(f'    <priority>{page_item["priority"]}</priority>')
        img = page_item.get('image')
        if img:
            parts.append('    <image:image>')
            parts.append(f'      <image:loc>{xml_escape(img["loc"])}</image:loc>')
            parts.append(f'      <image:title>{xml_escape(img["title"] or "")}</image:title>')
            parts.append('    </image:image>')
        parts.append('  </url>')
    parts.append('</urlset>')

    return Response('\n'.join(parts), mimetype='application/xml')


@web_bp.route('/feed/facebook.xml')
def facebook_feed():
    """Facebook/Instagram Catalog Feed"""
    rss = Element('rss', {'xmlns:g': 'http://base.google.com/ns/1.0', 'version': '2.0'})
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text = SITE_NAME
    SubElement(channel, 'link').text = SITE_URL
    SubElement(channel, 'description').text = SITE_DESCRIPTION

    services_list = Service.query.filter_by(is_active=True).all()
    for s in services_list:
        item = SubElement(channel, 'item')
        SubElement(item, 'g:id').text = f"service_{s.slug}"
        SubElement(item, 'g:title').text = s.title
        SubElement(item, 'g:description').text = s.full_description or s.description
        SubElement(item, 'g:link').text = f"{SITE_URL}/services/{s.slug}"
        if s.image_url:
            img_link = s.image_url if s.image_url.startswith('http') else f"{SITE_URL}{s.image_url}"
        else:
            img_link = f"{SITE_URL}/static/images/services/{s.slug}.jpg"
        SubElement(item, 'g:image_link').text = img_link
        SubElement(item, 'g:brand').text = "TrendoAI"
        SubElement(item, 'g:condition').text = "new"
        SubElement(item, 'g:availability').text = "in stock"
        raw_price = s.price or '0'
        price_numeric = re.sub(r'[^0-9]', '', raw_price) or "0"
        SubElement(item, 'g:price').text = f"{price_numeric} UZS"
        SubElement(item, 'g:google_product_category').text = "Software > Business & Productivity Software"

    portfolios = Portfolio.query.filter_by(is_published=True).all()
    for p in portfolios:
        item = SubElement(channel, 'item')
        SubElement(item, 'g:id').text = f"portfolio_{p.id}"
        SubElement(item, 'g:title').text = p.title
        SubElement(item, 'g:description').text = p.description
        link = f"{SITE_URL}/portfolio/project/{p.slug}" if p.slug else f"{SITE_URL}/portfolio"
        SubElement(item, 'g:link').text = link
        SubElement(item, 'g:image_link').text = p.image_url or f"{SITE_URL}/static/logo.png"
        SubElement(item, 'g:brand').text = "TrendoAI"
        SubElement(item, 'g:condition').text = "new"
        SubElement(item, 'g:availability').text = "in stock"
        raw_price = getattr(p, 'safe_price', None) or '0'
        price_numeric = re.sub(r'[^0-9]', '', raw_price) or "0"
        SubElement(item, 'g:price').text = f"{price_numeric} UZS"
        SubElement(item, 'g:custom_label_0').text = p.category
        SubElement(item, 'g:google_product_category').text = "Software > Business & Productivity Software"

    xml_str = xml.dom.minidom.parseString(tostring(rss)).toprettyxml(indent="   ")
    return Response(xml_str, mimetype='application/xml')


@web_bp.route('/api/catalog.xml')
def api_catalog_xml():
    """XML Katalog Facebook Ads va Google Merchant uchun"""
    portfolios = Portfolio.query.filter_by(is_published=True).all()
    base_url = SITE_URL

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
    xml += '<channel>\n'
    xml += f'  <title>{SITE_NAME} Portfolios</title>\n'
    xml += f'  <link>{base_url}/portfolio</link>\n'
    xml += f'  <description>{SITE_DESCRIPTION}</description>\n'

    cat_names = {'bot': 'Telegram Botlar', 'web': 'Veb-saytlar', 'ai': 'AI Chatbotlar', 'mobile': 'Ilovalar'}

    for item in portfolios:
        category_name = cat_names.get(item.category, item.category)
        image_url = item.image_url if item.image_url else f'{base_url}/static/favicon.svg'
        item_url = f'{base_url}/portfolio/project/{item.slug}' if item.slug else f'{base_url}/portfolio'

        xml += '  <item>\n'
        xml += f'    <g:id>{item.id}</g:id>\n'
        xml += f'    <title>{xml_escape(item.title)}</title>\n'
        xml += f'    <link>{item_url}</link>\n'
        xml += f'    <description><![CDATA[{item.description}]]></description>\n'
        xml += f'    <g:image_link>{image_url}</g:image_link>\n'
        xml += '    <g:brand>TrendoAI</g:brand>\n'
        xml += '    <g:condition>new</g:condition>\n'
        xml += '    <g:availability>in stock</g:availability>\n'
        xml += '    <g:price>0 UZS</g:price>\n'
        xml += f'    <g:product_type>{category_name}</g:product_type>\n'
        xml += '    <g:google_product_category>Software &gt; Computer Software &gt; Business &amp; Productivity Software</g:google_product_category>\n'

        if item.meta_keywords:
            for keyword in item.meta_keywords.split(',')[:5]:
                xml += f'    <g:custom_label_0>{xml_escape(keyword.strip())}</g:custom_label_0>\n'
        xml += '  </item>\n'

    xml += '</channel>\n'
    xml += '</rss>'
    return Response(xml, mimetype='application/xml')


@web_bp.route('/api/catalog/facebook.xml')
@web_bp.route('/feed/facebook-catalog.xml')
def facebook_catalog_feed():
    """Facebook & Meta Commerce Manager uchun Dynamic Product Catalog Feed"""
    site_url = SITE_URL.rstrip('/')
    site_name = SITE_NAME

    items_xml = []
    services_list = Service.query.filter_by(is_active=True).all()
    if not services_list:
        # Fallback to core SERVICES_DATA
        for key, s in SERVICES_DATA.items():
            item_id = f"service_{key}"
            title = s.get('title', 'IT Xizmat')
            desc = s.get('full_description') or s.get('description') or f"TrendoAI {title} xizmati"
            link = f"{site_url}/services/{key}"
            img = f"{site_url}/static/img/og-image.jpg"
            price_str = "500000 UZS"
            if key == 'telegram_bot':
                price_str = "400000 UZS"
            elif key == 'web_site':
                price_str = "700000 UZS"
            elif key == 'ai_chatbot':
                price_str = "1200000 UZS"
            elif key == 'target_ads':
                price_str = "600000 UZS"

            items_xml.append(f"""    <item>
      <g:id>{xml_escape(item_id)}</g:id>
      <g:title>{xml_escape(title)}</g:title>
      <g:description>{xml_escape(desc)}</g:description>
      <g:link>{xml_escape(link)}</g:link>
      <g:image_link>{xml_escape(img)}</g:image_link>
      <g:brand>{xml_escape(site_name)}</g:brand>
      <g:condition>new</g:condition>
      <g:availability>in stock</g:availability>
      <g:price>{xml_escape(price_str)}</g:price>
      <g:product_type>IT Services</g:product_type>
      <g:custom_label_0>Service</g:custom_label_0>
    </item>""")
    else:
        for s in services_list:
            item_id = f"service_{s.id}"
            title = s.title or "IT Xizmat"
            desc = s.description or s.meta_desc or f"TrendoAI {title} xizmati"
            link = f"{site_url}/services/{s.slug}" if s.slug else f"{site_url}/services"
            img = s.image_url or f"{site_url}/static/img/og-image.jpg"
            if not img.startswith('http'):
                img = f"{site_url}{img if img.startswith('/') else '/' + img}"

            price_val = (s.price or "500000 UZS").strip()
            if not any(curr in price_val.upper() for curr in ('UZS', 'USD', '$', 'SO\'M', 'SOM')):
                price_str = f"{price_val} UZS"
            else:
                price_str = price_val.replace("so'm", "UZS").replace("som", "UZS").replace("$", "USD")

            items_xml.append(f"""    <item>
      <g:id>{xml_escape(item_id)}</g:id>
      <g:title>{xml_escape(title)}</g:title>
      <g:description>{xml_escape(desc)}</g:description>
      <g:link>{xml_escape(link)}</g:link>
      <g:image_link>{xml_escape(img)}</g:image_link>
      <g:brand>{xml_escape(site_name)}</g:brand>
      <g:condition>new</g:condition>
      <g:availability>in stock</g:availability>
      <g:price>{xml_escape(price_str)}</g:price>
      <g:product_type>IT Services</g:product_type>
      <g:custom_label_0>Service</g:custom_label_0>
    </item>""")

    portfolios = Portfolio.query.filter_by(is_published=True).all()
    for p in portfolios:
        item_id = f"portfolio_{p.id}"
        title = p.title or "Portfolio Loyiha"
        desc = p.description or f"TrendoAI tomonidan yaratilgan {title} loyihasi"
        link = f"{site_url}/portfolio/project/{p.slug}" if p.slug else f"{site_url}/portfolio"
        img = p.image_url or f"{site_url}/static/img/og-image.jpg"
        if not img.startswith('http'):
            img = f"{site_url}{img if img.startswith('/') else '/' + img}"

        price_val = (p.price or "1000000 UZS").strip()
        if not any(curr in price_val.upper() for curr in ('UZS', 'USD', '$', 'SO\'M', 'SOM')):
            price_str = f"{price_val} UZS"
        else:
            price_str = price_val.replace("so'm", "UZS").replace("som", "UZS").replace("$", "USD")

        items_xml.append(f"""    <item>
      <g:id>{xml_escape(item_id)}</g:id>
      <g:title>{xml_escape(title)}</g:title>
      <g:description>{xml_escape(desc)}</g:description>
      <g:link>{xml_escape(link)}</g:link>
      <g:image_link>{xml_escape(img)}</g:image_link>
      <g:brand>{xml_escape(site_name)}</g:brand>
      <g:condition>new</g:condition>
      <g:availability>in stock</g:availability>
      <g:price>{xml_escape(price_str)}</g:price>
      <g:product_type>Portfolio Case Study</g:product_type>
      <g:custom_label_0>Portfolio</g:custom_label_0>
    </item>""")

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>{xml_escape(site_name)} Products Catalog</title>
    <link>{xml_escape(site_url)}</link>
    <description>Official Dynamic Product Catalog Feed for Meta Ads</description>
{chr(10).join(items_xml)}
  </channel>
</rss>"""
    return Response(xml_content, mimetype='application/xml')


@web_bp.route('/indexnow-key.txt')
@web_bp.route('/trendoai_indexnow_key_2026.txt')
def indexnow_key_file():
    from seo_indexer import get_indexnow_key
    return Response(get_indexnow_key(), mimetype='text/plain')


@web_bp.route('/google<verification_code>.html')
def google_verification(verification_code):
    return f'google-site-verification: google{verification_code}.html'


@web_bp.route('/yandex_<verification_code>.html')
def yandex_verification(verification_code):
    html_content = f'''<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    </head>
    <body>Verification: {verification_code}</body>
</html>'''
    return Response(html_content, mimetype='text/html')


@web_bp.route('/sw.js')
def service_worker():
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    return response


@web_bp.route('/set-lang/<lang_code>')
def set_language(lang_code):
    """Foydalanuvchi tilini o'zgartirish (uz, ru, en)"""
    from flask import session
    if lang_code in ('uz', 'ru', 'en'):
        session['lang'] = lang_code
    referer = request.referrer or url_for('web.index')
    return redirect(referer)

