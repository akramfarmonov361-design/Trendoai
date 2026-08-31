from flask import current_app, flash, redirect, render_template, request, url_for
from extensions import db
from models.portfolio import Portfolio
from routes.admin._blueprint import admin_bp, login_required, _save_uploaded_image
from utils.logger import setup_logger
logger = setup_logger("portfolio")


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
                logger.info(f"[admin] Telegram yuborishda xato: {e}")

            try:
                from seo_indexer import ping_search_engines
                site_url = current_app.config.get('SITE_URL') or 'https://trendoai.uz'
                item_url = f"{site_url}/portfolio/project/{portfolio.slug}" if portfolio.slug else f"{site_url}/portfolio"
                ping_search_engines(item_url)
            except Exception as se:
                logger.error(f"[admin] Auto-indexing ping error: {se}")

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

@admin_bp.route('/admin/portfolio/ai-generate', methods=['POST'])
@login_required
def admin_portfolio_ai_generate():
    """Loyiha nomiga qarab AI orqali to'liq ma'lumotlarni generatsiya qilish"""
    from flask import jsonify
    from services.ai_service import generate_text
    import json

    data = request.get_json() or {}
    title = data.get('title', '').strip()
    category = data.get('category', 'web').strip()

    if not title:
        return jsonify({'success': False, 'error': 'Loyiha nomini kiriting!'}), 400

    prompt = f"""
Siz professional IT loyihalar kopirayterisiz. Quyidagi IT loyiha uchun o'zbek tilida to'liq portfolio ma'lumotlarini JSON formatida tayyorlab bering.

Loyiha nomi: {title}
Kategoriya: {category}

Faqat va faqat quyidagi kalitlar bilan to'g'ri JSON qaytaring (hech qanday markdown belgilari, faqat JSON):
{{
    "description": "Loyiha haqida 2-3 jumlali jozibali qisqacha ma'lumot",
    "details": "Loyiha haqida batafsil ma'lumot (2-3 paragraf)",
    "technologies": "Texnologiyalar vergul bilan (masalan: Python, Flask, React, PostgreSQL)",
    "features": "Asosiy 4-5 ta imkoniyati vergul bilan ajratilgan",
    "problem": "Mijoz duch kelgan asosiy biznes muammosi",
    "solution": "Biz ishlab chiqqan sun'iy intellekt / IT yechimi",
    "result": "Loyiha ishga tushgach erishilgan biznes natijasi (masalan: Sotuvlar 40% oshdi)",
    "meta_description": "SEO uchun 150 belgili meta tavsif",
    "meta_keywords": "SEO kalit so'zlari vergul bilan",
    "emoji": "Loyiha mazmuniga mos bitta emoji"
}}
"""
    try:
        raw_res = generate_text(prompt)
        # JSON ni tozalab olish
        clean_json = raw_res.strip()
        if clean_json.startswith('```'):
            lines = clean_json.split('\n')
            clean_json = '\n'.join([l for l in lines if not l.startswith('```')])
        
        parsed = json.loads(clean_json)
        return jsonify({'success': True, 'data': parsed})
    except Exception as e:
        logger.error(f"[admin] Portfolio AI generate error: {e}")
        return jsonify({'success': False, 'error': f'AI generatsiyada xatolik: {str(e)}'}), 500
