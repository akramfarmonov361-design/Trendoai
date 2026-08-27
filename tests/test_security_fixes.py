"""
Xavfsizlik va arxitektura tuzatishlarini tekshiruvchi testlar to'plami.
"""
import re

from app import app
from config import FB_CONVERSIONS_API_TOKEN
from extensions import db
from models.interaction import Lead
from routes.api import TELEGRAM_WEBHOOK_SECRET
from services import rate_limit_service

def test_admin_seed_endpoints_require_login():
    """Admin seed va webhook endpointlari faqat POST qabul qilishi va autentifikatsiya talab qilishini tekshirish"""
    with app.test_client() as client:
        for endpoint in ['/admin/seed-blog', '/admin/seed-portfolio', '/admin/seed-services', '/admin/fix-webhook', '/admin/seed-menu']:
            # GET so'rovi 405 Method Not Allowed qaytarishi kerak
            resp_get = client.get(endpoint)
            assert resp_get.status_code == 405

            # Unauthenticated POST so'rovi 302 redirect bo'lishi va bajarilmasligi kerak
            resp_post = client.post(endpoint)
            assert resp_post.status_code == 302

def test_max_content_length_configured():
    """Flask MAX_CONTENT_LENGTH xavfsizlik cheklovi borligini tekshirish"""
    assert app.config.get('MAX_CONTENT_LENGTH') == 16 * 1024 * 1024


def test_rate_limit_has_a_local_fallback_when_redis_is_unavailable(monkeypatch):
    """Redis uzilsa ham bitta worker limitni qo'llashda davom etadi."""
    monkeypatch.setattr(rate_limit_service, 'get_redis_client', lambda: None)
    rate_limit_service._FALLBACK_REQUESTS.clear()

    assert rate_limit_service.allow_request('test', '127.0.0.1', 2, 60)
    assert rate_limit_service.allow_request('test', '127.0.0.1', 2, 60)
    assert not rate_limit_service.allow_request('test', '127.0.0.1', 2, 60)



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


def test_verification_routes_reject_html_payloads():
    """Google/Yandex tasdiqlash kodlari reflected XSS uchun ishlatilmasligi kerak"""
    payload = '<img src=x onerror=alert(1)>'
    with app.test_client() as client:
        for path in (f'/yandex_{payload}.html', f'/google{payload}.html'):
            resp = client.get(path)
            assert resp.status_code == 404
            assert 'onerror=alert(1)>' not in resp.get_data(as_text=True)


def test_verification_routes_still_serve_real_codes():
    """Haqiqiy tasdiqlash kodlari avvalgidek ishlashi kerak"""
    with app.test_client() as client:
        google_resp = client.get('/google1a2b3c4d5e6f.html')
        assert google_resp.status_code == 200
        assert 'google-site-verification: google1a2b3c4d5e6f.html' in google_resp.get_data(as_text=True)

        yandex_resp = client.get('/yandex_a1b2c3d4e5.html')
        assert yandex_resp.status_code == 200
        assert 'Verification: a1b2c3d4e5' in yandex_resp.get_data(as_text=True)


def test_kanban_crm_endpoints_work_with_csrf_token():
    """Kanban CRM AJAX so'rovlari tokensiz rad etilishi, token bilan ishlashi kerak"""
    with app.app_context():
        db.create_all()
        # Haqiqiy lead'lar o'zgarib ketmasligi uchun test o'z qatorini yaratadi
        lead = Lead(name='CSRF Test', contact='@csrftest', source='pytest')
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

    try:
        _assert_kanban_csrf_flow(lead_id)
    finally:
        with app.app_context():
            db.session.query(Lead).filter_by(id=lead_id).delete()
            db.session.commit()


