from flask import redirect, render_template, url_for
from models.service import Service
from models.portfolio import Portfolio
from routes.web._blueprint import web_bp

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
