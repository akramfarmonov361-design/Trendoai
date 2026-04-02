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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
GEMINI_MODEL_BACKUP = os.getenv("GEMINI_MODEL_BACKUP", "gemini-3.1-flash-lite-preview")
AI_RETRY_ATTEMPTS = 3
AI_RETRY_DELAY = 2

# ========== TELEGRAM SOZLAMALARI ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_RETRY_ATTEMPTS = 3

# ========== ADMIN SOZLAMALARI ==========
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "trendoai2025")
SECRET_KEY = os.getenv("SECRET_KEY", "trendoai-secret-key-change-in-production")

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
CRON_SECRET = os.getenv("CRON_SECRET", "trendoai-cron-secret-2025")

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
