from routes.api._blueprint import api_bp, TELEGRAM_WEBHOOK_SECRET
from routes.api.chat import _local_chat_fallback
from routes.api.public import is_duplicate_contact

# Register all route sub-modules
from routes.api import public, chat, cron, webhook  # noqa: F401

__all__ = ['api_bp', 'TELEGRAM_WEBHOOK_SECRET', '_local_chat_fallback', 'is_duplicate_contact']
