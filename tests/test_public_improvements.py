import sys
import types
import unittest
from unittest import mock

import app as trendo_app


class PublicImprovementTests(unittest.TestCase):
    def setUp(self):
        self._orig_csrf = trendo_app.app.config.get('WTF_CSRF_ENABLED', True)
        trendo_app.app.config['TESTING'] = True
        trendo_app.app.config['WTF_CSRF_ENABLED'] = False
        trendo_app._order_submissions.clear()
        self.client = trendo_app.app.test_client()

    def tearDown(self):
        # Global app config'ni tiklaymiz, aks holda boshqa testlarda CSRF o'chib qoladi.
        trendo_app.app.config['WTF_CSRF_ENABLED'] = self._orig_csrf

    def test_security_headers_are_present(self):
        response = self.client.get('/api/health')

        self.assertEqual(response.status_code, 200)
        self.assertIn("object-src 'none'", response.headers['Content-Security-Policy'])
        self.assertIn('microphone=(self)', response.headers['Permissions-Policy'])
        self.assertEqual(response.headers['X-Permitted-Cross-Domain-Policies'], 'none')

    def test_invalid_order_is_rejected_before_database_write(self):
        with mock.patch.object(trendo_app.db.session, 'add') as add:
            response = self.client.post(
                '/submit-order',
                data={'name': 'A', 'phone': 'x', 'service': 'unknown'},
                headers={'Referer': '/order'},
            )

        self.assertEqual(response.status_code, 303)
        add.assert_not_called()

    def test_honeypot_submission_does_not_create_order(self):
        with mock.patch.object(trendo_app.db.session, 'add') as add:
            response = self.client.post(
                '/submit-order',
                data={
                    'website': 'https://spam.example',
                    'name': 'Spam Bot',
                    'phone': '+998901234567',
                    'service': 'web_site',
                },
            )

        self.assertEqual(response.status_code, 303)
        add.assert_not_called()

    def test_fourth_valid_order_from_same_ip_is_rate_limited(self):
        fake_order = types.SimpleNamespace(id=123)
        fake_telegram = types.SimpleNamespace(send_to_admin=lambda _message: True)
        data = {
            'name': 'Test User',
            'phone': '+998 90 123 45 67',
            'service': 'web_site',
            'budget': '1m-3m',
            'message': 'Test loyiha',
        }

        with (
            mock.patch.object(trendo_app, 'Order', return_value=fake_order),
            mock.patch.object(trendo_app.db.session, 'add'),
            mock.patch.object(trendo_app.db.session, 'commit'),
            mock.patch.dict(sys.modules, {'telegram_poster': fake_telegram}),
        ):
            responses = [self.client.post('/submit-order', data=data) for _ in range(4)]

        self.assertEqual([response.status_code for response in responses[:3]], [303, 303, 303])
        self.assertEqual(responses[3].status_code, 429)

    def test_set_language_blocks_open_redirect_and_strips_stale_lang_query(self):
        # Tashqi domenga Open Redirect bo'lmasligi kerak
        evil_resp = self.client.get(
            '/set-lang/ru',
            headers={'Referer': 'https://evil.example.com/phish'},
        )
        self.assertEqual(evil_resp.status_code, 302)
        self.assertEqual(evil_resp.headers['Location'], '/')

        # O'z hostidagi ?lang=uz parametri olib tashlanishi kerak
        same_host_resp = self.client.get(
            '/set-lang/en',
            headers={'Referer': 'http://localhost/portfolio?category=web&lang=uz'},
        )
        self.assertEqual(same_host_resp.status_code, 302)
        self.assertEqual(same_host_resp.headers['Location'], '/portfolio?category=web')
        self.assertIn('no-store', same_host_resp.headers.get('Cache-Control', ''))

    def test_language_switching_updates_page_and_disables_public_cache(self):
        self.client.get('/set-lang/ru')
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('private, no-cache', resp.headers.get('Cache-Control', ''))
        self.assertIn('Cookie', resp.headers.get('Vary', ''))
        self.assertIn('Услуги'.encode('utf-8'), resp.data)

    def test_resolve_portfolio_image_supports_site_and_feed_modes(self):
        from services.seed_portfolio import resolve_portfolio_image

        site_img = resolve_portfolio_image(title='JonGiyoh.uz E-commerce', for_feed=False)
        feed_img = resolve_portfolio_image(
            title='JonGiyoh.uz E-commerce',
            for_feed=True,
            site_url='https://trendoai.uz',
        )
        self.assertEqual(site_img, '/static/img/portfolio/jongiyoh.webp')
        self.assertEqual(feed_img, 'https://trendoai.uz/static/img/portfolio/jongiyoh.jpg?v=2026_sep')

    def test_portfolio_detail_json_ld_is_valid_json_with_uzs_numeric_price(self):
        import json
        import re
        from models.portfolio import Portfolio

        with trendo_app.app.app_context():
            trendo_app.db.create_all()
            item = Portfolio.query.filter_by(slug='test-jsonld-project').first()
            if not item:
                item = Portfolio(
                    title='Test "AI" Loyiha',
                    slug='test-jsonld-project',
                    category='ai',
                    description='Loyiha "maxsus" tavsifi',
                    price='8,500,000 UZS',
                    image_url='/static/img/portfolio/instadubuz.webp',
                    is_published=True,
                )
                trendo_app.db.session.add(item)
                trendo_app.db.session.commit()

        resp = self.client.get('/portfolio/project/test-jsonld-project')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        blocks = re.findall(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            html,
            flags=re.DOTALL,
        )
        self.assertGreaterEqual(len(blocks), 3)
        parsed = [json.loads(b) for b in blocks]
        product_schema = next(p for p in parsed if p.get('@type') == 'Product')
        self.assertEqual(product_schema['offers']['price'], '8500000')
        self.assertEqual(product_schema['offers']['priceCurrency'], 'UZS')
        self.assertTrue(product_schema['image'].startswith('http'))

    def test_live_call_transcript_and_exit_offer_modal_present(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('id="callLiveTranscript"', html)
        self.assertIn('id="exitOfferModal"', html)
        self.assertIn('id="exitOfferForm"', html)


if __name__ == '__main__':
    unittest.main()
