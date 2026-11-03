from flask import current_app, redirect, render_template, request, url_for
from models.portfolio import Portfolio
from routes.web._blueprint import web_bp
from services.cache_service import cache_get, cache_set
from services.view_models import empty_page, page_namespace, portfolio_page

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
    payload = cache_get(cache_key, is_testing=is_testing)

    if payload is None:
        try:
            query = Portfolio.query.filter_by(is_published=True)
            if category:
                query = query.filter_by(category=category)

            pagination = query.order_by(Portfolio.created_at.desc()).paginate(
                page=page,
                per_page=12,
                error_out=False,
            )
            # Keshga ORM obyekti emas, pickle-safe dict yoziladi. Aks holda
            # Redis'ga saqlash jimgina muvaffaqiyatsiz bo'lib, kesh faqat
            # bitta worker ichida qolardi (qarang: services/view_models.py).
            payload = portfolio_page(pagination, _get_item_image)
            cache_set(cache_key, payload, ttl=60, is_testing=is_testing)
        except Exception as e:
            from utils.logger import setup_logger
            _logger = setup_logger("portfolio_routes")
            _logger.error(f"[portfolio] Baza ulanish xatosi (fallback ishlatiladi): {e}")
            payload = empty_page(12)
            payload["json_items"] = []

    page_view = page_namespace(payload)

    return render_template(
        'portfolio.html',
        portfolios=page_view.items,
        portfolios_json=payload.get('json_items', []),
        pagination=page_view,
        active_category=category,
        get_item_image=_get_item_image,
    )

def _get_item_image(item):
    """Loyiha uchun to'g'ri va ishlaydigan rasm manzilini qaytaradi"""
    from services.seed_portfolio import resolve_portfolio_image
    return resolve_portfolio_image(
        title=getattr(item, 'title', None),
        image_url=getattr(item, 'image_url', None),
        category=getattr(item, 'category', None),
        for_feed=False,
    )

@web_bp.route('/portfolio/project/<slug>')
def portfolio_item(slug):
    """Loyiha batafsil sahifasi"""
    try:
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
    except Exception as e:
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise e
        return redirect(url_for('web.portfolio'))
