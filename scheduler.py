"""
APScheduler yordamida kunlik avtomatlashtirilgan kontent generatsiyasi.
TrendoAI uchun moslashtirilgan.

Bitta reja mavjud: har kuni SEO_POST_HOUR:SEO_POST_MINUTE (standart 09:00,
Asia/Tashkent) da bitta post generatsiya qilinadi va Telegramga yuboriladi.
"""

import random
import sys
import time
import traceback
from datetime import datetime, timedelta
from utils.logger import setup_logger
logger = setup_logger("scheduler")


from apscheduler.schedulers.background import BackgroundScheduler

from services.ai_service import generate_post_for_seo, get_last_ai_error
from config import CATEGORIES, SITE_URL, TIMEZONE

# 80/20 QOIDASI BO'YICHA 2026-YILNING ENG ZAMONAVIY VA TALABGIR MAVZULARI
TOPICS = [
    # 🧠 Zamonaviy AI Modellar va Reasoning (Fikrlash)
    "Gemini 3.7 Flash va DeepSeek R1: Murakkab biznes mantiqini avtomatlashtirish",
    "Hybrid Reasoning (Gibrid fikrlash) nima va dasturlashda unumdorlikni qanday 3x oshiradi",
    "Local LLM (Ollama va vLLM) vs Cloud API: Korxona maxfiyligi uchun qaysi biri ma'qul",
    "Kichik modellar (SLM) inqilobi: Server xarajatlarini 80% ga kamaytirish usullari",
    "Google Gemini 3 avlodi: Multimodal AI vositalarini biznesga joriy qilish",
    "DeepSeek R1 arxitekturasi: Ochiq kodli AI yordamida tejamkor tahliliy tizimlar",
    "AI Agentlarda Prompt Caching: API xarajatlarini keskin kamaytirish sirlari",

    # 🤖 AI Agentlar va Avtonom Ish Oqimlari (Workflow Automation)
    "Model Context Protocol (MCP) nima: AI vositalarni ma'lumotlar bazasiga ulashning yangi standarti",
    "n8n va Gemini AI bilan to'liq avtomatlashtirilgan savdo voronkasi (Sales Pipeline) qurish",
    "AI SDR (Sales Development Rep): Sayt va Telegramda mijozlar bilan mustaqil savdo qiluvchi agent",
    "CrewAI va AutoGen: 1 ta xodim o'rniga 5 ta ixtisoslashgan AI agent boshqarish",
    "RAG 2.0 (Retrieval-Augmented Generation): Kompaniya PDF, Excel va bazalarini AI ga o'rgatish",
    "Avtonom AI agentlar xavfsizligi: Prompt Injection hujumlaridan himoyalanish",
    "AI bilan xatoliklarni avtomatik tuzatish va loglarni tahlil qilish tizimi",

    # 📱 Telegram Mini Apps (TMA), Botlar va To'lovlar
    "Telegram Mini App (TMA) va React/Vue: Nega barcha bizneslar mobil ilovadan TMA ga o'tmoqda",
    "Telegram Stars va Mahalliy To'lovlar (Click/Payme): Raqamli tovar va xizmatlarni qonuniy sotish",
    "Telegram botda Webhook vs Polling: 100,000+ faol foydalanuvchiga xizmat ko'rsatish arxitekturasi",
    "Voice AI Telegram Bot: Ovozli xabarlarni matnga o'girib, aqlli ovozda javob qaytarish",
    "Telegram Bot orqali to'liq E-commerce do'kon: Savat, buyurtma kuzatish va kassa cheklari",
    "Telegram Bot va Google Sheets / Notion avtomatik sinxronizatsiyasi",
    "Telegram Botda Face-ID va Biometrik autentifikatsiya imkoniyatlari",

    # 🌐 Zamonaviy Veb-Dasturlash va Super Tezlik (PageSpeed 99+)
    "Next.js 15 va React Server Components: Google PageSpeed 99+ ball olish sirlari",
    "Astro va TailwindCSS bilan o'ta tezkor korporativ landing page qurish",
    "PWA (Progressive Web App): Saytni foydalanuvchi telefoniga ilova sifatida o'rnatish",
    "Veb-sayt xavfsizligi: Cloudflare, Rate Limiting va DDoS hujumlaridan ishonchli qalqon",
    "Google AI Overviews (SGE) davrida SEO strategiyasi: Maqolalarni AI qidiruvlarida 1-o'ringa chiqarish",
    "WebP va AVIF formatlar: Rasmlar hajmini 85% ga kamaytirib, saytni 0.3 soniyada ochish",
    "Headless E-commerce: Sayt dizayni va CRM tizimini mustaqil boshqarish afzalliklari",

    # 💼 Haqiqiy Biznes keyslar va ROI (Daromadni 2-3x oshirish)
    "Restoran va Kafelar uchun Telegram Menyu Bot: Ofitsiantlar yuklamasini 40% ga qisqartirish keysi",
    "O'quv markazlari va Kurslar uchun CRM + Bot: Lidlar yo'qolishini 0 ga tushirish tajribasi",
    "Klinikalar va Stomatologiyalar uchun Avtomatik Navbat va Qabul boti",
    "Uzum Market va Wildberries sotuvchilari uchun AI narx monitoringi va avto-javob",
    "Rieltorlik va Ko'chmas mulk agentliklari uchun AI maslahatchi: Mijoz saralash (Lead Qualification)",
    "Avtoservis va Yetkazib berish xizmatlarini Telegram orqali boshqarish",
    "AmoCRM va Bitrix24 ga Gemini AI ulash: Sotuvchilarga real vaqtda maslahat beruvchi tizim",

    # 🛠 Texnik Arxitektura va Dasturlash Asboblari
    "FastAPI va Async Python: Yuqori yuklamali AI backend arxitekturasi",
    "PostgreSQL va pgvector: AI uchun qidiruv va tavsiya tizimlari yaratish",
    "Docker va CI/CD (GitHub Actions): Loyihani 1 bosishda serverga yangilash",
    "Redis Caching va Celery: Og'ir vazifalarni fonda tezkor bajarish",
    "API xavfsizligi: JWT, OAuth2 va API Rate Limiting qoidalari",

    # 🇺🇿 O'zbekiston IT Bozori va Trendlari
    "O'zbekistonda B2B AI yechimlari: Qaysi sohalar avtomatlashtirishga eng ko'p ehtiyoj sezmoqda",
    "IT Outsourcing va Mahalliy xizmatlar: Sifatli dasturiy ta'minot yaratish mezonlari",
    "Raqamli O'zbekiston: Milliy to'lov tizimlari va davlat xizmatlari API integratsiyasi",
]



