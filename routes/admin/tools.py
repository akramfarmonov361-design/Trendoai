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
                'title': "Restoran Voice AI Delivery - Aqlli Ovozli Buyurtma Tizimi",
                'client_name': "Safir Restaurant & FastFood",
                'description': "Mijozlarning telefon qo'ng'iroqlarini sun'iy intellekt orqali qabul qilib, ovozni tushunuvchi va buyurtmani avtomatik oshxona va kuryerga yo'naltiruvchi innovatsion tizim.",
                'category': "ai",
                'emoji': "🎙️",
                'technologies': "Python, Gemini Live Audio API, Whisper, FastAPI, Telegram Bot, Click/Payme",
                'image_url': "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?q=80&w=1000&auto=format&fit=crop",
                'features': "Real-vaqt ovozli tushunish,Oshxona printeriga avto-chop,Kuryerlar telegram boti,Manzilni xaritada aniqlash,To'lov chekini yuborish",
                'price': "5,500,000 so'm",
                'problem': "Tushlik va kechki paytlarda kuniga 300+ qo'ng'iroqlar tushib, operatorlar ulgurmay qolar, mijozlar kutishdan norozi bo'lib buyurtmalar bekor bo'lardi.",
                'solution': "Gemini Live Audio asosida ovozli robot o'rnatildi. U mijoz bilan o'zbek tilida erkin suhbatlashib, taomlar va manzilni xatosiz qayd etadi.",
                'result': "Qo'ng'iroq yo'qotishlari 0% ga tushdi, buyurtma qabul qilish vaqti 3 barobar tezlashdi, oylik tushum 45% ga o'sdi.",
                'demo_url': "https://t.me/trendoai",
                'gallery_images': "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?q=80&w=1000&auto=format&fit=crop,https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1000&auto=format&fit=crop",
                'meta_description': "Restoranlar uchun sun'iy intellektli ovozli buyurtma va yetkazib berish tizimi.",
                'meta_keywords': "restoran bot, ovozli ai, voice ai delivery, telegram bot fastfood, dostavka avtomatizatsiya"
            },
            {
                'title': "AI-News - Avtomatlashtirilgan IT va AI Yangiliklari Portali",
                'client_name': "AI Tech Media Group",
                'description': "Dunyo bo'ylab eng so'nggi sun'iy intellekt yangiliklarini real-vaqtda tahlil qilib, o'zbek tilida professional SEO maqolalar tayyorlovchi aqlli axborot portali.",
                'category': "web",
                'emoji': "📰",
                'technologies': "Flask, Gemini 3.7 Flash, RSS Crawlers, IndexNow API, PWA, Tailwind-grade CSS",
                'image_url': "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=1000&auto=format&fit=crop",
                'features': "Avtomatik kontent generatsiya,Google IndexNow tezkor indeks,Telegram kanalga avto-post,Ko'p tilli arxitektura",
                'price': "6,000,000 so'm",
                'problem': "Kunlik 50+ xorijiy texnologik yangiliklarni qo'lda qidirish, tarjima qilish va tahrirlash juda katta inson resursi va vaqt talab qilardi.",
                'solution': "Google Search Grounding va Gemini 3.7 modeli bilan integratsiyalashgan, to'liq avtonom media boshqaruv platformasi qurildi.",
                'result': "Oylik organik o'quvchilar soni 40,000+ ga yetdi, kontent ishlab chiqarish vaqti 90% ga qisqardi.",
                'demo_url': "https://trendoai.uz/blog",
                'gallery_images': "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=1000&auto=format&fit=crop,https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1000&auto=format&fit=crop",
                'meta_description': "Avtomatlashtirilgan sun'iy intellekt yangiliklar portali va media platformasi.",
                'meta_keywords': "ai yangiliklar, avtomatik yangiliklar sayti, media platforma, seo portal"
            },
            {
                'title': "PaketShop - B2B va B2C Qadoqlash Mahsulotlari E-Commerce Do'koni",
                'client_name': "PaketShop O'zbekiston",
                'description': "Qadoqlash mahsulotlari ulgurji va chakana savdosi uchun mo'ljallangan, Telegram Mini App va Web platformani birlashtirgan zamonaviy internet do'kon.",
                'category': "web",
                'emoji': "🛍️",
                'technologies': "Flask/Next.js, Telegram Mini App, Payme/Click, PostgreSQL, Warehouse Sync",
                'image_url': "https://images.unsplash.com/photo-1472851294608-062f824d29cc?q=80&w=1000&auto=format&fit=crop",
                'features': "Telegram Mini App do'kon,Savat va Click/Payme to'lov,Ombor qoldiqlari sinxroni,B2B ulgurji narxlar,Kassa hisoboti",
                'price': "7,500,000 so'm",
                'problem': "Katalog mahsulotlarining qoldiqlari va narxlarini doimiy telefon orqali tushuntirish va buyurtmalarni daftarga yozish xatoliklarga sabab bo'lardi.",
                'solution': "Veb-sayt va Telegram Mini App orqali real vaqtda ombor qoldiqlari ko'rinuvchi, avtomatik hisob-faktura chiqaruvchi e-commerce tizim ishga tushirildi.",
                'result': "B2B ulgurji buyurtmalar 2.5 barobarga o'sdi, doimiy mijozlarning qayta xaridlari 65% ga yetdi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "https://images.unsplash.com/photo-1472851294608-062f824d29cc?q=80&w=1000&auto=format&fit=crop,https://images.unsplash.com/photo-1556742049-0a67e5572293?q=80&w=1000&auto=format&fit=crop",
                'meta_description': "Zamonaviy B2B va B2C e-commerce internet do'kon va Telegram Mini App.",
                'meta_keywords': "internet do'kon yaratish, e-commerce uzbekistan, telegram mini app do'kon, b2b savdo"
            },
            {
                'title': "Company Contact Finder - B2B Lidlar va Kontaktlar Qidiruv Tizimi",
                'client_name': "LeadGen Analytics Solutions",
                'description': "Tadbirkorlar va korxonalar uchun maqsadli B2B mijozlar bazasini, ularning telefon va manzillarini avtomatik yig'ib beruvchi aqlli tahlil dasturi.",
                'category': "ai",
                'emoji': "🔍",
                'technologies': "Python, Async Scraping, AI Data Extractor, CRM Export, FastAPI",
                'image_url': "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1000&auto=format&fit=crop",
                'features': "Avtomatik B2B qidiruv,Telefon va email filtrlash,Excel/CRM ga eksport,Duplikatlarni tozalash,AI orqali saralash",
                'price': "4,500,000 so'm",
                'problem': "Sotuv menejerlari yangi kompaniyalar kontaktlarini qo'lda qidirishga kuniga 4-5 soat vaqt sarflar, natijada kam qo'ng'iroq amalga oshirilar edi.",
                'solution': "Ochiq reestrlar va xaritalardan avtomatik ravishda korxonalar telefon, email va faoliyat turini aniqlovchi aqlli parser tizimi ishlab chiqildi.",
                'result': "Har kuni 1,000+ toza B2B kontaktlar avtomatik yig'iladi, sotuvchilarning yangi shartnomalar tuzish ko'rsatkichi 400% ga oshdi.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1000&auto=format&fit=crop",
                'meta_description': "B2B mijozlar bazasini yig'ish va sotuv bo'limini avtomatlashtirish tizimi.",
                'meta_keywords': "lead generation, b2b mijozlar, kontaktlar bazasi, sotuvni avtomatlashtirish"
            },
            {
                'title': "Biznes-Xabar - Iqtisodiyot va Tadbirkorlik Tahliliy Portali",
                'client_name': "Biznes Xabar Media Group",
                'description': "O'zbekiston va jahon biznes yangiliklari, bozor tahlillari va qonunchilikdagi o'zgarishlarni tezkor yoritib boruvchi yuqori tezlikdagi axborot platformasi.",
                'category': "web",
                'emoji': "📊",
                'technologies': "Flask, Core Web Vitals 98+, Dynamic XML Feed, Telegram Channel Bot, PWA",
                'image_url': "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1000&auto=format&fit=crop",
                'features': "Google PageSpeed 98+,Telegram kanal integratsiyasi,Reklama bannerlari moduli,Smart Search tizimi",
                'price': "5,000,000 so'm",
                'problem': "Katta yuklama vaqtida server sekinlashishi va yangiliklarni Telegram kanal bilan saytga bir vaqtda joylashdagi noqulayliklar.",
                'solution': "Ultra-tezkor kesh arxitekturasi va har bir yangilikni 1 bosishda sayt, Telegram kanal hamda ijtimoiy tarmoqlarga avto-ulashuvchi panel qurildi.",
                'result': "Telegram kanaldagi auditoriya 25,000+ ga oshdi, maqolalarning Google qidiruvidagi o'rni 1-sahifaga chiqdi.",
                'demo_url': "https://trendoai.uz/blog",
                'gallery_images': "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1000&auto=format&fit=crop",
                'meta_description': "Iqtisodiy tahlil va biznes yangiliklari axborot portali.",
                'meta_keywords': "biznes yangiliklar, iqtisodiy portal, media sayt yaratish, telegram xabar boti"
            },
            {
                'title': "TrendoAI - IT Agentlik va Avtomatizatsiya Platformasi",
                'client_name': "TrendoAI Digital",
                'description': "Zamonaviy 'Show, don't tell' konsepsiyasiga asoslangan web platforma. Tizimda o'rnatilgan AI assistent to'g'ridan-to'g'ri chatbot rejimida mijozlarga konsultatsiya beradi va lidlarni yig'ishga yordam beradi.",
                'category': "web",
                'emoji': "🌐",
                'technologies': "Flask, Tailwind-grade CSS, Gemini AI, PostgreSQL, Redis, PWA",
                'image_url': "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1000&auto=format&fit=crop",
                'features': "SEO optimizatsiya,Jonli AI yordamchi,Dark/Light rejim,Interaktiv narx kalkulyatori,Telegram Mini App",
                'price': "6,000,000 so'm",
                'problem': "An'anaviy statik veb-saytlar mijozlar bilan muloqotga kirmasdi va tashrif buyuruvchilarning 90% dan ko'prog'i ariza qoldirmasdan chiqib ketardi.",
                'solution': "O'zbek tilida erkin so'zlashuvchi AI Chatbot va interaktiv narx kalkulyatori o'rnatildi, sayt PWA va Telegram Mini App ko'rinishida barcha qurilmalarga moslashtirildi.",
                'result': "Sayt konversiyasi 4.2 barobar oshdi, har kuni 15+ yangi qiziqqan mijozlar (leads) avtomatik tarzda CRM tizimiga tushmoqda.",
                'demo_url': "https://trendoai.uz",
                'gallery_images': "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1000&auto=format&fit=crop,https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1000&auto=format&fit=crop",
                'meta_description': "Zamonaviy IT va marketing agentliklari uchun biznes vizitka va xizmatlar sayti.",
                'meta_keywords': "it agentlik sayti, landing page yaratish, biznes web sayt, korporativ sayt"
            }
        ]
        created_count = 0
        for item_data in items:
            existing = Portfolio.query.filter_by(title=item_data['title']).first()
            if existing:
                existing.client_name = item_data.get('client_name')
                existing.problem = item_data.get('problem')
                existing.solution = item_data.get('solution')
                existing.result = item_data.get('result')
                existing.demo_url = item_data.get('demo_url')
                existing.gallery_images = item_data.get('gallery_images')
                db.session.commit()
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
        return f"✅ Portfolio loyihalari va Case Studylar muvaffaqiyatli yangilandi! <a href='/portfolio'>Portfolioga o'tish</a>"
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
