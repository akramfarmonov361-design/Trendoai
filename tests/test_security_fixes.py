"""
Xavfsizlik va arxitektura tuzatishlarini tekshiruvchi testlar to'plami.
"""
from app import app
from config import FB_CONVERSIONS_API_TOKEN
from routes.api import TELEGRAM_WEBHOOK_SECRET

def test_admin_seed_endpoints_require_login():
    """Admin seed endpointlari faqat POST qabul qilishi va autentifikatsiya talab qilishini tekshirish"""
    with app.test_client() as client:
        for endpoint in ['/admin/seed-blog', '/admin/seed-portfolio', '/admin/seed-services']:
            # GET so'rovi 405 Method Not Allowed qaytarishi kerak
            resp_get = client.get(endpoint)
            assert resp_get.status_code == 405

            # Unauthenticated POST so'rovi 302 redirect bo'lishi va bajarilmasligi kerak
            resp_post = client.post(endpoint)
            assert resp_post.status_code == 302

def test_max_content_length_configured():
    """Flask MAX_CONTENT_LENGTH xavfsizlik cheklovi borligini tekshirish"""
    assert app.config.get('MAX_CONTENT_LENGTH') == 16 * 1024 * 1024

def test_telegram_webhook_strictly_enforces_secret():
    """Telegram webhook secret token bo'lmasa 403 qaytarishini tekshirish"""
    with app.test_client() as client:
        # Secret headeri umuman yo'q
        resp_no_secret = client.post('/webhook', json={'update_id': 123})
        assert resp_no_secret.status_code == 403

        # Noto'g'ri secret header
        resp_bad_secret = client.post('/webhook', json={'update_id': 123}, headers={
            'X-Telegram-Bot-Api-Secret-Token': 'wrong_secret_123'
        })
        assert resp_bad_secret.status_code == 403

        # To'g'ri secret header
        resp_good = client.post('/webhook', json={'update_id': 123}, headers={
            'X-Telegram-Bot-Api-Secret-Token': TELEGRAM_WEBHOOK_SECRET
        })
        # If bot is not configured or mock update, it should at least pass auth (not 403)
        assert resp_good.status_code in (200, 400)

def test_markdown_xss_protection():
    """Markdown filtri zararli HTML skriptlarni xavfsiz escape qilishini tekshirish"""
    with app.app_context():
        # Jinja template filterini chaqirish
        md_filter = app.jinja_env.filters['markdown']
        malicious_input = '<script>alert("XSS")</script> **Qalin matn**'
        rendered = md_filter(malicious_input)
        assert '<script>' not in rendered
        assert '&lt;script&gt;' in rendered
        assert '<strong>Qalin matn</strong>' in rendered

def test_ai_chat_payload_length_limit():
    """AI Chat endpointida juda uzun xabarlarga cheklov borligini tekshirish"""
    with app.test_client() as client:
        huge_message = 'A' * 5000
        resp = client.post('/api/chat', json={'message': huge_message})
        assert resp.status_code == 400
        assert 'juda uzun' in resp.json.get('error', '')

def test_ai_audio_payload_size_limit():
    """AI Audio endpointida 5MB dan katta fayllar rad etilishini tekshirish"""
    with app.test_client() as client:
        huge_audio = 'A' * (6 * 1024 * 1024)
        resp = client.post('/api/chat/audio', json={'audio': huge_audio})
        assert resp.status_code == 400
        assert 'katta' in resp.json.get('error', '')