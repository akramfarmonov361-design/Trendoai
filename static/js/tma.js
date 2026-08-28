// TrendoAI Telegram Mini App — tablar, narx kalkulyatori va buyurtma modali.
// Inline blokdan chiqarildi (CSP: script-src 'self').

        // Telegram WebApp Initialization
        const tg = window.Telegram?.WebApp;
        if (tg) {
            tg.ready();
            tg.expand();
            if (tg.initDataUnsafe?.user) {
                const u = tg.initDataUnsafe.user;
                const name = u.first_name || u.username || 'Foydalanuvchi';
                document.getElementById('user-greeting').innerText = `👋 ${name}`;
                document.getElementById('modal-name').value = `${u.first_name || ''} ${u.last_name || ''}`.trim();
                if (u.username) {
                    document.getElementById('modal-contact').value = `@${u.username}`;
                }
            }
        }

        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

            const target = document.getElementById(`tab-${tabId}`);
            if (target) target.classList.add('active');

            const tabBtns = document.querySelectorAll('.tab-btn');
            const navItems = document.querySelectorAll('.nav-item');
            const tabMap = { 'catalog': 0, 'calc': 1, 'chat': 2, 'about': 3 };
            const idx = tabMap[tabId] || 0;
            if (tabBtns[idx]) tabBtns[idx].classList.add('active');
            if (navItems[idx]) navItems[idx].classList.add('active');
        }

        function formatNumber(num) {
            return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
        }

        function calculatePrice() {
            const serviceSelect = document.getElementById('calc-service');
            const selectedOpt = serviceSelect.options[serviceSelect.selectedIndex];
            let price = parseInt(selectedOpt.getAttribute('data-price') || 0);
            let days = parseInt(selectedOpt.getAttribute('data-days') || 3);

            const options = ['opt-payment', 'opt-admin', 'opt-ai', 'opt-lang', 'opt-express'];
            options.forEach(id => {
                const el = document.getElementById(id);
                if (el && el.checked) {
                    price += parseInt(el.getAttribute('data-price') || 0);
                    days += parseInt(el.getAttribute('data-days') || 0);
                }
            });

            if (days < 2) days = 2;

            document.getElementById('calc-total').innerText = `${formatNumber(price)} so'm`;
            document.getElementById('calc-time').innerText = `⏱ Tayyor bo'lish muddati: ~${days} kun`;
            return { price: `${formatNumber(price)} so'm`, days, serviceTitle: selectedOpt.text.split('(')[0].trim() };
        }

        function openOrderModal(service, price) {
            document.getElementById('modal-service').value = service;
            document.getElementById('modal-price').value = price;
            document.getElementById('order-modal').classList.add('open');
        }

        function closeOrderModal() {
            document.getElementById('order-modal').classList.remove('open');
        }

        function orderFromCalculator() {
            const calc = calculatePrice();
            openOrderModal(`Kalkulyator: ${calc.serviceTitle}`, `${calc.price} (~${calc.days} kun)`);
        }

        async function submitOrder() {
            const service = document.getElementById('modal-service').value;
            const price = document.getElementById('modal-price').value;
            const name = document.getElementById('modal-name').value.trim();
            const contact = document.getElementById('modal-contact').value.trim();
            const comment = document.getElementById('modal-comment').value.trim();

            if (!contact) {
                alert("Iltimos, telefon raqamingiz yoki Telegram profilingizni kiriting!");
                return;
            }

            const btn = document.getElementById('modal-submit-btn');
            btn.disabled = true;
            btn.innerText = "Yuborilmoqda...";

            try {
                const payload = {
                    name: name || "Telegram Mini App Mijoz",
                    contact: contact,
                    source: `Mini App (${service} - ${price}) ${comment ? '| Izoh: ' + comment : ''}`
                };

                const res = await fetch('/api/lead', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    if (tg && tg.showPopup) {
                        tg.showPopup({
                            title: 'Muvaffaqiyatli!',
                            message: 'Buyurtmangiz qabul qilindi. Tez orada mutaxassisimiz siz bilan bog\'lanadi.',
                            buttons: [{ type: 'ok' }]
                        });
                    } else {
                        alert("Rahmat! Buyurtmangiz qabul qilindi. Tez orada bog'lanamiz.");
                    }
                    closeOrderModal();
                } else {
                    alert(data.message || "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.");
                }
            } catch (err) {
                alert("Tarmoq xatosi. Iltimos, qaytadan urinib ko'ring.");
            } finally {
                btn.disabled = false;
                btn.innerText = "Yuborish 🚀";
            }
        }

// ===== Inline handlerlar o'rniga listenerlar =====
// Barcha funksiyalar aniq parametr oladi (global `event` ga bog'liq emas),
// shuning uchun ko'chirish xulqni o'zgartirmaydi.

// Tab almashtirish (avval onclick="switchTab('...')")
document.querySelectorAll('[data-tab]').forEach(function (btn) {
    btn.addEventListener('click', function () { switchTab(btn.dataset.tab); });
});

// Kalkulyator inputlari (avval onchange="calculatePrice()")
document.querySelectorAll('[data-calc-input]').forEach(function (input) {
    input.addEventListener('change', calculatePrice);
});

// Xizmat tugmalari (avval onclick="openOrderModal('nom', 'narx')")
document.querySelectorAll('[data-order-name]').forEach(function (btn) {
    btn.addEventListener('click', function () {
        openOrderModal(btn.dataset.orderName, btn.dataset.orderPrice || '');
    });
});

// Kalkulyator hisobi bilan buyurtma (avval onclick="orderFromCalculator()")
document.querySelectorAll('[data-calc-order]').forEach(function (btn) {
    btn.addEventListener('click', orderFromCalculator);
});

// Modalni yopish tugmasi (avval onclick="closeOrderModal()")
document.querySelectorAll('[data-modal-close]').forEach(function (btn) {
    btn.addEventListener('click', closeOrderModal);
});

// Modal fonini bosish (avval onclick="if(event.target === this) closeOrderModal()")
const orderModal = document.getElementById('order-modal');
if (orderModal) {
    orderModal.addEventListener('click', function (e) {
        if (e.target === orderModal) closeOrderModal();
    });
}

// Buyurtmani yuborish (avval onclick="submitOrder()")
const submitBtn = document.getElementById('modal-submit-btn');
if (submitBtn) submitBtn.addEventListener('click', submitOrder);

// Tashqi havola tugmasi (avval onclick="window.location.href='...'")
document.querySelectorAll('[data-href]').forEach(function (btn) {
    btn.addEventListener('click', function () { window.location.href = btn.dataset.href; });
});