# Kunlik post bir marta chiqishi kerak. Ichki APScheduler bilan tashqi cron
# bir kunda ikkalasi ham ishga tushsa, ikkinchisi shu oyna ichida to'xtaydi.
_DUPLICATE_WINDOW_HOURS = 20


def _strip_tz(value):
    """tz-aware vaqtni naive ga keltiradi.

    Postgres ``now()`` ni ``timestamptz`` qaytaradi, ya'ni psycopg2 tz-aware
    datetime beradi. ``Post.created_at`` esa oddiy ``DateTime`` — naive.
    Ularni to'g'ridan-to'g'ri ayirish ``TypeError`` beradi va qalqon jim
    ravishda ishlamay qolardi (chaqiruvchi xatoni yutib, generatsiyani davom
    ettiradi). Ikkala qiymat ham bir xil sessiya mintaqasidagi ``now()`` dan
    kelgani uchun tzinfo ni shunchaki olib tashlash to'g'ri natija beradi.
    """
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _post_published_recently(window_hours=_DUPLICATE_WINDOW_HOURS):
    """Oxirgi ``window_hours`` soat ichida post chiqqan-chiqmaganini aytadi.

    Ikkala vaqt ham bazaning o'z soatidan olinadi: ``Post.created_at`` ustuni
    ``server_default=now()`` bilan to'ladi, shuning uchun uni ilova soati bilan
    solishtirish mintaqa farqi bo'lganda noto'g'ri natija berardi.
    """
    from app import Post, db

    last_created = _strip_tz(db.session.query(db.func.max(Post.created_at)).scalar())
    if not isinstance(last_created, datetime):
        return False

    reference = _strip_tz(db.session.query(db.func.now()).scalar())
    if not isinstance(reference, datetime):
        # SQLite ``now()`` ni matn qaytaradi — u holda ilova soatiga qaytamiz.
        reference = datetime.now()

    return (reference - last_created) < timedelta(hours=window_hours)


