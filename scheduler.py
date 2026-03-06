"""
APScheduler yordamida kunlik avtomatlashtirilgan kontent generatsiyasi.
TrendoAI uchun moslashtirilgan.
Har soatda 06:00 dan 22:00 gacha post chiqaradi.
"""

import random
import sys
import traceback
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from ai_generator import generate_post_for_seo, get_last_ai_error
from config import CATEGORIES, SITE_URL, TIMEZONE

# 80/20 QOIDASI BO'YICHA MAVZULAR
# 80% - Mijozga qiymat beradigan foydali ma'lumotlar
# 20% - Xizmatlarimiz haqida yengil eslatmalar
TOPICS = [
    # AI agentlar
    "AI Agent nima: Sun'iy intellekt agentlari haqida to'liq qo'llanma",
    "CrewAI bilan multi-agent tizim yaratish: amaliy loyiha",
    "LangChain agentlari: aqlli AI yordamchi yaratish bosqichma-bosqich",
    "Avtonom AI tizimlar qanday ishlaydi va qayerda foydali",
    "AI Agent va Telegram bot: aqlli biznes assistenti yaratish",
    "RAG: kompaniya ma'lumotlari bilan ishlaydigan AI tizimlari",
    "AI agent ish oqimlarini avtomatlashtirish: real misollar",
    "Multi-agent arxitektura: AI agentlar hamkorligi",
    "AI agent xavfsizligi: risklar va himoya usullari",
    "Biznes uchun AI agent: xarajatlarni kamaytirish yondashuvlari",

    # AI modellar
    "Zamonaviy AI modellarini tanlash: biznes uchun asosiy mezonlar",
    "Reasoning modeli nima va qachon kerak bo'ladi",
    "OpenAI modellari: qaysi vazifaga qaysi tur mos",
    "Google Gemini oilasi: turli vazifalar uchun to'g'ri tanlov",
    "Anthropic Claude oilasi: coding va analysis uchun tanlov mezonlari",
    "Tezkor model va kuchli model: xarajat hamda sifat muvozanati",
    "Kichik model va katta model: qaysi biri sizga mos",
    "AI model tanlash: biznes ehtiyojlariga mos yondashuv",
    "Fine-tuning va RAG: qaysi usul sizga mos",

    # Web saytlar
    "Landing page trendlari: konversiyani oshirish usullari",
    "Next.js bilan professional sayt yaratish",
    "Veb-sayt tezligi optimizatsiyasi: Core Web Vitals bo'yicha amaliy qo'llanma",
    "SEO: Google AI Overview davrida kontent strategiyasi",
    "E-commerce sayt: Uzum va Wildberries integratsiyasi",
    "Progressive Web App: sayt-ilova yaratish",
    "Headless CMS: Strapi va Sanity bilan ishlash",
    "Veb-sayt xavfsizligi: zamonaviy himoya usullari",

    # Telegram botlar
    "Telegram bot yaratishda yangi API imkoniyatlaridan foydalanish",
    "Telegram Mini App: web ilovalar uchun amaliy yondashuv",
    "AI yordamidagi Telegram bot: Gemini integratsiyasi",
    "Telegram botda to'lov: Click, Payme va Uzum Pay",
    "Telegram bot va CRM: mijozlarni avtomatik boshqarish",
    "Telegram bot monetizatsiyasi: premium funksiyalarni sotish",
    "Telegram Stars bilan ishlash: botda monetizatsiya yondashuvlari",
    "Voice message bot: ovozli xabarlarni AI bilan qayta ishlash",

    # AI chatbotlar
    "AI chatbotlar: zamonaviy texnologiyalar va qo'llash usullari",
    "Gemini API bilan o'zbek tilida chatbot yaratish",
    "Chatbot va RAG: kompaniya ma'lumotlari bilan AI",
    "Voice AI chatbot: telefonda gaplashuvchi sun'iy intellekt",
    "WhatsApp AI chatbot integratsiyasi",
    "Chatbot analytics: samaradorlikni o'lchash",
    "24/7 mijoz xizmati: AI bilan xarajatlarni kamaytirish",
    "Chatbot UX: foydalanuvchi tajribasini yaxshilash",

    # Biznes avtomatlashtirish
    "Biznes avtomatlashtirish: AI bilan yangi imkoniyatlar",
    "n8n vs Zapier vs Make: qaysi platformani tanlash",
    "CRM avtomatlashtirish: AmoCRM va AI yechimlar",
    "Email marketing: AI bilan personalizatsiya",
    "HR avtomatlashtirish: ishga qabul va onboarding",
    "Moliyaviy avtomatlashtirish: invoice va hisobotlar",
    "Omborxona avtomatlashtirish: inventory management",
    "Sotuv jarayonini avtomatlashtirish: lead nurturing",

    # Amaliy case study
    "Telegram bot bilan savdoni oshirish: real kejslar",
    "AI chatbot mijoz xizmatida: avtomatlashtirish tajribasi",
    "Landing page va AI bot: konversiyani oshirish strategiyasi",
    "Biznes avtomatlashtirish: vaqt va xarajatni tejash",
    "E-commerce uchun AI: sotuvni oshirish strategiyasi",

    # Texnik qollanmalar
    "Python 3.13 yangiliklari: dasturchilar uchun muhim o'zgarishlar",
    "FastAPI va LangChain bilan AI backend yaratish",
    "Docker bilan AI ilovalarni deploy qilish",
    "PostgreSQL va pgvector: AI uchun vektor baza",
    "Redis caching: AI ilovalar tezligini oshirish",

    # O'zbekiston IT bozori
    "O'zbekistonda IT freelance: hozirgi imkoniyatlar",
    "O'zbek tilidagi AI: mahalliy yechimlar",
    "IT startaplar uchun AI: imkoniyatlar va grantlar",
    "Raqamli O'zbekiston: davlat xizmatlari avtomatlashtirish",
]



