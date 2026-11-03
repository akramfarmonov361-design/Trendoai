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
            item = db.session.get(MenuItem, item_id)
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
    from services.seo_indexer import ping_search_engines
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
        from models import Post
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
        if created_count:
            try:
                from services.cache_service import cache_delete_prefix
                cache_delete_prefix("blog:")
            except Exception:
                pass
        return f"✅ {created_count} ta SEO maqola muvaffaqiyatli yaratildi! <a href='/blog'>Blogga o'tish</a>"
    except Exception as e:
        return f"Xatolik: {e}"


@admin_bp.route('/admin/seed-portfolio', methods=['POST'])
@login_required
def seed_portfolio():
    """Demo portfoliolarni bazaga qo'shish va Case Studylarni boyitish (Faqat POST)"""
    try:
        from services.seed_portfolio import seed_desktop_portfolios
        created_count, updated_count = seed_desktop_portfolios(return_counts=True)

        # Keshni tozalash (Portfolio + Meta Catalog Feed)
        try:
            from services.cache_service import clear_catalog_cache
            clear_catalog_cache()
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
        try:
            from services.cache_service import clear_catalog_cache
            clear_catalog_cache()
        except Exception:
            pass
        return f"✅ {created_count} ta Xizmat muvaffaqiyatli yaratildi!"
    except Exception as e:
        return f"Xatolik: {e}"