def generate_and_publish_post(topic=None, category=None, force=False):
    """
    Yangi post generatsiya qilib, bazaga saqlaydi va Telegramga yuboradi.

    topic: Agar berilsa, ushbu mavzuda yozadi. Aks holda takrorlanmagan yangi trend mavzu tanlaydi.
    category: Agar berilsa, ushbu kategoriyani qo'yadi. Aks holda random tanlaydi.
    force: Kunlik takrorlanish qalqonini chetlab o'tadi (qo'lda chaqiruvlar uchun).
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"\n{'=' * 60}")
    logger.info(f"[scheduler] TrendoAI post generatsiyasi boshlandi... [{current_time}]")
    logger.info(f"{'=' * 60}")
    sys.stdout.flush()

    from app import Post, app, db

    with app.app_context():
        # Avtomatik chaqiruvlarda kuniga bitta post. Tekshiruvning o'zi yiqilsa
        # generatsiya davom etadi — post ikkilangandan ko'ra chiqmay qolgani yomonroq.
        if not force and topic is None:
            try:
                if _post_published_recently():
                    logger.info("[scheduler] Bugun post allaqachon chiqarilgan — o'tkazib yuborildi.")
                    return None
            except Exception as exc:
                logger.warning(f"[scheduler] Takrorlanish tekshiruvi ishlamadi, davom etamiz: {exc}")

        # Takrorlanmagan yangi trend mavzuni tanlash
        if topic:
            selected_topic = topic
        else:
            try:
                recent_topics = [
                    row[0] for row in db.session.query(Post.topic).order_by(Post.created_at.desc()).limit(30).all()
                    if row[0]
                ]
                available_topics = [t for t in TOPICS if t not in recent_topics]
                if not available_topics:
                    available_topics = TOPICS
                selected_topic = random.choice(available_topics)
            except Exception:
                selected_topic = random.choice(TOPICS)

        selected_category = category if category else random.choice(CATEGORIES)

        logger.info(f"[scheduler] Tanlangan trend mavzu: {selected_topic}")
        logger.info(f"[scheduler] Kategoriya: {selected_category}")
        try:
            post_data = generate_post_for_seo(selected_topic)

            if post_data:
                from image_fetcher import get_image_for_topic, build_image_prompt

                existing_unsplash_urls = [
                    row[0] for row in db.session.query(Post.image_url)
                    .filter(
                        Post.image_url.isnot(None),
                        Post.image_url.contains("images.unsplash.com"),
                    )
                    .all()
                ]
                image_url = get_image_for_topic(
                    selected_topic,
                    exclude_image_urls=existing_unsplash_urls,
                )
                image_prompt = build_image_prompt(
                    topic=selected_topic,
                    title=post_data.get("title"),
                    category=selected_category,
                )
                logger.info(f"[scheduler] Rasm: {image_url[:50]}...")

                new_post = Post(
                    title=post_data["title"],
                    content=post_data["content"],
                    topic=selected_topic,
                    category=selected_category,
                    keywords=post_data["keywords"],
                    image_url=image_url,
                    image_prompt=image_prompt,
                    is_published=True,
                )
                new_post.reading_time = new_post.calculate_reading_time()

                db.session.add(new_post)
                db.session.commit()

                new_post.slug = new_post.generate_slug()
                db.session.commit()

                logger.info(f"[scheduler] Yangi post '{new_post.title}' bazaga saqlandi.")

                from telegram_poster import send_photo_to_channel, send_to_telegram_channel

                def escape_md(text):
                    if not text:
                        return text
                    for char in ["_", "*", "[", "]", "`", "~", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
                        text = text.replace(char, "\\" + char)
                    return text

                post_url = f"{SITE_URL}/blog/{new_post.slug}" if new_post.slug else f"{SITE_URL}/post/{new_post.id}"
                safe_title = escape_md(new_post.title)
                safe_category = escape_md(selected_category.replace(" ", "_"))

                tg_caption = f"""📝 *Yangi Maqola!*

