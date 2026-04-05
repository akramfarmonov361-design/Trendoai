# app.py
"""
TrendoAI — Trending texnologiyalar va sun'iy intellekt haqida professional blog.
Flask asosiy fayli.
"""
import os
import re
import sys
import markdown2
from datetime import datetime
from functools import wraps
import threading
import xml.etree.ElementTree as ET
import time
import google.generativeai as genai
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# .env faylidagi o'zgaruvchilarni yuklash
load_dotenv()

# Windows kabi no-UTF8 terminallarda emoji/log sababli ilova qulamasligi uchun
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = Flask(__name__)

# Konfiguratsiya
from config import (
    SITE_URL, SITE_NAME, SITE_DESCRIPTION, DATABASE_URI, SECRET_KEY,
    ADMIN_USERNAME, ADMIN_PASSWORD, POSTS_PER_PAGE, CATEGORIES,
    GA4_ID, GOOGLE_ADS_ID, FACEBOOK_PIXEL_ID,
    CRON_SECRET, GEMINI_API_KEY, GEMINI_MODEL,
    VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIMS_SUB
)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY
app.config['CRON_SECRET'] = CRON_SECRET
app.config['GEMINI_API_KEY'] = GEMINI_API_KEY
app.config['VAPID_PUBLIC_KEY'] = VAPID_PUBLIC_KEY
app.config['VAPID_PRIVATE_KEY'] = VAPID_PRIVATE_KEY
app.config['VAPID_CLAIMS_SUB'] = VAPID_CLAIMS_SUB

# PostgreSQL connection pool sozlamalari - ulanish uzilganda qayta ulanish
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Har bir so'rovdan oldin ulanishni tekshirish
    'pool_recycle': 300,    # 5 daqiqada ulanishni yangilash
    'pool_size': 5,         # Ulanishlar soni
    'max_overflow': 10,     # Qo'shimcha ulanishlar
}

db = SQLAlchemy(app)


# ========== SERVICE DATA (For Landing Pages) ==========
SERVICES_DATA = {
    'ai_content': {
        'key': 'ai_content',
        'title': 'AI Kontent Generatsiya',
        'icon': '🤖',
        'description': "Sun'iy intellekt yordamida SEO-optimallashtirilgan blog maqolalari va marketing kontentlari.",
        'features': [
            'Avtomatik blog postlar va maqolalar',
            'SEO kalit so\'zlar tahlili va integratsiyasi',
            'Telegram kanallarga avtomatik yuborish',
            'Ko\'p tilli kontent yaratish (Uz, Ru, En)'
        ],
        'price': '500,000 so\'m/oy dan',
        'full_description': "TrendoAI taklif etayotgan AI Kontent Generatsiya xizmati sizning biznesingiz uchun avtomatik, sifatli va SEO-optimallashtirilgan kontent yaratishga yordam beradi. Bizning tizim Google-ning eng so'nggi Gemini AI texnologiyasi asosida ishlaydi va o'zbek tilidagi eng mukammal, inson tomonidan yozishga o'xshash kontentni taqdim etadi.",
        'meta_desc': "AI yordamida professional blog va marketing kontentlari yaratish. TrendoAI AI-agentlari biznesingiz uchun 24/7 ishlaydi."
    },
    'telegram_bot': {
        'key': 'telegram_bot',
        'title': 'Telegram Botlar',
        'icon': '📱',
        'description': "Biznesingiz uchun murakkab funksional va foydalanuvchilarga qulay Telegram botlar.",
        'features': [
            'Telegram Mini App (Web App) yaratish',
            'To\'lov tizimlari (Click, Payme) integratsiyasi',
            'Boshqaruv paneli (Admin Panel)',
            'Mijozlar bazasi va statistika'
        ],
        'price': '1,500,000 so\'m dan',
        'full_description': "Sizning biznes jarayonlaringizni avtomatlashtirish uchun murakkab va foydali Telegram botlarni ishlab chiqamiz. Savdo botlari, mijozlarni qo'llab-quvvatlash botlari, e-commerce Mini Applar va maxsus tizimlar - barchasini TrendoAI jamoasi taqdim etadi.",
        'meta_desc': "Telegram botlar va Mini Applar ishlab chiqish. Biznesingizni Telegram orqali avtomatlashtiring va savdoni oshiring."
    },
    'web_site': {
        'key': 'web_site',
        'title': 'Web Saytlar',
        'icon': '🌐',
        'description': "Zamonaviy, o'ta tez va SEO-optimallashtirilgan professional veb-saytlar.",
        'features': [
            'Landing Page (Bir sahifali sayt)',
            'Korporativ va brend saytlari',
            'E-commerce (Internet do\'konlar)',
            'Zamonaviy UI/UX va mobil moslashuv'
        ],
        'price': '2,000,000 so\'m dan',
        'full_description': "Biz zamonaviy texnologiyalar (Next.js, React, Flask, Node.js) yordamida har qanday murakkablikdagi veb-saytlarni yaratamiz. Saytlarimiz tezligi, Google qidiruv tizimi uchun to'liq optimalligi va brendingizga mos dizayni bilan ajralib turadi.",
        'meta_desc': "Professional veb-saytlar yaratish. Landing page, korporativ saytlar va internet do'konlar. SEO va mobil adaptiv."
    },
    'ai_chatbot': {
        'key': 'ai_chatbot',
        'title': 'AI Chatbot Yaratish',
        'icon': '🧠',
        'description': "Mijozlaringizga sun'iy intellekt orqali 24/7 xizmat ko'rsatish tizimi.",
        'features': [
            'Intellektual javoblar (LLM asosida)',
            'Mavjud ma\'lumotlar bazasi bilan integratsiya',
            'Telegram, WhatsApp va Sayt uchun yagona bot',
            'Mijozlar bilan insondek muloqot'
        ],
        'price': '2,500,000 so\'m dan',
        'full_description': "Mijozlaringiz bilan kechayu-kunduz muloqot qiladigan, ularning savollariga aniq va aqlli javob beradigan AI chatbotlarni yarating. Gemini yoki ChatGPT asosidagi ushbu tizimlar xodimlar xarajatini kamaytiradi va mijozlar talabiga tezkor javob beradi.",
        'meta_desc': "Aqlli AI Chatbotlar va virtual assistentlar yaratish. Biznesingiz uchun sun'iy intellektli mijozlar xizmati."
    },
    'smm': {
        'key': 'smm',
        'title': 'SMM Avtomatlashtirish',
        'icon': '📢',
        'description': "Ijtimoiy tarmoqlar uchun AI agentlar yordamida avtomatik boshqaruv.",
        'features': [
            'Postlarni AI yordamida rejalashtirish',
            'Kreativ rasm va matnlar generatsiyasi',
            'Avtomatik ijtimoiy tarmoq tahlili',
            'Kross-platforma posting (TG, FB, IG)'
        ],
        'price': '800,000 so\'m/oy dan',
        'full_description': "Ijtimoiy tarmoqlardagi faolligingizni aqlli avtomatlashtirish orqali yanada samarali qiling. Bizning AI tizimlarimiz trendlarni kuzatadi, matn yozadi va brendingiz uchun foydali auditoriyani jalb qilishga yordam beradi.",
        'meta_desc': "AI SMM avtomatlashtirish xizmatlari. Kontent yaratish va ijtimoiy tarmoqlarni avtomatik boshqarish."
    },
    'consulting': {
        'key': 'consulting',
        'title': 'IT Konsalting',
        'icon': '💡',
        'description': "Raqamli transformatsiya va sun'iy intellektni joriy qilish bo'yicha maslahatlar.",
        'features': [
            'Biznes jarayonlarni texnik audit qilish',
            'AI texnologiyalarini rejalashtirish',
            'Dasturiy mahsulotlar arxitekturasi',
            'Top-menejment uchun texnik treninglar'
        ],
        'price': '500,000 so\'m/soat dan',
        'full_description': "Sizning g'oyangizni qanday qilib texnologiya orqali amalga oshirish yoki mavjud tizimingizni qanday optimallashtirish bo'yicha professional maslahat beramiz. AI asrida biznesingizni yangi bosqichga olib chiqishda yo'l ko'rsatamiz.",
        'meta_desc': "Professional IT konsalting va AI audit xizmatlari. Biznesingizni raqamli transformatsiya qiling."
    },
    'crm_integration': {
        'key': 'crm_integration',
        'title': 'CRM Integratsiya',
        'icon': '⚙️',
        'description': "Sotuv jarayonlarini avtomatlashtirish va mijozlar bazasini tartibga solish.",
        'features': [
            'AmoCRM / Bitrix24 integratsiyasi',
            'Telegram botdan CRM ga lidlar tushishi',
            'Sotuv voronkalarini avtomatlashtirish',
            'Menejerlar faoliyatini nazorat qilish'
        ],
        'price': '2,000,000 so\'m',
        'discount': {
            'percent': 30,
            'until': '1-aprel'
        },
        'full_description': "Biznesingizda tartib o'rnating! Buyurtmalarni Excel yoki daftarda emas, zamonaviy CRM tizimlarida yuriting. Biz sizning Telegram botingiz, saytingiz va Instagram sahifangizni yagona CRM bazasiga ulab beramiz. Har bir mijoz nazoratda bo'ladi.",
        'meta_desc': "CRM tizimlarini (AmoCRM, Bitrix24) joriy qilish va integratsiya xizmatlari. Biznes jarayonlarni avtomatlashtirish."
    },
    'voice_ai': {
        'key': 'voice_ai',
        'title': 'AI Ovozli Assistent',
        'icon': '📞',
        'description': "Call-markazlar o'rniga sun'iy intellekt asosidagi aqlli ovozli operatorlar.",
        'features': [
            'Kiruvchi qo\'ng\'iroqlarga javob berish',
            'Mijozlarga avtomatik qo\'ng\'iroq qilish (Cold calling)',
            'Inson ovozidan farq qilmaydigan muloqot',
            '24/7 ish tartibi'
        ],
        'price': '3,000,000 so\'m dan',
        'discount': {
            'percent': 30,
            'until': '1-aprel'
        },
        'full_description': "Endi katta call-markaz ushlash shart emas. Bizning AI ovozli assistentlarimiz mijozlaringiz bilan xuddi insondek gaplashadi, savollarga javob beradi va buyurtma qabul qiladi. Bu xarajatlarni 70% ga qisqartiradi.",
        'meta_desc': "AI ovozli assistentlar va virtual call-markaz xizmatlari. Sun'iy intellekt orqali mijozlar bilan ovozli muloqot."
    },
    'marketplace_auto': {
        'key': 'marketplace_auto',
        'title': 'Marketpleys Avtomatlashtirish',
        'icon': '🛍️',
        'description': "Uzum va Wildberries da savdo qiluvchilar uchun maxsus botlar va dasturlar.",
        'features': [
            'Tovarlarni avtomatik yuklash',
            'Raqobatchilar narxini kuzatish',
            'Sotuvlar analitikasi (Bot orqali)',
            'Ombor qoldiqlarini boshqarish'
        ],
        'price': '1,500,000 so\'m',
        'discount': {
            'percent': 30,
            'until': '1-aprel'
        },
        'full_description': "E-tijoratda vaqt bu pul. Uzum Market yoki Wildberries do'koningizni boshqarishni avtomatlashtiring. Bizning yechimlarimiz orqali siz narxlarni tezkor o'zgartirishingiz va kunlik foydani telefoningizdan kuzatib borishingiz mumkin.",
        'meta_desc': "Uzum va Wildberries marketpleyslari uchun avtomatlashtirish xizmatlari. Savdoni oshirish uchun maxsus dasturlar."
    },
    'data_analytics': {
        'key': 'data_analytics',
        'title': 'Data Analitika',
        'icon': '📊',
        'description': "Biznes ko'rsatkichlarini real vaqtda kuzatib borish uchun Dashboardlar.",
        'features': [
            'Sotuv va xarajatlar Dashboardi',
            'Telegram orqali kunlik hisobotlar',
            'Power BI / Google Data Studio integratsiyasi',
            'Marketing samaradorligi tahlili'
        ],
        'price': '2,500,000 so\'m',
        'discount': {
            'percent': 30,
            'until': '1-aprel'
        },
        'full_description': "Raqamlarga asoslanib qaror qabul qiling. Biz sizning barcha ma'lumotlaringizni (Excel, CRM, 1C) yagona tushunarli Dashboardga yig'ib beramiz. Endi biznesingiz holatini bir qarashda tushunasiz.",
        'meta_desc': "Biznes uchun Data Analitika va Dashboardlar yaratish. Power BI va Google Data Studio xizmatlari."
    },
    'ai_education': {
        'key': 'ai_education',
        'title': 'AI Ta\'lim (Korporativ)',
        'icon': '🎓',
        'description': "Xodimlaringizga sun'iy intellekt (ChatGPT, Midjourney) dan foydalanishni o'rgatamiz.",
        'features': [
            'Prompt Engineering asoslari',
            'Ish jarayonida AI dan foydalanish',
            'Marketing va SMM uchun AI',
            'Amaliy master-klasslar'
        ],
        'price': '1,000,000 so\'m (guruh)',
        'discount': {
            'percent': 30,
            'until': '1-aprel'
        },
        'full_description': "Raqobatchilardan oldinda bo'ling! Xodimlaringizga sun'iy intellektdan foydalanishni o'rgating va ish samaradorligini 10 barobar oshiring. Biz har bir soha (sotuv, marketing, HR) uchun maxsus o'quv dasturlarini taklif qilamiz.",
        'meta_desc': "Sun'iy intellekt (AI) bo'yicha korporativ treninglar va kurslar. ChatGPT va Midjourney dan foydalanishni o'rganing."
    }
}


