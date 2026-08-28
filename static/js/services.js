// TrendoAI — bosh sahifa (services.html): buyurtma formasi, Pixel
// hodisalari va narx kalkulyatori.
// Inline bloklardan chiqarildi: CSP script-src 'self' ga o'tish uchun.

    function formatMoney(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    }

    function selectTypeCard(labelElement) {
        document.querySelectorAll('.type-card').forEach(el => el.classList.remove('active'));
        labelElement.classList.add('active');
        const radio = labelElement.querySelector('input[type="radio"]');
        if (radio) {
            radio.checked = true;
            updateCalc();
        }
    }

    function updateCalc() {
        const checkedRadio = document.querySelector('input[name="calc_base"]:checked');
        if (!checkedRadio) return;

        let total = parseInt(checkedRadio.getAttribute('data-price') || 0);
        let days = parseInt(checkedRadio.getAttribute('data-days') || 4);
        const title = checkedRadio.value;

        const features = [
            'feat-pay', 'feat-admin', 'feat-ai-engine', 'feat-multilingual', 'feat-express'
        ];

        features.forEach(id => {
            const el = document.getElementById(id);
            if (el && el.checked) {
                total += parseInt(el.getAttribute('data-price') || 0);
                days += parseInt(el.getAttribute('data-days') || 0);
            }
        });

        if (days < 2) days = 2;

        document.getElementById('res-selected-title').innerText = title;
        document.getElementById('res-total-cost').innerHTML = `${formatMoney(total)} <small>so'm</small>`;
        document.getElementById('res-total-days').innerText = `~${days} ish kuni`;
    }

    function applyCalculationToOrder() {
        const checkedRadio = document.querySelector('input[name="calc_base"]:checked');
        const serviceName = checkedRadio ? checkedRadio.value : 'Telegram Bot';
        const costText = document.getElementById('res-total-cost').innerText.replace(/\s+/g, ' ').trim();
        const daysText = document.getElementById('res-total-days').innerText.trim();

        // Check if there is an order form on page or redirect to /order
        const orderForm = document.querySelector('.order-form');
        if (orderForm) {
            const msgField = document.getElementById('message') || document.querySelector('textarea[name="message"]');
            if (msgField) {
                msgField.value = `Kalkulyatordan tanlangan loyiha:\n- Yo'nalish: ${serviceName}\n- Taxminiy smeta: ${costText}\n- Muddat: ${daysText}\n`;
            }
            const svcSelect = document.getElementById('service') || document.querySelector('select[name="service"]');
            if (svcSelect) {
                if (serviceName.includes('Bot')) svcSelect.value = 'telegram_bot';
                else if (serviceName.includes('Sayt')) svcSelect.value = 'web_site';
                else if (serviceName.includes('AI')) svcSelect.value = 'ai_chatbot';
                else if (serviceName.includes('Target')) svcSelect.value = 'smm';
            }
            orderForm.scrollIntoView({ behavior: 'smooth' });
        } else {
            window.location.href = `/order?service=${encodeURIComponent(serviceName)}&budget=${encodeURIComponent(costText)}`;
        }
    }

    document.addEventListener('DOMContentLoaded', updateCalc);

    document.addEventListener('DOMContentLoaded', function () {
        const urlParams = new URLSearchParams(window.location.search);
        const service = urlParams.get('service');
        if (service) {
            const select = document.getElementById('service');
            if (select) {
                select.value = service;
                setTimeout(() => {
                    const el = document.getElementById('order');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                }, 500);
            }
        }

        // Animate cards on scroll
        const cards = document.querySelectorAll('.service-card-new');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.classList.add('visible');
                    }, index * 150);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        cards.forEach(card => observer.observe(card));
    });

    const form = document.querySelector('.order-form');
    if (form && typeof fbq !== 'undefined') {
        form.addEventListener('submit', function () {
            const serviceId = document.getElementById('service').value;
            const serviceName = document.getElementById('service').selectedOptions[0]?.text || 'Unknown';
            const catalogId = 'service_' + serviceId.replace('_', '-');

            fbq('track', 'Purchase', {
                content_name: serviceName,
                content_category: 'Service Order',
                content_ids: [catalogId],
                content_type: 'product',
                value: 0.00,
                currency: 'UZS'
            });

            fbq('track', 'Lead', {
                content_name: serviceName,
                content_category: 'Service Order'
            });
        });
    }

// ===== Inline handlerlar o'rniga listenerlar =====
// Avvalgi onclick="" / onchange="" atributlarini CSP nonce bilan ham
// qamrab bo'lmaydi — yagona yo'l addEventListener.

// Meta Pixel AddToCart: har xizmat tugmasida inline fbq chaqiruvi bor edi
document.querySelectorAll('[data-fb-addtocart]').forEach(function (el) {
    el.addEventListener('click', function () {
        if (typeof fbq === 'undefined') return;
        fbq('track', 'AddToCart', {
            content_ids: [el.dataset.fbAddtocart],
            content_type: 'product'
        });
    });
});

// Kalkulyator: yo'nalish kartochkalari (onclick="selectTypeCard(this)")
document.querySelectorAll('.type-card').forEach(function (label) {
    label.addEventListener('click', function () { selectTypeCard(label); });
});

// Kalkulyator: narxga ta'sir qiluvchi inputlar (onchange="updateCalc()")
document.querySelectorAll('[data-calc-input]').forEach(function (input) {
    input.addEventListener('change', updateCalc);
});

// Hisobni buyurtma formasiga ko'chirish (onclick="applyCalculationToOrder()")
var applyBtn = document.querySelector('.btn-calc-apply');
if (applyBtn) applyBtn.addEventListener('click', applyCalculationToOrder);
