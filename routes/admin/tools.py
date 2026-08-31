import time
from flask import current_app, flash, redirect, render_template, request, url_for
from extensions import db
from models.bot_models import MenuCategory, MenuItem
from models.portfolio import Portfolio
from models.post import Post
from models.service import Service
from config import SITE_URL
from routes.web import SERVICES_DATA
from routes.admin._blueprint import admin_bp, login_required

# ========== BOT ADMIN ROUTES (Menu) ==========

@admin_bp.route('/admin/menu', methods=['GET', 'POST'])
@login_required
def admin_menu():
    """Menyu boshqaruvi (mahsulotlar va kategoriyalar)"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_category':
            name = request.form.get('name')
            emoji = request.form.get('emoji', '📋')
            new_cat = MenuCategory(name=name, emoji=emoji)
            db.session.add(new_cat)
            db.session.commit()
            flash('Kategoriya qo\'shildi', 'success')

        elif action == 'add_item':
            name = request.form.get('name')
            price = int(request.form.get('price', 0))
            category = request.form.get('category')
            description = request.form.get('description', '')
            emoji = request.form.get('emoji', '🍽')
            new_item = MenuItem(name=name, price=price, category=category, description=description, emoji=emoji)
            db.session.add(new_item)
            db.session.commit()
            flash('Mahsulot qo\'shildi', 'success')

        elif action == 'delete_item':
            item_id = request.form.get('item_id')
            item = MenuItem.query.get(item_id)
            if item:
                db.session.delete(item)
                db.session.commit()
                flash('Mahsulot o\'chirildi', 'success')

        return redirect(url_for('admin.admin_menu'))

    items = MenuItem.query.order_by(MenuItem.category, MenuItem.order_index).all()
    categories = MenuCategory.query.order_by(MenuCategory.order_index).all()
    return render_template('admin/menu_manage.html', items=items, categories=categories)


# ========== SEO PING & MIGRATION / SEED ROUTES ==========

@admin_bp.route('/admin/seo/ping-all', methods=['POST'])
@login_required
def admin_seo_ping_all():
    """Admin panel orqali barcha sahifalarni IndexNow va Google Search Console ga ping berish"""
    from seo_indexer import ping_search_engines
    site_url = current_app.config.get('SITE_URL') or SITE_URL

    urls = [site_url, f"{site_url}/portfolio", f"{site_url}/services", f"{site_url}/about"]
    for p in Portfolio.query.filter_by(is_published=True).all():
        if p.slug:
            urls.append(f"{site_url}/portfolio/project/{p.slug}")

    for p in Post.query.filter_by(is_published=True).all():
        if p.slug:
            urls.append(f"{site_url}/blog/{p.slug}")

    ping_search_engines(urls)
    flash(f"✅ {len(urls)} ta sahifa Google va IndexNow ga tezkor indekslash uchun yuborildi!", "success")
    return redirect(request.referrer or url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/migrate-db')
@login_required
def admin_migrate_db():
    """Bazaga yangi ustunlar qo'shish"""
    results = []
    try:
        try:
            db.session.execute(db.text("ALTER TABLE portfolio ADD COLUMN price VARCHAR(100)"))
            db.session.commit()
            results.append("✅ Portfolio.price ustuni qo'shildi")
        except Exception as e:
            db.session.rollback()
            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                results.append("ℹ️ Portfolio.price ustuni allaqachon mavjud")
            else:
                results.append(f"⚠️ Portfolio.price: {e}")

        try:
            db.create_all()
            results.append("✅ db.create_all() bajarildi")
        except Exception as e:
            results.append(f"⚠️ db.create_all: {e}")

        flash('Baza migratsiyasi yakunlandi: ' + '; '.join(results), 'success')
    except Exception as e:
        flash(f'Migratsiya xatosi: {e}', 'error')

    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/fix-webhook', methods=['POST'])
@login_required
def admin_fix_webhook():
    """Manual webhook setup via browser (Faqat POST)"""
    from bot_service import bot
    webhook_url = f"{SITE_URL}/webhook"
    try:
        if bot:
            from config import TELEGRAM_WEBHOOK_SECRET
            bot.remove_webhook()
            time.sleep(0.5)
            bot.set_webhook(url=webhook_url, secret_token=TELEGRAM_WEBHOOK_SECRET)
            return f"✅ Webhook muvaffaqiyatli o'rnatildi (secret_token bilan): {webhook_url}.", 200
        return "❌ Bot sozlanmagan", 400
    except Exception as e:
        return f"❌ Xatolik: {e}", 500


