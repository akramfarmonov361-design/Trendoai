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
SITE_URL = os.getenv("SITE_URL", "https://www.trendoai.uz")

SITE_NAME = "TrendoAI (Trendo AI)"
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

# ========== AI SOZLAMALARI ==========
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY2") or os.getenv("GEMINI_API_KEY3")
_DEFAULT_MODEL = "gemini-3.1-flash-lite"
_DEFAULT_MODEL_BACKUP = "gemini-2.5-flash-lite"

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
AI_RETRY_ATTEMPTS = 3
AI_RETRY_DELAY = 2

# ========== TELEGRAM SOZLAMALARI ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_RETRY_ATTEMPTS = 3

# ========== ADMIN SOZLAMALARI ==========
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "trendoai2025"
DEFAULT_SECRET_KEY = "trendoai-secret-key-change-in-production"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME)
ADMIN_PASSWORD = _require_production_secret(
    "ADMIN_PASSWORD",
    os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
    DEFAULT_ADMIN_PASSWORD,
)
SECRET_KEY = _require_production_secret(
    "SECRET_KEY",
    os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY),
    DEFAULT_SECRET_KEY,
)

# ========== PUSH NOTIFICATION SOZLAMALARI ==========
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "BJt75bqZyZdfqtfNkvQUT3uZpg6ytWSi0mg9riLZl2zOTIarMwxvxJNHCc8OvfVwh8Xe2o60cYXzqa3MBKYOT8s")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgctR2TTZXKwU2B62L6mQUTlyqjdEeWBWOMD97+9Q6yjOhRANCAASbe+W6mcmXX6rXzZL0FE97maYOsrVkotJoPa4i2ZdszkyGqzMMb8STRwnPDr31cIfF3tqOtHGF86mtzASmDk/L")
VAPID_CLAIMS_SUB = "mailto:admin@trendoai.uz"

# ========== SCHEDULER SOZLAMALARI ==========
TIMEZONE = "Asia/Tashkent"
SEO_POST_HOUR = 9
SEO_POST_MINUTE = 0
MARKETING_POST_HOUR = 12
MARKETING_POST_MINUTE = 0

# ========== CRON SOZLAMALARI ==========
# Tashqi cron xizmatlari uchun secret key
DEFAULT_CRON_SECRET = "trendoai-cron-secret-2025"
CRON_SECRET = _require_production_secret(
    "CRON_SECRET",
    os.getenv("CRON_SECRET", DEFAULT_CRON_SECRET),
    DEFAULT_CRON_SECRET,
)

# ========== ANALYTICS & REMARKETING ==========
# Google Analytics 4 (G-XXXXXXXXXX formatida)
GA4_ID = os.getenv("GA4_ID")
# Google Ads Remarketing (AW-XXXXXXXXXX formatida)
GOOGLE_ADS_ID = os.getenv("GOOGLE_ADS_ID")
# Facebook Pixel ID (faqat raqamlar)
FACEBOOK_PIXEL_ID = os.getenv("FACEBOOK_PIXEL_ID", "886188897254491")

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