def generate_and_publish_post(topic=None, category=None):
    """
    Yangi post generatsiya qilib, bazaga saqlaydi va Telegramga yuboradi.

    topic: Agar berilsa, ushbu mavzuda yozadi. Aks holda random tanlaydi.
    category: Agar berilsa, ushbu kategoriyani qo'yadi. Aks holda random tanlaydi.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'=' * 60}", flush=True)
    print(f"[scheduler] TrendoAI post generatsiyasi boshlandi... [{current_time}]", flush=True)
    print(f"{'=' * 60}", flush=True)
    sys.stdout.flush()

    selected_topic = topic if topic else random.choice(TOPICS)
    selected_category = category if category else random.choice(CATEGORIES)

    print(f"[scheduler] Mavzu: {selected_topic}")
    print(f"[scheduler] Kategoriya: {selected_category}")

    from app import Post, app, db

    with app.app_context():
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
                print(f"[scheduler] Rasm: {image_url[:50]}...")

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

                print(f"[scheduler] Yangi post '{new_post.title}' bazaga saqlandi.")

                from telegram_poster import send_photo_to_channel, send_to_telegram_channel

                def escape_md(text):
                    if not text:
                        return text
                    for char in ["_", "*", "[", "]", "`", "~", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
                        text = text.replace(char, "\\" + char)
                    return text

                post_url = f"{SITE_URL}/post/{new_post.id}"
                safe_title = escape_md(new_post.title)
                safe_category = escape_md(selected_category.replace(" ", "_"))

                tg_caption = f"""Yangi Maqola!

*{safe_title}*

Kategoriya: #{safe_category}
O'qish vaqti: {new_post.reading_time} daqiqa

[Maqolani o'qish]({post_url})

#TrendoAI #Texnologiya"""

                success = False
                if image_url:
                    success = send_photo_to_channel(image_url, tg_caption)
                else:
                    success = send_to_telegram_channel(tg_caption)

                if success:
                    print("[scheduler] Telegram kanalga yuborildi!")
                else:
                    print("[scheduler] Telegram yuborishda muammo yuz berdi")

                try:
                    from app import notify_all_subscribers

                    print("[scheduler] Push xabar yuborilmoqda...")
                    push_count = notify_all_subscribers(
                        title=f"Yangi: {new_post.title}",
                        message=f"{selected_category} | O'qish uchun bosing!",
                        url=post_url,
                    )
                    print(f"[scheduler] {push_count} ta obunachiga push yuborildi.")
                except Exception as push_err:
                    print(f"[scheduler] Push xabar xatosi: {push_err}")

                return True

            ai_error_detail = get_last_ai_error() or "Noma'lum AI xatosi"
            error_msg = (
                "Post generatsiya qilishda xatolik yuz berdi "
                "(AI javob bermadi yoki xato qaytardi).\n"
                f"Mavzu: {selected_topic}\n"
                f"Sabab: {ai_error_detail}"
            )
            print(error_msg)
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
            print(error_msg, flush=True)
            traceback.print_exc()
            sys.stdout.flush()
            try:
                from telegram_poster import send_admin_alert

                send_admin_alert(error_msg)
            except Exception:
                pass
            return False

    print(f"{'=' * 60}\n", flush=True)


scheduler = BackgroundScheduler(timezone=TIMEZONE)

for hour in range(6, 23):
    scheduler.add_job(
        generate_and_publish_post,
        "cron",
        hour=hour,
        minute=0,
        id=f"hourly_post_{hour}",
        name=f"TrendoAI Soatlik Post ({hour}:00)",
    )

print("[scheduler] Har kuni 06:00 - 22:00 oralig'ida 17 ta post sozlandi")



def get_scheduled_jobs():
    """Barcha rejalashtirilgan vazifalarni qaytaradi."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time),
            }
        )
    return jobs


if __name__ == "__main__":
    scheduler.start()
    print("[scheduler] TrendoAI Scheduler ishga tushdi!")
    print(f"[scheduler] Jami vazifalar: {len(scheduler.get_jobs())}")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Scheduler to'xtatildi.")