@admin_bp.route('/admin/seed-menu', methods=['POST'])
@login_required
def seed_menu():
    """Menyuni tozalab haqiqiy xizmatlarni qo'shish (Faqat POST)"""
    try:
        MenuItem.query.delete()
        MenuCategory.query.delete()
        db.session.commit()

        cat_bot = MenuCategory(name="🤖 Telegram Botlar (Do'kon, Katalog)", emoji="🤖", order_index=1)
        cat_web = MenuCategory(name="🌐 Veb-saytlar (Landing, Korporativ)", emoji="🌐", order_index=2)
        cat_ai = MenuCategory(name="🧠 AI Xizmatlar (AI Chatbot)", emoji="🧠", order_index=3)
        cat_target = MenuCategory(name="🎯 Target Reklama", emoji="🎯", order_index=4)

        db.session.add_all([cat_bot, cat_web, cat_ai, cat_target])
        db.session.commit()

        items = [
            MenuItem(name="Telegram Bot (Do'kon yoki Katalog)", price=300000, category=cat_bot.name, emoji="🤖", description="Biznesingiz uchun aynan sizning talabingizdagi mukammal Telegram botlar."),
            MenuItem(name="Veb-sayt (Landing yoki Korporativ)", price=500000, category=cat_web.name, emoji="🌐", description="Mijozlar ishonchini oson qozonish uchun barcha qurilmalarga mos veb-saytlar."),
            MenuItem(name="AI Chatbot", price=1000000, category=cat_ai.name, emoji="💬", description="Mijozlarga sizsiz ham 24/7 javob qaytarish xususiyatiga ega aqlli AI yordamchilari."),
            MenuItem(name="Facebook va Instagram Target Ads", price=600000, category=cat_target.name, emoji="🎯", description="Aniqlik bilan qilingan Target reklamasi – sizning eng ko'p haridor topuvchi qurolingiz.")
        ]
        db.session.add_all(items)
        db.session.commit()
        return "✅ Baza muvaffaqiyatli tozalandi va haqiqiy xizmatlar qo'shildi! <a href='/admin/menu'>Menyu sozlamalariga qaytish</a>"
    except Exception as e:
        return f"Xatolik: {e}"


@admin_bp.route('/admin/seed-blog', methods=['POST'])
@login_required
def seed_blog():
    """SEO maqolalarni bazaga qo'shish (Faqat POST)"""
    try:
        from app import Post  # or from models import Post
        articles = [
            {
                'title': "Telegram Bot Nima va U Biznesingizga Qanday Foyda Keltiradi?",
                'topic': "Telegram Bot",
                'category': "Texnologiya",
                'keywords': "telegram bot, telegram bot yaratish, biznes bot, do'kon bot, O'zbekiston",
                'content': """## Telegram Bot — Biznesingizning 24/7 Xodimi

Hozirgi kunda O'zbekistonda **20 milliondan ortiq** inson Telegram'dan foydalanadi. Bu degani — sizning potensial mijozlaringiz aynan shu yerda. Telegram bot esa ularni sizga olib keluvchi eng samarali vositadir.

### Telegram Bot Nima?
Telegram bot — bu avtomatik ravishda foydalanuvchilar bilan muloqot qiladigan dastur.
📱 **Hoziroq buyurtma bering:** [Bot orqali bog'laning](https://t.me/TrendoAibot)""",
            },
            {
                'title': "2026-yilda Biznesingizga Veb-sayt Kerakmi? Javob: Ha!",
                'topic': "Veb-sayt",
                'category': "Texnologiya",
                'keywords': "veb sayt yaratish, web site, landing page, korporativ sayt, sayt narxi O'zbekiston",
                'content': """## Nima Uchun Har Bir Biznesga Veb-sayt Kerak?
Google'da qidiruv qiluvchi har bir inson — bu sizning potensial mijozingiz.
**Bepul konsultatsiya olish uchun:** [Bog'laning](https://t.me/TrendoAibot)""",
            },
        ]
        created_count = 0
        for article in articles:
            existing = Post.query.filter_by(title=article['title']).first()
            if existing:
                continue
            p = Post(
                title=article['title'],
                content=article['content'],
                topic=article['topic'],
                category=article['category'],
                keywords=article['keywords'],
                is_published=True
            )
            p.reading_time = p.calculate_reading_time()
            db.session.add(p)
            db.session.commit()
            p.slug = p.generate_slug()
            db.session.commit()
            created_count += 1
        return f"✅ {created_count} ta SEO maqola muvaffaqiyatli yaratildi! <a href='/blog'>Blogga o'tish</a>"
    except Exception as e:
        return f"Xatolik: {e}"


