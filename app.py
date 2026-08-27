"""
TrendoAI — Trending texnologiyalar va sun'iy intellekt haqida professional IT platforma.
Asosiy Flask ilovasi (Modular Architecture).
"""
import os
import re
import sys
import threading
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from flask_wtf.csrf import CSRFError
import markdown2

from config import (
    CATEGORIES,
    CRON_SECRET,
    DATABASE_URI,
    DEBUG,
    FACEBOOK_PIXEL_ID,
    GA4_ID,
    GEMINI_API_KEY,
    GEMINI_LIVE_MODEL,
    GOOGLE_ADS_ID,
    SECRET_KEY,
    SITE_DESCRIPTION,
    SITE_NAME,
    SITE_URL,
    VAPID_CLAIMS_SUB,
    VAPID_PRIVATE_KEY,
    VAPID_PUBLIC_KEY,
)
from extensions import csrf, db, migrate
from models import (
    BotOrder,
    Lead,
    MenuCategory,
    MenuItem,
    Order,
    Portfolio,
    Post,
    PushSubscription,
    Service,
    TelegramUser,
)
from routes import admin_bp, api_bp, web_bp
from routes.web import PUBLIC_SERVICE_PRICING, SERVICES_DATA
from services.cache_service import (
    cache_get,
    cache_set,
    clear_list_cache,
)
from services.crm_service import capture_lead_from_message
from services.push_service import notify_all_subscribers
from services.voice_service import (
    chat_audio_system_prompt as _chat_audio_system_prompt,
    friendly_audio_error as _friendly_audio_error,
    get_gemini_api_key_candidates as _gemini_api_key_candidates,
    get_live_audio_reply,
)

load_dotenv()

# Windows terminallarida UTF-8 muammolarini oldini olish
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _url_build_error_handler(error, endpoint, values):
    """
    url_for('index') kabi chaqiruvlarni avtomatik ravishda
    url_for('web.index') yoki 'admin.index' ga yo'naltiradi (100% orqaga moslik).
    """
    for bp in ('web', 'admin', 'api'):
        bp_endpoint = f"{bp}.{endpoint}"
        if bp_endpoint in current_app.view_functions:
            return url_for(bp_endpoint, **values)
    raise error


