"""
TrendoAI Admin Panel, Kanban CRM va Boshqaruv Marshrutlari - Blueprint and Helpers.
"""
from functools import wraps
import os
import threading
import time
from utils.logger import setup_logger
logger = setup_logger("_blueprint")


from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for,
)

from config import (
    ADMIN_PASSWORD,
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
)

admin_bp = Blueprint('admin', __name__)

LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60

# Bu lug'at faqat to'ldirilardi: har bir yangi IP uchun yozuv qolib,
# jarayon xotirasi cheksiz o'sardi (oddiy DoS vektori).
LOGIN_TRACKER_MAX_IPS = 10_000
_failed_logins = {}
_failed_logins_lock = threading.Lock()


def _prune_failed_logins(now):
    """Muddati o'tgan urinish yozuvlarini o'chiradi."""
    with _failed_logins_lock:
        for ip in [
            ip for ip, times in _failed_logins.items()
            if not any(now - t < LOGIN_WINDOW_SECONDS for t in times)
        ]:
            _failed_logins.pop(ip, None)

        # Hammasi yangi bo'lsa ham lug'at cheksiz o'smasligi kerak.
        overflow = len(_failed_logins) - LOGIN_TRACKER_MAX_IPS
        if overflow > 0:
            oldest = sorted(_failed_logins.items(), key=lambda kv: max(kv[1], default=0))
            for ip, _ in oldest[:overflow]:
                _failed_logins.pop(ip, None)


def _client_ip():
    """ProxyFix orqali xavfsiz olingan mijoz IP manzili"""
    return request.remote_addr or 'unknown'


def _check_admin_credentials(username, password):
    """Admin login ma'lumotlarini vaqt-bardosh (constant-time) tekshirish."""
    import hmac
    import sys
    admin_mod = sys.modules.get('routes.admin')
    
    curr_username = getattr(admin_mod, 'ADMIN_USERNAME', ADMIN_USERNAME)
    curr_password = getattr(admin_mod, 'ADMIN_PASSWORD', ADMIN_PASSWORD)
    curr_hash = getattr(admin_mod, 'ADMIN_PASSWORD_HASH', ADMIN_PASSWORD_HASH)

    username_ok = hmac.compare_digest((username or ''), curr_username or '')

    if curr_hash:
        from werkzeug.security import check_password_hash
        password_ok = check_password_hash(curr_hash, password or '')
    else:
        password_ok = hmac.compare_digest((password or ''), curr_password or '')

    return username_ok and password_ok


# Sessiya uchun maksimal vaqt (30 daqiqa = 1800 soniya)
SESSION_TIMEOUT_SECONDS = 1800

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Iltimos, avval tizimga kiring.', 'warning')
            return redirect(url_for('admin.admin_login'))
            
        # Session timeout tekshiruvi
        last_active = session.get('last_active')
        if last_active is not None:
            now = time.time()
            if now - last_active > SESSION_TIMEOUT_SECONDS:
                session.clear()
                flash('Seans vaqti tugadi. Xavfsizlik yuzasidan qayta kiring.', 'warning')
                return redirect(url_for('admin.admin_login'))
                
        # Har safar sahifani yangilaganda oxirgi faoliyat vaqtini yangilaymiz
        session['last_active'] = time.time()
        
        return f(*args, **kwargs)
    return decorated_function


def _save_uploaded_image(file_storage, folder='portfolio'):
    """Faylni WebP formatida siqib saqlash (S3/R2 bulutli saqlash yoki static/uploads/ lokal papkasi)."""
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None
    filename = str(file_storage.filename).strip()
    if not filename:
        return None

    import io
    import uuid
    from PIL import Image

    unique_base = uuid.uuid4().hex[:12]
    webp_data = None

    try:
        file_storage.seek(0)
        img = Image.open(file_storage.stream)

        # Convert RGBA / P / LA modes if needed for optimal WebP
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in getattr(img, 'info', {})):
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        # Resize proportionally if width or height > 1600px
        max_dimension = 1600
        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        out_buffer = io.BytesIO()
        img.save(out_buffer, 'WEBP', quality=85, method=6)
        webp_data = out_buffer.getvalue()
        file_name = f"{unique_base}.webp"
        content_type = "image/webp"
    except Exception as e:
        logger.error(f"[upload] Pillow WebP conversion failed: {e}")
        file_storage.seek(0)
        webp_data = file_storage.read()
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'):
            ext = '.jpg'
        file_name = f"{unique_base}{ext}"
        content_type = file_storage.content_type or "image/jpeg"

    # 1. S3 / Cloudflare R2 / Supabase Storage tekshiruvi
    s3_bucket = os.getenv("S3_BUCKET") or os.getenv("R2_BUCKET")
    s3_endpoint = os.getenv("S3_ENDPOINT_URL") or os.getenv("R2_ENDPOINT_URL")
    s3_access_key = os.getenv("S3_ACCESS_KEY_ID") or os.getenv("R2_ACCESS_KEY_ID")
    s3_secret_key = os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("R2_SECRET_ACCESS_KEY")
    public_url_base = os.getenv("STORAGE_PUBLIC_URL") or os.getenv("R2_PUBLIC_URL")

    if s3_bucket and s3_access_key and s3_secret_key:
        try:
            import boto3
            s3_client = boto3.client(
                's3',
                endpoint_url=s3_endpoint,
                aws_access_key_id=s3_access_key,
                aws_secret_access_key=s3_secret_key,
            )
            object_key = f"{folder}/{file_name}"
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=object_key,
                Body=webp_data,
                ContentType=content_type,
            )
            if public_url_base:
                return f"{public_url_base.rstrip('/')}/{object_key}"
            return f"{s3_endpoint.rstrip('/')}/{s3_bucket}/{object_key}"
        except Exception as s3_err:
            logger.error(f"[upload] S3/R2 upload failed, fallback to local storage: {s3_err}")

    # 2. Lokal saqlash (Fallback)
    # Render'da konteyner diski efemer: bu yo'lga tushgan rasmlar keyingi
    # deploy yoki restartda yo'qoladi. Sabab ko'rinib turishi uchun log qoldiramiz.
    if not (s3_bucket and s3_access_key and s3_secret_key):
        logger.info(
            "[upload] OGOHLANTIRISH: S3/R2 sozlanmagan, rasm lokal diskka saqlanmoqda. "
            "Render'da bu fayl keyingi deploy'da yo'qoladi. "
            "S3_BUCKET / S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY ni bering."
        )

    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', folder)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file_name)
    with open(file_path, 'wb') as f:
        f.write(webp_data)

    return f"/static/uploads/{folder}/{file_name}"
