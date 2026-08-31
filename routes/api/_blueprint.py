from flask import Blueprint, request, jsonify, current_app
from config import CRON_SECRET, TELEGRAM_WEBHOOK_SECRET
from services.rate_limit_service import allow_request
from utils.logger import setup_logger
logger = setup_logger("_blueprint")


api_bp = Blueprint('api', __name__)

# TELEGRAM_WEBHOOK_SECRET config.py'da aniqlanadi va shu yerda qayta eksport qilinadi.

def _client_ip():
    """ProxyFix orqali xavfsiz olingan mijoz IP manzili"""
    return request.remote_addr or 'unknown'


def _check_rate_limit(key, limit=30, window_seconds=60):
    """Redis bilan workerlar orasida umumiy bo'lgan rate limiter."""
    scope, _, client_ip = key.partition(':')
    return allow_request(scope or 'api', client_ip or 'unknown', limit, window_seconds)


def _verify_meta_signature():
    """Meta lead webhook imzosini (X-Hub-Signature-256) tekshiradi.

    FB_APP_SECRET berilmagan bo'lsa endpoint eskicha imzosiz ishlaydi —
    bu holat logga yoziladi, chunki u endpointni ochiq qoldiradi.
    """
    import hashlib
    import hmac

    from config import FB_APP_SECRET

    if not FB_APP_SECRET:
        logger.info(
            "[api] OGOHLANTIRISH: FB_APP_SECRET yo'q, Facebook lead webhook imzosi "
            "tekshirilmadi. Endpoint autentifikatsiyasiz ishlamoqda."
        )
        return True

    header = request.headers.get('X-Hub-Signature-256') or ''
    if not header.startswith('sha256='):
        return False

    expected = hmac.new(
        FB_APP_SECRET.encode('utf-8'),
        request.get_data(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(header[len('sha256='):], expected)


def _cron_secret_error():
    return jsonify({'error': 'Unauthorized', 'message': 'Invalid secret key'}), 401


def _has_valid_cron_secret():
    secret = request.args.get('secret') or request.headers.get('X-Cron-Secret')
    expected = current_app.config.get('CRON_SECRET') or CRON_SECRET
    return bool(secret and secret == expected)