def create_app(config_overrides=None):
    """Flask ilova fabrikasi"""
    application = Flask(__name__)

    application.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    application.config['SECRET_KEY'] = SECRET_KEY
    application.config['CRON_SECRET'] = CRON_SECRET
    application.config['GEMINI_API_KEY'] = GEMINI_API_KEY
    application.config['GEMINI_LIVE_MODEL'] = GEMINI_LIVE_MODEL
    application.config['VAPID_PUBLIC_KEY'] = VAPID_PUBLIC_KEY
    application.config['VAPID_PRIVATE_KEY'] = VAPID_PRIVATE_KEY
    application.config['VAPID_CLAIMS_SUB'] = VAPID_CLAIMS_SUB
    application.config['SESSION_COOKIE_HTTPONLY'] = True
    application.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    application.config['SESSION_COOKIE_SECURE'] = not DEBUG
    application.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max payload limit

    application.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 5,
        'max_overflow': 10,
    }

    if config_overrides:
        application.config.update(config_overrides)

    # Kengaytmalarni ulash
    db.init_app(application)
    csrf.init_app(application)
    if migrate:
        migrate.init_app(application, db)

    # CSRF: avtomatik tekshiruvni o'chirib, qo'lda boshqarish
    application.config['WTF_CSRF_CHECK_DEFAULT'] = False

    # Reverse Proxy (Render/Cloudflare) uchun xavfsiz ProxyFix middleware
    from werkzeug.middleware.proxy_fix import ProxyFix
    application.wsgi_app = ProxyFix(application.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    csrf_exempt_names = {
        'telegram_webhook',
        'api_health',
        'api_posts',
        'api_post',
        'api_stats',
        'api_init_database',
        'cron_status',
        'cron_generate_post',
        'cron_keep_alive',
        'cron_debug_generate',
        'cron_test_ai',
        'api_chat',
        'api_chat_audio',
        'push_subscribe',
        'submit_lead',
        'facebook_lead_webhook',
        'api.telegram_webhook',
        'api.api_health',
        'api.api_posts',
        'api.api_post',
        'api.api_stats',
        'api.api_init_database',
        'api.cron_status',
        'api.cron_generate_post',
        'api.cron_keep_alive',
        'api.cron_debug_generate',
        'api.cron_test_ai',
        'api.api_chat',
        'api.api_chat_audio',
        'api.push_subscribe',
        'api.submit_lead',
        'api.facebook_lead_webhook',
    }

    @application.before_request
    def check_csrf():
        if not application.config.get('WTF_CSRF_ENABLED', True):
            return
        if request.endpoint in csrf_exempt_names:
            return
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            csrf.protect()

    @application.after_request
    def security_headers(response):
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "object-src 'none'; base-uri 'self'; frame-ancestors 'self'; "
            "form-action 'self'; upgrade-insecure-requests"
        )
        response.headers['Permissions-Policy'] = (
            'camera=(), geolocation=(), payment=(), usb=(), microphone=(self)'
        )
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        if request.path.startswith('/static/'):
            response.headers.setdefault('Cache-Control', 'public, max-age=604800')
        if not DEBUG:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    @application.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'CSRF token xato yoki topilmadi'}), 400
        flash('Forma xavfsizlik tokeni eskirgan. Iltimos, sahifani yangilab qayta urinib ko\'ring.', 'error')
        return redirect(request.referrer or url_for('web.index'))

    @application.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @application.errorhandler(413)
    def request_entity_too_large(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': "So'rov hajmi juda katta (maksimal 16MB)"}), 413
        return "So'rov hajmi juda katta (maksimal 16MB)", 413

    @application.errorhandler(500)
    def server_error(e):
        print(f"Server Error (500): {e}")
        return render_template('errors/500.html'), 500

    # Template Filtrlari (XSS himoyasi bilan: safe_mode='escape')
    @application.template_filter('markdown')
    def markdown_filter(s):
        return markdown2.markdown(s or '', extras=["fenced-code-blocks", "tables", "break-on-newline"], safe_mode="escape")

    leading_h1_pattern = re.compile(r"^\s*#\s+[^\n]+\n+")

    @application.template_filter('markdown_body')
    def markdown_body_filter(s):
        cleaned = leading_h1_pattern.sub("", s or "", count=1)
        return markdown2.markdown(cleaned, extras=["fenced-code-blocks", "tables", "break-on-newline"], safe_mode="escape")

    # Global Context Processor & Multilingual Support
    @application.context_processor
    def inject_globals():
        if not hasattr(application, '_log_shown'):
            print(f"DEBUG: FACEBOOK_PIXEL_ID={FACEBOOK_PIXEL_ID}")
            print(f"DEBUG: GA4_ID={GA4_ID}")
            application._log_shown = True

        from flask import session
        from translations import get_translation

        lang = request.args.get('lang') or session.get('lang') or 'uz'
        if lang not in ('uz', 'ru', 'en'):
            lang = 'uz'

        return {
            'config': {
                'SITE_URL': SITE_URL,
                'SITE_NAME': SITE_NAME,
                'SITE_DESCRIPTION': SITE_DESCRIPTION,
                'VAPID_PUBLIC_KEY': application.config.get('VAPID_PUBLIC_KEY')
            },
            'GA4_ID': GA4_ID,
            'GOOGLE_ADS_ID': GOOGLE_ADS_ID,
            'FACEBOOK_PIXEL_ID': FACEBOOK_PIXEL_ID,
            'categories': CATEGORIES,
            'current_lang': lang,
            't': lambda key, default=None: get_translation(key, lang, default),
            'now': datetime.now()
        }

    # Blueprintlarni ro'yxatdan o'tkazish
    application.register_blueprint(web_bp)
    application.register_blueprint(admin_bp)
    application.register_blueprint(api_bp)

    # URL for fallback
    application.url_build_error_handlers.append(_url_build_error_handler)

    # HTTP Caching & Performance Headers (Google PageSpeed 95+)
    @application.after_request
    def apply_caching_and_performance_headers(response):
        # Static asset caching (1 year for immutable static assets)
        if request.path.startswith('/static/'):
            if request.path.endswith('/sw.js') or request.path.endswith('/manifest.json'):
                response.headers['Cache-Control'] = 'public, max-age=3600, must-revalidate'
            else:
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.method == 'GET' and response.status_code == 200 and not request.path.startswith('/admin') and not request.path.startswith('/api'):
            # Public HTML pages: stale-while-revalidate for instantaneous repeat loading
            response.headers['Cache-Control'] = 'public, max-age=120, stale-while-revalidate=86400'

        # Security & Core Web Vitals optimizations
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Vary'] = 'Accept-Encoding, Accept'
        return response

    return application


app = create_app()


# ========== DATABASE INITIALIZATION & MIGRATIONS ==========

def init_database():
    """Bazani yangilash va ustunlarni tekshirish"""
    with app.app_context():
        from sqlalchemy import inspect, text

        try:
            db.create_all()
        except Exception as e:
            print(f"WARN: db.create_all failed: {e}")
            return

        try:
            inspector = inspect(db.engine)
            table_names = set(inspector.get_table_names())

            def ensure_varchar_column(table_name, column_name):
                if table_name not in table_names:
                    return
                existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                if column_name in existing_columns:
                    return
                with db.engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} VARCHAR(100)'))
                print(f"OK: added {table_name}.{column_name}.")

            def ensure_text_column(table_name, column_name):
                if table_name not in table_names:
                    return
                existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                if column_name in existing_columns:
                    return
                with db.engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} TEXT'))
                print(f"OK: added {table_name}.{column_name}.")

            ensure_varchar_column("portfolio", "price")
            ensure_varchar_column("portfolio", "client_name")
            ensure_text_column("portfolio", "problem")
            ensure_text_column("portfolio", "solution")
            ensure_text_column("portfolio", "result")
            ensure_varchar_column("portfolio", "demo_url")
            ensure_varchar_column("portfolio", "video_url")
            ensure_text_column("portfolio", "gallery_images")
            ensure_varchar_column("service", "price")
            ensure_text_column("post", "image_prompt")
            ensure_text_column("order", "admin_note")
            ensure_text_column("lead", "admin_note")
            ensure_varchar_column("lead", "status")

            for table_name, index_names in {
                'post': (
                    'ix_post_published_created',
                    'ix_post_published_views',
                    'ix_post_category_published_created',
                ),
                'portfolio': (
                    'ix_portfolio_published_created',
                    'ix_portfolio_category_published_created',
                ),
            }.items():
                table = db.metadata.tables.get(table_name)
                if table is None or table_name not in table_names:
                    continue
                indexes_by_name = {index.name: index for index in table.indexes}
                for index_name in index_names:
                    index = indexes_by_name.get(index_name)
                    if index is not None:
                        index.create(bind=db.engine, checkfirst=True)
                        print(f"INFO: ensured index {index_name}.")

            if "portfolio" in table_names and db.engine.dialect.name == "postgresql":
                portfolio_columns = {col["name"] for col in inspector.get_columns("portfolio")}
                if "meta_description" in portfolio_columns:
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE portfolio ALTER COLUMN meta_description TYPE TEXT"))
                    print("OK: portfolio.meta_description converted to TEXT.")
        except Exception as e:
            print(f"WARN: Database migration step failed: {e}")


