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
        'image_url': '/static/img/portfolio/optombazar.webp',
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
        'image_url': '/static/img/portfolio/quiz-video-generator.webp',
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
        'image_url': '/static/img/portfolio/viral-video.webp',
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
        'image_url': '/static/img/portfolio/instadubuz.webp',
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
        'image_url': '/static/img/portfolio/luxe-core.webp',
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
        'image_url': '/static/img/portfolio/trendoai-uz.webp',
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
        'image_url': '/static/img/portfolio/uzum-tezkor.webp',
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
        'image_url': '/static/img/portfolio/real-smart-ai.webp',
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
        'image_url': '/static/img/portfolio/ismlar-manosi-ai.webp',
        'description': 'Ismlar etimologiyasi, ma\'nosi va shaxsiy tavsifini she\'riy va badiiy formatda tayyorlab beruvchi ommabop sun\'iy intellekt boti.',
        'problem': 'Odamlar ismlar ma\'nosi va kelib chiqishini qidirganda internetdagi eskirgan va cheklangan manbalardan norozi bo\'lishar edi.',
        'solution': 'Har qanday ismning tarixiy etimologiyasini, ma\'nosi va shaxsiy tavsifini she\'riy va chiroyli dizaynda generatsiya qilib beruvchi AI bot qurildi.',
        'result': '100 000+ dan ortiq foydalanuvchiga xizmat ko\'rsatildi, kanallar uchun 40 000+ yangi obunachi yig\'ildi.',
        'features': 'AI etimologiya qidiruvi, Ismga mos tabrik va fotokartochka generatsiyasi, Telegram kanalga avto-ulanish'
    },
    {
        'title': 'JonGiyoh.uz - Tabiiy Giyohlar va Shifobaxsh Mahsulotlar Platformasi',
        'category': 'web',
        'emoji': '🌿',
        'technologies': 'React, TailwindCSS, Vercel, Node.js, Telegram Bot',
        'price': '8,000,000 UZS',
        'client_name': 'JonGiyoh Brand & Shifobaxsh Giyohlar',
        'image_url': '/static/img/portfolio/jongiyoh.png',
        'description': 'O\'zbekistondagi tabiiy giyohlar, damlamalar va shifobaxsh mahsulotlarni onlayn xarid qilish uchun qulay e-commerce platformasi.',
        'problem': 'Shifobaxsh giyohlar va tabiiy mahsulotlar xaridorlari uchun aniq qo\'llanma, qabul qilish me\'yorlari va ishonchli onlayn yetkazib berish tizimi yo\'q edi.',
        'solution': 'Har bir giyohning xususiyatlari, xalq tabobati tavsiyalari, savat va bir tugmada buyurtma qilish imkoniyatiga ega minimalist dizaynli veb-do\'kon yaratildi.',
        'result': 'Mijozlar ishonchi 85% ga oshdi, onlayn buyurtmalar hajmi 3 barobar o\'sdi.',
        'features': 'Mahsulotlar katalogi, Shifobaxsh damlamalar qo\'llanmasi, Telegramga tezkor buyurtma, Mobil moslashuvchan dizayn'
    },
    {
        'title': 'Paketshop.uz Assistant (Malika) - Qadoqlash Mahsulotlari uchun AI Sotuvchi',
        'category': 'ai',
        'emoji': '🛍️',
        'technologies': 'TypeScript, Vite, Gemini Live AI, WebAudio, Node.js',
        'price': '7,000,000 UZS',
        'client_name': 'Paketshop.uz Ulgurji Savdo',
        'image_url': '/static/img/portfolio/paketshop-assistent.webp',
        'description': 'Paketshop.uz mijozlari uchun qadoq o\'lchamlari, narxlar va buyurtmalarni real vaqtda ovozli va matnli qabul qiluvchi AI sotuvchi assistenti.',
        'problem': 'Ulgurji qadoq va paketlar bo\'yicha mijozlar kuniga yuzlab bir xil savollar (o\'lcham, mikron, narx) bilan operatorlarni band qilar edi.',
        'solution': 'Gemini sun\'iy intellekti asosida mijozlarga do\'stona tarzda (Malika) qadoq turlarini tavsiya qiluvchi va hisob-kitob qilib beruvchi AI assistent ishga tushirildi.',
        'result': 'Operatorlar yuki 70% ga qisqardi, tungi va dam olish kunlaridagi sotuvlar 50% ga oshdi.',
        'features': 'Real-vaqt AI suhbat, O\'lcham va mikron kalkulyatori, Ovozli diktor, Savatga avto-qo\'shish'
    },
    {
        'title': 'Mijoz Topar (Company Contact Finder) - B2B Sotuvlar uchun Kontaktlar Bazasi AI',
        'category': 'ai',
        'emoji': '🎯',
        'technologies': 'Next.js 14, TypeScript, Prisma, Google Maps API, PostgreSQL',
        'price': '11,000,000 UZS',
        'client_name': 'B2B Kompaniyalar va Sotuv Bo\'limlari',
        'image_url': '/static/img/portfolio/mijoz-topar.webp',
        'description': 'Google va ochiq manbalardan real kompaniyalarning telefon, email, manzil va rahbarlar kontaktlarini bir zumda topib beruvchi AI skaner.',
        'problem': 'Sotuv bo\'limlari sovuq qo\'ng\'iroqlar uchun yangi mijozlar kontaktlarini qo\'lda soatlab qidirib, eskirgan va yaroqsiz raqamlarga vaqt yo\'qotar edi.',
        'solution': 'Soha va hudud bo\'yicha faol kompaniyalarni skanerlab, tozalangan telefon, email va Telegram profillarini Excel formatida beruvchi B2B qidiruv tizimi yaratildi.',
        'result': 'Lid yig\'ish vaqti 10 barobarga tezlashdi, sotuvchilar konversiyasi 45% ga oshdi.',
        'features': 'Avtomatik B2B skaner, Excel/CSV eksport, Dublikatlarni tozalash, Telegram kontaktlar filtri'
    },
    {
        'title': 'Restoran Voice AI Delivery - Ovozli AI Buyurtma va Yetkazib Berish Stansiyasi',
        'category': 'ai',
        'emoji': '🍔',
        'technologies': 'React, TypeScript, Gemini Live API, WebAudio, Firebase',
        'price': '10,000,000 UZS',
        'client_name': 'Fast-Food va Restoranlar Tarmoqlari',
        'image_url': '/static/img/portfolio/restoran.webp',
        'description': 'Mijozlar bilan xuddi ofitsiant kabi ovozli muloqot qilib, taomlar va yetkazib berish manzilini aniqlovchi interaktiv AI restoran ilovasi.',
        'problem': 'Pik soatlarda (tushlik va kechki ovqat) qo\'ng\'iroqlar ko\'pligidan operatorlar ulgurmay, mijozlar kutishdan charchab buyurtmani bekor qilar edi.',
        'solution': 'Kechikishlarsiz (real-time) mijozning ovozini tushunib, menyudan taomlarni savatga soluvchi va manzilni belgilovchi AI ovozli ofitsiant qurildi.',
        'result': 'Qo\'ng\'iroq o\'tkazib yuborish holatlari nolga tushdi, buyurtma qabul qilish vaqti 40 soniyaga qisqardi.',
        'features': 'Jonli ovozli muloqot (Gemini Live), Taomlar filtri va garnirlar, Lokatsiya aniqlash, Tezkor to\'lov'
    },
    {
        'title': 'Sado AI: Biznes Yordamchisi - O\'zbek Tili uchun Korporativ AI Konsultatsiya Platformasi',
        'category': 'ai',
        'emoji': '⚡',
        'technologies': 'React, Vite, Gemini Pro, TailwindCSS, Express.js',
        'price': '9,500,000 UZS',
        'client_name': 'SaaS Loyihalar va Korxona Rahbarlari',
        'image_url': '/static/img/portfolio/trendo-mascot-corporate-ai.jpg',
        'description': 'O\'zbek tilida biznes tahlili, marketing rejalari, moliyaviy hisobotlar va mijozlar bilan muloqotni avtomatlashtiruvchi universal korporativ AI platformasi.',
        'problem': 'O\'zbek tilidagi biznes terminologiyasini to\'g\'ri tushunadigan va lokal bozor talablariga mos javob beradigan aqlli AI tizimlari yetishmas edi.',
        'solution': 'O\'zbekiston qonunchiligi, soliq tizimi va marketing tajribasiga moslashtirilgan aqlli maslahatchi va hujjat generatsiya qiluvchi tizim ishlab chiqildi.',
        'result': 'Kompaniyalarda biznes hujjatlarni tayyorlash 5 barobar tezlashdi, marketing rejalari 1 kunda tuzildi.',
        'features': 'O\'zbekcha biznes promptlar, PDF hisobotlar tahlili, Shartnoma loyihalari generatsiyasi, Jamoaviy kirish'
    },
    {
        'title': 'TrendoAI Speak - O\'zbek va Ingliz Tili uchun Interaktiv AI Repetitor',
        'category': 'ai',
        'emoji': '🎓',
        'technologies': 'Next.js, Web Speech API, Gemini Live, Vercel, TailwindCSS',
        'price': '6,500,000 UZS',
        'client_name': 'Online Ta\'lim Markazlari va Til Maktablari',
        'image_url': '/static/img/portfolio/trendospeak.webp',
        'description': 'Foydalanuvchi bilan jonli suhbat qurib, grammatika va talaffuz xatolarini to\'g\'rilab boruvchi sun\'iy intellekt repetitori.',
        'problem': 'Ingliz tilini o\'rganuvchilar jonli so\'zlashuv (Speaking) amaliyoti uchun repetitorga katta mablag\' sarflar, uyalish tufayli muloqotga kirisha olmas edi.',
        'solution': 'Qo\'rqmasdan, istalgan vaqtda erkin mavzularda ovozli muloqot qilish, darajaga mos mashqlar va xatolarni tushuntirib beruvchi interaktiv AI tutor yaratildi.',
        'result': 'O\'quvchilarning so\'zlashuv tezligi 2 oyda 40% ga oshdi, ta\'lim xarajatlari 80% ga qisqardi.',
        'features': 'Ovozli talaffuz tahlili, Grammatika tuzatish, Darajalar (A1-C1) bo\'yicha suhbat, Dialog ssenariylari'
    },
    {
        'title': 'Shifo Nur Klinikasi Chatbot - Tibbiy Konsultatsiya va Shifokor Qabuliga Yozilish AI Boti',
        'category': 'bot',
        'emoji': '🏥',
        'technologies': 'Python, Aiogram 3, PostgreSQL, Gemini AI, Webhook',
        'price': '7,500,000 UZS',
        'client_name': 'Shifo Nur Ko\'p Tarmoqli Klinikasi',
        'image_url': '/static/img/portfolio/trendo-shifo-nur-clinic-ai.jpg',
        'description': 'Klinika bemorlari uchun shifokorlar jadvali, xizmat narxlari va onlayn navbatga yozilishni boshqaruvchi tibbiy sun\'iy intellekt boti.',
        'problem': 'Klinika registratsiyasida navbatlar ko\'p bo\'lib, bemorlar telefon qilib shifokorlar qabul vaqtini bilish uchun uzoq kutishga majbur bo\'lar edi.',
        'solution': 'Bemorlarning shikoyatlari bo\'yicha to\'g\'ri mutaxassisni tavsiya qiluvchi, navbatga yozuvchi va SMS eslatma yuboruvchi aqlli bot joriy etildi.',
        'result': 'Registratsiya navbatlari 60% ga kamaydi, bekor qilingan qabullar soni 4 barobarga qisqardi.',
        'features': 'Mutaxassis tavsiya etuvchi AI, Onlayn navbat va vaqt tanlash, Bemor kabineti, SMS bildirishnomalar'
    },
    {
        'title': 'Texnomarket.uz - Maishiy Texnika va Elektronika Gipermarketi E-Commerce',
        'category': 'web',
        'emoji': '💻',
        'technologies': 'Next.js 14, TypeScript, PostgreSQL, Payme, Click, Redis, TailwindCSS',
        'price': '14,000,000 UZS',
        'client_name': 'Texnomarket Maishiy Texnika Do\'konlar Tarmog\'i',
        'image_url': '/static/img/portfolio/texnomarket.webp',
        'description': 'Minglab elektronika va maishiy texnika mahsulotlarini bo\'lib to\'lash (muddatli to\'lov) integratsiyasi bilan sotuvchi zamonaviy internet do\'kon.',
        'problem': 'Katta assortimentdagi mahsulotlarni filtrlash sekin ishlar, muddatli to\'lov arizalari qo\'lda uzoq ko\'rib chiqilar edi.',
        'solution': 'Bir zumda natija beruvchi qidiruv, xarakteristikalarni taqqoslash, avtomatik muddatli to\'lov skoringiga ega yuqori tezlikdagi platforma ishlab chiqildi.',
        'result': 'Sayt yuklanish tezligi 1.2 soniyaga tushdi, muddatli to\'lov orqali sotuvlar 65% ga o\'sdi.',
        'features': 'Tezkor qidiruv & Filtrlar, Mahsulotlarni solishtirish, Muddatli to\'lov kalkulyatori, 1-klikda xarid'
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