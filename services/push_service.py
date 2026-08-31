"""
Web Push xabarnomalarni yuborish xizmati.
"""
import json
import os
import tempfile
from extensions import db
from models.interaction import PushSubscription
from config import VAPID_PRIVATE_KEY, VAPID_CLAIMS_SUB
from utils.logger import setup_logger
logger = setup_logger("push_service")



def notify_all_subscribers(title, message, url="/", vapid_key=None, claims_sub=None):
    """Barcha obunachilarga Web Push xabar yuborish"""
    try:
        from pywebpush import webpush, WebPushException

        vapid_private_key_path = vapid_key or VAPID_PRIVATE_KEY
        sub_claim = claims_sub or VAPID_CLAIMS_SUB or "mailto:admin@trendoai.uz"
        temp_pem_path = None

        if not str(vapid_private_key_path).strip():
            logger.info("[push] VAPID_PRIVATE_KEY sozlanmagan — push yuborilmadi")
            return 0

        if not os.path.exists(str(vapid_private_key_path)):
            try:
                with tempfile.NamedTemporaryFile(suffix='.pem', delete=False, mode='w', encoding='utf-8') as temp_pem:
                    key_content = str(vapid_private_key_path).strip()
                    if "-----BEGIN PRIVATE KEY-----" not in key_content:
                        key_content = f"-----BEGIN PRIVATE KEY-----\n{key_content}\n-----END PRIVATE KEY-----"
                    temp_pem.write(key_content)
                    temp_pem_path = temp_pem.name
                    vapid_private_key_path = temp_pem_path
            except Exception as e:
                logger.error(f"[push] VAPID Temp file error: {e}")
                return 0

        subscriptions = PushSubscription.query.all()
        if not subscriptions:
            logger.info("[push] Faol obunachilar topilmadi")
            return 0

        count = 0
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info=sub.to_json(),
                    data=json.dumps({'title': title, 'body': message, 'url': url}),
                    vapid_private_key=vapid_private_key_path,
                    vapid_claims={'sub': sub_claim}
                )
                count += 1
            except WebPushException as ex:
                status_code = getattr(getattr(ex, 'response', None), 'status_code', None)
                logger.info(f"[push] WebPush xatosi ({status_code}): {ex}")
                if status_code in (404, 410):
                    db.session.delete(sub)
            except Exception as e:
                logger.error(f"[push] Individual push error: {e}")

        db.session.commit()

        if temp_pem_path and os.path.exists(temp_pem_path):
            try:
                os.unlink(temp_pem_path)
            except Exception:
                pass

        return count
    except Exception as e:
        logger.error(f"[push] Error notifying subscribers: {e}")
        return 0