@admin_bp.route('/admin/seed-portfolio', methods=['POST'])
@login_required
def seed_portfolio():
    """Demo portfoliolarni bazaga qo'shish va Case Studylarni boyitish (Faqat POST)"""
    try:
        items = [
            {
                'title': "Insta-Dub UZ - Sun'iy Intellekt Video Dublyaj va Ovozlashtirish Platformasi",
                'client_name': "Media Production & Dubbing Studio",
                'description': "Instagram Reels, YouTube va TikTok videolarni o'zbek tiliga avtomatik tarjima qilish, ko'p ovozli professional dublyaj va lab harakatiga sinxronlash tizimi.",
                'category': "ai",
                'emoji': "🎬",
                'technologies': "Python, Whisper AI, ElevenLabs API, MoviePy, Gemini Flash, FastAPI, Telegram Bot",
                'image_url': "/static/img/portfolio/instadubuz.webp",
                'features': "O'zbek tilida tabiiy ovozlar,Speakerlarni alohida ajratish,Avtomatik dinamik subtitrlar,9:16 Reels preview,Tezkor eksport",
                'price': "8,000,000 so'm",
                'problem': "Xorijiy sifatli videolarni o'zbekchalashtirish uchun diktor, tarjimon va montajchi haftalab vaqt sarflar, bitta 1 daqiqali video 50$ ga tushardi.",
                'solution': "Sun'iy intellekt orqali 2 daqiqada videoni matnga o'girib, o'zbek tiliga tarjima qiluvchi va professional ovozda sinxronlashtiruvchi studio dasturi qurildi.",
                'result': "Video ishlab chiqarish vaqti 95% ga qisqardi, 1 ta video tannarxi 0.5$ ga tushdi, auditoriya qamrovi 350,000+ ga yetdi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/instadubuz.webp",
                'meta_description': "Video dublyaj va sun'iy intellektli ovozlashtirish platformasi.",
                'meta_keywords': "ai dublyaj, video tarjima bot, elevenlabs uzbek, ovozlashtirish dasturi"
            },
            {
                'title': "Bolajon English AI - Bolalar Uchun Ingliz Tili Ta'lim Platformasi",
                'client_name': "Kids Smart Education Center",
                'description': "Kichik yoshdagi bolalarga ingliz tilini o'yinlar, suhbatdosh AI qahramonlar va vizual darsliklar orqali qiziqarli o'rgatuvchi interaktiv ta'lim tizimi.",
                'category': "ai",
                'emoji': "👶",
                'technologies': "React/Flask, Gemini Live API, Gamification Engine, WebSpeech, PWA",
                'image_url': "/static/img/portfolio/bolajon-ai-english.webp",
                'features': "AI suhbatdosh ustoz,So'z boyligi o'yinlari,Ovozli talaffuz tekshiruvi,Yulduzchali yutuqlar tizimi,Ota-onalar hisoboti",
                'price': "6,500,000 so'm",
                'problem': "Bolalar an'anaviy zerikarli darslardan tez charchab, ingliz tili to'garaklariga borishni istashmas edi.",
                'solution': "Bolaning qiziqishiga moslashuvchi, quvnoq animatsion AI qahramon bilan jonli muloqot qiluvchi mobil ta'lim platformasi ishlab chiqildi.",
                'result': "O'quvchilarning so'z yodlash tezligi 3 barobar oshdi, 1,200+ bola platformadan doimiy foydalanmoqda.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/bolajon-ai-english.webp",
                'meta_description': "Bolalar uchun aqlli ingliz tili o'rgatuvchi AI platforma.",
                'meta_keywords': "bolalar uchun ingliz tili, kids english ai, talim ilovasi, interaktiv oyinlar"
            },
            {
                'title': "Chatbot Factory AI - Ko'p Platformali Aqlli Botlar Yaratish Tizimi",
                'client_name': "Enterprise Bot Solutions",
                'description': "Telegram, Instagram Direct va WhatsApp tarmoqlari uchun bir vaqtning o'zida korporativ bilimlar bazasiga ulangan professional AI botlarni boshqarish paneli.",
                'category': "bot",
                'emoji': "🤖",
                'technologies': "Python, Meta Graph API, Telegram Bot API, WhatsApp Cloud API, Gemini 3.7, Vector DB",
                'image_url': "/static/img/portfolio/botfactory.webp",
                'features': "Telegram/Instagram/WhatsApp bir joyda,Kompaniya PDF/Excel bazasini o'qish,Operatorga uzatish,Analitika va konversiya,CRM integratsiya",
                'price': "9,000,000 so'm",
                'problem': "Mijozlar 3 xil ijtimoiy tarmoqdan yozishar, 10 nafar operator barcha xabarlarga ulgura olmasdan lidlar yo'qotilar edi.",
                'solution': "Barcha kanallarni yagona aqlli AI konsolga birlashtirib, 90% savollarga insondek aniq javob beruvchi bot platforma joriy qilindi.",
                'result': "Javob berish tezligi 3 soniyaga tushdi, sotuv konversiyasi 42% ga o'sdi, oylik operator xarajatlari 60% ga tejaldi.",
                'demo_url': "https://t.me/TrendoAibot",
                'gallery_images': "/static/img/portfolio/botfactory.webp",
                'meta_description': "Telegram, Instagram va WhatsApp uchun universal AI chatbot platformasi.",
                'meta_keywords': "chatbot factory, telegram bot, instagram direct bot, whatsapp bot ai"
            },
            {
                'title': "Ismlar Ma'nosi - Sun'iy Intellektli Ismlar Qidiruvi va Tahlili Portali",
                'client_name': "Ismlar.uz Media Group",
                'description': "O'zbek, arab, fors va turkiy ismlarning chuqur etimologik ma'nosi, kelib chiqishi va moslik tahlilini taqdim etuvchi zamonaviy ma'lumotlar platformasi.",
                'category': "web",
                'emoji': "📖",
                'technologies': "Flask, Tailwind CSS, Gemini Grounding, Smart Search, Core Web Vitals 99, PWA",
                'image_url': "/static/img/portfolio/ismlar-manosi-ai.webp",
                'features': "10,000+ ismlar bazasi,AI orqali xarakter tahlili,Tezkor qidiruv,Dark/Gold premium dizayn,Sevimlilar ro'yxati",
                'price': "5,000,000 so'm",
                'problem': "Eski ismlar saytlarida reklama ko'pligi, sekin ishlashi va ismlarning to'liq ma'nosi berilmagani foydalanuvchilarni ranjitar edi.",
                'solution': "Zamonaviy minimalist dizaynda, Google qidiruvida 1-o'rinda chiquvchi ultra-tezkor va AI bilan boyitilgan portal yaratildi.",
                'result': "Kunlik tashrif buyuruvchilar soni 15,000+ ga yetdi, o'rtacha saytda qolish vaqti 4 daqiqani tashkil qildi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/ismlar-manosi-ai.webp",
                'meta_description': "O'zbek va jahon ismlari ma'nosi, kelib chiqishi va tahlili.",
                'meta_keywords': "ismlar manosi, ismlar qidiruvi, o'g'il qiz ismlari, ma'noli ismlar"
            },
            {
                'title': "Luxe Core - Premium Kiyim va Aksessuarlar E-Commerce Brend Do'koni",
                'client_name': "Luxe Core Fashion",
                'description': "Zamonaviy premium kiyim brendlari uchun qulay xarid savati, Click/Payme to'lovlari va Telegram xabarnomalari bilan ta'minlangan internet do'kon.",
                'category': "web",
                'emoji': "✨",
                'technologies': "Flask, Tailwind CSS, PostgreSQL, Payme, Click, Telegram Mini App",
                'image_url': "/static/img/portfolio/luxe-core.webp",
                'features': "Premium qora-oltin dizayn,O'lcham va rang tanlash,Onlayn to'lov,Kuryer kuzatuv tizimi,Chegirma promokodlari",
                'price': "7,500,000 so'm",
                'problem': "Instagram orqali kiyim sotishda o'lchamlar va buyurtmalarni direktda yozish orqali qabul qilish juda ko'p vaqt va chalkashlik keltirib chiqarardi.",
                'solution': "Mijoz 1 daqiqada o'lcham tanlab to'lov qila oladigan, avtomatik ombor nazoratiga ega veb-sayt va Mini App ishga tushirildi.",
                'result': "Buyurtmalarni rasmiylashtirish 5 barobar tezlashdi, oylik savdo aylanmasi 2.8 barobarga ko'paydi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/luxe-core.webp",
                'meta_description': "Premium kiyimlar internet do'koni va e-commerce veb sayti.",
                'meta_keywords': "kiyim dukoni sayti, e-commerce uzbekistan, online do'kon yaratish, luxe core"
            },
            {
                'title': "Optombazar.uz - O'zbekistondagi Yirik B2B Ulgurji Savdo Platformasi",
                'client_name': "Optom Bazar Trade Group",
                'description': "Ishlab chiqaruvchilar, importyorlar va do'kon egalarini to'g'ridan-to'g'ri bog'lovchi yirik B2B ulgurji marketplace va boshqaruv tizimi.",
                'category': "web",
                'emoji': "🏢",
                'technologies': "Python/Flask, PostgreSQL, Redis, Elasticsearch, Multi-vendor Engine",
                'image_url': "/static/img/portfolio/optombazar.webp",
                'features': "Multi-vendor platforma,Ulgurji narxlar jadvali,Shartnomalar generatori,Transport va logistika moduli,B2B to'lovlar",
                'price': "12,000,000 so'm",
                'problem': "Viloyatlardagi do'kon egalari Toshkent bozorlariga qatnab tovar olishga haftada 2 kun vaqt va yo'l xarajatlari sarflashardi.",
                'solution': "Barcha ulgurji sotuvchilarni yagona xavfsiz elektron savdo tizimiga jamlovchi B2B portal yo'lga qo'yildi.",
                'result': "Platformada 500+ ishlab chiqaruvchilar ro'yxatdan o'tdi, oylik savdo aylanmasi 3 milliard so'mdan oshdi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/optombazar.webp",
                'meta_description': "B2B ulgurji savdo portali va marketplace platformasi.",
                'meta_keywords': "optom bozor, ulgurji savdo sayti, b2b marketplace uzbekistan, ishlab chiqaruvchilar"
            },
            {
                'title': "Restoran Voice AI Delivery - Aqlli Ovozli Buyurtma Tizimi",
                'client_name': "Safir Restaurant & FastFood",
                'description': "Mijozlarning telefon qo'ng'iroqlarini sun'iy intellekt orqali qabul qilib, ovozni tushunuvchi va buyurtmani avtomatik oshxona va kuryerga yo'naltiruvchi tizim.",
                'category': "ai",
                'emoji': "🎙️",
                'technologies': "Python, Gemini Live Audio API, Whisper, FastAPI, Telegram Bot, Click/Payme",
                'image_url': "/static/img/portfolio/restoran.webp",
                'features': "Real-vaqt ovozli tushunish,Oshxona printeriga avto-chop,Kuryerlar telegram boti,Manzilni xaritada aniqlash,To'lov cheki",
                'price': "5,500,000 so'm",
                'problem': "Tushlik va kechki paytlarda kuniga 300+ qo'ng'iroqlar tushib, operatorlar ulgurmay qolar, mijozlar kutishdan norozi bo'lardi.",
                'solution': "Gemini Live Audio asosida ovozli robot o'rnatildi. U mijoz bilan o'zbek tilida erkin suhbatlashib, taomlar va manzilni xatosiz qayd etadi.",
                'result': "Qo'ng'iroq yo'qotishlari 0% ga tushdi, buyurtma qabul qilish vaqti 3 barobar tezlashdi, oylik tushum 45% ga o'sdi.",
                'demo_url': "https://t.me/trendoai",
                'gallery_images': "/static/img/portfolio/restoran.webp",
                'meta_description': "Restoranlar uchun sun'iy intellektli ovozli buyurtma va yetkazib berish tizimi.",
                'meta_keywords': "restoran bot, ovozli ai, voice ai delivery, telegram bot fastfood, dostavka avtomatizatsiya"
            },
            {
                'title': "Mijoz Topar - B2B Lidlar va Kontaktlar Qidiruv Tizimi",
                'client_name': "LeadGen Analytics Solutions",
                'description': "Tadbirkorlar va korxonalar uchun maqsadli B2B mijozlar bazasini, ularning telefon va manzillarini avtomatik yig'ib beruvchi aqlli tahlil dasturi.",
                'category': "ai",
                'emoji': "🔍",
                'technologies': "Python, Async Scraping, AI Data Extractor, CRM Export, FastAPI",
                'image_url': "/static/img/portfolio/mijoz-topar.webp",
                'features': "Avtomatik B2B qidiruv,Telefon va email filtrlash,Excel/CRM ga eksport,Duplikatlarni tozalash,AI orqali saralash",
                'price': "4,500,000 so'm",
                'problem': "Sotuv menejerlari yangi kompaniyalar kontaktlarini qo'lda qidirishga kuniga 4-5 soat vaqt sarflar edi.",
                'solution': "Ochiq reestrlar va xaritalardan avtomatik ravishda korxonalar telefon, email va faoliyat turini aniqlovchi aqlli parser tizimi ishlab chiqildi.",
                'result': "Har kuni 1,000+ toza B2B kontaktlar avtomatik yig'iladi, yangi shartnomalar tuzish 400% ga oshdi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/mijoz-topar.webp",
                'meta_description': "B2B mijozlar bazasini yig'ish va sotuv bo'limini avtomatlashtirish tizimi.",
                'meta_keywords': "lead generation, b2b mijozlar, kontaktlar bazasi, sotuvni avtomatlashtirish"
            },
            {
                'title': "Text-to-Speech UZ - Matnni Tabiiy Ovozga Aylantirish Platformasi",
                'client_name': "Voice Tech Solutions",
                'description': "ElevenLabs va maxsus AI neyrotarmoqlari yordamida o'zbekcha matnlarni professional diktor ovozida MP3 audio fayllarga aylantiruvchi audio studiya.",
                'category': "ai",
                'emoji': "🔊",
                'technologies': "Python, ElevenLabs API, FFmpeg, Audio Waveform Visualizer, FastAPI",
                'image_url': "/static/img/portfolio/text-ovoz.webp",
                'features': "Erkak va ayol tabiiy ovozlari,O'zbekcha maxsus talaffuz filtri,Tezkor MP3 yuklab olish,Fon musiqasi bilan miks",
                'price': "6,000,000 so'm",
                'problem': "Audio kitoblar, roliklar va reklamalar uchun doimiy diktor yollash qimmat va uzoq vaqt talab qilardi.",
                'solution': "Istalgan matnni 5 soniyada yuqori sifatli jonli diktor darajasida ovozlashtirib beruvchi onlayn platforma yo'lga qo'yildi.",
                'result': "100+ audio kitob va reklama roliklari minimal xarajat bilan ovozlashtirildi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/text-ovoz.webp",
                'meta_description': "O'zbek tilidagi eng sifatli matnni ovozga aylantirish platformasi.",
                'meta_keywords': "text to speech uzbek, ovozlashtirish, audio yaratish, diktor ovozi ai"
            },
            {
                'title': "NovaTech - IT va Raqamli Marketing Agentligi Sayti",
                'client_name': "NovaTech Digital",
                'description': "Zamonaviy IT kompaniyalar va konsalting xizmatlari uchun mijozlarni jalb qiluvchi, portfoliolar va interaktiv kalkulyatorga ega korporativ sayt.",
                'category': "web",
                'emoji': "💻",
                'technologies': "Flask, Tailwind CSS, Animated Canvas, SEO Engine, PWA",
                'image_url': "/static/img/portfolio/novatech.webp",
                'features': "Interaktiv 3D elementlar,Xizmatlar narxi kalkulyatori,Mijozlar fikrlari bloki,Google PageSpeed 98+",
                'price': "5,500,000 so'm",
                'problem': "Oddiy shablon saytlar mijozlarda ishonch uyg'otmas va kompaniyaning texnologik darajasini ko'rsata olmas edi.",
                'solution': "Yuqori darajadagi zamonaviy animatsiyalar va aniq konversiyaga yo'naltirilgan zamonaviy agentlik portali qurildi.",
                'result': "Murojaat qoldiruvchi korporativ mijozlar soni 3 barobar ko'paydi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/novatech.webp",
                'meta_description': "IT va raqamli marketing kompaniyalari uchun zamonaviy veb-sayt.",
                'meta_keywords': "it sayt yaratish, korporativ veb sayt, novatech, web development uzbekistan"
            },
            {
                'title': "Real-Smart AI - Ko'chmas Mulk va Qurilish Tahliliy CRM Tizimi",
                'client_name': "Smart Realty Group",
                'description': "Rieltorlik agentliklari va qurilish kompaniyalari uchun uylar va xaridorlarni sun'iy intellekt orqali moslashtiruvchi zamonaviy CRM tizimi.",
                'category': "ai",
                'emoji': "🏠",
                'technologies': "Python, Flask, PostgreSQL, Telegram Bot, AI Smart Matching, Chart.js",
                'image_url': "/static/img/portfolio/real-smart-ai.webp",
                'features': "Xaridor va kvartiralarni avto-moslash,Telegram orqali yangi uylarni yuborish,Shartnomalar avto-generatsiyasi,Sotuv voronkasi",
                'price': "8,500,000 so'm",
                'problem': "Mijoz talabiga mos kvartirani qidirishga rieltorlar kunlab vaqt sarflar, natijada ko'plab xaridorlar boshqa agentliklarga o'tib ketardi.",
                'solution': "AI yordamida mijoz byudjeti va talabiga mos xonadonlarni soniyalar ichida topuvchi aqlli matching platformasi joriy etildi.",
                'result': "Bitimlar tuzish muddati 14 kundan 4 kunga qisqardi, oylik sotuvlar 70% ga oshdi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/real-smart-ai.webp",
                'meta_description': "Ko'chmas mulk agentliklari uchun sun'iy intellektli CRM va matching tizimi.",
                'meta_keywords': "rieltor crm, ko'chmas mulk boti, uy savdosi, smart realty ai"
            },
            {
                'title': "PaketShop Assistent - Telegram Mini App Do'koni va AI Maslahatchi",
                'client_name': "PaketShop O'zbekiston",
                'description': "Qadoqlash mahsulotlari ulgurji va chakana savdosi uchun Telegram Mini App internet do'koni va mijozlarga mos o'lchamdagi qadoqni tavsiya qiluvchi AI assistent.",
                'category': "bot",
                'emoji': "📦",
                'technologies': "Telegram Mini App, Flask, Payme/Click, PostgreSQL, Warehouse Sync",
                'image_url': "/static/img/portfolio/paketshop-assistent.webp",
                'features': "Telegram Mini App do'kon,Savat va Click/Payme to'lov,Mahsulot o'lchami bo'yicha AI tavsiya,Ombor qoldiqlari sinxroni",
                'price': "7,500,000 so'm",
                'problem': "Mijozlar o'z mahsulotlariga qaysi o'lchamdagi paket yoki quti to'g'ri kelishini bilmay, uzoq vaqt konsultatsiya so'rashardi.",
                'solution': "Mahsulot o'lchamini kiritganda unga mos qadoqlarni avtomatik ko'rsatib, to'lovni Telegram ichida qabul qiluvchi Mini App yaratildi.",
                'result': "Xaridorlarning buyurtma berish jarayoni 2 daqiqaga qisqardi, doimiy xaridorlar 65% ga oshdi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/paketshop-assistent.webp",
                'meta_description': "Telegram Mini App internet do'kon va AI qadoqlash assistenti.",
                'meta_keywords': "telegram mini app do'kon, paket dukoni, e-commerce bot, click payme tolov"
            },
            {
                'title': "TrendoAI - Boshqaruv Portali va AI Agentlik Tizimi",
                'client_name': "TrendoAI Digital",
                'description': "Barcha raqamli xizmatlar, jonli chat assistenti, dinamik narx kalkulyatori va portfolio keyslarini o'zida birlashtirgan rasmiy platforma.",
                'category': "web",
                'emoji': "🌐",
                'technologies': "Flask, Tailwind CSS, Gemini 3.7 Flash, Redis, PostgreSQL, PWA",
                'image_url': "/static/img/portfolio/trendoai-uz.webp",
                'features': "SEO optimizatsiya 100%,Jonli AI maslahatchi,Dark/Light rejim,Interaktiv kalkulyator,Meta & Google Feed",
                'price': "6,000,000 so'm",
                'problem': "Statik veb-saytlar mijozlar bilan muloqotga kirmasdi va tashrif buyuruvchilarning 90% dan ortig'i chiqib ketardi.",
                'solution': "O'zbek tilida erkin so'zlashuvchi AI Chatbot va interaktiv narx kalkulyatori o'rnatilgan zamonaviy platforma ishga tushirildi.",
                'result': "Sayt konversiyasi 4.2 barobar oshdi, har kuni yangi lidlar CRM tizimiga tushmoqda.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/trendoai-uz.webp",
                'meta_description': "Zamonaviy IT va marketing agentliklari uchun biznes vizitka va xizmatlar sayti.",
                'meta_keywords': "it agentlik sayti, landing page yaratish, biznes web sayt, trendoai"
            },
            {
                'title': "Texnomarket - Maishiy Texnika va Elektronika Do'koni Boti",
                'client_name': "Texnomarket Retail",
                'description': "Telefonlar, noutbuklar va maishiy texnika mahsulotlarini bo'lib to'lash (muddatli to'lov) kalkulyatori va yetkazib berish tizimiga ega Telegram do'kon.",
                'category': "bot",
                'emoji': "📱",
                'technologies': "Python, aiogram 3, PostgreSQL, Muddatli to'lov moduli, Click/Payme",
                'image_url': "/static/img/portfolio/texnomarket.webp",
                'features': "Muddatli to'lov kalkulyatori,Kafolat taloni generatsiyasi,Filiallar xaritasi,Kuryer kuzatuvi",
                'price': "5,000,000 so'm",
                'problem': "Xaridorlar muddatli to'lov oylik to'lovlarini hisoblash uchun operatorlarga doimiy qo'ng'iroq qilishardi.",
                'solution': "Mijoz bir zumda muddatli to'lov grafigini ko'rib, buyurtma bera oladigan avtomatlashtirilgan bot ishga tushirildi.",
                'result': "Operatorlar qo'ng'iroq yuki 60% ga kamaydi, bot orqali savdo 35% ga o'sdi.",
                'demo_url': "https://t.me/TrendoAibot",
                'gallery_images': "/static/img/portfolio/texnomarket.webp",
                'meta_description': "Elektronika do'konlari uchun muddatli to'lov kalkulyatoriga ega Telegram bot.",
                'meta_keywords': "texnomarket bot, muddatli tolov boti, elektronika dukoni, telegram magazin"
            },
            {
                'title': "TrendoSpeak - Ko'p Tilli AI Ovozli Sinxronlash Platformasi",
                'client_name': "Global Voice Media",
                'description': "Xalqaro konferensiyalar, vebinarlar va o'quv videolari uchun real-vaqtda ovozni o'zbek, ingliz va rus tillariga professional tarjima qilib beruvchi tizim.",
                'category': "ai",
                'emoji': "🎙️",
                'technologies': "Python, Gemini Live API, Whisper Large v3, WebRTC, FastAPI",
                'image_url': "/static/img/portfolio/trendospeak.webp",
                'features': "Real-vaqt sinxron tarjima,Tabiiy intonatsiya va pauzalar,Ko'p tilli qo'llab-quvvatlash,Shovqindan tozalash",
                'price': "9,500,000 so'm",
                'problem': "Jonli xalqaro tadbirlarda sinxron tarjimonlar xizmati soatiga 200$ dan tushar edi.",
                'solution': "AI neyrotarmoqlar orqali so'zlovchining ovoz tembrini saqlagan holda jonli tarjima qiluvchi dastur joriy qilindi.",
                'result': "Tarjima xarajatlari 85% ga arzonlashdi, ishtirokchilar qoniqishi 98% ni tashkil qildi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/trendospeak.webp",
                'meta_description': "Jonli tadbirlar va videolar uchun ovozli sun'iy intellekt tarjima tizimi.",
                'meta_keywords': "trendospeak, ovozli tarjima ai, sinxron tarjima, voice ai uzbekistan"
            },
            {
                'title': "Uzum Tezkor Yetkazib Berish va Buyurtmalar Integratsiyasi",
                'client_name': "Express Delivery Solutions",
                'description': "Restoranlar va yetkazib berish xizmatlari uchun Uzum Tezkor, Yandex Eats va Express platformalari bilan avtomatik sinxronlanuvchi markaziy POS moduli.",
                'category': "bot",
                'emoji': "🛵",
                'technologies': "Python, FastAPI, Uzum API, Yandex Eats API, Telegram POS Bot",
                'image_url': "/static/img/portfolio/uzum-tezkor.webp",
                'features': "Barcha agregatorlar yagona ekranda,Oshxonaga avto-chop,Kuryer kelish vaqti xabari,Menyu va to'xtash ro'yxati (Stop-list)",
                'price': "6,000,000 so'm",
                'problem': "Har bir yetkazib berish xizmati uchun alohida planshet ishlatilib, taomlar qoldiqlari o'z vaqtida yangilanmasdi.",
                'solution': "Barcha agregatorlarni bitta Telegram bot va oshxona printeriga birlashtiruvchi universal integratsiya yaratildi.",
                'result': "Buyurtma tayyorlash vaqti 8 daqiqaga tezlashdi, oshxonadagi chalkashliklar to'liq bartaraf etildi.",
                'demo_url': "https://t.me/TrendoAibot",
                'gallery_images': "/static/img/portfolio/uzum-tezkor.webp",
                'meta_description': "Uzum Tezkor va Yandex Eats bilan integratsiyalashgan yetkazib berish tizimi.",
                'meta_keywords': "uzum tezkor bot, yandex eats integratsiya, dostavka dasturi, restoran pos"
            },
            {
                'title': "VibeCoding - Zamonaviy IT Kurslari va Kodlash Portali",
                'client_name': "VibeCoding Academy",
                'description': "Sun'iy intellekt, dasturlash va prompt engineering bo'yicha onlayn darslar, interaktiv topshiriqlar va sertifikatlash platformasi.",
                'category': "web",
                'emoji': "👨‍💻",
                'technologies': "Flask, Tailwind CSS, Video Player, Kod Muhiti, Sertifikat Generator",
                'image_url': "/static/img/portfolio/vibecoding.webp",
                'features': "Interaktiv darslar va topshiriqlar,Avtomatik QR kodli sertifikat,Telegram bot orqali uyga vazifa tekshirish,Click/Payme to'lov",
                'price': "7,000,000 so'm",
                'problem': "Onlayn kurslarda o'quvchilarning 80%i topshiriqlarni bajarmay, kursni yarmida tashlab ketishardi.",
                'solution': "AI o'qituvchi uyga vazifalarni darhol tekshirib, xatolarni ko'rsatib beruvchi interaktiv platforma ishlab chiqildi.",
                'result': "Kursni muvaffaqiyatli yakunlash ko'rsatkichi 35% dan 88% ga ko'tarildi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/vibecoding.webp",
                'meta_description': "Dasturlash va IT kurslari uchun zamonaviy ta'lim platformasi.",
                'meta_keywords': "it kurslar, vibecoding, dasturlashni organish, onlayn akademiya"
            },
            {
                'title': "Viral Video Generator AI - Avtomatlashtirilgan Video Ishlab Chiqarish",
                'client_name': "SMM Viral Agency",
                'description': "TikTok va Reels uchun matn va g'oyalardan avtomatik ravishda yuqori ko'rishlar yig'uvchi qiziqarli videolarni ishlab chiqaruvchi AI tizim.",
                'category': "ai",
                'emoji': "🔥",
                'technologies': "Python, OpenCV, Whisper, MoviePy, Gemini Flash, TikTok API",
                'image_url': "/static/img/portfolio/viral-video.webp",
                'features': "Avtomatik skript yozish,Fon videosi va musiqani tanlash,Subtitrlar animatsiyasi,Kuniga 50+ video ishlab chiqarish",
                'price': "8,500,000 so'm",
                'problem': "Kuniga 10 ta sifatli Reels chiqarish uchun 3 ta montajchi va ssenariynavis kerak bo'lib, oylik xarajat 1500$ dan oshar edi.",
                'solution': "Bitta g'oyadan 1 daqiqada 5 xil variantdagi to'liq tayyor Reels yasab beruvchi avtomatlashtirilgan tizim joriy etildi.",
                'result': "Oylik kanallar qamrovi 2 million ko'rishga yetdi, video tannarxi 90% ga arzonlashdi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "/static/img/portfolio/viral-video.webp",
                'meta_description': "Reels va TikTok uchun avtomatik sun'iy intellekt video generatori.",
                'meta_keywords': "viral video ai, reels generator, tiktok avtomatizatsiya, video montaj ai"
            }
        ]
        created_count = 0
        updated_count = 0
        for item_data in items:
            existing = Portfolio.query.filter_by(title=item_data['title']).first()
            if existing:
                existing.client_name = item_data.get('client_name')
                existing.description = item_data.get('description')
                existing.category = item_data.get('category')
                existing.emoji = item_data.get('emoji')
                existing.technologies = item_data.get('technologies')
                existing.image_url = item_data.get('image_url')
                existing.features = item_data.get('features')
                existing.price = item_data.get('price')
                existing.problem = item_data.get('problem')
                existing.solution = item_data.get('solution')
                existing.result = item_data.get('result')
                existing.demo_url = item_data.get('demo_url')
                existing.gallery_images = item_data.get('gallery_images')
                existing.meta_description = item_data.get('meta_description')
                existing.meta_keywords = item_data.get('meta_keywords')
                db.session.commit()
                updated_count += 1
                continue
            item = Portfolio(
                title=item_data['title'],
                client_name=item_data.get('client_name'),
                description=item_data['description'],
                category=item_data['category'],
                emoji=item_data['emoji'],
                technologies=item_data['technologies'],
                image_url=item_data['image_url'],
                features=item_data['features'],
                price=item_data['price'],
                problem=item_data.get('problem'),
                solution=item_data.get('solution'),
                result=item_data.get('result'),
                demo_url=item_data.get('demo_url'),
                gallery_images=item_data.get('gallery_images'),
                meta_description=item_data['meta_description'],
                meta_keywords=item_data['meta_keywords'],
                is_published=True
            )
            db.session.add(item)
            db.session.commit()
            item.slug = item.generate_slug()
            db.session.commit()
            created_count += 1

        # Keshni tozalash
        try:
            from services.cache_service import cache_delete
            for cat in ('', 'bot', 'web', 'ai', 'mobile'):
                for p in range(1, 10):
                    cache_delete(f"portfolio:{p}:{cat}")
        except Exception:
            pass

        return f"✅ Portfolio loyihalari va rasmlari muvaffaqiyatli yangilandi! (Qo'shildi: {created_count}, Yangilandi: {updated_count}) <a href='/portfolio'>Portfolioga o'tish</a>"
    except Exception as e:
        return f"Xatolik: {e}"


@admin_bp.route('/admin/seed-services', methods=['POST'])
@login_required
def seed_services():
    """Xizmatlarni SERVICES_DATA dan bazaga qo'shish (Faqat POST)"""
    try:
        import json
        created_count = 0
        order_idx = 1
        for key, data in SERVICES_DATA.items():
            slug = data.get('key', key)
            existing = Service.query.filter_by(slug=slug).first()
            if existing:
                continue
            service = Service(
                slug=slug,
                title=data.get('title', ''),
                description=data.get('description', ''),
                full_description=data.get('full_description', ''),
                price=data.get('price', ''),
                icon=data.get('icon', ''),
                features=json.dumps(data.get('features', [])),
                meta_desc=data.get('meta_desc', ''),
                is_active=True,
                order=order_idx
            )
            discount = data.get('discount')
            if discount:
                service.discount_percent = discount.get('percent', 0)
                service.discount_until = discount.get('until', '')
            db.session.add(service)
            db.session.commit()
            created_count += 1
            order_idx += 1
        return f"✅ {created_count} ta Xizmat muvaffaqiyatli yaratildi!"
    except Exception as e:
        return f"Xatolik: {e}"
