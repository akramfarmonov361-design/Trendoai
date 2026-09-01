// TrendoAI — portfolio sahifasi: modal, filtrlar va qidiruv.
// Inline blokdan chiqarildi (CSP: script-src 'self').
// Ma'lumot shablonda <script type="application/json"> data-blokida
// qoladi — u bajarilmaydi, shuning uchun script-src unga tegmaydi.

const PORTFOLIO_CONFIG = JSON.parse(
    document.getElementById('portfolios-data').textContent
);

// Baza bo'sh bo'lganda ko'rsatiladigan namoyish loyihalari
// (avval shablonda pagination.total shartli bloki ichida edi).
const FALLBACK_PROJECTS = [
        {
            id: 'manual-kfc',
            slug: 'restoran-kfc-frontend',
            title: 'Restoran KFC Frontend',
            description: "Fast food restoran uchun zamonaviy frontend. Menyu, promo bloklar va onlayn buyurtmaga yo'naltirilgan interfeys.",
            category: 'web',
            emoji: '🍗',
            technologies: ['Frontend', 'Responsive UI', 'Vercel'],
            link: 'https://restorankfc-frontend.vercel.app/',
            image_url: '/static/img/portfolio/restoran.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Fast food/restoran yo'nalishidagi landing sahifa. Foydalanuvchini menyu va promo bloklar orqali buyurtma jarayoniga olib kirishga mo'ljallangan.</p>",
            features: ['Menyu ko\'rinishi', 'Responsive dizayn', 'Promo bloklar', 'Live demo link']
        },
        {
            id: 'manual-realnews',
            slug: 'realnewsuz',
            title: 'RealNewsUZ',
            description: "Yangiliklar va media kontent uchun tayyorlangan zamonaviy web interfeys. Kontentni tez o'qish va ko'rishga qulay struktura bilan ishlab chiqilgan.",
            category: 'web',
            emoji: '📰',
            technologies: ['Frontend', 'News UI', 'Vercel'],
            link: 'https://realnewsuz.vercel.app/',
            image_url: '/static/img/portfolio/trendoai-uz.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Yangiliklar portali yo'nalishidagi web interfeys. Asosiy fokus kontentni toza ko'rsatish, sarlavhalarni ajratish va foydalanuvchi uchun qulay o'qish tajribasini berish.</p>",
            features: ['Yangiliklar interfeysi', 'Responsive dizayn', 'Tez navigatsiya', 'Live demo link']
        },
        {
            id: 'manual-trendoaispeak',
            slug: 'trendoaispeak-uzbek-english-tutor',
            title: 'TrendoAI Speak',
            description: "O'zbek va ingliz tili uchun interaktiv tutor interfeysi. O'quvchini mashq va suhbat formatida til o'rganishga yo'naltiradigan yechim.",
            category: 'ai',
            emoji: 'AI',
            technologies: ['AI Tutor', 'Language Learning', 'Vercel'],
            link: 'https://trendoaispeak-uzbek-english-tutor.vercel.app/',
            image_url: '/static/img/portfolio/trendospeak.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Til o'rganish uchun mo'ljallangan interaktiv AI tutor interfeysi. Asosiy fokus foydalanuvchiga o'zbek va ingliz tilida mashq qilish va suhbat orqali o'rganish imkonini berish.</p>",
            features: ['Interaktiv tutor', 'Til mashqlari', 'Responsive dizayn', 'Live demo link']
        },
        {
            id: 'manual-shifo-nur-chatbot',
            slug: 'shifo-nur-klinikasi-chatbot',
            title: 'Shifo Nur Klinikasi Chatbot',
            description: "Klinika uchun mo'ljallangan chatbot interfeysi. Foydalanuvchiga xizmatlar, murojaat va tezkor aloqa jarayonini sodda ko'rsatadigan yechim.",
            category: 'ai',
            emoji: 'MED',
            technologies: ['Healthcare', 'AI Chatbot', 'Vercel'],
            link: 'https://shifo-nur-klinikasi-chatbot.vercel.app/',
            image_url: '/static/img/portfolio/botfactory.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Tibbiyot yo'nalishidagi chatbot interfeysi. Asosiy fokus foydalanuvchini klinika xizmatlari, savollar va tezkor murojaat jarayoniga yo'naltirish.</p>",
            features: ['Klinika chatboti', 'Murojaat oqimi', 'Responsive dizayn', 'Live demo link']
        },
        {
            id: 'manual-ozbek-talaffuz-kontent',
            slug: 'ozbek-talaffuz-kontent',
            title: "O'zbek Talaffuz Kontent",
            description: "O'zbek talaffuzi va o'quv kontenti uchun tayyorlangan web interfeys. Foydalanuvchiga materiallarni sodda va tushunarli ko'rinishda taqdim etadigan yechim.",
            category: 'web',
            emoji: 'EDU',
            technologies: ['Education', 'Content Platform', 'Vercel'],
            link: 'https://o-zbek-talaffuz-kontent.vercel.app/',
            image_url: '/static/img/portfolio/bolajon-ai-english.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Ta'lim yo'nalishidagi kontent platformasi. Asosiy fokus o'zbek talaffuzi bo'yicha materiallarni foydalanuvchi uchun qulay va tushunarli ko'rinishda berish.</p>",
            features: ["Ta'lim kontenti", "Responsive dizayn", "Sodda navigatsiya", "Live demo link"]
        },
        {
            id: 'manual-ai-project-scoper',
            slug: 'ai-project-scoper',
            title: 'AI Project Scoper',
            description: "Loyiha scope va talablarni tez shakllantirish uchun tayyorlangan AI interfeys. Foydalanuvchiga task, deliverable va ish hajmini aniqroq belgilashga yordam beradi.",
            category: 'ai',
            emoji: 'SCOPE',
            technologies: ['AI Planning', 'Project Scope', 'Vercel'],
            link: 'https://ai-project-scoper.vercel.app/',
            image_url: '/static/img/portfolio/real-smart-ai.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Loyiha scope va requirementlarni tezroq yig'ish uchun mo'ljallangan AI vosita. Asosiy fokus foydalanuvchiga vazifalar, deliverable va ish hajmini strukturali ko'rinishda shakllantirishga yordam berish.</p>",
            features: ['Scope generator', 'Requirement tuzish', 'Responsive dizayn', 'Live demo link']
        },
        {
            id: 'manual-texnomarket',
            slug: 'texnomarket',
            title: 'Texnomarket',
            description: "Elektronika va texnika mahsulotlari uchun tayyorlangan e-commerce interfeys. Foydalanuvchiga katalog, mahsulot va xarid jarayonini sodda ko'rinishda taqdim etadigan yechim.",
            category: 'web',
            emoji: 'SHOP',
            technologies: ['E-commerce', 'Frontend', 'Vercel'],
            link: 'https://texnomarket.vercel.app/',
            image_url: '/static/img/portfolio/texnomarket.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Texnika va elektronika savdosi uchun mo'ljallangan web interfeys. Asosiy fokus foydalanuvchiga mahsulot katalogi va xarid oqimini qulay ko'rinishda ko'rsatish.</p>",
            features: ['Mahsulot katalogi', 'Responsive dizayn', 'Sodda navigatsiya', 'Live demo link']
        },
        {
            id: 'manual-paketshop',
            slug: 'paketshop',
            title: 'Paketshop',
            description: "Onlayn savdo va mahsulot ko'rish uchun tayyorlangan web interfeys. Foydalanuvchiga katalog va murojaat jarayonini sodda ko'rinishda taqdim etadigan yechim.",
            category: 'web',
            emoji: 'PKG',
            technologies: ['E-commerce', 'Catalog', 'Web Platform'],
            link: 'https://www.paketshop.uz/',
            image_url: '/static/img/portfolio/paketshop.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Onlayn savdo va katalog ko'rsatishga mo'ljallangan web interfeys. Asosiy fokus foydalanuvchiga mahsulotlarni qulay ko'rinishda taqdim etish va murojaat jarayonini soddalashtirish.</p>",
            features: ['Mahsulot katalogi', 'Responsive dizayn', 'Sodda navigatsiya', 'Live demo link']
        },
        {
            id: 'manual-restoran-kfc-site',
            slug: 'restoran-kfc',
            title: 'Restoran KFC',
            description: "Restoran va fast food yo'nalishi uchun tayyorlangan web interfeys. Foydalanuvchiga menyu, promo bloklar va buyurtmaga o'tish jarayonini sodda ko'rinishda taqdim etadigan yechim.",
            category: 'web',
            emoji: 'FOOD',
            technologies: ['Restaurant', 'Landing Page', 'Vercel'],
            link: 'https://restoran-kfc.vercel.app/',
            image_url: '/static/img/portfolio/restoran.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Restoran va fast food yo'nalishidagi landing sahifa. Asosiy fokus foydalanuvchiga menyu va promo bloklarni ko'rsatish hamda buyurtma oqimini soddalashtirish.</p>",
            features: ['Menyu bloklari', 'Responsive dizayn', 'Promo section', 'Live demo link']
        },
        {
            id: 'manual-nomoz-vaqtlari',
            slug: 'nomoz-vaqtlari',
            title: 'Nomoz Vaqtlari',
            description: "Namoz vaqtlarini ko'rsatish uchun tayyorlangan web interfeys. Foydalanuvchiga vaqtlar, kunlik ko'rsatkichlar va kerakli ma'lumotlarni sodda ko'rinishda taqdim etadigan yechim.",
            category: 'web',
            emoji: 'TIME',
            technologies: ['Prayer Times', 'Utility App', 'Vercel'],
            link: 'https://nomoz-vaqtlari-xi.vercel.app/',
            image_url: '/static/img/portfolio/ismlar-manosi-ai.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Namoz vaqtlarini ko'rsatishga mo'ljallangan web interfeys. Asosiy fokus foydalanuvchiga vaqtlar va kunlik ma'lumotlarni qulay ko'rinishda taqdim etish.</p>",
            features: ["Vaqtlar ko'rinishi", 'Responsive dizayn', 'Sodda navigatsiya', 'Live demo link']
        },
        {
            id: 'manual-botfactory',
            slug: 'botfactory',
            title: 'BotFactory',
            description: "Bot yaratish va avtomatlashtirish uchun tayyorlangan platforma interfeysi. Foydalanuvchiga bot xizmatlari va ish jarayonini sodda ko'rinishda taqdim etadigan yechim.",
            category: 'bot',
            emoji: 'BOT',
            technologies: ['Bot Platform', 'Automation', 'Render'],
            link: 'https://botfactory-am64.onrender.com/',
            image_url: '/static/img/portfolio/botfactory.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Bot yaratish va avtomatlashtirishga mo'ljallangan platforma interfeysi. Asosiy fokus foydalanuvchiga bot xizmatlari va jarayonlarni qulay ko'rinishda taqdim etish.</p>",
            features: ['Bot platforma', 'Automation oqimi', 'Responsive dizayn', 'Live demo link']
        },
        {
            id: 'manual-instadub',
            slug: 'instadub',
            title: 'InstaDub',
            description: "Kontentni dublyaj va media ishloviga yo'naltirilgan AI interfeys. Foydalanuvchiga ovoz, media va tezkor ishlov jarayonini sodda ko'rinishda taqdim etadigan yechim.",
            category: 'ai',
            emoji: 'DUB',
            technologies: ['AI Media', 'Voice Tool', 'Vercel'],
            link: 'https://instadub.vercel.app/',
            image_url: '/static/img/portfolio/instadubuz.webp',
            is_featured: false,
            details: "",
            details_html: "<p>Media va dublyaj ishloviga mo'ljallangan AI interfeys. Asosiy fokus foydalanuvchiga audio yoki media jarayonlarini qulay va tez boshqarish imkonini berish.</p>",
            features: ['Media ishlov', 'Dublyaj oqimi', 'Responsive dizayn', 'Live demo link']
        }
];

