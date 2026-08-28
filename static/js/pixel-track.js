// TrendoAI — Meta Pixel ViewContent / AddToCart kuzatuvi.
// portfolio_detail va service_detail sahifalari uchun umumiy.
// Ma'lumot shablondagi <script type="application/json"> blokidan olinadi:
// u bajarilmaydi, shuning uchun CSP script-src unga tegmaydi.
(function () {
    const holder = document.getElementById('pixel-track-data');
    if (!holder) return;

    const data = JSON.parse(holder.textContent);

    function payload() {
        const p = {
            content_name: data.contentName,
            content_category: data.contentCategory,
            content_ids: data.contentIds,
            content_type: 'product'
        };
        if (data.value !== null && data.value !== undefined) {
            p.value = data.value;
            p.currency = data.currency || 'USD';
        }
        return p;
    }

    function track(eventName) {
        if (typeof fbq === 'undefined') return;
        fbq('track', eventName, payload());
    }

    track('ViewContent');

    // Avval onclick="trackAddToCart()" edi
    document.querySelectorAll('[data-track-add-to-cart]').forEach(function (el) {
        el.addEventListener('click', function () { track('AddToCart'); });
    });
})();