# ========== DATABASE MODELS ==========


class Service(db.Model):
    """Xizmatlar modeli"""
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    full_description = db.Column(db.Text)
    price = db.Column(db.String(100))
    icon = db.Column(db.String(50))
    image_url = db.Column(db.String(500))
    features = db.Column(db.Text) # JSON string sifatida saqlanadi
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    meta_desc = db.Column(db.String(300))
    discount_percent = db.Column(db.Integer, default=0)
    discount_until = db.Column(db.String(50))

    def get_features_list(self):
        if not self.features: return []
        import json
        try:
            return json.loads(self.features)
        except:
            return self.features.split(',')


class Post(db.Model):
    """Blog post modeli"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=True)
    content = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Texnologiya')
    keywords = db.Column(db.String(250), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    image_prompt = db.Column(db.Text, nullable=True)
    views = db.Column(db.Integer, default=0)
    reading_time = db.Column(db.Integer, default=5)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    def __repr__(self):
        return f'<Post {self.title}>'
    
    def calculate_reading_time(self):
        """O'qish vaqtini hisoblash (250 so'z/daqiqa)"""
        word_count = len(self.content.split())
        return max(1, round(word_count / 250))
    
    def generate_slug(self):
        """URL uchun slug yaratish"""
        slug = self.title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        return f"{slug}-{self.id}"
    
    def to_dict(self):
        """API uchun dict formatiga o'tkazish"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'topic': self.topic,
            'category': self.category,
            'keywords': self.keywords,
            'image_prompt': self.image_prompt,
            'views': self.views,
            'reading_time': self.reading_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Order(db.Model):
    """Xizmatga buyurtma modeli"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service = db.Column(db.String(50), nullable=False)
    service_name = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.String(50), nullable=True)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='new')  # new, contacted, completed, cancelled
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    def __repr__(self):
        return f'<Order {self.id} - {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'service': self.service,
            'service_name': self.service_name,
            'budget': self.budget,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class TelegramUser(db.Model):
    """Bot bilan muloqot qilgan foydalanuvchilar (marketing uchun)"""
    id = db.Column(db.Integer, primary_key=True)
    tg_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=True)
    full_name = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    last_interaction = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    def __repr__(self):
        return f'<TelegramUser {self.tg_id}>'

class MenuCategory(db.Model):
    """Menyu kategoriyalari"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    emoji = db.Column(db.String(10), default='📋')
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

class MenuItem(db.Model):
    """Bot menyu elementlari"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)  # so'mda
    category = db.Column(db.String(50), default='taom')
    emoji = db.Column(db.String(10), default='🍽')
    image_url = db.Column(db.String(500))
    is_available = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class BotOrder(db.Model):
    """Telegram bot orqali kelgan menyu buyurtmalari"""
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True)  # #TRD-0001
    tg_id = db.Column(db.BigInteger, nullable=False)
    tg_username = db.Column(db.String(100))
    customer_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    items_json = db.Column(db.Text)  # JSON: [{"id":1, "name":"...", "qty":2, "price":25000}]
    total_amount = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='new')  # new -> confirmed -> preparing -> delivering -> done / cancelled
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

class Portfolio(db.Model):
    """Portfolio loyihalar modeli (SEO-optimized)"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=True)  # SEO URL
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='web')  # bot, web, ai, mobile
    emoji = db.Column(db.String(10), default='🚀')
    technologies = db.Column(db.String(250))  # vergul bilan ajratilgan
    link = db.Column(db.String(500))
    image_url = db.Column(db.String(500))  # Rasm URL
    is_featured = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=True)
    # SEO fields
    meta_description = db.Column(db.Text)  # SEO tavsifi (uzun bo'lishi mumkin)
    meta_keywords = db.Column(db.String(250))  # SEO kalit so'zlar
    details = db.Column(db.Text)  # Batafsil ma'lumot (Markdown)
    features = db.Column(db.Text)  # Loyiha imkoniyatlari (vergul bilan ajratilgan)
    price = db.Column(db.String(100), nullable=True)  # Narxi - nullable for backward compatibility
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    @property
    def safe_price(self):
        """Safely get price"""
        try:
            return self.price or ''
        except:
            return ''
    
    def __repr__(self):
        return f'<Portfolio {self.title}>'
    
    def generate_slug(self):
        """URL uchun slug yaratish"""
        slug = self.title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        return f"{slug}-{self.id}"
    
    def to_dict(self):
        # Use getattr for new columns to handle missing DB columns gracefully
        details = getattr(self, 'details', None) or ''
        features = getattr(self, 'features', None) or ''
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'category': self.category,
            'emoji': self.emoji,
            'technologies': self.technologies.split(',') if self.technologies else [],
            'link': self.link,
            'image_url': self.image_url,
            'is_featured': self.is_featured,
            'details': details,
            'details_html': markdown2.markdown(details) if details else "",
            'features': features.split(',') if features else [],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }



class PushSubscription(db.Model):
    """Web Push obunachilari"""
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_json(self):
        return {
            'endpoint': self.endpoint,
            'keys': {
                'p256dh': self.p256dh,
                'auth': self.auth
            }
        }


class Lead(db.Model):
    """Lead Magnet va Chatbot orqali yig'ilgan sovuq klientlar (bazamiz)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False) # tel yoki telegram username
    source = db.Column(db.String(50), default='Lead Magnet') # Lead Magnet, AI Chat, etc
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact': self.contact,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ========== TEMPLATE FILTERS ==========

@app.template_filter('markdown')
def markdown_filter(s):
    """Markdown'ni HTML'ga o'girish"""
    return markdown2.markdown(s, extras=["fenced-code-blocks", "tables", "break-on-newline"])


# ========== CONTEXT PROCESSORS ==========

@app.context_processor
def inject_globals():
    """Barcha template'larga global o'zgaruvchilar"""
    # Debug log (Render loglarida ko'rinadi)
    if not hasattr(app, '_log_shown'):
        print(f"DEBUG: FACEBOOK_PIXEL_ID={FACEBOOK_PIXEL_ID}")
        print(f"DEBUG: GA4_ID={GA4_ID}")
        app._log_shown = True
        
    return {
        'config': {
            'SITE_NAME': SITE_NAME,
            'SITE_DESCRIPTION': SITE_DESCRIPTION,
            'VAPID_PUBLIC_KEY': app.config.get('VAPID_PUBLIC_KEY')
        },
        'GA4_ID': GA4_ID,
        'GOOGLE_ADS_ID': GOOGLE_ADS_ID,
        'FACEBOOK_PIXEL_ID': FACEBOOK_PIXEL_ID,
        'categories': CATEGORIES,
        'now': datetime.now()
    }


# ========== AUTH HELPERS ==========

def login_required(f):
    """Admin sahifalar uchun login tekshirish"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Iltimos, avval tizimga kiring.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ========== PUBLIC ROUTES ==========

@app.route('/')
def index():
    """Bosh sahifa — xizmatlar sahifasi"""
    all_services = Service.query.filter_by(is_active=True).order_by(Service.order.asc()).all()
    return render_template('services.html', services=all_services)


@app.route('/blog')
def blog():
    """Blog sahifasi — barcha postlar ro'yxati"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)
    
    query = Post.query.filter_by(is_published=True)
    
    if category:
        query = query.filter_by(category=category)
    
    pagination = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=POSTS_PER_PAGE, error_out=False
    )
    
    # Eng ko'p o'qilgan postlar (Top 5)
    popular_posts = Post.query.filter_by(is_published=True).order_by(
        Post.views.desc()
    ).limit(5).all()
    
    return render_template('index.html', 
                          posts=pagination.items, 
                          pagination=pagination,
                          popular_posts=popular_posts)


