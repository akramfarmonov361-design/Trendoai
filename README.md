# 🔥 TrendoAI — AI-Powered Trending Tech Blog

O'zbekistonda trending texnologiya yangiliklari va sun'iy intellekt haqida professional blog platformasi.

![TrendoAI](https://img.shields.io/badge/TrendoAI-v2.0-667eea?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)
![Gemini](https://img.shields.io/badge/Gemini-AI-4285F4?style=for-the-badge&logo=google)

## ✨ Xususiyatlar

- 🤖 **AI-Powered Kontent** — Gemini AI yordamida avtomatik SEO-optimallashtirilgan maqolalar
- 📱 **Telegram Integratsiya** — Yangi maqolalarni avtomatik kanalga yuborish
- 🔍 **Qidiruv** — Maqolalarni sarlavha, kontent va kalit so'zlar bo'yicha qidirish
- 📂 **Kategoriyalar** — 8 ta texnologiya kategoriyasi
- 👨‍💼 **Admin Panel** — To'liq boshqaruv: postlar, generatsiya, statistika
- 🌐 **SEO** — Meta taglar, Open Graph, Sitemap, Robots.txt
- 📊 **API** — RESTful API endpoints
- 🐳 **Docker Ready** — Render.com va boshqa platformalarga deploy

## 🛠️ Texnologiyalar

| Texnologiya | Versiya | Vazifasi |
|------------|---------|----------|
| Flask | 3.0.3 | Web framework |
| SQLAlchemy | 3.1.1 | ORM / Database |
| Gemini AI | Flash | Kontent generatsiyasi |
| APScheduler | 3.10.4 | Cron jobs |
| Gunicorn | 21.2.0 | Production server |

## 📦 O'rnatish

### 1. Repozitoriyani klonlash
```bash
git clone https://github.com/your-username/trendoai.git
cd trendoai
```

### 2. Virtual muhit yaratish
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. `.env` faylini sozlash

To'liq ro'yxat [`.env.example`](.env.example) da — uni nusxalab to'ldiring:

```bash
cp .env.example .env
```

Ishga tushirish uchun majburiy bo'lganlari:

| O'zgaruvchi | Nima uchun |
|---|---|
| `GEMINI_API_KEY` | AI kontent va chatbot (Google AI Studio) |
| `SECRET_KEY` | Flask sessiya imzosi — production'da majburiy |
| `CRON_SECRET` | Cron endpointlarini himoyalash — production'da majburiy |
| `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH` | Admin panel (hash: `python scripts/generate_admin_hash.py`) |
| `SITE_URL` | Kanonik manzil, sitemap va webhook uchun |
| `FLASK_ENV=production` | Xavfsizlik tekshiruvlarini yoqadi |

Xavfsizlik uchun kuchli tavsiya etiladi:

| O'zgaruvchi | Bo'lmasa nima bo'ladi |
|---|---|
| `TELEGRAM_WEBHOOK_SECRET` | Webhook siri `CRON_SECRET` bilan bir xil bo'lib qoladi |
| `FB_APP_SECRET` | Meta lead webhook imzosiz, ya'ni ochiq qabul qiladi |
| `REDIS_URL` | Rate-limit workerlar bo'ylab taqsimlanmaydi |
| `S3_BUCKET` va boshqa S3 kalitlari | Yuklangan rasmlar Render'da har deploy'da yo'qoladi |

### 5. Ilovani ishga tushirish
```bash
# Development
python app.py

# Production
gunicorn --bind 0.0.0.0:5000 app:app
```

### 6. Tailwind CSS build (faqat dizayn o'zgarsa)

Tailwind CDN o'rniga pre-built CSS ishlatilmoqda (`static/css/tailwind.css`).
Yangi class qo'shsangiz yoki dizayn o'zgartirsangiz qayta build qilish kerak:

```bash
# Bir martalik (paketlarni o'rnatish)
npm install

# CSS'ni build qilish
npm run build:css

# Yoki tahrirlash vaqtida avtomatik kuzatish
npm run watch:css
```

Build natijasi (`static/css/tailwind.css`) **git'ga commit qilinishi kerak** —
Render.com'da Node.js yo'q, shuning uchun build mahalliy mashinada amalga oshiriladi.

## 🌐 Sahifalar

| URL | Tavsif |
|-----|--------|
| `/` | Bosh sahifa — barcha maqolalar |
| `/post/<id>` | Bitta maqola sahifasi |
| `/search?q=...` | Qidiruv natijalari |
| `/about` | Biz haqimizda |
| `/services` | Xizmatlar |
| `/admin` | Admin panel (login kerak) |

## 🔌 API Endpoints

| Endpoint | Method | Tavsif |
|----------|--------|--------|
| `/api/health` | GET | Health check |
| `/api/posts` | GET | Barcha postlar (pagination) |
| `/api/posts/<id>` | GET | Bitta post |
| `/api/stats` | GET | Statistika |
| `/sitemap.xml` | GET | SEO sitemap |
| `/robots.txt` | GET | Robots file |

## ⏰ Avtomatlashtirish Jadvali

| Vaqt (Toshkent) | Vazifa |
|-----------------|--------|
| 09:00 | SEO blog maqolasi generatsiyasi + Telegramga yuborish |

Vaqtni `config.py` dagi `SEO_POST_HOUR` / `SEO_POST_MINUTE` orqali o'zgartiring.
Tashqi cron ishlatmoqchi bo'lsangiz: `POST /api/cron/generate?secret=<CRON_SECRET>`.

## 🧵 Redis rate-limit

Web-ilova va scheduler alohida jarayonlarda ishlaydi. Production muhitida
`REDIS_URL` bering — AI rate-limit shu Redis orqali barcha web workerlar uchun
umumiy va atomar ishlaydi. Redis bo'lmasa lokal development uchun in-memory
fallback ishlaydi, lekin u ko'p worker/konteynerga taqsimlanmaydi.

Render Free rejimida scheduler va Telegram webhook web service ichida ishlaydi.
Pullik Background Worker keyinchalik ulansa, scheduler va og'ir fon vazifalari
unga ajratiladi.

## 🚀 Render.com Deploy

1. [Render.com](https://render.com) da yangi Web Service yarating
2. GitHub repo'ni ulang
3. Environment variables qo'shing — ro'yxat [`render.yaml`](render.yaml) da,
   `sync: false` belgilanganlarini qo'lda kiriting
4. Deploy tugmasini bosing

`healthCheckPath` sifatida `/api/health` ishlatiladi.


## 📁 Loyiha Strukturasi

```
trendoai/
├── app.py                 # Flask fabrikasi, CSRF/xavfsizlik, boot ketma-ketligi
├── config.py              # Barcha sozlamalar va muhit o'zgaruvchilari
├── extensions.py          # db / csrf / migrate (sirkulyar importni oldini oladi)
├── models/                # SQLAlchemy modellari
│   ├── post.py            # Blog postlari
│   ├── order.py           # Order, BotOrder
│   ├── interaction.py     # Lead, PushSubscription
│   ├── portfolio.py       # Portfolio keyslari
│   ├── service.py         # Xizmatlar
│   └── bot_models.py      # MenuCategory, MenuItem
├── routes/                # Blueprint'lar
│   ├── web.py             # Ommaviy sahifalar, SEO, sitemap, feed'lar
│   ├── admin.py           # Admin panel va Kanban CRM
│   └── api.py             # REST API, AI chat, webhook, cron
├── services/              # Biznes mantiq
│   ├── cache_service.py   # Redis + in-memory kesh
│   ├── rate_limit_service.py  # Redis sliding-window (atomar, Lua)
│   ├── crm_service.py     # Lead aniqlash va dedup
│   ├── meta_capi.py       # Meta Conversions API
│   ├── push_service.py    # Web Push
│   └── voice_service.py   # Gemini Live audio
├── ai_helpers.py          # Gemini wrapper (kalit + model fallback)
├── ai_generator.py        # SEO maqola generatsiyasi
├── scheduler.py           # APScheduler (kunlik post)
├── bot_service.py         # Telegram bot handlerlari
├── telegram_poster.py     # Telegram xabar yuborish
├── seo_indexer.py         # IndexNow
├── translations.py        # UZ / RU / EN
├── scripts/               # Yordamchi skriptlar (VAPID, admin hash, migratsiya)
├── tests/                 # Pytest to'plami
├── templates/             # Jinja shablonlari
└── static/                # CSS, ikonkalar, sw.js, manifest
```

## 📞 Aloqa

- 🌐 **Sayt**: [trendoai.uz](https://trendoai.uz)
- 📱 **Telegram**: [@trendoai](https://t.me/trendoai)
- 📧 **Email**: info@trendoai.uz

## 📄 Litsenziya

MIT License © 2025 TrendoAI
