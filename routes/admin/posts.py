import threading
from flask import flash, redirect, render_template, request, url_for
from extensions import db
from models.post import Post
from config import CATEGORIES
from routes.admin._blueprint import admin_bp, login_required
from utils.logger import setup_logger
logger = setup_logger("posts")


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
                logger.error(f"[admin] Auto push/telegram error: {e}")

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
        # Admin ataylab bosgan tugma — kunlik takrorlanish qalqoni chetlab o'tiladi.
        success = generate_and_publish_post(force=True)
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
