from routes.web._blueprint import web_bp
from routes.web.services_routes import PUBLIC_SERVICE_PRICING, SERVICES_DATA
from routes.web.pages import _order_submissions

# Register all route sub-modules
from routes.web import pages, blog, services_routes, portfolio_routes, seo  # noqa: F401

__all__ = ['web_bp', 'PUBLIC_SERVICE_PRICING', 'SERVICES_DATA', '_order_submissions']
