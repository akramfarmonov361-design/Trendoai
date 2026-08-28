// TrendoAI — buyurtma sahifasi: URL parametridan xizmatni tanlash.
// Inline blokdan chiqarildi (CSP: script-src 'self').

// URL'dan service parametrni olish va avtomatik tanlash
    document.addEventListener('DOMContentLoaded', function () {
        const urlParams = new URLSearchParams(window.location.search);
        const serviceParam = urlParams.get('service');

        if (serviceParam) {
            const serviceSelect = document.getElementById('service');
            if (serviceSelect) {
                const serviceMap = {
                    web: 'web_site',
                    bot: 'telegram_bot',
                    ai: 'ai_chatbot',
                    mobile: 'other',
                };
                serviceSelect.value = serviceMap[serviceParam] || serviceParam;
                // AddToCart event if coming from service page
                if (typeof fbq !== 'undefined') {
                    fbq('track', 'AddToCart', {
                        content_ids: ['service_' + serviceParam.replace('_', '-')],
                        content_type: 'product'
                    });
                }
            }
        }
    });

    // Facebook Pixel - Form submission tracking
    const orderForm = document.querySelector('.order-form');
    if (orderForm && typeof fbq !== 'undefined') {
        orderForm.addEventListener('submit', function () {
            const serviceId = document.getElementById('service').value;
            const serviceName = document.getElementById('service').selectedOptions[0]?.text || 'Unknown';
            const budget = document.getElementById('budget').value || '0';

            // Map form values to catalog IDs (slugs usually have hyphens, keys have underscores)
            const catalogId = 'service_' + serviceId.replace('_', '-');

            // Lead/Purchase event for Catalog matching
            fbq('track', 'Purchase', {
                content_name: serviceName,
                content_category: 'Service Order',
                content_ids: [catalogId],
                content_type: 'product',
                value: 0.00, // No price fixed yet
                currency: 'UZS'
            });

            // Standard Lead event
            fbq('track', 'Lead', {
                content_name: serviceName,
                content_category: 'Service Order'
            });
        });
    }

    // Google Analytics - Form submission tracking  
    if (orderForm && typeof gtag !== 'undefined') {
        orderForm.addEventListener('submit', function () {
            gtag('event', 'generate_lead', {
                'event_category': 'Order',
                'event_label': document.getElementById('service').value
            });
        });
    }
