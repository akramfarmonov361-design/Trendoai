"""
TrendoAI Admin Panel, Kanban CRM va Boshqaruv Marshrutlari.
"""
from functools import wraps
import os
import re
import threading
import time
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    CATEGORIES,
    SITE_URL,
)
from extensions import db
from models.bot_models import MenuCategory, MenuItem
from models.interaction import Lead
from models.order import BotOrder, Order
from models.portfolio import Portfolio
from models.post import Post
from models.service import Service
from routes.web import SERVICES_DATA

admin_bp = Blueprint('admin', __name__)

LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
_failed_logins = {}


def _client_ip():
    """ProxyFix orqali xavfsiz olingan mijoz IP manzili"""
    return request.remote_addr or 'unknown'


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Iltimos, avval tizimga kiring.', 'warning')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def _save_uploaded_image(file_storage, folder='portfolio'):
    """Faylni WebP formatida siqib saqlash (S3/R2 bulutli saqlash yoki static/uploads/ lokal papkasi)."""
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None
    filename = str(file_storage.filename).strip()
    if not filename:
        return None

    import io
    import uuid
    from PIL import Image

    unique_base = uuid.uuid4().hex[:12]
    webp_data = None

    try:
        file_storage.seek(0)
        img = Image.open(file_storage.stream)

        # Convert RGBA / P / LA modes if needed for optimal WebP
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in getattr(img, 'info', {})):
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        # Resize proportionally if width or height > 1600px
        max_dimension = 1600
        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        out_buffer = io.BytesIO()
        img.save(out_buffer, 'WEBP', quality=85, method=6)
        webp_data = out_buffer.getvalue()
        file_name = f"{unique_base}.webp"
        content_type = "image/webp"
    except Exception as e:
        print(f"[upload] Pillow WebP conversion failed: {e}")
        file_storage.seek(0)
        webp_data = file_storage.read()
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'):
            ext = '.jpg'
        file_name = f"{unique_base}{ext}"
        content_type = file_storage.content_type or "image/jpeg"

    # 1. S3 / Cloudflare R2 / Supabase Storage tekshiruvi
    s3_bucket = os.getenv("S3_BUCKET") or os.getenv("R2_BUCKET")
    s3_endpoint = os.getenv("S3_ENDPOINT_URL") or os.getenv("R2_ENDPOINT_URL")
    s3_access_key = os.getenv("S3_ACCESS_KEY_ID") or os.getenv("R2_ACCESS_KEY_ID")
    s3_secret_key = os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("R2_SECRET_ACCESS_KEY")
    public_url_base = os.getenv("STORAGE_PUBLIC_URL") or os.getenv("R2_PUBLIC_URL")

    if s3_bucket and s3_access_key and s3_secret_key:
        try:
            import boto3
            s3_client = boto3.client(
                's3',
                endpoint_url=s3_endpoint,
                aws_access_key_id=s3_access_key,
                aws_secret_access_key=s3_secret_key,
            )
            object_key = f"{folder}/{file_name}"
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=object_key,
                Body=webp_data,
                ContentType=content_type,
            )
            if public_url_base:
                return f"{public_url_base.rstrip('/')}/{object_key}"
            return f"{s3_endpoint.rstrip('/')}/{s3_bucket}/{object_key}"
        except Exception as s3_err:
            print(f"[upload] S3/R2 upload failed, fallback to local storage: {s3_err}")

    # 2. Lokal saqlash (Fallback)
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', folder)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file_name)
    with open(file_path, 'wb') as f:
        f.write(webp_data)

    return f"/static/uploads/{folder}/{file_name}"


