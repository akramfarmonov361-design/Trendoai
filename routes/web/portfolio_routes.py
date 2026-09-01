from flask import current_app, render_template, request
from models.portfolio import Portfolio
from routes.web._blueprint import web_bp
from services.cache_service import cache_get, cache_set

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

    # Har bir loyiha uchun rasm manzilini kafolatli to'ldirish
    for it in pagination.items:
        it._resolved_img = _get_item_image(it)

    return render_template(
        'portfolio.html',
        portfolios=pagination.items,
        pagination=pagination,
        active_category=category,
        get_item_image=_get_item_image,
    )

def _get_item_image(item):
    """Loyiha uchun to'g'ri va ishlaydigan rasm manzilini qaytaradi"""
    img = (item.image_url or '').strip()
    if img:
        return img
    
    t_lower = (item.title or '').lower()
    if any(w in t_lower for w in ['insta', 'dub', 'video', 'dublyaj']):
        return "/static/img/portfolio/instadubuz.webp"
    elif any(w in t_lower for w in ['bolajon', 'english', 'bola']):
        return "/static/img/portfolio/bolajon-ai-english.webp"
    elif any(w in t_lower for w in ['botfactory', 'chatbot factory', 'factory']):
        return "/static/img/portfolio/botfactory.webp"
    elif any(w in t_lower for w in ['ism', 'ismlar']):
        return "/static/img/portfolio/ismlar-manosi-ai.webp"
    elif any(w in t_lower for w in ['luxe', 'kiyim', 'brend']):
        return "/static/img/portfolio/luxe-core.webp"
    elif any(w in t_lower for w in ['optom', 'optombazar']):
        return "/static/img/portfolio/optombazar.webp"
    elif any(w in t_lower for w in ['restoran', 'voice ai delivery', 'ovqat', 'fastfood']):
        return "/static/img/portfolio/restoran.webp"
    elif any(w in t_lower for w in ['mijoz', 'finder', 'lid', 'topar']):
        return "/static/img/portfolio/mijoz-topar.webp"
    elif any(w in t_lower for w in ['text', 'ovoz', 'speech', 'diktor']):
        return "/static/img/portfolio/text-ovoz.webp"
    elif any(w in t_lower for w in ['nova', 'novatech']):
        return "/static/img/portfolio/novatech.webp"
    elif any(w in t_lower for w in ['real', 'smart', 'rieltor']):
        return "/static/img/portfolio/real-smart-ai.webp"
    elif any(w in t_lower for w in ['paket', 'qadoq', 'assistent']):
        return "/static/img/portfolio/paketshop-assistent.webp"
    elif any(w in t_lower for w in ['texno', 'elektronika']):
        return "/static/img/portfolio/texnomarket.webp"
    elif any(w in t_lower for w in ['speak', 'trendospeak']):
        return "/static/img/portfolio/trendospeak.webp"
    elif any(w in t_lower for w in ['uzum', 'yetkazib']):
        return "/static/img/portfolio/uzum-tezkor.webp"
    elif any(w in t_lower for w in ['vibe', 'kodlash', 'kurs']):
        return "/static/img/portfolio/vibecoding.webp"
    elif any(w in t_lower for w in ['viral', 'reels', 'tiktok']):
        return "/static/img/portfolio/viral-video.webp"
    return "/static/img/portfolio/trendoai-uz.webp"

@web_bp.route('/portfolio/project/<slug>')
def portfolio_item(slug):
    """Loyiha batafsil sahifasi"""
    item = Portfolio.query.filter_by(slug=slug, is_published=True).first_or_404()
    related_items = Portfolio.query.filter(
        Portfolio.id != item.id,
        Portfolio.category == item.category,
        Portfolio.is_published == True
    ).limit(3).all()

    # Rasm bo'lmasa zaxira rasm
    if not item.image_url:
        item.image_url = _get_item_image(item)

    for rel in related_items:
        if not rel.image_url:
            rel.image_url = _get_item_image(rel)

    return render_template('portfolio_detail.html', item=item, related_items=related_items)