@app.route('/post/<int:post_id>')
def post(post_id):
    """ID orqali post sahifasi - slug ga redirect"""
    post = Post.query.get_or_404(post_id)
    if post.slug:
        return redirect(url_for('post_by_slug', slug=post.slug), code=301)
    
    # Agar slug yo'q bo'lsa, oddiy ko'rsatish
    post.views = (post.views or 0) + 1
    db.session.commit()
    
    related_posts = Post.query.filter(
        Post.id != post.id,
        Post.category == post.category,
        Post.is_published == True
    ).order_by(Post.created_at.desc()).limit(3).all()
    
    return render_template('post.html', post=post, related_posts=related_posts)


@app.route('/blog/<slug>')
def post_by_slug(slug):
    """Slug orqali post sahifasi (SEO-friendly)"""
    post = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
    
    # Ko'rishlar sonini oshirish
    post.views = (post.views or 0) + 1
    db.session.commit()
    
    # O'xshash postlarni olish (same category)
    related_posts = Post.query.filter(
        Post.id != post.id,
        Post.category == post.category,
        Post.is_published == True
    ).order_by(Post.created_at.desc()).limit(3).all()
    
    return render_template('post.html', post=post, related_posts=related_posts)


@app.route('/search')
def search():
    """Qidiruv sahifasi"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if query:
        posts = Post.query.filter(
            Post.is_published == True,
            (Post.title.contains(query) | Post.content.contains(query) | Post.keywords.contains(query))
        ).order_by(Post.created_at.desc()).paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    else:
        posts = None
    
    return render_template('search.html', posts=posts, query=query)


@app.route('/about')
def about():
    """Biz haqimizda sahifasi"""
    post_count = Post.query.filter_by(is_published=True).count()
    return render_template('about.html', post_count=post_count)


@app.route('/services')
def services():
    """Legacy xizmatlar URL'ini bosh sahifaga yo'naltirish"""
    return redirect(url_for('index'), code=301)


@app.route('/services/<service_key>')
def service_detail(service_key):
    """Xizmat batafsil sahifasi"""
    service = Service.query.filter_by(slug=service_key).first_or_404()
    
    # Portfolio projects related to this service (simple matching by category)
    # Mapping service keys to portfolio categories
    category_map = {
        'web_site': 'web',
        'telegram_bot': 'bot',
        'smm': 'smm',
        'design': 'design',
        'ai': 'ai'
    }
    
    # Try to match category, if not found use generic 'web' or search by slug parts
    cat = category_map.get(service.slug)
    if not cat:
        if 'bot' in service.slug: cat = 'bot'
        elif 'ai' in service.slug: cat = 'ai'
        
    related_portfolio = []
    if cat:
        related_portfolio = Portfolio.query.filter_by(category=cat, is_published=True).limit(3).all()

    all_services = Service.query.filter_by(is_active=True).order_by(Service.order.asc()).all()

    return render_template('service_detail.html', 
                         service=service, 
                         related_portfolio=related_portfolio,
                         services=all_services)


@app.route('/portfolio')
def portfolio():
    """Portfolio sahifasi"""
    portfolios = Portfolio.query.filter_by(is_published=True).order_by(Portfolio.created_at.desc()).all()
    return render_template('portfolio.html', portfolios=portfolios)


@app.route('/portfolio/project/<slug>')
def portfolio_item(slug):
    """Loyiha batafsil sahifasi (Ads Landing Page)"""
    item = Portfolio.query.filter_by(slug=slug, is_published=True).first_or_404()
    
    # O'xshash loyihalar (same category)
    related_items = Portfolio.query.filter(
        Portfolio.id != item.id,
        Portfolio.category == item.category,
        Portfolio.is_published == True
    ).limit(3).all()
    
    return render_template('portfolio_detail.html', item=item, related_items=related_items)


@app.route('/order')
def order_page():
    """Alohida buyurtma sahifasi"""
    return render_template('order.html')


@app.route('/submit-order', methods=['POST'])
def submit_order():
    """Xizmatga yozilish formasi"""
    name = request.form.get('name')
    phone = request.form.get('phone')
    service = request.form.get('service')
    budget = request.form.get('budget', '')
    message = request.form.get('message', '')
    
    # Service nomlarini o'zbekchaga o'girish
    service_names = {
        'ai_content': 'AI Kontent Generatsiya',
        'telegram_bot': 'Telegram Bot',
        'web_site': 'Web Sayt',
        'consulting': 'IT Konsalting',
        'smm': 'SMM Avtomatlashtirish',
        'ai_chatbot': 'AI Chatbot'
    }
    
    service_name = service_names.get(service, service)
    
    # Bazaga saqlash
    order = Order(
        name=name,
        phone=phone,
        service=service,
        service_name=service_name,
        budget=budget,
        message=message,
        status='new'
    )
    db.session.add(order)
    db.session.commit()
    
    # Telegram Admin ga yuborish
    try:
        from telegram_poster import send_to_admin
        
        budget_text = budget if budget else "Ko'rsatilmagan"
        message_text = message if message else "Yo'q"
        time_text = datetime.now().strftime('%d.%m.%Y %H:%M')
        
        order_message = f"""
🆕 *Yangi Buyurtma #{order.id}*

👤 *Ism:* {name}
📞 *Telefon:* {phone}
🛠️ *Xizmat:* {service_name}
💰 *Byudjet:* {budget_text}

💬 *Xabar:*
{message_text}

📅 *Vaqt:* {time_text}

