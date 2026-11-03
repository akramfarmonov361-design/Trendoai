import unittest
import json
from app import app, db, PushSubscription

class PWATests(unittest.TestCase):
    def setUp(self):
        self._orig_csrf = app.config.get('WTF_CSRF_ENABLED', True)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        # Ensure database is set up
        with app.app_context():
            db.create_all()

    def tearDown(self):
        # Global app config'ni tiklaymiz, aks holda boshqa testlarda CSRF o'chib qoladi.
        app.config['WTF_CSRF_ENABLED'] = self._orig_csrf

    def test_manifest_exists(self):
        """Verify the manifest.json is served correctly"""
        response = self.client.get('/static/manifest.json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('name'), 'TrendoAI')
        self.assertEqual(data.get('short_name'), 'TrendoAI')
        self.assertEqual(data.get('display'), 'standalone')

    def test_service_worker_served(self):
        """Verify sw.js is served at root with correct content type"""
        response = self.client.get('/sw.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/javascript')
        self.assertIn(b'trendoai-v8', response.data)
        self.assertIn(b"event.request.method !== 'GET'", response.data)
        self.assertIn(b"url.pathname.startsWith('/api/')", response.data)

    def test_push_subscribe_valid(self):
        """Test subscribing to push notifications with valid keys"""
        with app.app_context():
            # Delete existing subscriptions with the test endpoint to avoid collisions
            PushSubscription.query.filter_by(endpoint='https://updates.push.services.mozilla.com/wpush/v2/test-endpoint').delete()
            db.session.commit()

        payload = {
            'endpoint': 'https://updates.push.services.mozilla.com/wpush/v2/test-endpoint',
            'keys': {
                'p256dh': 'BIP6v86jH1F2l44t33w',
                'auth': '5sT7h_U5w'
            }
        }
        response = self.client.post(
            '/api/push/subscribe',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('message'), 'Obuna saqlandi')

        # Verify it was added to the database
        with app.app_context():
            sub = PushSubscription.query.filter_by(endpoint='https://updates.push.services.mozilla.com/wpush/v2/test-endpoint').first()
            self.assertIsNotNone(sub)
            self.assertEqual(sub.p256dh, 'BIP6v86jH1F2l44t33w')
            self.assertEqual(sub.auth, '5sT7h_U5w')

            # Clean up
            db.session.delete(sub)
            db.session.commit()

    def test_push_subscribe_invalid(self):
        """Test subscription with missing keys or invalid data"""
        payload = {
            'endpoint': 'https://updates.push.services.mozilla.com/wpush/v2/test-endpoint'
        }
        response = self.client.post(
            '/api/push/subscribe',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_portfolio_send_telegram_returns_redirect(self):
        """admin_portfolio_send_telegram None qaytarmasdan /admin/portfolio ga redirect qilishi kerak."""
        from unittest import mock
        from models.portfolio import Portfolio

        with app.app_context():
            item = Portfolio.query.first()
            if not item:
                item = Portfolio(
                    title="Telegram Test Loyiha",
                    slug="telegram-test-loyiha",
                    category="bot",
                    description="Tavsif",
                    is_published=True,
                )
                db.session.add(item)
                db.session.commit()
            pid = item.id

        with self.client.session_transaction() as sess:
            sess['logged_in'] = True

        with mock.patch('telegram_poster.send_portfolio_to_channel', return_value=True):
            resp = self.client.post(f'/admin/portfolio/{pid}/send-telegram')

        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin/portfolio', resp.headers.get('Location', ''))

if __name__ == '__main__':
    unittest.main()
