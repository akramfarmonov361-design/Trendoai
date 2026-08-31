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

    return render_template(
        'portfolio.html',
        portfolios=pagination.items,
        pagination=pagination,
        active_category=category,
    )

def _get_item_image(item):
    """Loyiha uchun to'g'ri va ishlaydigan rasm manzilini qaytaradi"""
    img = (item.image_url or '').strip()
    if img:
        return img
    
    t_lower = (item.title or '').lower()
    if any(w in t_lower for w in ['voice', 'ovoz', 'chatbot', 'kundalik', 'rag']):
        return "https://images.unsplash.com/photo-1589254065878-42c9da997008?q=80&w=1000&auto=format&fit=crop"
    elif any(w in t_lower for w in ['video', 'dublyaj', 'insta-dub', 'youtube']):
        return "https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?q=80&w=1000&auto=format&fit=crop"
    elif any(w in t_lower for w in ['telegram', 'bot', 'botfactory']):
        return "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1000&auto=format&fit=crop"
    elif any(w in t_lower for w in ['crm', 'smart', 'boshqaruv', 'tahlil', 'finder']):
        return "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1000&auto=format&fit=crop"
    elif any(w in t_lower for w in ['restoran', 'delivery', 'ovqat', 'fast-food']):
        return "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?q=80&w=1000&auto=format&fit=crop"
    elif any(w in t_lower for w in ['paket', 'shop', 'dokon', 'savdo', 'optombazar']):
        return "https://images.unsplash.com/photo-1472851294608-062f824d29cc?q=80&w=1000&auto=format&fit=crop"
    elif item.category == 'web' or 'sayt' in t_lower:
        return "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1000&auto=format&fit=crop"
    return "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=1000&auto=format&fit=crop"

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
