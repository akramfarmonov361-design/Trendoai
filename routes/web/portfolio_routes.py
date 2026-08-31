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