const portfoliosData = PORTFOLIO_CONFIG.useFallback
    ? PORTFOLIO_CONFIG.items.concat(FALLBACK_PROJECTS)
    : PORTFOLIO_CONFIG.items;

const modal = document.getElementById('projectModal');
let lastFocusedElement = null;

    function openModal(projectId) {
        const project = portfoliosData.find(p => String(p.id) === String(projectId));
        if (!project) return;

        lastFocusedElement = document.activeElement;

        const modalImg = document.getElementById('modalImg');
        const modalEmoji = document.getElementById('modalEmoji');
        if (project.image_url) {
            modalImg.src = project.image_url;
            modalImg.classList.remove('hidden');
            modalEmoji.classList.add('hidden');
        } else {
            modalImg.classList.add('hidden');
            modalEmoji.classList.remove('hidden');
            modalEmoji.textContent = project.emoji || '🚀';
        }
        document.getElementById('modalTitle').textContent = project.title;
        document.getElementById('modalDescription').textContent = project.description;

        // Category
        const catMap = { 'bot': '🤖 Telegram Bot', 'web': '🌐 Web Sayt', 'ai': '🧠 AI Yechim', 'mobile': '📱 Mobile App' };
        document.getElementById('modalCategory').textContent = catMap[project.category] || project.category;

        // Tech
        const techBox = document.getElementById('modalTech');
        techBox.innerHTML = '';
        project.technologies.forEach(tech => {
            const span = document.createElement('span');
            span.textContent = tech;
            techBox.appendChild(span);
        });

        // Features
        const featuresSection = document.getElementById('modalFeaturesSection');
        const featuresList = document.getElementById('modalFeatures');
        if (project.features && project.features.length > 0) {
            featuresSection.style.display = 'block';
            featuresList.innerHTML = '';
            project.features.forEach(f => {
                const li = document.createElement('li');
                li.textContent = f;
                featuresList.appendChild(li);
            });
        } else {
            featuresSection.style.display = 'none';
        }

        // Details
        const detailsSection = document.getElementById('modalDetailsSection');
        const detailsContent = document.getElementById('modalDetails');
        if (project.details_html) {
            detailsSection.style.display = 'block';
            detailsContent.innerHTML = project.details_html;
        } else {
            detailsSection.style.display = 'none';
        }

        // Pre-fill order link with category
        const orderBtn = document.getElementById('modalOrderBtn');
        const categoryMap = {
            'bot': 'telegram_bot',
            'web': 'web_site',
            'ai': 'ai_chatbot',
            'mobile': 'mobile_app'
        };
        const serviceKey = categoryMap[project.category] || '';
        orderBtn.href = `${PORTFOLIO_CONFIG.orderUrl}?service=${serviceKey}`;

        // Link
        const linkBtn = document.getElementById('modalLink');
        if (project.link) {
            linkBtn.style.display = 'block';
            linkBtn.href = project.link;
        } else {
            linkBtn.style.display = 'none';
        }

        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        modal.querySelector('.modal-close').focus();

        // Facebook Pixel: Track ViewContent event for ads optimization
        if (typeof fbq !== 'undefined') {
            fbq('track', 'ViewContent', {
                content_name: project.title,
                content_category: project.category,
                content_type: 'product',
                content_ids: [project.id]
            });
        }
    }

    function closeModal() {
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = 'auto';
        if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
            lastFocusedElement.focus();
        }
    }

    // Close on backdrop click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });

    modal.addEventListener('keydown', event => {
        if (event.key !== 'Tab') return;
        const focusable = Array.from(modal.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )).filter(element => element.offsetParent !== null);
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    document.querySelectorAll('.portfolio-card[onclick]').forEach(card => {
        card.tabIndex = 0;
        card.setAttribute('role', 'button');
        const title = card.querySelector('h3')?.textContent?.trim();
        if (title) card.setAttribute('aria-label', `${title} loyihasini ko'rish`);
        card.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                card.click();
            }
        });
    });

    // Optional client-side filters (server-rendered links are used by default).
    document.querySelectorAll('.filter-btn[data-client-filter]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn[data-client-filter]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const filter = btn.dataset.filter;
            document.querySelectorAll('.portfolio-card').forEach(card => {
                if (filter === 'all' || card.dataset.category === filter) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });

    // Deep Deep Linking: Open modal if hash reflects a project slug
    window.addEventListener('DOMContentLoaded', () => {
        const hash = window.location.hash.substring(1);
        if (hash) {
            const project = portfoliosData.find(p => p.slug === hash);
            if (project) {
                openModal(project.id);
            }
        }
    });

    // Handle back/forward navigation for hash changes
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.substring(1);
        if (hash) {
            const project = portfoliosData.find(p => p.slug === hash);
            if (project) openModal(project.id);
        } else {
            closeModal();
        }
    });

// ===== Inline handlerlar o'rniga bitta delegatsiya =====
// Avval 66 ta atribut bor edi: kartochkalarda openModal(...), ichkaridagi
// har bir havola/tugmada esa event.stopPropagation() (39 ta) — kartochka
// ochilib ketmasligi uchun. Delegatsiyada stopPropagation umuman kerak emas.
document.addEventListener('click', function (e) {
    if (e.target.closest('[data-modal-close]')) {
        closeModal();
        return;
    }

    const opener = e.target.closest('[data-modal-id]');
    if (!opener) return;

    // Kartochka ichidagi o'z harakati bor element (havola yoki boshqa
    // tugma) bosilgan bo'lsa, modal ochilmaydi — avvalgi
    // stopPropagation() bilan bir xil natija.
    const interactive = e.target.closest('a, button');
    if (interactive && interactive !== opener && !interactive.hasAttribute('data-modal-id')) return;

    openModal(opener.dataset.modalId);
});
