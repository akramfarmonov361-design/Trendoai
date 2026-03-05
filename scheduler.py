# scheduler.py
"""
APScheduler yordamida kunlik avtomatlashtirilgan kontent generatsiyasi.
TrendoAI uchun moslashtirilgan.
Har soatda 06:00 dan 22:00 gacha post chiqaradi.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from ai_generator import generate_post_for_seo
from telegram_poster import send_to_telegram_channel
from config import SITE_URL, TIMEZONE, CATEGORIES
import random
import sys
import traceback
from datetime import datetime

# 80/20 QOIDASI BO'YICHA MAVZULAR (2026-YIL UCHUN YANGILANDI)
# 80% - Mijozga qiymat beradigan foydali ma'lumotlar
# 20% - Xizmatlarimiz haqida yengil eslatmalar

TOPICS = [
    # ============ AI AGENTLAR (2026 TREND) ============
    "AI Agent nima: Sun'iy intellekt agentlari haqida to'liq qo'llanma 2026",
    "CrewAI bilan multi-agent tizim yaratish: Amaliy loyiha",
    "LangChain Agents: Aqlli AI yordamchi yaratish bosqichma-bosqich",
    "AutoGPT va AgentGPT: Avtonom AI tizimlar qanday ishlaydi",
    "AI Agent + Telegram Bot: Aqlli biznes assistenti yaratish",
    "RAG (Retrieval-Augmented Generation): Ma'lumotlar bazasi bilan AI",
    "AI Agent ish oqimlarini avtomatlashtirish: Real misollar",
    "Multi-agent arxitektura 2026: AI Agentlar Hamkorligi",
    "AI Agent xavfsizligi: Risklar va himoya usullari",
    "Biznes uchun AI Agent: Xarajatlarni 70% kamaytirish",
    
    # ============ YANGI AI MODELLARI (2026 YIL - REAL) ============
    "GPT-5.2 vs Gemini 3 vs Claude Opus 4.5: 2026 yil eng kuchli AI modellari",
    "GPT-5.2 Thinking: OpenAI ning yangi reasoning modeli qanday ishlaydi",
    "Gemini 3 Pro va Deep Think: Google ning eng yangi AI modellari",
    "Claude Opus 4.5: Anthropic ning coding va reasoning ustasi",
    "Gemini 3 Flash Preview: Tezkor va arzon AI yechim 2026",
    "OpenAI o1 vs GPT-5.2: Mantiqiy fikrlash modellarini solishtirish",
    "Claude Sonnet 4.5 vs Claude Haiku 4.5: Qaysi biri sizga mos",
    "AI modellarni tanlash 2026: Biznes ehtiyojlariga mos AI",
    "Fine-tuning vs RAG: Qaysi usul sizga mos?",

    
    # ============ WEB SAYTLAR (80% QIYMAT) ============
    "2026-yil Landing page trendlari: Konversiyani 2x oshirish",
    "Next.js 15 bilan professional sayt yaratish",
    "Veb-sayt tezligi optimizatsiyasi: Core Web Vitals 2026",
    "SEO 2026: Google AI Overview va yangi qoidalar",
    "E-commerce sayt: Uzum, Wildberries integratsiyasi",
    "Progressive Web App (PWA): Sayt-ilova yaratish",
    "Headless CMS: Strapi, Sanity bilan ishlash",
    "Veb-sayt xavfsizligi 2026: Zamonaviy himoya usullari",
    
    # ============ TELEGRAM BOTLAR (80% QIYMAT) ============
    "Telegram Bot 2026: Yangi API imkoniyatlari",
    "Telegram Mini App 2.0: Web ilovalar evolyutsiyasi",
    "AI-powered Telegram bot: Gemini integratsiyasi",
    "Telegram botda to'lov: Click, Payme, Uzum Pay",
    "Telegram bot + CRM: Mijozlarni avtomatik boshqarish",
    "Telegram bot monetizatsiya: Premium funksiyalar sotish",
    "Telegram Stars: Botda pul ishlashning yangi usuli",
    "Voice message bot: Ovozli xabarlarni AI bilan qayta ishlash",
    
    # ============ AI CHATBOTLAR (80% QIYMAT) ============
    "AI Chatbot 2026: Eng so'nggi texnologiyalar",
    "Gemini API bilan o'zbek tilida chatbot yaratish",
    "Chatbot + RAG: Kompaniya ma'lumotlari bilan AI",
    "Voice AI chatbot: Telefonda gaplashuvchi sun'iy intellekt",
    "WhatsApp AI chatbot integratsiyasi",
    "Chatbot analytics: Samaradorlikni o'lchash 2026",
    "24/7 mijoz xizmati: AI bilan xarajatlarni kamaytirish",
    "Chatbot UX: Foydalanuvchi tajribasini yaxshilash",
    
    # ============ BIZNES AVTOMATLASHTIRISH ============
    "Biznes avtomatlashtirish 2026: AI bilan yangi imkoniyatlar",
    "n8n vs Zapier vs Make: Qaysi platformani tanlash",
    "CRM avtomatlashtirish: AmoCRM + AI yechimlar",
    "Email marketing 2026: AI bilan personalizatsiya",
    "HR avtomatlashtirish: Ishga qabul va onboarding",
    "Moliyaviy avtomatlashtirish: Invoice va hisobotlar",
    "Omborxona avtomatlashtirish: AI inventory management",
    "Sotuv jarayonini avtomatlashtirish: Lead nurturing",
    
    # ============ AMALIY CASE STUDIES ============
    "Telegram bot bilan oylik 50 million so'm: Real kejs",
    "AI chatbot mijoz xizmatida: 90% avtomatizatsiya",
    "Landing page + AI bot = Konversiya 300% oshdi",
    "Biznes avtomatlashtirish: 40 soat/oyni tejash",
    "E-commerce AI: Sotuvni 200% oshirish strategiyasi",
    
    # ============ TEXNIK QO'LLANMALAR ============
    "Python 3.13 yangiliklari: Dasturchilar uchun muhim o'zgarishlar",
    "FastAPI + LangChain: AI backend yaratish",
    "Docker bilan AI ilovalarni deploy qilish",
    "PostgreSQL + pgvector: AI uchun vektor baza",
    "Redis caching: AI ilovalar tezligini oshirish",
    
    # ============ O'ZBEKISTON IT BOZORI ============
    "O'zbekistonda IT freelance: 2026 imkoniyatlar",
    "O'zbek tilidagi AI: Mahalliy yechimlar",
    "IT startaplar uchun AI: Imkoniyatlar va grantlar",
    "Raqamli O'zbekiston: Davlat xizmatlari avtomatlashtirish",
]



def generate_and_publish_post(topic=None, category=None):
    """
    Yangi post generatsiya qilib, bazaga saqlaydi va Telegramga yuboradi.
    
    topic: Agar berilsa, ushbu mavzuda yozadi. Aks holda random tanlaydi.
    category: Agar berilsa, ushbu kategoriyani qo'yadi. Aks holda random tanlaydi.
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*60}", flush=True)
    print(f"🚀 TrendoAI — Post generatsiyasi boshlandi... [{current_time}]", flush=True)
    print(f"{'='*60}", flush=True)
    sys.stdout.flush()
    
    # Mavzu va kategoriya tanlash
    selected_topic = topic if topic else random.choice(TOPICS)
    selected_category = category if category else random.choice(CATEGORIES)
    
    print(f"📌 Mavzu: {selected_topic}")
    print(f"📂 Kategoriya: {selected_category}")
    
    from app import app, db, Post
    with app.app_context():
        try:
            post_data = generate_post_for_seo(selected_topic)
            
            if post_data:
                # Rasm olish
                from image_fetcher import get_image_for_topic
                image_url = get_image_for_topic(selected_topic)
                print(f"🖼️ Rasm: {image_url[:50]}...")
                
                new_post = Post(
                    title=post_data['title'],
                    content=post_data['content'],
                    topic=selected_topic,
                    category=selected_category,
                    keywords=post_data['keywords'],
                    image_url=image_url,
                    is_published=True
                )
                new_post.reading_time = new_post.calculate_reading_time()
                
                db.session.add(new_post)
                db.session.commit()
                
                new_post.slug = new_post.generate_slug()
                db.session.commit()
                
                print(f"✅ Yangi post '{new_post.title}' bazaga saqlandi.")
                
                # Telegramga yuborish
                from telegram_poster import send_photo_to_channel, send_to_telegram_channel
                
                # Markdown maxsus belgilarni escape qilish
                def escape_md(text):
                    if not text: return text
                    # Escape characters that have special meaning in Markdown V2
                    # _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., !
                    # We only escape those that are likely to appear in titles/categories
                    # and would cause formatting issues.
                    for char in ['_', '*', '[', ']', '`', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
                        text = text.replace(char, '\\' + char)
                    return text
                
                post_url = f"{SITE_URL}/post/{new_post.id}"
                safe_title = escape_md(new_post.title)
                safe_category = escape_md(selected_category.replace(' ', '_')) # Replace spaces then escape
                
                tg_caption = f"""📝 *Yangi Maqola!*
    
*{safe_title}*
    
🏷 Kategoriya: #{safe_category}
⏱ O'qish vaqti: {new_post.reading_time} daqiqa
    
🔗 [Maqolani o'qish]({post_url})
    
#TrendoAI #Texnologiya"""
                
                # Rasm bilan yoki rasmsiz yuborish
                success = False
                if image_url:
                    success = send_photo_to_channel(image_url, tg_caption)
                else:
                    success = send_to_telegram_channel(tg_caption)
                
                if success:
                    print("✅ Telegram kanalga yuborildi!")
                else:
                    print("⚠️ Telegram yuborishda muammo yuz berdi")
                
                # Push Notification yuborish
                try:
                    from app import notify_all_subscribers
                    print("🔔 Push xabar yuborilmoqda...")
                    push_count = notify_all_subscribers(
                        title=f"🆕 Yangi: {new_post.title}",
                        message=f"{selected_category} | O'qish uchun bosing!",
                        url=post_url
                    )
                    print(f"✅ {push_count} ta obunachiga push yuborildi.")
                except Exception as push_err:
                     print(f"⚠️ Push xabar xatosi: {push_err}")
                    
                return True
            else:
                error_msg = f"❌ Post generatsiya qilishda xatolik yuz berdi (AI javob bermadi yoki xato qaytardi).\nMavzu: {selected_topic}"
                print(error_msg)
                try:
                    from telegram_poster import send_admin_alert
                    send_admin_alert(error_msg)
                except:
                    pass
                return False
        except Exception as e:
            error_msg = f"❌ Scheduler (generate_post) xatosi yuz berdi:\n\n{str(e)}\n\nMavzu: {selected_topic}"
            print(error_msg, flush=True)
            traceback.print_exc()
            sys.stdout.flush()
            try:
                from telegram_poster import send_admin_alert
                send_admin_alert(error_msg)
            except:
                pass
            return False
    
    print(f"{'='*60}\n", flush=True)


# Scheduler yaratish
scheduler = BackgroundScheduler(timezone=TIMEZONE)

# Har soatda 06:00 dan 22:00 gacha post chiqarish
# 17 ta soat = 17 ta post kuniga
for hour in range(6, 23):  # 6, 7, 8... 22
    scheduler.add_job(
        generate_and_publish_post, 
        'cron', 
        hour=hour, 
        minute=0,
        id=f'hourly_post_{hour}',
        name=f'TrendoAI Soatlik Post ({hour}:00)'
    )

print(f"📅 Scheduler sozlandi: Har kuni 06:00 - 22:00 oralig'ida 17 ta post")


def get_scheduled_jobs():
    """Barcha rejalashtirilgan vazifalarni qaytaradi."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': str(job.next_run_time)
        })
    return jobs


if __name__ == "__main__":
    scheduler.start()
    print("🚀 TrendoAI Scheduler ishga tushdi!")
    print(f"📊 Jami vazifalar: {len(scheduler.get_jobs())}")
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Scheduler to'xtatildi.")