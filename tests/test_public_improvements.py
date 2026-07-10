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


if __name__ == '__main__':
    unittest.main()