# ========== AUTH ROUTES ==========

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login sahifasi"""
    if session.get('logged_in'):
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        ip = _client_ip()
        now = time.time()
        attempts = [t for t in _failed_logins.get(ip, []) if now - t < LOGIN_WINDOW_SECONDS]

        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            _failed_logins[ip] = attempts
            flash("Juda ko'p urinish. 15 daqiqadan so'ng qayta urinib ko'ring.", 'error')
            return render_template('admin/login.html'), 429

        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            _failed_logins.pop(ip, None)
            session['logged_in'] = True
            session['username'] = username
            flash('Tizimga muvaffaqiyatli kirdingiz!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            attempts.append(now)
            _failed_logins[ip] = attempts
            flash('Login yoki parol noto\'g\'ri!', 'error')

    return render_template('admin/login.html')


@admin_bp.route('/admin/logout')
def admin_logout():
    """Chiqish"""
    session.clear()
    flash('Tizimdan chiqdingiz.', 'info')
    return redirect(url_for('web.index'))


@admin_bp.route('/admin')
@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    total_posts = Post.query.count()
    published_posts = Post.query.filter_by(is_published=True).count()
    total_views = db.session.query(db.func.sum(Post.views)).scalar() or 0

    total_orders = Order.query.count()
    new_orders = Order.query.filter_by(status='new').count()
    total_portfolio = Portfolio.query.count()

    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    top_posts = Post.query.filter_by(is_published=True).order_by(Post.views.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_posts=total_posts,
                           published_posts=published_posts,
                           total_views=total_views,
                           total_orders=total_orders,
                           new_orders=new_orders,
                           total_portfolio=total_portfolio,
                           recent_posts=recent_posts,
                           top_posts=top_posts)


# ========== BOT ADMIN ROUTES ==========

@admin_bp.route('/admin/bot-orders')
@login_required
def admin_bot_orders():
    """Bot orqali tushgan menyu buyurtmalarini boshqarish"""
    orders = BotOrder.query.order_by(BotOrder.created_at.desc()).all()
    return render_template('admin/bot_orders.html', orders=orders)


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


# ========== SERVICE ADMIN ROUTES ==========

@admin_bp.route('/admin/services/generate', methods=['POST'])
@login_required
def admin_service_generate():
    """AI yordamida xizmat ma'lumotlarini generatsiya qilish"""
    try:
        from ai_generator import generate_custom_content
        import json

        title = (request.json or {}).get('title', '')
        if not title:
            return jsonify({'error': 'Sarlavha (title) kiritilmagan'}), 400

        prompt = f"""
Sen professional IT xizmatlar uchun kontent yozuvchisan. O'zbek tilida yoz.
Quyidagi xizmat uchun kontent yarat:

Xizmat nomi: {title}

Quyidagi formatda JSON qaytaring (faqat JSON, boshqa matn yo'q):
{{
    "description": "1-2 gaplik jozibali qisqa tavsif (tagline)",
    "full_description": "3-4 gaplik to'liq professional tavsif. Mijozga qanday foyda keltirishini yoz.",
    "features": ["Xususiyat 1", "Xususiyat 2", "Xususiyat 3", "Xususiyat 4"],
    "meta_desc": "SEO uchun 150 belgidan kam meta description",
    "icon": "Mos emoji (bitta)",
    "slug": "english-slug-format"
}}
"""
        text = (generate_custom_content(prompt) or "").strip()
        if not text:
            return jsonify({'error': 'AI generatsiya muvaffaqiyatsiz'}), 500

        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]

        data = json.loads(text)
        return jsonify(data)
    except Exception as e:
        print(f"[admin] AI Service Generation Error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/services')
@login_required
def admin_services():
    """Xizmatlar ro'yxati"""
    services_list = Service.query.order_by(Service.order.asc()).all()
    return render_template('admin/services.html', services=services_list)


@admin_bp.route('/admin/services/new', methods=['GET', 'POST'])
@login_required
def admin_service_new():
    """Yangi xizmat qo'shish"""
    if request.method == 'POST':
        try:
            slug = request.form.get('slug')
            if not slug:
                slug = re.sub(r'[^a-z0-9-]', '', (request.form.get('title') or '').lower().replace(' ', '-'))

            service = Service(
                slug=slug,
                title=request.form.get('title'),
                description=request.form.get('description'),
                full_description=request.form.get('full_description'),
                price=request.form.get('price'),
                icon=request.form.get('icon', '🚀'),
                image_url=request.form.get('image_url'),
                features=request.form.get('features'),
                is_active=request.form.get('is_active') == 'on',
                order=int(request.form.get('order', 0)),
                meta_desc=request.form.get('meta_desc'),
                discount_percent=int(request.form.get('discount_percent', 0)),
                discount_until=request.form.get('discount_until')
            )
            db.session.add(service)
            db.session.commit()
            flash(f'"{service.title}" muvaffaqiyatli qo\'shildi!', 'success')
            return redirect(url_for('admin.admin_services'))
        except Exception as e:
            flash(f'Xatolik: {e}', 'error')

    return render_template('admin/service_form.html', service=None)


@admin_bp.route('/admin/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_service_edit(service_id):
    """Xizmatni tahrirlash"""
    service = Service.query.get_or_404(service_id)

    if request.method == 'POST':
        try:
            service.slug = request.form.get('slug')
            service.title = request.form.get('title')
            service.description = request.form.get('description')
            service.full_description = request.form.get('full_description')
            service.price = request.form.get('price')
            service.icon = request.form.get('icon')
            service.image_url = request.form.get('image_url')
            service.features = request.form.get('features')
            service.is_active = request.form.get('is_active') == 'on'
            service.order = int(request.form.get('order', 0))
            service.meta_desc = request.form.get('meta_desc')
            service.discount_percent = int(request.form.get('discount_percent', 0))
            service.discount_until = request.form.get('discount_until')

            db.session.commit()
            flash(f'"{service.title}" yangilandi!', 'success')
            return redirect(url_for('admin.admin_services'))
        except Exception as e:
            flash(f'Xatolik: {e}', 'error')

    return render_template('admin/service_form.html', service=service)


@admin_bp.route('/admin/services/<int:service_id>/delete', methods=['POST'])
@login_required
def admin_service_delete(service_id):
    """Xizmatni o'chirish"""
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash('Xizmat o\'chirildi!', 'success')
    return redirect(url_for('admin.admin_services'))


# ========== POST ADMIN ROUTES ==========

@admin_bp.route('/admin/posts')
@login_required
def admin_posts():
    """Barcha postlarni boshqarish"""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/posts.html', posts=posts)


@admin_bp.route('/admin/posts/new', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    """Yangi post yaratish"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        topic = request.form.get('topic', 'Umumiy')
        category = request.form.get('category', 'Texnologiya')
        keywords = request.form.get('keywords', '')
        image_url = request.form.get('image_url', '')
        image_prompt = request.form.get('image_prompt', '').strip()
        if not image_prompt:
            try:
                from image_fetcher import build_image_prompt
                image_prompt = build_image_prompt(topic=topic, title=title, category=category)
            except Exception:
                image_prompt = ''
        is_published = request.form.get('is_published') == 'on'

        new_p = Post(
            title=title,
            content=content,
            topic=topic,
            category=category,
            keywords=keywords,
            image_url=image_url,
            image_prompt=image_prompt,
            is_published=is_published
        )
        new_p.reading_time = new_p.calculate_reading_time()

        db.session.add(new_p)
        db.session.commit()

        new_p.slug = new_p.generate_slug()
        db.session.commit()

        if is_published:
            try:
                post_url = url_for('web.post_by_slug', slug=new_p.slug, _external=True)
                from telegram_poster import send_photo_to_channel, send_to_telegram_channel
                from services.push_service import notify_all_subscribers

                tg_message = f"""📝 *Yangi Maqola!*

*{title}*

🏷 Kategoriya: {category}
⏱ O'qish uchun tayyor

🔗 [Maqolani o'qish]({post_url})

#TrendoAI #Texnologiya"""

                if image_url:
                    send_photo_to_channel(image_url, tg_message)
                else:
                    send_to_telegram_channel(tg_message)

                notify_all_subscribers(
                    title=f"🆕 Yangi Maqola: {title}",
                    message=f"{category} | {topic}\nO'qish uchun bosing!",
                    url=post_url
                )
            except Exception as e:
                print(f"[admin] Auto push/telegram error: {e}")

        flash('Post muvaffaqiyatli yaratildi!', 'success')
        return redirect(url_for('admin.admin_posts'))

    return render_template('admin/edit_post.html', post=None, categories=CATEGORIES)


@admin_bp.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    """Postni tahrirlash"""
    p = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        p.title = request.form.get('title')
        p.content = request.form.get('content')
        p.topic = request.form.get('topic')
        p.category = request.form.get('category')
        p.keywords = request.form.get('keywords')
        p.image_url = request.form.get('image_url', '')
        p.image_prompt = request.form.get('image_prompt', '').strip()
        p.is_published = request.form.get('is_published') == 'on'
        p.reading_time = p.calculate_reading_time()

        db.session.commit()
        flash('Post muvaffaqiyatli yangilandi!', 'success')
        return redirect(url_for('admin.admin_posts'))

    return render_template('admin/edit_post.html', post=p, categories=CATEGORIES)


@admin_bp.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    """Postni o'chirish"""
    try:
        p = Post.query.get_or_404(post_id)
        post_title = p.title
        db.session.delete(p)
        db.session.commit()
        flash(f'"{post_title}" muvaffaqiyatli o\'chirildi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Xatolik yuz berdi: {str(e)}', 'error')

    return redirect(url_for('admin.admin_posts'))


@admin_bp.route('/admin/generate', methods=['GET', 'POST'])
@login_required
def admin_generate():
    """AI bilan post generatsiya qilish (Asinxron)"""
    if request.method == 'POST':
        topic = request.form.get('topic')
        category = request.form.get('category', 'Texnologiya')

        if not topic:
            flash('Mavzu kiritilishi shart!', 'error')
            return redirect(url_for('admin.admin_generate'))

        from scheduler import generate_and_publish_post
        thread = threading.Thread(target=generate_and_publish_post, args=(topic, category))
        thread.daemon = True
        thread.start()

        flash(f'"{topic}" mavzusida generatsiya orqa fonda boshlandi. Tez orada Telegramga chiqadi.', 'success')
        return redirect(url_for('admin.admin_posts'))

    return render_template('admin/generate.html', categories=CATEGORIES)


@admin_bp.route('/admin/generate-post')
@login_required
def admin_generate_post():
    """Manual post generation"""
    try:
        from scheduler import generate_and_publish_post
        success = generate_and_publish_post()
        if success:
            return "✅ Yangi post muvaffaqiyatli generatsiya qilindi va Telegramga yuborildi!", 200
        else:
            return "❌ Post generatsiya qilishda xatolik.", 500
    except Exception as e:
        return f"❌ Xatolik: {e}", 500


@admin_bp.route('/admin/migrate-slugs', methods=['POST'])
@login_required
def admin_migrate_slugs():
    """Barcha postlarga slug qo'shish (SEO uchun)"""
    posts_without_slug = Post.query.filter(
        (Post.slug == None) | (Post.slug == '')
    ).all()

    count = 0
    for p in posts_without_slug:
        p.slug = p.generate_slug()
        count += 1

    db.session.commit()
    flash(f'{count} ta postga slug qo\'shildi!', 'success')
    return redirect(url_for('admin.admin_posts'))


# ========== PORTFOLIO ADMIN ROUTES ==========

@admin_bp.route('/admin/portfolio')
@login_required
def admin_portfolio():
    """Portfolio ro'yxati"""
    portfolios = Portfolio.query.order_by(Portfolio.created_at.desc()).all()
    return render_template('admin/portfolio.html', portfolios=portfolios)


@admin_bp.route('/admin/portfolio/new', methods=['GET', 'POST'])
@login_required
def admin_portfolio_new():
    """Yangi portfolio qo'shish"""
    if request.method == 'POST':
        uploaded_image = _save_uploaded_image(request.files.get('image_file'), folder='portfolio')
        image_url = uploaded_image or request.form.get('image_url')

        portfolio = Portfolio(
            title=request.form.get('title'),
            description=request.form.get('description'),
            category=request.form.get('category', 'web'),
            emoji=request.form.get('emoji', '🚀'),
            technologies=request.form.get('technologies'),
            link=request.form.get('link'),
            image_url=image_url,
            is_featured=request.form.get('is_featured') == 'on',
            is_published=request.form.get('is_published') == 'on',
            meta_description=request.form.get('meta_description'),
            meta_keywords=request.form.get('meta_keywords'),
            details=request.form.get('details'),
            features=request.form.get('features'),
            price=request.form.get('price'),
            client_name=request.form.get('client_name'),
            problem=request.form.get('problem'),
            solution=request.form.get('solution'),
            result=request.form.get('result'),
            demo_url=request.form.get('demo_url'),
            video_url=request.form.get('video_url'),
            gallery_images=request.form.get('gallery_images')
        )
        db.session.add(portfolio)
        db.session.commit()

        portfolio.slug = portfolio.generate_slug()
        db.session.commit()

        if portfolio.is_published:
            try:
                from telegram_poster import send_portfolio_to_channel
                send_portfolio_to_channel(portfolio)
            except Exception as e:
                print(f"[admin] Telegram yuborishda xato: {e}")

            try:
                from seo_indexer import ping_search_engines
                site_url = current_app.config.get('SITE_URL') or 'https://trendoai.uz'
                item_url = f"{site_url}/portfolio/project/{portfolio.slug}" if portfolio.slug else f"{site_url}/portfolio"
                ping_search_engines(item_url)
            except Exception as se:
                print(f"[admin] Auto-indexing ping error: {se}")

        flash(f'"{portfolio.title}" muvaffaqiyatli qo\'shildi!', 'success')
        return redirect(url_for('admin.admin_portfolio'))

    return render_template('admin/portfolio_form.html', portfolio=None)


@admin_bp.route('/admin/portfolio/<int:portfolio_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_portfolio_edit(portfolio_id):
    """Portfolio tahrirlash"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)

    if request.method == 'POST':
        uploaded_image = _save_uploaded_image(request.files.get('image_file'), folder='portfolio')
        image_url = uploaded_image or request.form.get('image_url')

        portfolio.title = request.form.get('title')
        portfolio.description = request.form.get('description')
        portfolio.category = request.form.get('category', 'web')
        portfolio.emoji = request.form.get('emoji', '🚀')
        portfolio.technologies = request.form.get('technologies')
        portfolio.link = request.form.get('link')
        if image_url:
            portfolio.image_url = image_url
        portfolio.is_featured = request.form.get('is_featured') == 'on'
        portfolio.is_published = request.form.get('is_published') == 'on'
        portfolio.meta_description = request.form.get('meta_description')
        portfolio.meta_keywords = request.form.get('meta_keywords')
        portfolio.details = request.form.get('details')
        portfolio.features = request.form.get('features')
        portfolio.price = request.form.get('price')
        portfolio.client_name = request.form.get('client_name')
        portfolio.problem = request.form.get('problem')
        portfolio.solution = request.form.get('solution')
        portfolio.result = request.form.get('result')
        portfolio.demo_url = request.form.get('demo_url')
        portfolio.video_url = request.form.get('video_url')
        portfolio.gallery_images = request.form.get('gallery_images')

        if not portfolio.slug:
            portfolio.slug = portfolio.generate_slug()

        db.session.commit()
        flash(f'"{portfolio.title}" yangilandi!', 'success')
        return redirect(url_for('admin.admin_portfolio'))

    return render_template('admin/portfolio_form.html', portfolio=portfolio)


@admin_bp.route('/admin/portfolio/<int:portfolio_id>/delete', methods=['POST'])
@login_required
def admin_portfolio_delete(portfolio_id):
    """Portfolio o'chirish"""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        title = portfolio.title
        db.session.delete(portfolio)
        db.session.commit()
        flash(f'"{title}" muvaffaqiyatli o\'chirildi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Xatolik yuz berdi: {str(e)}', 'error')

    return redirect(url_for('admin.admin_portfolio'))


@admin_bp.route('/admin/portfolio/<int:portfolio_id>/send-telegram', methods=['POST'])
@login_required
def admin_portfolio_send_telegram(portfolio_id):
    """Portfolioni Telegram kanalga yuborish"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    try:
        from telegram_poster import send_portfolio_to_channel
        if send_portfolio_to_channel(portfolio):
            flash(f'"{portfolio.title}" Telegram kanalga yuborildi!', 'success')
        else:
            flash('Telegramga yuborishda xatolik yuz berdi.', 'error')
    except Exception as e:
        flash(f'Xatolik: {e}', 'error')

    return redirect(url_for('admin.admin_portfolio'))


# ========== ORDER & KANBAN ROUTES ==========

@admin_bp.route('/admin/orders')
@login_required
def admin_orders():
    """Barcha buyurtmalarni ko'rish"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', None)

    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    new_count = Order.query.filter_by(status='new').count()
    total_count = Order.query.count()

    return render_template('admin/orders.html',
                           orders=orders,
                           new_count=new_count,
                           total_count=total_count,
                           current_status=status_filter)


@admin_bp.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
def admin_update_order_status(order_id):
    """Buyurtma statusini yangilash"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    if new_status in ['new', 'contacted', 'completed', 'cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Buyurtma #{order.id} statusi yangilandi!', 'success')

    return redirect(url_for('admin.admin_orders'))


@admin_bp.route('/admin/orders/<int:order_id>/delete', methods=['POST'])
@login_required
def admin_delete_order(order_id):
    """Buyurtmani o'chirish"""
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash(f'Buyurtma #{order_id} o\'chirildi!', 'success')
    return redirect(url_for('admin.admin_orders'))


@admin_bp.route('/admin/kanban')
@login_required
def admin_kanban():
    """CRM Kanban Board va Sotuvlar Analitikasi"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    leads = Lead.query.order_by(Lead.created_at.desc()).all()

    kanban_data = {
        'new': [],
        'contacted': [],
        'in_progress': [],
        'completed': [],
        'cancelled': []
    }

    for o in orders:
        st = o.status if o.status in kanban_data else 'new'
        kanban_data[st].append({
            'type': 'order',
            'id': o.id,
            'name': o.name,
            'contact': o.phone,
            'title': o.service_name,
            'budget': o.budget or 'Kelishilgan',
            'message': o.message,
            'admin_note': o.admin_note or '',
            'status': st,
            'date': o.created_at.strftime('%d.%m.%Y %H:%M') if o.created_at else 'N/A'
        })

    for l in leads:
        st = l.status if l.status in kanban_data else 'new'
        kanban_data[st].append({
            'type': 'lead',
            'id': l.id,
            'name': l.name or 'Lead Mijoz',
            'contact': l.contact,
            'title': f"Lead ({l.source})",
            'budget': 'Ma\'lumot berilmagan',
            'message': f"Manba: {l.source}",
            'admin_note': l.admin_note or '',
            'status': st,
            'date': l.created_at.strftime('%d.%m.%Y %H:%M') if l.created_at else 'N/A'
        })

    total_items = len(orders) + len(leads)
    completed_count = len(kanban_data['completed'])
    conversion_rate = round((completed_count / total_items * 100), 1) if total_items > 0 else 0

    stats = {
        'total': total_items,
        'new': len(kanban_data['new']),
        'contacted': len(kanban_data['contacted']),
        'in_progress': len(kanban_data['in_progress']),
        'completed': completed_count,
        'cancelled': len(kanban_data['cancelled']),
        'conversion_rate': conversion_rate
    }

    return render_template('admin/kanban.html', kanban=kanban_data, stats=stats)


@admin_bp.route('/admin/invoice/<int:order_id>')
@login_required
def admin_invoice(order_id):
    """Buyurtma bo'yicha professional hisob-faktura (Invoice & Contract) sahifasi"""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/invoice.html', order=order, now=datetime.now())


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
            from config import CRON_SECRET
            secret_token = (CRON_SECRET or 'trendoai_super_secret_123')[:256]
            bot.remove_webhook()
            time.sleep(0.5)
            bot.set_webhook(url=webhook_url, secret_token=secret_token)
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
