"""
Desktopdagi loyihalarni Trendo AI Portfolio bazasiga avtomatik joylash va yangilash xizmati.
Barcha rasmlar Meta Ads (1:1 va 16:9) standartlariga moslangan Premium HD formatda.
"""
from extensions import db
from models.portfolio import Portfolio
from utils.logger import setup_logger
logger = setup_logger("seed_portfolio")


PROJECTS_DATA = [
    {
        'title': 'Optombazar.uz - O\'zbekistondagi Yirik B2B Ulgurji Savdo Platformasi',
        'category': 'web',
        'emoji': '🏬',
        'technologies': 'Next.js 14, TypeScript, Prisma, PostgreSQL, Docker, TailwindCSS, Caddy',
        'price': '15,000,000 UZS',
        'client_name': 'Optombazar B2B Group',
        'image_url': 'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=85&w=1200&auto=format&fit=crop',
        'description': 'Katta ulgurji savdo korxonalari va do\'konlar uchun avtomatlashtirilgan ko\'p omborli B2B marketplace platformasi.',
        'problem': 'Ulgurji savdogarlar va do\'kon egalari o\'rtasida tovarlarni buyurtma qilish, hisob-kitob va yetkazib berish jarayonlari qo\'lda (qog\'oz va telefon orqali) boshqarilar edi.',
        'solution': 'To\'liq avtomatlashtirilgan ko\'p omborli, tannarx va ulgurji narxlar kalkulyatori, mijozlar shaxsiy kabineti va buyurtma boshqaruviga ega zamonaviy B2B platforma ishlab chiqildi.',
        'result': 'Buyurtmalarni qabul qilish vaqti 75% ga qisqardi, savdo aylanmasi 3.5 barobarga oshdi.',
        'features': 'Ko\'p omborli inventar, B2B shaxsiy kabinet, Ulgurji narxlar tizimi, Eksport/Import Excel, Tezkor qidiruv'
    },
    {
        'title': 'Quiz Video Generator AI - Shorts, Reels va TikTok uchun Avtomatik Video Generator',
        'category': 'ai',
        'emoji': '🎬',
        'technologies': 'Vite, TypeScript, React, Gemini AI, Canvas 2D, WebAudio API, Node.js',
        'price': '6,000,000 UZS',
        'client_name': 'Media & SMM Agentliklari',
        'image_url': 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=85&w=1200&auto=format&fit=crop',
        'description': 'TikTok, YouTube Shorts va Instagram Reels uchun savol-javob (quiz) formatidagi videolarni bir necha soniyada avtomatik yasab beruvchi AI stansiyasi.',
        'problem': 'SMM mutaxassislari va blogerlar har kuni TikTok va YouTube Shorts uchun savol-javob (quiz) videolarini qo\'lda montaj qilishga 3-4 soatlab vaqt sarflar edi.',
        'solution': 'Sun\'iy intellekt yordamida matnli savollarni bir necha soniyada musiqali, animatsiyali va ovozli vertikal 9:16 videolarga aylantirib beruvchi generator yaratildi.',
        'result': 'Kuniga 50+ gacha professional video yaratish imkoniyati paydo bo\'ldi, montaj xarajatlari 90% ga kamaydi.',
        'features': 'AI matn generatsiya, 9:16 vertikal format, Dinamik taymer, Fon musiqasi, Ovozli diktor, 1080p eksport'
    },
    {
        'title': 'Veo Video Generator AI - Google Veo asosidagi Video Ishlab Chiqarish Stansiyasi',
        'category': 'ai',
        'emoji': '🎥',
        'technologies': 'Python, Google Veo AI, FastAPI, FFmpeg, React, TailwindCSS',
        'price': '12,000,000 UZS',
        'client_name': 'Reklama va Media Studiyalari',
        'image_url': 'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?q=85&w=1200&auto=format&fit=crop',
        'description': 'Google Veo neyron tarmog\'i asosida matnli tavsif (prompt) orqali 4K kinemotografik video lavhalarni generatsiya qiluvchi tizim.',
        'problem': 'Reklama va kinostudiyalar uchun yuqori sifatli vizual effektlar va video kadrlarni suratga olish juda qimmatga tushar edi.',
        'solution': 'Google Veo sun\'iy intellekt modeli orqali faqat matnli prompt orqali kinemotografik 4K/1080p video kadrlarni generatsiya qiluvchi tizim ishlab chiqildi.',
        'result': 'Video ishlab chiqarish xarajatlari 80% ga kamaytirildi, 1 ta kadrni tayyorlash 1 daqiqaga tushdi.',
        'features': 'Kinemotografik 4K video, Prompt muhandisligi, FFmpeg post-processing, Harakat traektoriyalari nazorati'
    },
    {
        'title': 'Insta-Dub UZ - Sun\'iy Intellekt Video Dublyaj va Ovozlashtirish Platformasi',
        'category': 'ai',
        'emoji': '🎙️',
        'technologies': 'Python, Whisper AI, ElevenLabs, PyTorch, MoviePy, Flask',
        'price': '8,000,000 UZS',
        'client_name': 'Online Ta\'lim va Dublyaj Studiyalari',
        'image_url': 'https://images.unsplash.com/photo-1590602847861-f357a9332bbc?q=85&w=1200&auto=format&fit=crop',
        'description': 'Xorijiy videolarni bir necha daqiqada o\'zbek tiliga tabiiy ovoz bilan professional dublyaj qiluvchi AI tizimi.',
        'problem': 'Xorijiy (ingliz, rus, turk) videolarni o\'zbek tiliga tarjima qilish va dublyaj qilish uchun qimmatbaho aktyorlar va studiyalar kerak edi.',
        'solution': 'Whisper orqali ovozdan matnga o\'tkazish, Gemini orqali professional tarjima va neyron ovozlar yordamida lab harakatiga mos (lip-sync) dublyaj qiluvchi platforma qurildi.',
        'result': '1 soatlik video 5 daqiqada o\'zbekcha ovozlashtirildi, dublyaj xarajatlari 15 barobarga arzonlashdi.',
        'features': 'Ko\'p tilli tarjima, Haqiqiy inson ovozi klonlash, Subtitrlar avtomatik generatsiyasi, Lip-sync moslashtirish'
    },
    {
        'title': 'Luxe Core - Premium Kiyim va Aksessuarlar E-Commerce Brend Do\'koni',
        'category': 'web',
        'emoji': '💎',
        'technologies': 'Next.js, TailwindCSS, PostgreSQL, Stripe, Payme, Click, Cloudinary',
        'price': '9,000,000 UZS',
        'client_name': 'Luxe Core Fashion Brand',
        'image_url': 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?q=85&w=1200&auto=format&fit=crop',
        'description': 'Zamonaviy moda brendlari uchun premium dizaynga va qulay xarid imkoniyatlariga ega onlayn butik do\'koni.',
        'problem': 'Premium brend uchun oddiy shablon do\'konlar to\'g\'ri kelmas, mijozlar uchun yuqori darajadagi minimalist va tezkor onlayn xarid tajribasi talab etilar edi.',
        'solution': 'Apple uslubidagi minimalist dizayn, 3D mahsulot ko\'rish, o\'lchamlar bo\'yicha tavsiyalar va bir bosishda to\'lov tizimiga ega onlayn butik yaratildi.',
        'result': 'Sayt konversiyasi 4.2% ga yetdi, o\'rtacha xarid cheki 40% ga oshdi.',
        'features': 'Minimalist Premium UI, 3D mahsulot prevyu, Payme & Click to\'lovlari, Telegramga buyurtma xabarlari'
    },
    {
        'title': 'Futbol-Xabar - Avtomatlashtirilgan Jonli Futbol Yangiliklari va Natijalar Portali',
        'category': 'web',
        'emoji': '⚽',
        'technologies': 'Python, Flask, Football-Data API, Telegram Bot API, Redis',
        'price': '5,000,000 UZS',
        'client_name': 'Sport Media & Fan Klublar',
        'image_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=85&w=1200&auto=format&fit=crop',
        'description': 'Dunyodagi eng sara futbol ligalari yangiliklari va o\'yinlar natijalarini real vaqtda avtomatik nashr qiluvchi sport portali.',
        'problem': 'Futbol o\'yinlari natijalari, transferlar va yangiliklarni sayt va kanallarga doimiy ravishda inson omili orqali qo\'lda yozib borish sekin va qimmat edi.',
        'solution': 'Dunyo bo\'yicha 50+ ligalarni jonli kuzatib, gollar va natijalarni avtomatik tarzda tahliliy maqola qilib sayt va Telegramga chiqaruvchi bot va portal qurildi.',
        'result': 'Kunlik 30 000+ faol o\'quvchi jalb qilindi, yangiliklar e\'lon qilinish tezligi 15 soniyaga tushdi.',
        'features': 'Jonli hisoblar (Live Score), AI tahlil maqolalari, Avtomatik Telegram postlar, Match Center'
    },
    {
        'title': 'Uzum Tezkor Integratsiya - Restoranlar uchun Yetkazib Berish va Buyurtma Hubi',
        'category': 'bot',
        'emoji': '🛵',
        'technologies': 'Python, PostgreSQL, REST API, Webhook, Uzum Tezkor API, Telegram Bot',
        'price': '7,500,000 UZS',
        'client_name': 'Restoran va Fast-Food Tarmoqlari',
        'image_url': 'https://images.unsplash.com/photo-1617347454431-f49d7ff5c3b1?q=85&w=1200&auto=format&fit=crop',
        'description': 'Restoran va oshxonalar uchun barcha yetkazib berish xizmatlari va Telegram buyurtmalarini yagona tizimga birlashtiruvchi aqlli hub.',
        'problem': 'Restoran buyurtmalari alohida planshetlarda, saytda va Telegramda tarqoq holda bo\'lib, oshpazlar va kuryerlar adashib qolar edi.',
        'solution': 'Barcha yetkazib berish xizmatlari (Uzum Tezkor, Yandex, sayt, bot) buyurtmalarini bitta oshxona ekraniga (KDS) jamlovchi yagona hub tizimi ishlab chiqildi.',
        'result': 'Buyurtma tayyorlash va yetkazish vaqti 22 daqiqadan 14 daqiqaga tushdi, xatoliklar nolga tenglashdi.',
        'features': 'Yagona KDS ekrani, Avtomatik kuryer chaqirish, Oshxona printeriga avto-chop, SMS bildirishnomalar'
    },
    {
        'title': 'Real-Smart AI - Biznes Jarayonlarini Tahlil Qiluvchi va Optimallashtiruvchi AI Platforma',
        'category': 'ai',
        'emoji': '🧠',
        'technologies': 'Python, Gemini Pro, Pandas, Streamlit, PostgreSQL, FastAPI',
        'price': '14,000,000 UZS',
        'client_name': 'Kompaniya Direktorlari va Tahlilchilar',
        'image_url': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=85&w=1200&auto=format&fit=crop',
        'description': 'Katta hajmdagi korporativ ma\'lumotlar, savdo va moliyaviy hisobotlarni tahlil qilib, o\'sish strategiyalarini beruvchi AI analitik platformasi.',
        'problem': 'Kompaniya rahbarlari o\'nlab Excel jadvallari va hisobotlardan xulosalar chiqarishga kunlab vaqt yo\'qotar edi.',
        'solution': 'Katta hajmdagi moliyaviy va savdo ma\'lumotlarini 1 soniyada tahlil qilib, o\'sish nuqtalarini, kamchiliklarni va kelgusi oy prognozini beruvchi AI tahlilchi yaratildi.',
        'result': 'Moliyaviy xatoliklar 35% ga kamaydi, strategik qarorlar qabul qilish 5 barobar tezlashdi.',
        'features': 'Tabiiy tilda ma\'lumotlar bilan suhbat (Chat with Data), Moliyaviy prognozlash, Avtomatik PDF hisobotlar'
    },
    {
        'title': 'Ismlar Ma\'nosi AI - Sun\'iy Intellekt Ismlar va Shaxsiyat Tahlili Boti',
        'category': 'bot',
        'emoji': '📜',
        'technologies': 'Python, AI Studio, Telegram Bot API, SQLite, AsyncIO',
        'price': '3,500,000 UZS',
        'client_name': 'Ommaviy Media va Telegram Kanallar',
        'image_url': 'https://images.unsplash.com/photo-1455390582262-044cdead277a?q=85&w=1200&auto=format&fit=crop',
        'description': 'Ismlar etimologiyasi, ma\'nosi va shaxsiy tavsifini she\'riy va badiiy formatda tayyorlab beruvchi ommabop sun\'iy intellekt boti.',
        'problem': 'Odamlar ismlar ma\'nosi va kelib chiqishini qidirganda internetdagi eskirgan va cheklangan manbalardan norozi bo\'lishar edi.',
        'solution': 'Har qanday ismning tarixiy etimologiyasini, ma\'nosi va shaxsiy tavsifini she\'riy va chiroyli dizaynda generatsiya qilib beruvchi AI bot qurildi.',
        'result': '100 000+ dan ortiq foydalanuvchiga xizmat ko\'rsatildi, kanallar uchun 40 000+ yangi obunachi yig\'ildi.',
        'features': 'AI etimologiya qidiruvi, Ismga mos tabrik va fotokartochka generatsiyasi, Telegram kanalga avto-ulanish'
    }
]

def seed_desktop_portfolios():
    """Desktopdagi loyihalarni bazaga kiritish va rasmlarini yangilash"""
    try:
        existing = {p.title: p for p in Portfolio.query.all()}
        for data in PROJECTS_DATA:
            if data['title'] not in existing:
                p = Portfolio(
                    title=data['title'],
                    category=data['category'],
                    emoji=data['emoji'],
                    technologies=data['technologies'],
                    price=data['price'],
                    client_name=data['client_name'],
                    image_url=data['image_url'],
                    description=data['description'],
                    problem=data['problem'],
                    solution=data['solution'],
                    result=data['result'],
                    features=data['features'],
                    is_featured=True,
                    is_published=True
                )
                db.session.add(p)
                db.session.commit()
                p.slug = p.generate_slug()
                db.session.commit()
                logger.info(f"[seed] Portfolio qo'shildi: {p.title}")
            else:
                # Update image_url if exists
                p = existing[data['title']]
                p.image_url = data['image_url']
                db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.info(f"[seed] Xatolik: {e}")