🔗 Admin panel: /admin/orders
"""
        if send_to_admin(order_message):
            try:
                # Log to console/file
                print(f"✅ Order #{order.id} sent to Admin")
            except:
                pass
        else:
            print(f"❌ Failed to send Order #{order.id} to Admin")
    except Exception as e:
        print(f"Telegram yuborishda xato: {e}")
    
    flash(f'Rahmat, {name}! Arizangiz qabul qilindi. Tez orada siz bilan boglanamiz!', 'success')
    return redirect(url_for('index'))


# ========== ADMIN ROUTES ==========

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login sahifasi"""
    if session.get('logged_in'):
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('Tizimga muvaffaqiyatli kirdingiz!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Login yoki parol noto\'g\'ri!', 'error')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    """Chiqish"""
    session.clear()
    flash('Tizimdan chiqdingiz.', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    # Post statistikasi
    total_posts = Post.query.count()
    published_posts = Post.query.filter_by(is_published=True).count()
    total_views = db.session.query(db.func.sum(Post.views)).scalar() or 0
    
    # Buyurtmalar statistikasi
    total_orders = Order.query.count()
    new_orders = Order.query.filter_by(status='new').count()
    
    # Portfolio statistikasi
    total_portfolio = Portfolio.query.count()
    
    # So'nggi postlar
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    
    # Eng ko'p ko'rilgan postlar
    top_posts = Post.query.filter_by(is_published=True).order_by(Post.views.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                          total_posts=total_posts,
                          published_posts=published_posts,
                          total_views=total_views,
                          total_orders=total_orders,
                          new_orders=new_orders,
                          total_portfolio=total_portfolio,
                          recent_posts=recent_posts,
                          top_posts=top_posts)

# ========== BOT ADMIN ROUTES ==========

@app.route('/admin/bot-orders')
@login_required
def admin_bot_orders():
    """Bot orqali tushgan menyu buyurtmalarini boshqarish"""
    orders = BotOrder.query.order_by(BotOrder.created_at.desc()).all()
    return render_template('admin/bot_orders.html', orders=orders)

@app.route('/api/bot-order-status', methods=['POST'])
@login_required
def update_bot_order_status():
    """Bot buyurtma statusini o'zgartirish (AJAX)"""
    try:
        order_id = request.json.get('order_id') or request.form.get('order_id')
        status = request.json.get('status') or request.form.get('status')
        order = BotOrder.query.get(order_id)
        if order:
            order.status = status
            db.session.commit()
            
            # Mijozga status o'zgargani haqida xabar berish
            from telegram_poster import bot
            if bot and order.tg_id:
                status_text = {
                    'confirmed': "✅ Qabul qilindi",
                    'preparing': "👨‍🍳 Tayyorlanmoqda",
                    'delivering': "🛵 Yetkazilmoqda",
                    'done': "🎉 Yetkazib berildi",
                    'cancelled': "❌ Bekor qilindi"
                }.get(status, status)
                
                msg = f"📋 Buyurtma {order.order_number} yangilandi!\n"
                msg += f"📦 Status: *{status_text}*"
                try:
                    bot.send_message(order.tg_id, msg, parse_mode='Markdown')
                except Exception as e:
                    print(f"Failed to send status update to customer: {e}")
            
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Order not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/menu', methods=['GET', 'POST'])
@login_required
def admin_menu():
    """Menyu boshqaruvi (mahsulotlar va kategoriyalar)"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_category':
            name = request.form.get('name')
            emoji = request.form.get('emoji', '📋')
            new_cat = MenuCategory(name=name, emoji=emoji)
            db.session.add(new_cat)
            db.session.commit()
            flash('Kategoriya qo\'shildi', 'success')
            
        elif action == 'add_item':
            name = request.form.get('name')
            price = int(request.form.get('price', 0))
            category = request.form.get('category')
            description = request.form.get('description', '')
            emoji = request.form.get('emoji', '🍽')
            new_item = MenuItem(name=name, price=price, category=category, description=description, emoji=emoji)
            db.session.add(new_item)
            db.session.commit()
            flash('Mahsulot qo\'shildi', 'success')
            
        elif action == 'delete_item':
            item_id = request.form.get('item_id')
            item = MenuItem.query.get(item_id)
            if item:
                db.session.delete(item)
                db.session.commit()
                flash('Mahsulot o\'chirildi', 'success')
                
        return redirect(url_for('admin_menu'))

    items = MenuItem.query.order_by(MenuItem.category, MenuItem.order_index).all()
    categories = MenuCategory.query.order_by(MenuCategory.order_index).all()
    return render_template('admin/menu_manage.html', items=items, categories=categories)


# ========== SERVICE ADMIN ROUTES ==========


@app.route('/admin/services/generate', methods=['POST'])
@login_required
def admin_service_generate():
    """AI yordamida xizmat ma'lumotlarini generatsiya qilish"""
    try:
        from ai_generator import model
        import json
        
        title = request.json.get('title', '')
        if not title:
            return jsonify({'error': 'Sarlavha (title) kiritilmagan'}), 400
        
        prompt = f"""
Sen professional IT xizmatlar uchun kontent yozuvchisan. O'zbek tilida yoz.
Quyidagi xizmat uchun kontent yarat:

Xizmat nomi: {title}

Quyidagi formatda JSON qaytaring (faqat JSON, boshqa matn yo'q):
{{
    "description": "1-2 gaplik jozibali qisqa tavsif (tagline)",
    "full_description": "3-4 gaplik to'liq professional tavsif. Mijozga qanday foyda keltirishini yoz.",
    "features": ["Xususiyat 1", "Xususiyat 2", "Xususiyat 3", "Xususiyat 4"],
    "meta_desc": "SEO uchun 150 belgidan kam meta description",
    "icon": "Mos emoji (bitta)",
    "slug": "english-slug-format"
}}
"""
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # JSON ni ajratib olish
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        
        data = json.loads(text)
        return jsonify(data)
        
    except Exception as e:
        print(f"AI Generation Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/services')
@login_required
def admin_services():
    """Xizmatlar ro'yxati"""
    services = Service.query.order_by(Service.order.asc()).all()
    return render_template('admin/services.html', services=services)

@app.route('/admin/services/new', methods=['GET', 'POST'])
@login_required
def admin_service_new():
    """Yangi xizmat qo'shish"""
    if request.method == 'POST':
        try:
            slug = request.form.get('slug')
            if not slug:
                # Auto generate basic slug from title
                import re
                slug = re.sub(r'[^a-z0-9-]', '', request.form.get('title').lower().replace(' ', '-'))
            
            service = Service(
                slug=slug,
                title=request.form.get('title'),
                description=request.form.get('description'),
                full_description=request.form.get('full_description'),
                price=request.form.get('price'),
                icon=request.form.get('icon', '🚀'),
                image_url=request.form.get('image_url'),
                features=request.form.get('features'),
                is_active=request.form.get('is_active') == 'on',
                order=int(request.form.get('order', 0)),
                meta_desc=request.form.get('meta_desc'),
                discount_percent=int(request.form.get('discount_percent', 0)),
                discount_until=request.form.get('discount_until')
            )
            db.session.add(service)
            db.session.commit()
            flash(f'"{service.title}" muvaffaqiyatli qo\'shildi!', 'success')
            return redirect(url_for('admin_services'))
        except Exception as e:
            flash(f'Xatolik: {e}', 'error')
            
    return render_template('admin/service_form.html', service=None)

@app.route('/admin/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_service_edit(service_id):
    """Xizmatni tahrirlash"""
    service = Service.query.get_or_404(service_id)
    
    if request.method == 'POST':
        try:
            service.slug = request.form.get('slug')
            service.title = request.form.get('title')
            service.description = request.form.get('description')
            service.full_description = request.form.get('full_description')
            service.price = request.form.get('price')
            service.icon = request.form.get('icon')
            service.image_url = request.form.get('image_url')
            service.features = request.form.get('features')
            service.is_active = request.form.get('is_active') == 'on'
            service.order = int(request.form.get('order', 0))
            service.meta_desc = request.form.get('meta_desc')
            service.discount_percent = int(request.form.get('discount_percent', 0))
            service.discount_until = request.form.get('discount_until')
            
            db.session.commit()
            flash(f'"{service.title}" yangilandi!', 'success')
            return redirect(url_for('admin_services'))
        except Exception as e:
            flash(f'Xatolik: {e}', 'error')
            
    return render_template('admin/service_form.html', service=service)

@app.route('/admin/services/<int:service_id>/delete', methods=['POST'])
@login_required
def admin_service_delete(service_id):
    """Xizmatni o'chirish"""
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash('Xizmat o\'chirildi!', 'success')
    return redirect(url_for('admin_services'))


# ========== POST ADMIN ROUTES ==========
@app.route('/admin/posts')
@login_required
def admin_posts():
    """Barcha postlarni boshqarish"""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/posts.html', posts=posts)


@app.route('/admin/orders')
@login_required
def admin_orders():
    """Barcha buyurtmalarni ko'rish"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', None)
    
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Statistika
    new_count = Order.query.filter_by(status='new').count()
    total_count = Order.query.count()
    
    return render_template('admin/orders.html', 
                          orders=orders, 
                          new_count=new_count,
                          total_count=total_count,
                          current_status=status_filter)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
def admin_update_order_status(order_id):
    """Buyurtma statusini yangilash"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status in ['new', 'contacted', 'completed', 'cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Buyurtma #{order.id} statusi yangilandi!', 'success')
    
    return redirect(url_for('admin_orders'))


@app.route('/admin/orders/<int:order_id>/delete', methods=['POST'])
@login_required
def admin_delete_order(order_id):
    """Buyurtmani o'chirish"""
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash(f'Buyurtma #{order_id} o\'chirildi!', 'success')
    return redirect(url_for('admin_orders'))




def notify_all_subscribers(title, message, url):
    """Barcha obunachilarga push xabar yuborish"""
    try:
        from pywebpush import webpush, WebPushException
        import json
        import tempfile

        vapid_private_key_path = app.config['VAPID_PRIVATE_KEY']
        temp_pem_path = None

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
                print(f"VAPID Temp file error: {e}")
                return 0

        subscriptions = PushSubscription.query.all()
        if not subscriptions:
            print("[push] Faol obunachilar topilmadi")
            return 0

        count = 0

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info=sub.to_json(),
                    data=json.dumps({'title': title, 'body': message, 'url': url}),
                    vapid_private_key=vapid_private_key_path,
                    vapid_claims={
                        'sub': app.config.get('VAPID_CLAIMS_SUB', 'mailto:admin@trendoai.uz')
                    }
                )
                count += 1
            except WebPushException as ex:
                status_code = getattr(getattr(ex, 'response', None), 'status_code', None)
                print(f"[push] WebPush xatosi ({status_code}): {ex}")
                if status_code in (404, 410):
                    db.session.delete(sub)
            except Exception as e:
                print(f"[push] Individual push error: {e}")

        db.session.commit()

        if temp_pem_path and os.path.exists(temp_pem_path):
            try:
                os.unlink(temp_pem_path)
            except Exception:
                pass

        print(f"[push] {count}/{len(subscriptions)} ta obunachiga xabar yuborildi")
        return count
    except Exception as e:
        print(f"Push notification error: {e}")
        return 0
@app.route('/admin/posts/new', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    """Yangi post yaratish"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        topic = request.form.get('topic', 'Umumiy')
        category = request.form.get('category', 'Texnologiya')
        keywords = request.form.get('keywords', '')
        image_url = request.form.get('image_url', '')
        image_prompt = request.form.get('image_prompt', '').strip()
        if not image_prompt:
            try:
                from image_fetcher import build_image_prompt
                image_prompt = build_image_prompt(topic=topic, title=title, category=category)
            except Exception:
                image_prompt = ''
        is_published = request.form.get('is_published') == 'on'
        
        post = Post(
            title=title,
            content=content,
            topic=topic,
            category=category,
            keywords=keywords,
            image_url=image_url,
            image_prompt=image_prompt,
            is_published=is_published
        )
        post.reading_time = post.calculate_reading_time()
        
        db.session.add(post)
        db.session.commit()
        
        post.slug = post.generate_slug()
        db.session.commit()
        
        # Avtomatik Telegram + Push xabar yuborish
        if is_published:
            try:
                post_url = url_for('post_by_slug', slug=post.slug, _external=True)

                # Telegram kanalga yuborish
                from telegram_poster import send_photo_to_channel, send_to_telegram_channel

                tg_message = f"""📝 *Yangi Maqola!*

*{title}*

🏷 Kategoriya: {category}
⏱ O'qish uchun tayyor

🔗 [Maqolani o'qish]({post_url})

#TrendoAI #Texnologiya"""

                telegram_sent = (
                    send_photo_to_channel(image_url, tg_message)
                    if image_url else
                    send_to_telegram_channel(tg_message)
                )

                if telegram_sent:
                    print(f"Telegramga post yuborildi: Post ID {post.id}")
                else:
                    print(f"Telegramga post yuborilmadi: Post ID {post.id}")

                notify_all_subscribers(
                    title=f"🆕 Yangi Maqola: {title}",
                    message=f"{category} | {topic}\nO'qish uchun bosing!",
                    url=post_url
                )
            except Exception as e:
                print(f"Auto push/telegram error: {e}")
        
        flash('Post muvaffaqiyatli yaratildi!', 'success')
        return redirect(url_for('admin_posts'))
    
    return render_template('admin/edit_post.html', post=None, categories=CATEGORIES)


@app.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    """Postni tahrirlash"""
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.topic = request.form.get('topic')
        post.category = request.form.get('category')
        post.keywords = request.form.get('keywords')
        post.image_url = request.form.get('image_url', '')
        post.image_prompt = request.form.get('image_prompt', '').strip()
        post.is_published = request.form.get('is_published') == 'on'
        post.reading_time = post.calculate_reading_time()
        
        db.session.commit()
        
        flash('Post muvaffaqiyatli yangilandi!', 'success')
        return redirect(url_for('admin_posts'))
    
    return render_template('admin/edit_post.html', post=post, categories=CATEGORIES)


@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    """Postni o'chirish"""
    try:
        post = Post.query.get_or_404(post_id)
        post_title = post.title
        db.session.delete(post)
        db.session.commit()
        flash(f'"{post_title}" muvaffaqiyatli o\'chirildi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Xatolik yuz berdi: {str(e)}', 'error')
        print(f"Post deletion error: {e}")
    
    return redirect(url_for('admin_posts'))


@app.route('/admin/generate', methods=['GET', 'POST'])
@login_required
def admin_generate():
    """AI bilan post generatsiya qilish (Asinxron)"""
    if request.method == 'POST':
        topic = request.form.get('topic')
        category = request.form.get('category', 'Texnologiya')
        
        if not topic:
            flash('Mavzu kiritilishi shart!', 'error')
            return redirect(url_for('admin_generate'))
            
        from scheduler import generate_and_publish_post
        
        # Orqa fonda generatsiyani boshlash
        thread = threading.Thread(target=generate_and_publish_post, args=(topic, category))
        thread.daemon = True
        thread.start()
        
        flash(f'"{topic}" mavzusida generatsiya orqa fonda boshlandi. Tez orada Telegramga chiqadi.', 'success')
        return redirect(url_for('admin_posts'))
    
    return render_template('admin/generate.html', categories=CATEGORIES)


@app.route('/admin/migrate-slugs', methods=['POST'])
@login_required
def admin_migrate_slugs():
    """Barcha postlarga slug qo'shish (SEO uchun)"""
    posts_without_slug = Post.query.filter(
        (Post.slug == None) | (Post.slug == '')
    ).all()
    
    count = 0
    for post in posts_without_slug:
        post.slug = post.generate_slug()
        count += 1
    
    db.session.commit()
    flash(f'{count} ta postga slug qo\'shildi!', 'success')
    return redirect(url_for('admin_posts'))


# ========== PORTFOLIO ADMIN ROUTES ==========

@app.route('/admin/portfolio')
@login_required
def admin_portfolio():
    """Portfolio ro'yxati"""
    portfolios = Portfolio.query.order_by(Portfolio.created_at.desc()).all()
    return render_template('admin/portfolio.html', portfolios=portfolios)


@app.route('/admin/portfolio/new', methods=['GET', 'POST'])
@login_required
def admin_portfolio_new():
    """Yangi portfolio qo'shish"""
    if request.method == 'POST':
        portfolio = Portfolio(
            title=request.form.get('title'),
            description=request.form.get('description'),
            category=request.form.get('category', 'web'),
            emoji=request.form.get('emoji', '🚀'),
            technologies=request.form.get('technologies'),
            link=request.form.get('link'),
            image_url=request.form.get('image_url'),
            is_featured=request.form.get('is_featured') == 'on',
            is_published=request.form.get('is_published') == 'on',
            meta_description=request.form.get('meta_description'),
            meta_keywords=request.form.get('meta_keywords'),
            details=request.form.get('details'),
            features=request.form.get('features'),
            price=request.form.get('price')
        )
        db.session.add(portfolio)
        db.session.commit()
        
        # Slug yaratish
        portfolio.slug = portfolio.generate_slug()
        db.session.commit()
        
        # Telegram kanalga yuborish
        if portfolio.is_published:
            try:
                from telegram_poster import send_portfolio_to_channel
                send_portfolio_to_channel(portfolio)
                print(f"✅ Portfolio '{portfolio.title}' Telegram kanalga yuborildi")
            except Exception as e:
                print(f"⚠️ Telegram yuborishda xato: {e}")
        
        flash(f'"{portfolio.title}" muvaffaqiyatli qo\'shildi!', 'success')
        return redirect(url_for('admin_portfolio'))
    
    return render_template('admin/portfolio_form.html', portfolio=None)


@app.route('/admin/portfolio/<int:portfolio_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_portfolio_edit(portfolio_id):
    """Portfolio tahrirlash"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    
    if request.method == 'POST':
        portfolio.title = request.form.get('title')
        portfolio.description = request.form.get('description')
        portfolio.category = request.form.get('category', 'web')
        portfolio.emoji = request.form.get('emoji', '🚀')
        portfolio.technologies = request.form.get('technologies')
        portfolio.link = request.form.get('link')
        portfolio.image_url = request.form.get('image_url')
        portfolio.is_featured = request.form.get('is_featured') == 'on'
        portfolio.is_published = request.form.get('is_published') == 'on'
        portfolio.meta_description = request.form.get('meta_description')
        portfolio.meta_keywords = request.form.get('meta_keywords')
        portfolio.details = request.form.get('details')
        portfolio.features = request.form.get('features')
        portfolio.price = request.form.get('price')
        
        # Slug yangilash
        if not portfolio.slug:
            portfolio.slug = portfolio.generate_slug()
        
        db.session.commit()
        flash(f'"{portfolio.title}" yangilandi!', 'success')
        return redirect(url_for('admin_portfolio'))
    
    return render_template('admin/portfolio_form.html', portfolio=portfolio)


@app.route('/admin/portfolio/<int:portfolio_id>/delete', methods=['POST'])
@login_required
def admin_portfolio_delete(portfolio_id):
    """Portfolio o'chirish"""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        title = portfolio.title
        db.session.delete(portfolio)
        db.session.commit()
        flash(f'"{title}" muvaffaqiyatli o\'chirildi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Xatolik yuz berdi: {str(e)}', 'error')
        print(f"Portfolio deletion error: {e}")
        
    return redirect(url_for('admin_portfolio'))



@app.route('/admin/portfolio/<int:portfolio_id>/send-telegram', methods=['POST'])
@login_required
def admin_portfolio_send_telegram(portfolio_id):
    """Portfolioni Telegram kanalga yuborish"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    
    try:
        from telegram_poster import send_portfolio_to_channel
        if send_portfolio_to_channel(portfolio):
            flash(f'"{portfolio.title}" Telegram kanalga yuborildi!', 'success')
        else:
            flash('Telegramga yuborishda xatolik yuz berdi.', 'error')
    except Exception as e:
        flash(f'Xatolik: {e}', 'error')
        
    return redirect(url_for('admin_portfolio'))


@app.route('/admin/api/generate-portfolio')
@login_required
def api_generate_portfolio():
    """AI yordamida portfolio kontent generatsiya qilish"""
    from ai_generator import generate_portfolio_content
    
    title = request.args.get('title', '')
    category = request.args.get('category', 'web')
    
    if not title:
        return jsonify({'error': 'Title kerak'}), 400
    
    try:
        result = generate_portfolio_content(title, category)
        if result:
            return jsonify(result)
        return jsonify({'error': 'AI generatsiya muvaffaqiyatsiz'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== AI CHATBOT API ==========

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """AI chatbot yordamchisi API (saytdagi chat widget uchun)"""
    data = request.get_json(silent=True) or {}
    messages = data.get('messages') or []
    raw_message = (data.get('message') or '').strip()

    # Legacy klientlar faqat message yuborsa ham ishlasin.
    if not messages and raw_message:
        messages = [{'role': 'user', 'content': raw_message}]

    if not messages:
        fallback = 'Qanday yordam bera olaman?'
        return jsonify({'success': True, 'reply': fallback, 'response': fallback})

    last_user_msg = ''
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            content = (msg.get('content') or '').strip()
            if content:
                last_user_msg = content
                break

    if not last_user_msg:
        last_user_msg = raw_message

    if not last_user_msg:
        fallback = 'Savolingizni qaytadan yozib yuboring.'
        return jsonify({'success': False, 'reply': fallback, 'response': fallback}), 400

    api_key = app.config.get('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        fallback = "Uzr, AI yordamchi hozircha sozlanmagan. Telegram orqali yozing: @trendoai"
        return jsonify({'success': False, 'reply': fallback, 'response': fallback, 'error': 'GEMINI_API_KEY topilmadi'}), 503

    try:
        genai.configure(api_key=api_key)

        system_prompt = """Siz TrendoAI IT va marketing xizmatlarining aqlli menedjerisiz.
Siz O'zbekistonda bot yaratish, website tayyorlash, CRM joriy qilish va sun'iy intellekt integratsiyasi bo'yicha savollarga javob berasiz.
Maqsadingiz: mijozga ishonchli, foydali va qisqa javob berish.
Agar mijoz xizmatga qiziqsa, uning aloqa ma'lumotini yoki Telegram username'ini so'rang.
QOIDALAR:
1. Qisqa va do'stona o'zbek lotin tilida yozing.
2. Keraksiz markdown va uzun doston ishlatmang.
3. Zarur joyda TrendoAI xizmatlarini mos ravishda tavsiya qiling.
4. Agar aniq narxni bilmasangiz, konsultatsiyaga yo'naltiring."""

        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_prompt
        )

        history = []
        for msg in messages[-6:-1]:
            content = (msg.get('content') or '').strip()
            if not content:
                continue
            role = 'user' if msg.get('role') == 'user' else 'model'
            history.append({'role': role, 'parts': [content]})

        chat = model.start_chat(history=history)
        response = chat.send_message(last_user_msg)
        reply = (getattr(response, 'text', '') or '').strip()

        if not reply:
            reply = "Uzr, hozir javobni shakllantirib bo'lmadi. Telegram orqali yozing: @trendoai"

        return jsonify({'success': True, 'reply': reply, 'response': reply})

    except Exception as e:
        print(f"Chat error: {e}")
        fallback = "Uzr, hozircha men javob qaytara olmayapman. Telegram orqali yozing: @trendoai"
        return jsonify({'success': False, 'reply': fallback, 'response': fallback, 'error': str(e)}), 500

import asyncio
import io
import wave
import base64

async def _generate_native_audio_chunks(context_text):
    try:
        from google import genai as new_genai
        from google.genai import types as new_types
    except ImportError:
        print("google-genai not installed")
        return []
    
    # Barcha kalitlarni ro'yxati
    keys_to_try = [
        os.getenv('GEMINI_API_KEY'),
        os.getenv('GEMINI_API_KEY2'),
        os.getenv('GEMINI_API_KEY3')
    ]
    
    model = 'gemini-3.1-flash-live-preview'
    config = new_types.LiveConnectConfig(
        response_modalities=[new_types.Modality.AUDIO],
        speech_config=new_types.SpeechConfig(
            voice_config=new_types.VoiceConfig(
                prebuilt_voice_config=new_types.PrebuiltVoiceConfig(voice_name='Puck')
            )
        )
    )
    
    audio_chunks = []
    
    for key in keys_to_try:
        if not key:
            continue
            
        try:
            client = new_genai.Client(api_key=key)
            async with client.aio.live.connect(model=model, config=config) as session:
                await session.send(input=context_text, end_of_turn=True)
                async for response in session.receive():
                    server_content = response.server_content
                    if server_content is not None:
                        model_turn = server_content.model_turn
                        if model_turn is not None:
                            for part in model_turn.parts:
                                if part.inline_data:
                                    audio_chunks.append(part.inline_data.data)
            
            # Agar muvaffaqiyatli olsa, tsiklni to'xtatish
            if audio_chunks:
                break
        except Exception as e:
            print(f"Native audio live connect xatosi (Key: {key[:5]}...): {e}")
            
    return audio_chunks

def get_audio_base64_from_text(text):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    chunks = loop.run_until_complete(_generate_native_audio_chunks(text))
    loop.close()
    
    if not chunks:
        return None
        
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        for chunk in chunks:
            wav_file.writeframes(chunk)
            
    return base64.b64encode(wav_io.getvalue()).decode('utf-8')


@app.route('/api/chat/audio', methods=['POST'])
def api_chat_audio():
    """AI Chatbot audio endpoint - Gemini 2.5 Flash Native Audio bilan"""
    import google.generativeai as genai
    from pywebpush import webpush, WebPushException
    import markdown2
    import base64
    import tempfile
    import os
    
    try:
        data = request.get_json()
        audio_base64 = data.get('audio', '')
        
        if not audio_base64:
            return jsonify({'error': 'Audio topilmadi'}), 400
        
        # Base64 ni decode qilish
        audio_bytes = base64.b64decode(audio_base64)
        
        # Gemini modelni sozlash
        api_key = app.config.get('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        
        # Gemini 2.5 Flash (User requested)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # TrendoAI konteksti
        system_prompt = """Siz TrendoAI AI assistentisiz. 
Vazifangiz:
1. Kelayotgan ovozli xabarni to'g'ridan-to'g'ri tushuning (intonatsiya va hissiyotlarni hisobga olgan holda).
2. Foydalanuvchiga o'zbek tilida, samimiy va professional javob bering.

TrendoAI xizmatlari: Telegram Botlar, Web Saytlar, AI Chatbotlar, SMM.
Aloqa: @Akramjon1984, trendoai.uz

Javobni matn ko'rinishida yozing."""

        # Vaqtinchalik faylga saqlash
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name

        try:
            # Faylni Gemini File API ga yuklash
            uploaded_file = genai.upload_file(temp_audio_path, mime_type="audio/webm")
            
            # Fayl tayyor bo'lishini kutish
            # Native model uchun ham fayl yuklash usuli ishlaydi
            
            # Javob olish
            response = model.generate_content([system_prompt, uploaded_file])
            
            # Native Gemini 3.1 Audio generation
            audio_b64 = get_audio_base64_from_text(response.text)
            
            # Faylni o'chirish
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)

            return jsonify({
                'success': True,
                'response': response.text,
                'audio_base64': audio_b64
            })
        except Exception as inner_e:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            print(f"Gemini API Error: {inner_e}")
            raise inner_e
            
    except Exception as e:
        print(f"Audio chatbot error: {e}")
        return jsonify({
            'error': 'Ovozni tushunib bo\'lmadi',
            'response': "Ovozli xabarni tushunishda xatolik bo'ldi. Iltimos, donaroq gapiring yoki yozib yuboring."
        }), 500


# ========== PUSH NOTIFICATION ROUTES ==========

@app.route('/api/push/subscribe', methods=['POST'])
def push_subscribe():
    """Web Push obunasini saqlash yoki yangilash"""
    data = request.json
    if not data or not data.get('endpoint'):
        return jsonify({'error': 'Invalid data'}), 400

    endpoint = data['endpoint']
    keys = data.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not p256dh or not auth:
        return jsonify({'error': 'Missing keys'}), 400

    subscription = PushSubscription.query.filter_by(endpoint=endpoint).first()
    created = False

    if not subscription:
        subscription = PushSubscription(
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth
        )
        db.session.add(subscription)
        created = True
    else:
        subscription.p256dh = p256dh
        subscription.auth = auth

    db.session.commit()
    print(f"[push] Subscription {'yaratildi' if created else 'yangilandi'}: {endpoint[:80]}")
    return jsonify({'success': True, 'message': 'Obuna saqlandi', 'created': created})
@app.route('/api/push/send', methods=['POST'])
@login_required
def push_send():
    """Push xabar yuborish (Admin)"""
    data = request.json or {}
    title = data.get('title', 'TrendoAI')
    message = data.get('message', 'Yangi xabar!')
    url = data.get('url', '/')

    sent_count = notify_all_subscribers(title=title, message=message, url=url)
    return jsonify({'success': sent_count > 0, 'sent_count': sent_count})
@app.route('/sw.js')
def service_worker():
    """Service Worker faylini root'dan uzatish"""
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    return response



@app.route('/api/catalog.xml')
def facebook_catalog():
    """Facebook Product Catalog Feed (RSS 2.0 formatda)"""
    from flask import Response
    
    base_url = SITE_URL
    portfolios = Portfolio.query.filter_by(is_published=True).all()
    
    # RSS 2.0 format - Facebook Commerce Manager uchun
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
    xml += '<channel>\n'
    xml += f'  <title>TrendoAI Portfolio - IT Xizmatlari</title>\n'
    xml += f'  <link>{base_url}/portfolio</link>\n'
    xml += f'  <description>TrendoAI professional IT xizmatlari va loyihalar katalogi</description>\n'
    
    for item in portfolios:
        # Kategoriya nomlari
        category_names = {
            'bot': 'Telegram Bot',
            'web': 'Web Sayt',
            'ai': 'AI Yechim',
            'mobile': 'Mobile App'
        }
        category_name = category_names.get(item.category, item.category)
        
        # Rasm URL
        image_url = item.image_url if item.image_url else f'{base_url}/static/favicon.svg'
        
        # Loyiha URL
        item_url = f'{base_url}/portfolio#{item.slug}' if item.slug else f'{base_url}/portfolio'
        
        xml += '  <item>\n'
        xml += f'    <g:id>{item.id}</g:id>\n'
        xml += f'    <title>{item.title}</title>\n'
        xml += f'    <link>{item_url}</link>\n'
        xml += f'    <description><![CDATA[{item.description}]]></description>\n'
        xml += f'    <g:image_link>{image_url}</g:image_link>\n'
        xml += f'    <g:brand>TrendoAI</g:brand>\n'
        xml += f'    <g:condition>new</g:condition>\n'
        xml += f'    <g:availability>in stock</g:availability>\n'
        xml += f'    <g:price>0 UZS</g:price>\n'  # Bepul konsultatsiya
        xml += f'    <g:product_type>{category_name}</g:product_type>\n'
        xml += f'    <g:google_product_category>Software > Computer Software > Business &amp; Productivity Software</g:google_product_category>\n'
        
        # SEO kalit so'zlar
        if item.meta_keywords:
            for keyword in item.meta_keywords.split(',')[:5]:
                xml += f'    <g:custom_label_0>{keyword.strip()}</g:custom_label_0>\n'
        
        xml += '  </item>\n'
    
    xml += '</channel>\n'
    xml += '</rss>'
    
    return Response(xml, mimetype='application/xml')



# ========== DATABASE MIGRATION ROUTES ==========

@app.route('/admin/migrate-db')
@login_required
def admin_migrate_db():
    """Bazaga yangi ustunlar qo'shish"""
    results = []
    
    try:
        # Portfolio.price ustunini qo'shish
        try:
            db.session.execute(db.text("ALTER TABLE portfolio ADD COLUMN price VARCHAR(100)"))
            db.session.commit()
            results.append("✅ Portfolio.price ustuni qo'shildi")
        except Exception as e:
            db.session.rollback()
            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                results.append("ℹ️ Portfolio.price ustuni allaqachon mavjud")
            else:
                results.append(f"⚠️ Portfolio.price: {e}")
        
        # Service jadvalini tekshirish va yaratish
        try:
            db.create_all()
            results.append("✅ db.create_all() bajarildi (yangi jadvallar yaratildi)")
        except Exception as e:
            results.append(f"⚠️ db.create_all: {e}")
            
        flash('Baza migratsiyasi yakunlandi: ' + '; '.join(results), 'success')
        
    except Exception as e:
        flash(f'Migratsiya xatosi: {e}', 'error')
    
    return redirect(url_for('admin_dashboard'))


# ========== SEO ROUTES ==========

@app.route('/robots.txt')
def robots_txt():
    """Qidiruv tizimlari botlari uchun ruxsatnoma"""
    site_url = app.config.get('SITE_URL', 'https://trendoai.uz')
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
        f"Sitemap: {site_url}/sitemap.xml"
    ]
    return Response("\n".join(lines), mimetype="text/plain")



# ========== API ROUTES ==========

@app.route('/api/lead', methods=['POST'])
def submit_lead():
    """Lead Magnet yoki Chatbot orqali kelgan ma'lumotni saqlash"""
    data = request.json
    if not data or not data.get('contact'):
        return jsonify({'status': 'error', 'message': 'Iltimos, aloqa ma\'lumotini kiriting.'}), 400
        
    try:
        new_lead = Lead(
            name=data.get('name', 'Noma\'lum'),
            contact=data['contact'],
            source=data.get('source', 'Sayt Orqali')
        )
        db.session.add(new_lead)
        db.session.commit()
        
        # Adminga xabar
        from telegram_poster import send_admin_alert
        msg = f"🎯 <b>YANGI MIJOZ (LEAD)!</b>\n\n👤 <b>Ismi:</b> {new_lead.name}\n📞 <b>Aloqa:</b> {new_lead.contact}\n📍 <b>Manba:</b> {new_lead.source}"
        send_admin_alert(msg)
        
        return jsonify({'status': 'success', 'message': 'Ma\'lumot muvaffaqiyatli qabul qilindi!'})
    except Exception as e:
        print(f"Lead error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'TrendoAI',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/posts')
def api_posts():
    """Barcha postlar API"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', None)
    
    query = Post.query.filter_by(is_published=True)
    
    if category:
        query = query.filter_by(category=category)
    
    pagination = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=min(per_page, 50), error_out=False
    )
    
    return jsonify({
        'posts': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    })


@app.route('/api/posts/<int:post_id>')
def api_post(post_id):
    """Bitta post API"""
    post = Post.query.get_or_404(post_id)
    return jsonify(post.to_dict())


@app.route('/api/stats')
def api_stats():
    """Statistika API"""
    return jsonify({
        'total_posts': Post.query.count(),
        'published_posts': Post.query.filter_by(is_published=True).count(),
        'total_views': db.session.query(db.func.sum(Post.views)).scalar() or 0,
        'categories': CATEGORIES
    })


# ========== CRON API ROUTES ==========
# Note: Main cron routes defined in STARTUP section

@app.route('/api/init-db')
def api_init_database():
    """
    Database jadvallarini yaratish va tekshirish.
    Order jadvali yo'q bo'lsa yaratadi.
    """
    try:
        # Barcha jadvallarni yaratish
        db.create_all()
        
        # Order jadvalini tekshirish
        order_count = Order.query.count()
        post_count = Post.query.count()
        
        return jsonify({
            'status': 'success',
            'message': 'Database jadvallar muvaffaqiyatli yaratildi/yangilandi',
            'tables': {
                'orders': order_count,
                'posts': post_count
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/cron/status')
def cron_status():
    """Cron vazifalar statusi"""
    try:
        from scheduler import get_scheduled_jobs
        jobs = get_scheduled_jobs()
        return jsonify({
            'status': 'ok',
            'scheduled_jobs': len(jobs),
            'jobs': jobs,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500




@app.route('/admin/fix-webhook')
@login_required
def admin_fix_webhook():
    """Manual webhook setup via browser"""
    from bot_service import bot
    import time
    
    webhook_url = f"{SITE_URL}/webhook"
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        return f"✅ Webhook muvaffaqiyatli o'rnatildi: {webhook_url}. Botni tekshirib ko'ring!", 200
    except Exception as e:
        return f"❌ Xatolik: {e}", 500




# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(e):
    """404 sahifa"""
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """500 sahifa"""
    print(f"Server Error (500): {e}")
    import traceback
    traceback.print_exc()
    return render_template('errors/500.html'), 500


# ========== STARTUP ==========

# ========== STARTUP ==========

@app.route('/api/cron/generate', methods=['GET', 'POST'])
def cron_generate_post():
    """Tashqi cron xizmatlari uchun post generatsiya qilish"""
    secret = request.args.get('secret') or request.headers.get('X-Cron-Secret')
    
    # Secret key tekshirish
    if secret != app.config.get('CRON_SECRET'):
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid secret key'}), 401
        
    topic = request.args.get('topic')
    category = request.args.get('category')
    
    # Taskni asinxron ishga tushirish (timeout bo'lmasligi uchun)
    from scheduler import generate_and_publish_post
    thread = threading.Thread(target=generate_and_publish_post, args=(topic, category))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True, 
        'message': 'Post generation started in background',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/cron/keep-alive')
def cron_keep_alive():
    """Serverni uyg'oq saqlash va Cron Scheduler haqida ma'lumot berish"""
    status_data = {
        'status': 'alive', 
        'time': datetime.now().isoformat()
    }
    
    try:
        from scheduler import get_scheduled_jobs
        jobs = get_scheduled_jobs()
        status_data['scheduler_status'] = 'running' if len(jobs) > 0 else 'stopped'
        status_data['active_jobs_count'] = len(jobs)
    except Exception as e:
        status_data['scheduler_error'] = str(e)
        
    return jsonify(status_data)

@app.route('/api/cron/debug-generate')
def cron_debug_generate():
    """Sinxron debug endpoint — xatoliklarni aniq ko'rish uchun"""
    secret = request.args.get('secret') or request.headers.get('X-Cron-Secret')
    if secret != app.config.get('CRON_SECRET'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    import traceback as tb
    result = {'steps': [], 'success': False}
    
    try:
        # 0. Gemini API kalitni tekshirish
        from config import GEMINI_API_KEY, GEMINI_MODEL
        result['gemini_api_key_exists'] = bool(GEMINI_API_KEY)
        result['gemini_api_key_preview'] = GEMINI_API_KEY[:10] + '...' if GEMINI_API_KEY else 'NONE'
        result['gemini_model'] = GEMINI_MODEL
        key_state = "BOR" if GEMINI_API_KEY else "YO'Q"
        result['steps'].append(f"0. API kalit: {key_state}, Model: {GEMINI_MODEL}")
        
        if not GEMINI_API_KEY:
            result['error'] = 'GEMINI_API_KEY muhit o\'zgaruvchisi topilmadi!'
            return jsonify(result), 500
        
        # 1. Gemini API oddiy test
        result['steps'].append('1. Gemini API oddiy test...')
        try:
            import google.generativeai as test_genai
            test_genai.configure(api_key=GEMINI_API_KEY)
            test_model = test_genai.GenerativeModel(GEMINI_MODEL)
            test_response = test_model.generate_content("Salom, 1+1 nechta?")
            result['steps'].append(f'✅ Gemini API ishlaydi! Javob: {test_response.text[:100]}')
            result['gemini_test'] = 'OK'
        except Exception as gemini_err:
            result['steps'].append(f'❌ Gemini API xatosi: {str(gemini_err)}')
            result['gemini_error'] = str(gemini_err)
            result['gemini_traceback'] = tb.format_exc()
            return jsonify(result), 500
        
        # 2. AI post generatsiya
        result['steps'].append('2. AI post generatsiya boshlanmoqda...')
        try:
            from ai_generator import generate_post_for_seo
            import random
            from scheduler import TOPICS
            topic = request.args.get('topic') or random.choice(TOPICS)
            result['topic'] = topic
            
            post_data = generate_post_for_seo(topic)
            if not post_data:
                result['error'] = 'generate_post_for_seo None qaytardi (AI javob yoki JSON parse xatosi)'
                result['steps'].append('❌ AI generatsiya muvaffaqiyatsiz')
                return jsonify(result), 500
            
            result['steps'].append(f'✅ AI generatsiya muvaffaqiyatli: {post_data.get("title", "?")}')
            result['ai_title'] = post_data.get('title')
        except Exception as ai_err:
            result['steps'].append(f'❌ AI generatsiya exception: {str(ai_err)}')
            result['ai_error'] = str(ai_err)
            result['ai_traceback'] = tb.format_exc()
            return jsonify(result), 500
        
        # 3. Rasm olish
        result['steps'].append('3. Rasm olinmoqda...')
        image_url = None
        image_prompt = ''
        try:
            from image_fetcher import get_image_for_topic, build_image_prompt
            existing_unsplash_urls = [
                row[0] for row in db.session.query(Post.image_url)
                .filter(
                    Post.image_url.isnot(None),
                    Post.image_url.contains('images.unsplash.com'),
                )
                .all()
            ]
            image_url = get_image_for_topic(topic, exclude_image_urls=existing_unsplash_urls)
            image_prompt = build_image_prompt(topic=topic, title=post_data.get('title'), category=request.args.get('category'))
            result['image_url'] = image_url
            result['image_prompt'] = image_prompt
            result['steps'].append('✅ Rasm topildi')
        except Exception as img_err:
            result['steps'].append(f'⚠️ Rasm xatosi (davom etiladi): {str(img_err)}')
        
        # 4. Bazaga saqlash
        result['steps'].append('4. Bazaga saqlanmoqda...')
        import random
        selected_category = request.args.get('category') or random.choice(CATEGORIES)
        new_post = Post(
            title=post_data['title'],
            content=post_data['content'],
            topic=topic,
            category=selected_category,
            keywords=post_data.get('keywords', ''),
            image_url=image_url,
            image_prompt=image_prompt,
            is_published=True
        )
        new_post.reading_time = new_post.calculate_reading_time()
        db.session.add(new_post)
        db.session.commit()
        
        new_post.slug = new_post.generate_slug()
        db.session.commit()
        
        result['steps'].append(f'✅ Bazaga saqlandi: ID={new_post.id}, slug={new_post.slug}')
        result['post_id'] = new_post.id
        result['post_url'] = f'{SITE_URL}/blog/{new_post.slug}'
        result['success'] = True
        
        return jsonify(result)
        
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = tb.format_exc()
        result['steps'].append(f'❌ Xatolik: {str(e)}')
        return jsonify(result), 500

@app.route('/api/cron/test-ai')
def cron_test_ai():
    """Tezkor Gemini API test — retrylar yo'q, 10 soniya ichida javob"""
    secret = request.args.get('secret') or request.headers.get('X-Cron-Secret')
    if secret != app.config.get('CRON_SECRET'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    import traceback as tb
    result = {}
    
    # 1. API kalit tekshirish
    from config import GEMINI_API_KEY, GEMINI_MODEL
    result['api_key_exists'] = bool(GEMINI_API_KEY)
    result['api_key_preview'] = (GEMINI_API_KEY[:8] + '...') if GEMINI_API_KEY else 'NONE'
    result['model'] = GEMINI_MODEL
    
    if not GEMINI_API_KEY:
        result['error'] = 'GEMINI_API_KEY topilmadi'
        return jsonify(result), 500
    
    # 2. Oddiy Gemini test (retrylar yo'q)
    try:
        import google.generativeai as test_genai
        test_genai.configure(api_key=GEMINI_API_KEY)
        test_model = test_genai.GenerativeModel(GEMINI_MODEL)
        resp = test_model.generate_content("1+1=?")
        result['gemini_status'] = 'OK'
        result['gemini_response'] = resp.text[:200]
    except Exception as e:
        result['gemini_status'] = 'ERROR'
        result['gemini_error'] = str(e)
        result['gemini_traceback'] = tb.format_exc()
    
    # 3. DB test
    try:
        post_count = Post.query.count()
        result['db_status'] = 'OK'
        result['total_posts'] = post_count
    except Exception as e:
        result['db_status'] = 'ERROR'
        result['db_error'] = str(e)
    
    # 4. Telegram token test
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID
    result['telegram_token_exists'] = bool(TELEGRAM_BOT_TOKEN)
    result['telegram_channel_exists'] = bool(TELEGRAM_CHANNEL_ID)
    
    return jsonify(result)

# Server ishga tushganda bajariladigan amallar (Gunicorn va Local)
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Database error: {e}")

# Database Migration - Add missing columns at startup
def migrate_portfolio_columns():
    """Add missing columns to Portfolio table if they don't exist"""
    try:
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('portfolio')]
        
        with db.engine.connect() as conn:
            if 'details' not in columns:
                conn.execute(text("ALTER TABLE portfolio ADD COLUMN details TEXT"))
                print("✅ Added 'details' column to Portfolio")
            if 'features' not in columns:
                conn.execute(text("ALTER TABLE portfolio ADD COLUMN features TEXT"))
                print("✅ Added 'features' column to Portfolio")
            conn.commit()
    except Exception as e:
        print(f"Migration note: {e}")

# Run migration
with app.app_context():
    migrate_portfolio_columns()

# Auto-generate slugs for portfolio items without slugs
def generate_portfolio_slugs():
    """Generate slugs for portfolio items that don't have one"""
    import re
    try:
        portfolios = Portfolio.query.filter(
            (Portfolio.slug == None) | (Portfolio.slug == '')
        ).all()
        
        if not portfolios:
            return
        
        for item in portfolios:
            if item.title:
                # Simple slug generation
                slug = item.title.lower()
                slug = re.sub(r'[^a-z0-9\s-]', '', slug)
                slug = re.sub(r'[\s_]+', '-', slug)
                slug = slug.strip('-')
                
                if slug:
                    # Ensure unique
                    base_slug = slug
                    counter = 1
                    while Portfolio.query.filter_by(slug=slug).first():
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                    
                    item.slug = slug
                    print(f"✅ Generated slug: {item.title} -> {slug}")
        
        db.session.commit()
        print("✅ Portfolio slugs generated successfully")
    except Exception as e:
        print(f"Slug generation note: {e}")

@app.route('/admin/generate-post')
@login_required
def admin_generate_post():
    """Manual post generation"""
    try:
        from scheduler import generate_and_publish_post
        success = generate_and_publish_post()
        if success:
            return "✅ Yangi post muvaffaqiyatli generatsiya qilindi va Telegramga yuborildi!", 200
        else:
            return "❌ Post generatsiya qilishda xatolik.", 500
    except Exception as e:
        return f"❌ Xatolik: {e}", 500
@app.route('/feed/facebook.xml')
def facebook_feed():
    """Facebook/Instagram Catalog Feed (XML)"""
    from xml.etree.ElementTree import Element, SubElement, tostring
    import xml.dom.minidom
    
    # Root element
    rss = Element('rss', {'xmlns:g': 'http://base.google.com/ns/1.0', 'version': '2.0'})
    channel = SubElement(rss, 'channel')
    
    # Channel details
    SubElement(channel, 'title').text = SITE_NAME
    SubElement(channel, 'link').text = SITE_URL
    SubElement(channel, 'description').text = SITE_DESCRIPTION
    
    # 1. Add Services
    services = Service.query.filter_by(is_active=True).all()
    for service in services:
        item = SubElement(channel, 'item')
        
        SubElement(item, 'g:id').text = f"service_{service.slug}"
        SubElement(item, 'g:title').text = service.title
        SubElement(item, 'g:description').text = service.full_description or service.description
        SubElement(item, 'g:link').text = f"{SITE_URL}/services/{service.slug}"
        
        # Image
        if service.image_url:
            if service.image_url.startswith('http'):
                 SubElement(item, 'g:image_link').text = service.image_url
            else:
                 SubElement(item, 'g:image_link').text = f"{SITE_URL}{service.image_url}"
        else:
            SubElement(item, 'g:image_link').text = f"{SITE_URL}/static/images/services/{service.slug}.jpg"
            
        SubElement(item, 'g:brand').text = "TrendoAI"
        SubElement(item, 'g:condition').text = "new"
        SubElement(item, 'g:availability').text = "in stock"
        
        # Price
        raw_price = service.price or '0'
        price_numeric = re.sub(r'[^0-9]', '', raw_price)
        if not price_numeric: price_numeric = "0"
        SubElement(item, 'g:price').text = f"{price_numeric} UZS"
        
        SubElement(item, 'g:google_product_category').text = "Software > Business & Productivity Software"
        
    # 2. Add Portfolio Items
    portfolios = Portfolio.query.filter_by(is_published=True).all()
    for p in portfolios:
        item = SubElement(channel, 'item')
        
        SubElement(item, 'g:id').text = f"portfolio_{p.id}"
        SubElement(item, 'g:title').text = p.title
        SubElement(item, 'g:description').text = p.description
        
        link = f"{SITE_URL}/portfolio/project/{p.slug}" if p.slug else f"{SITE_URL}/portfolio"
        SubElement(item, 'g:link').text = link
        
        if p.image_url:
            SubElement(item, 'g:image_link').text = p.image_url
        else:
            SubElement(item, 'g:image_link').text = f"{SITE_URL}/static/logo.png"
            
        SubElement(item, 'g:brand').text = "TrendoAI"
        SubElement(item, 'g:condition').text = "new"
        SubElement(item, 'g:availability').text = "in stock"
        
        # Price from database
        raw_price = getattr(p, 'safe_price', None) or '0'
        price_numeric = re.sub(r'[^0-9]', '', raw_price)
        if not price_numeric: price_numeric = "0"
        SubElement(item, 'g:price').text = f"{price_numeric} UZS"
        SubElement(item, 'g:custom_label_0').text = p.category # Use custom label for filtering
        SubElement(item, 'g:google_product_category').text = "Software > Business & Productivity Software"

    # Convert to simple string with header
    xml_str = xml.dom.minidom.parseString(tostring(rss)).toprettyxml(indent="   ")
    
    return Response(xml_str, mimetype='application/xml')

# ========== SEO ROUTES ==========


@app.route('/sitemap.xml')
def sitemap_xml():
    """Dinamik sitemap.xml - barcha sahifalar va postlar"""
    from datetime import datetime
    
    pages = []
    
    # Asosiy sahifalar
    static_pages = [
        ('/', '1.0', 'daily'),
        ('/portfolio', '0.8', 'weekly'),
        ('/blog', '0.9', 'daily'),
        ('/about', '0.7', 'monthly'),
        ('/order', '0.8', 'monthly'),
    ]
    
    for url, priority, changefreq in static_pages:
        pages.append({
            'loc': f'{SITE_URL}{url}',
            'priority': priority,
            'changefreq': changefreq,
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        })
    
    # Xizmatlar sahifalari
    services = Service.query.filter_by(is_active=True).all()
    for service in services:
        pages.append({
            'loc': f'{SITE_URL}/services/{service.slug}',
            'priority': '0.8',
            'changefreq': 'weekly',
            'lastmod': datetime.now().strftime('%Y-%m-%d')
        })
    
    # Blog postlar
    posts = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).all()
    for post in posts:
        lastmod = post.updated_at or post.created_at
        pages.append({
            'loc': f'{SITE_URL}/blog/{post.slug}' if post.slug else f'{SITE_URL}/post/{post.id}',
            'priority': '0.7',
            'changefreq': 'monthly',
            'lastmod': lastmod.strftime('%Y-%m-%d') if lastmod else datetime.now().strftime('%Y-%m-%d')
        })
    
    # Portfolio loyihalar
    portfolios = Portfolio.query.filter_by(is_published=True).all()
    for p in portfolios:
        if not p.slug:
            continue
        pages.append({
            'loc': f'{SITE_URL}/portfolio/project/{p.slug}',
            'priority': '0.6',
            'changefreq': 'monthly',
            'lastmod': p.created_at.strftime('%Y-%m-%d') if p.created_at else datetime.now().strftime('%Y-%m-%d')
        })
    
    # XML yaratish
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        xml_content += '  <url>\n'
        xml_content += f'    <loc>{page["loc"]}</loc>\n'
        xml_content += f'    <lastmod>{page["lastmod"]}</lastmod>\n'
        xml_content += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        xml_content += f'    <priority>{page["priority"]}</priority>\n'
        xml_content += '  </url>\n'
    
    xml_content += '</urlset>'
    
    return Response(xml_content, mimetype='application/xml')


# ========== TELEGRAM WEBHOOK ==========
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Telegram webhook handler - botga kelgan xabarlarni qayta ishlash"""
    try:
        from bot_service import bot
        import telebot
        
        if bot and request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        else:
            return 'Bot not configured', 400
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return 'Error', 500
@app.route('/google<verification_code>.html')
def google_verification(verification_code):
    """Google Search Console verification"""
    return f'google-site-verification: google{verification_code}.html'


@app.route('/yandex_<verification_code>.html')
def yandex_verification(verification_code):
    """Yandex Webmaster verification"""
    html_content = f'''<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    </head>
    <body>Verification: {verification_code}</body>
</html>'''
    return Response(html_content, mimetype='text/html')



# ========== DATABASE INITIALIZATION ==========

def init_database():
    """Bazani yangilash va yangi ustunlarni qo'shish"""
    with app.app_context():
        from sqlalchemy import inspect, text

        try:
            # 1. Yangi jadvallarni yaratish
            db.create_all()
        except Exception as e:
            print(f"WARN: db.create_all failed: {e}")
            return

        try:
            inspector = inspect(db.engine)
            table_names = set(inspector.get_table_names())

            def ensure_varchar_column(table_name, column_name):
                if table_name not in table_names:
                    print(f"INFO: {table_name} table not found; skip {column_name}.")
                    return

                existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                if column_name in existing_columns:
                    print(f"INFO: {table_name}.{column_name} already exists.")
                    return

                with db.engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(100)")
                    )
                print(f"OK: added {table_name}.{column_name}.")

            def ensure_text_column(table_name, column_name):
                if table_name not in table_names:
                    print(f"INFO: {table_name} table not found; skip {column_name}.")
                    return

                existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                if column_name in existing_columns:
                    print(f"INFO: {table_name}.{column_name} already exists.")
                    return

                with db.engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT")
                    )
                print(f"OK: added {table_name}.{column_name}.")

            ensure_varchar_column("portfolio", "price")
            ensure_varchar_column("service", "price")
            ensure_text_column("post", "image_prompt")

            # PostgreSQL uchun meta_description ni TEXT ga o'zgartirish
            if "portfolio" in table_names and db.engine.dialect.name == "postgresql":
                portfolio_columns = {col["name"] for col in inspector.get_columns("portfolio")}
                if "meta_description" in portfolio_columns:
                    with db.engine.begin() as conn:
                        conn.execute(
                            text("ALTER TABLE portfolio ALTER COLUMN meta_description TYPE TEXT")
                        )
                    print("OK: portfolio.meta_description converted to TEXT.")
        except Exception as e:
            print(f"WARN: Database migration step failed: {e}")
        return

def migrate_service_discount_dates():
    """One-off update for expired promo text shown on service pages."""
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
    """Remove legacy fixed-date note from generated post content."""
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
        for post in posts:
            original = post.content or ""
            cleaned = pattern.sub("", original, count=1).lstrip()
            if cleaned != original:
                post.content = cleaned
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
    """Background boot sequence to prevent blocking Gunicorn worker start"""
    try:
        # Run database initialization
        init_database()
        with app.app_context():
            migrate_service_discount_dates()
            migrate_remove_post_freshness_notes()
            
        # ===== 1. Schedulerni ishga tushirish =====
        try:
            from scheduler import scheduler
            if not scheduler.running:
                scheduler.start()
                jobs = scheduler.get_jobs()
                print(f"✅ Scheduler ishga tushdi! Joblar soni: {len(jobs)}")
        except Exception as e:
            print(f"❌ Scheduler startup error: {e}")

        # ===== 2. Bot webhookni ishga tushirish =====
        try:
            from bot_service import setup_webhook, bot
            setup_webhook(app)
        except Exception as e:
            print(f"❌ Bot webhook error: {e}")

        print("🚀 TrendoAI xizmatlari ishga tushdi!")
    except Exception as e:
        print(f"❌ Boot sequence error: {e}")

# Start boot sequence in background thread
import threading
threading.Thread(target=_boot_sequence, daemon=True).start()


if __name__ == '__main__':
    # Flask ilovasini ishga tushirish
    app.run(debug=True, use_reloader=False, port=5000)
