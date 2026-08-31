from flask import request
from routes.api._blueprint import api_bp, TELEGRAM_WEBHOOK_SECRET
from extensions import csrf
from utils.logger import setup_logger
logger = setup_logger("webhook")


# ========== TELEGRAM WEBHOOK ==========

@api_bp.route('/webhook', methods=['POST'])
@csrf.exempt
def telegram_webhook():
    """Telegram webhook handler"""
    try:
        from bot_service import bot
        import telebot

        import hmac
        secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token') or ''
        if not TELEGRAM_WEBHOOK_SECRET or not hmac.compare_digest(secret_token, TELEGRAM_WEBHOOK_SECRET):
            return 'Unauthorized', 403

        if bot and request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        else:
            return 'Bot not configured', 400
    except Exception as e:
        logger.error(f"[api] Webhook error: {e}")
        return 'Error', 500