def _assert_kanban_csrf_flow(lead_id):
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'admin'

        page = client.get('/admin/kanban')
        assert page.status_code == 200
        html = page.get_data(as_text=True)

        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
        assert match, "base_admin.html csrf-token meta tagini render qilmadi"
        assert "'X-CSRFToken': csrfToken()" in html, "kanban.html CSRF sarlavhasini yubormayapti"
        token = match.group(1)

        payload = {'type': 'lead', 'id': lead_id, 'status': 'contacted'}
        assert client.post('/api/admin/crm/update-status', json=payload).status_code == 400
        assert client.post(
            '/api/admin/crm/update-status', json=payload, headers={'X-CSRFToken': token}
        ).status_code == 200

        note_payload = {'type': 'lead', 'id': lead_id, 'note': 'follow-up'}
        assert client.post('/api/admin/crm/update-note', json=note_payload).status_code == 400
        assert client.post(
            '/api/admin/crm/update-note', json=note_payload, headers={'X-CSRFToken': token}
        ).status_code == 200


def test_lead_endpoint_is_rate_limited(monkeypatch):
    """/api/lead cheklovsiz bo'lsa spam bilan baza va Telegram to'ldirilardi"""
    monkeypatch.setattr(rate_limit_service, 'get_redis_client', lambda: None)
    rate_limit_service._FALLBACK_REQUESTS.clear()
    monkeypatch.setattr('routes.api.is_duplicate_contact', lambda contact: False)
    monkeypatch.setattr('telegram_poster.send_admin_alert', lambda *a, **k: None)

    with app.app_context():
        db.create_all()

    statuses = []
    with app.test_client() as client:
        for i in range(7):
            resp = client.post('/api/lead', json={'contact': f'@spam{i}', 'name': 'Spam'})
            statuses.append(resp.status_code)

    assert 429 in statuses, f"rate limit ishlamadi: {statuses}"
    assert statuses.count(429) >= 2

    with app.app_context():
        db.session.query(Lead).filter(Lead.contact.like('@spam%')).delete(synchronize_session=False)
        db.session.commit()


def test_email_address_does_not_create_a_fake_lead():
    """'ali@gmail.com' ichidagi '@gmail' kontakt deb qabul qilinmasligi kerak"""
    from services.crm_service import extract_contact

    assert extract_contact('mening pochtam ali@gmail.com') is None
    assert extract_contact('telegram: @akramfarmonov') == '@akramfarmonov'
    assert extract_contact('+998 90 123 45 67') == '+998 90 123 45 67'


def test_duplicate_contact_is_detected():
    """Bir xil kontakt qayta yozilmasligi kerak (baza/Telegram spamining oldini olish)"""
    from services.crm_service import is_duplicate_contact

    with app.app_context():
        db.create_all()
        lead = Lead(name='Dup Test', contact='+998901112233', source='pytest')
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id
        try:
            assert is_duplicate_contact('+998901112233')
            # Formatlash farqi dublikatni yashirmasligi kerak
            assert is_duplicate_contact('+998 (90) 111-22-33')
            assert not is_duplicate_contact('+998907776655')
        finally:
            db.session.query(Lead).filter_by(id=lead_id).delete()
            db.session.commit()


def test_telegram_webhook_secret_is_telegram_safe():
    """Telegram secret_token faqat A-Z a-z 0-9 _ - belgilaridan iborat bo'lishi kerak"""
    assert TELEGRAM_WEBHOOK_SECRET
    assert re.fullmatch(r'[A-Za-z0-9_-]{1,256}', TELEGRAM_WEBHOOK_SECRET)


def test_facebook_lead_webhook_verifies_hmac_signature(monkeypatch):
    """FB_APP_SECRET berilganda imzosiz/soxta so'rovlar rad etilishi kerak"""
    import hashlib
    import hmac as _hmac
    import config

    monkeypatch.setattr(config, 'FB_APP_SECRET', 'test_app_secret')
    body = b'{"entry": []}'

    with app.test_client() as client:
        no_sig = client.post('/api/webhook/facebook-leads', data=body,
                             content_type='application/json')
        assert no_sig.status_code == 403

        bad_sig = client.post('/api/webhook/facebook-leads', data=body,
                              content_type='application/json',
                              headers={'X-Hub-Signature-256': 'sha256=deadbeef'})
        assert bad_sig.status_code == 403

        good = _hmac.new(b'test_app_secret', body, hashlib.sha256).hexdigest()
        ok_sig = client.post('/api/webhook/facebook-leads', data=body,
                             content_type='application/json',
                             headers={'X-Hub-Signature-256': f'sha256={good}'})
        assert ok_sig.status_code == 200


