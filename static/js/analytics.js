// TrendoAI — GA4, Google Ads va Meta Pixel yuklovchisi.
// base.html dagi uchta inline blokdan yig'ildi (CSP: script-src 'self').
// ID'lar shablondagi <script type="application/json"> blokidan olinadi;
// u data-blok, bajarilmaydi, shuning uchun script-src unga tegmaydi.
(function () {
    const holder = document.getElementById('analytics-config');
    if (!holder) return;

    const cfg = JSON.parse(holder.textContent);

    // gtag.js async yuklanadi, shuning uchun dataLayer u ishga tushishidan
    // oldin mavjud bo'lishi kerak — bu fayl gtag tegidan oldin turadi.
    if (cfg.ga4Id || cfg.googleAdsId) {
        window.dataLayer = window.dataLayer || [];
        window.gtag = function () { window.dataLayer.push(arguments); };
        window.gtag('js', new Date());
        if (cfg.ga4Id) window.gtag('config', cfg.ga4Id);
        if (cfg.googleAdsId) window.gtag('config', cfg.googleAdsId);
    }

    if (cfg.facebookPixelId) {
        !function (f, b, e, v, n, t, s) {
            if (f.fbq) return; n = f.fbq = function () {
                n.callMethod ?
                    n.callMethod.apply(n, arguments) : n.queue.push(arguments)
            };
            if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0';
            n.queue = []; t = b.createElement(e); t.async = !0;
            t.src = v; s = b.getElementsByTagName(e)[0];
            s.parentNode.insertBefore(t, s)
        }(window, document, 'script',
            'https://connect.facebook.net/en_US/fbevents.js');
        fbq('init', cfg.facebookPixelId, { autoConfig: true, debug: false });
        fbq('track', 'PageView');
    }
})();