*{safe_title}*

🏷 *Kategoriya:* #{safe_category}
⏱ *O'qish vaqti:* {new_post.reading_time} daqiqa

🔗 [Maqolani to'liq o'qish]({post_url})

#TrendoAI #Texnologiya #Biznes"""

                success = False
                if image_url:
                    success = send_photo_to_channel(image_url, tg_caption)
                else:
                    success = send_to_telegram_channel(tg_caption)

                if success:
                    logger.info("[scheduler] Telegram kanalga yuborildi!")
                else:
                    logger.info("[scheduler] Telegram yuborishda muammo yuz berdi")

                try:
                    from app import notify_all_subscribers

                    logger.info("[scheduler] Push xabar yuborilmoqda...")
                    push_count = notify_all_subscribers(
                        title=f"🆕 Yangi Maqola: {new_post.title}",
                        message=f"{selected_category} | O'qish uchun bosing!",
                        url=post_url,
                    )
                    logger.info(f"[scheduler] {push_count} ta obunachiga push yuborildi.")
                except Exception as push_err:
                    logger.info(f"[scheduler] Push yuborishda xato: {push_err}")

                try:
                    from seo_indexer import ping_search_engines
                    ping_search_engines([post_url, f"{SITE_URL}/sitemap.xml", f"{SITE_URL}/blog"])
                    logger.info("[scheduler] Google & IndexNow tezkor indekslashga ping yuborildi!")
                except Exception as seo_err:
                    logger.error(f"[scheduler] SEO ping error: {seo_err}")

                return True

            ai_error_detail = get_last_ai_error() or "Noma'lum AI xatosi"
            error_msg = (
                "Post generatsiya qilishda xatolik yuz berdi "
                "(AI javob bermadi yoki xato qaytardi).\n"
                f"Mavzu: {selected_topic}\n"
                f"Sabab: {ai_error_detail}"
            )
            logger.error(error_msg)
            try:
                from telegram_poster import send_admin_alert

                send_admin_alert(error_msg)
            except Exception:
                pass
            return False
        except Exception as exc:
            error_msg = (
                "Scheduler (generate_post) xatosi yuz berdi:\n\n"
                f"{str(exc)}\n\n"
                f"Mavzu: {selected_topic}"
            )
            logger.error(error_msg)
            traceback.print_exc()
            sys.stdout.flush()
            try:
                from telegram_poster import send_admin_alert

                send_admin_alert(error_msg)
            except Exception:
                pass
            return False

    logger.info(f"{'=' * 60}\n")


scheduler = BackgroundScheduler(timezone=TIMEZONE)

# Har kuni faqat bitta post chiqarish (soat 09:00 yoki configdagi vaqt)
try:
    from config import SEO_POST_HOUR, SEO_POST_MINUTE
except ImportError:
    SEO_POST_HOUR, SEO_POST_MINUTE = 9, 0

scheduler.add_job(
    generate_and_publish_post,
    "cron",
    hour=SEO_POST_HOUR,
    minute=SEO_POST_MINUTE,
    id="daily_seo_post",
    name=f"TrendoAI Kunlik Post ({SEO_POST_HOUR}:{SEO_POST_MINUTE:02d})",
)

logger.info(f"[scheduler] Har kuni soat {SEO_POST_HOUR}:{SEO_POST_MINUTE:02d} da 1 ta post chiqishi sozlandi")



def get_scheduled_jobs():
    """Barcha rejalashtirilgan vazifalarni qaytaradi."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                # Scheduler hali start qilinmagan bo'lsa next_run_time mavjud emas
                "next_run": str(getattr(job, "next_run_time", "pending (scheduler ishga tushmagan)")),
            }
        )
    return jobs


if __name__ == "__main__":
    scheduler.start()
    logger.info("[scheduler] TrendoAI Scheduler ishga tushdi!")
    logger.info(f"[scheduler] Jami vazifalar: {len(scheduler.get_jobs())}")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("Scheduler to'xtatildi.")