def migrate_service_discount_dates():
    """Eskirgan aksiya sanalarini yangilash"""
    try:
        updated_count = (
            Service.query
            .filter(Service.discount_percent > 0, Service.discount_until == '1-fevral')
            .update({'discount_until': '1-aprel'}, synchronize_session=False)
        )
        if updated_count:
            db.session.commit()
            print(f"OK: updated {updated_count} service discount date(s) to 1-aprel.")
        else:
            db.session.rollback()
    except Exception as e:
        db.session.rollback()
        print(f"WARN: Service discount date migration failed: {e}")


def migrate_remove_post_freshness_notes():
    """Eski statik sana eslatmalarini tozalash"""
    pattern = re.compile(
        r"^\s*_Ushbu maqola\s+\d{4}-\d{2}-\d{2}\s+holatiga ko'ra tayyorlandi\.\s*"
        r"Tez ozgaradigan versiya, narx va reliz malumotlari vaqt otishi bilan yangilanishi mumkin\._\s*\n*",
        re.IGNORECASE,
    )
    try:
        posts = Post.query.filter(
            Post.content.isnot(None),
            Post.content.contains("_Ushbu maqola "),
            Post.content.contains("holatiga ko'ra tayyorlandi"),
        ).all()

        updated_count = 0
        for p in posts:
            original = p.content or ""
            cleaned = pattern.sub("", original, count=1).lstrip()
            if cleaned != original:
                p.content = cleaned
                updated_count += 1

        if updated_count:
            db.session.commit()
            print(f"OK: removed legacy freshness notes from {updated_count} post(s).")
        else:
            db.session.rollback()
    except Exception as e:
        db.session.rollback()
        print(f"WARN: Freshness-note cleanup failed: {e}")


def _boot_sequence():
    """Gunicorn workerlarini bloklamaslik uchun background boot sequence"""
    try:
        try:
            init_database()
            with app.app_context():
                migrate_service_discount_dates()
                migrate_remove_post_freshness_notes()
                from services.seed_portfolio import seed_desktop_portfolios
                seed_desktop_portfolios()
        except Exception as e:
            print(f"❌ DB init/migratsiya xatosi: {e}")

        # 1. Scheduler
        try:
            from scheduler import scheduler
            if not scheduler.running:
                scheduler.start()
                jobs = scheduler.get_jobs()
                print(f"✅ Scheduler ishga tushdi! Joblar soni: {len(jobs)}")
        except Exception as e:
            print(f"❌ Scheduler startup error: {e}")

        # 2. Telegram Bot Webhook
        try:
            from bot_service import setup_webhook
            setup_webhook(app)
        except Exception as e:
            print(f"❌ Bot webhook error: {e}")

        print("🚀 TrendoAI xizmatlari ishga tushdi!")
    except Exception as e:
        print(f"❌ Boot sequence error: {e}")

is_testing_env = "pytest" in sys.modules or bool(os.getenv("TESTING")) or bool(os.getenv("PYTEST_CURRENT_TEST"))
if not is_testing_env:
    threading.Thread(target=_boot_sequence, daemon=True).start()


# Backward compatibility aliases for in-memory cache & tests
from routes.web import _order_submissions
from routes.api import _local_chat_fallback
from services.voice_service import (
    friendly_audio_error as _friendly_audio_error,
    friendly_audio_error,
    get_gemini_api_key_candidates as _gemini_api_key_candidates,
    get_gemini_api_key_candidates,
    get_live_audio_reply,
)

def _cache_get(key):
    return cache_get(str(key), is_testing=bool(app.config.get('TESTING')))


def _cache_set(key, value):
    cache_set(str(key), value, ttl=60, is_testing=bool(app.config.get('TESTING')))


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
