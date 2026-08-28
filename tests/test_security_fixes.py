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
        admin_js = open('static/js/admin.js', encoding='utf-8').read()
        assert "'X-CSRFToken': csrfToken()" in admin_js, 'admin.js CSRF sarlavhasini yubormayapti'
        assert 'js/admin.js' in html, 'admin.js sahifaga ulanmagan'
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


def test_admin_login_uses_constant_time_and_hash_when_configured(monkeypatch):
    """Parol hash rejimida ham, ochiq rejimda ham to'g'ri ishlashi kerak"""
    from werkzeug.security import generate_password_hash
    import routes.admin as admin_routes

    # 1) Ochiq parol rejimi (orqaga moslik)
    monkeypatch.setattr(admin_routes, 'ADMIN_PASSWORD_HASH', '')
    monkeypatch.setattr(admin_routes, 'ADMIN_PASSWORD', 'plain-parol-123')
    monkeypatch.setattr(admin_routes, 'ADMIN_USERNAME', 'admin')
    assert admin_routes._check_admin_credentials('admin', 'plain-parol-123')
    assert not admin_routes._check_admin_credentials('admin', 'notogri')
    assert not admin_routes._check_admin_credentials('boshqa', 'plain-parol-123')

    # 2) Hash rejimi — ochiq parol umuman ishlatilmaydi
    monkeypatch.setattr(admin_routes, 'ADMIN_PASSWORD_HASH',
                        generate_password_hash('hash-parol-456'))
    monkeypatch.setattr(admin_routes, 'ADMIN_PASSWORD', '')
    assert admin_routes._check_admin_credentials('admin', 'hash-parol-456')
    assert not admin_routes._check_admin_credentials('admin', 'plain-parol-123')


def test_failed_login_tracker_is_pruned():
    """_failed_logins cheksiz o'smasligi kerak"""
    import routes.admin as admin_routes

    admin_routes._failed_logins.clear()
    now = 1_000_000.0
    admin_routes._failed_logins['1.1.1.1'] = [now - admin_routes.LOGIN_WINDOW_SECONDS - 10]
    admin_routes._failed_logins['2.2.2.2'] = [now - 5]

    admin_routes._prune_failed_logins(now)

    assert '1.1.1.1' not in admin_routes._failed_logins, "eskirgan IP o'chirilmadi"
    assert '2.2.2.2' in admin_routes._failed_logins, "faol IP noto'g'ri o'chirildi"
    admin_routes._failed_logins.clear()


def test_bot_user_states_are_pruned():
    """user_states TTL va maksimal chegara bo'yicha tozalanishi kerak"""
    import bot_service

    bot_service.user_states.clear()
    now = 1_000_000.0
    bot_service.user_states[1] = {'state': 'idle', 'last_time': now - bot_service.USER_STATE_TTL_SECONDS - 10}
    bot_service.user_states[2] = {'state': 'idle', 'last_time': now - 10}

    removed = bot_service.prune_user_states(now=now)

    assert removed == 1
    assert 1 not in bot_service.user_states, "eskirgan holat o'chirilmadi"
    assert 2 in bot_service.user_states, "faol holat noto'g'ri o'chirildi"
    bot_service.user_states.clear()


def test_gunicorn_timeout_is_not_disabled():
    """timeout=0 osilgan worker'ni hech qachon qayta ishga tushirmasdi"""
    import runpy

    conf = runpy.run_path('gunicorn.conf.py')
    assert conf['timeout'] > 0
    assert conf['timeout'] >= 60, "AI so'rovlari uchun yetarlicha uzun bo'lsin"


def test_indexnow_key_matches_specification():
    """IndexNow kaliti [a-zA-Z0-9-] va 8-128 belgidan iborat bo'lishi shart"""
    from seo_indexer import INDEXNOW_KEY_PATTERN, get_indexnow_key

    key = get_indexnow_key()
    assert INDEXNOW_KEY_PATTERN.fullmatch(key), f"kalit spetsifikatsiyaga mos emas: {key}"
    assert '_' not in key


def test_indexnow_key_is_served_at_its_own_path():
    """keyLocation {host}/{key}.txt manzilida haqiqatan ham mavjud bo'lishi kerak"""
    from seo_indexer import get_indexnow_key

    key = get_indexnow_key()
    with app.test_client() as client:
        resp = client.get(f'/{key}.txt')
        assert resp.status_code == 200
        assert resp.get_data(as_text=True).strip() == key


def test_dead_google_sitemap_ping_is_removed():
    """google.com/ping 2024-yilda o'chirilgan — chaqiruv qolmasligi kerak.

    Izohlarda eslatib o'tish mumkin, tekshiruv faqat bajariladigan kodga tegishli.
    """
    import inspect

    import seo_indexer

    code_lines = [
        line for line in inspect.getsource(seo_indexer).splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]
    assert not any('google.com/ping' in line for line in code_lines)


def test_csp_defaults_to_report_only_mode():
    """Yangi qat'iy siyosat avval kuzatuv rejimida bo'lishi kerak"""
    import app as trendo_app

    with app.test_client() as client:
        resp = client.get('/api/health')

    enforced = resp.headers.get('Content-Security-Policy')
    report_only = resp.headers.get('Content-Security-Policy-Report-Only')

    if trendo_app.CSP_ENFORCE:
        assert report_only is None
        assert "default-src 'self'" in enforced
    else:
        # Jonli siyosat o'zgarmaydi, yangi qoidalar faqat kuzatiladi
        assert enforced == trendo_app.CSP_BASELINE_POLICY
        assert report_only and "default-src 'self'" in report_only
        # upgrade-insecure-requests report-only rejimda e'tiborsiz qoldiriladi
        assert 'upgrade-insecure-requests' not in report_only


def test_csp_enforce_mode_emits_full_policy(monkeypatch):
    """CSP_ENFORCE=true da to'liq siyosat majburiy sarlavhada bo'lishi kerak"""
    import app as trendo_app

    monkeypatch.setattr(trendo_app, 'CSP_ENFORCE', True)
    with app.test_client() as client:
        resp = client.get('/api/health')

    assert resp.headers.get('Content-Security-Policy-Report-Only') is None
    assert resp.headers['Content-Security-Policy'] == trendo_app.CSP_POLICY
    assert 'upgrade-insecure-requests' in resp.headers['Content-Security-Policy']


def test_csp_covers_every_external_origin_used_by_templates():
    """Inventarizatsiyada topilgan har bir tashqi manba siyosatda bo'lishi shart"""
    from config import CSP_POLICY

    required = {
        'script-src': ['www.googletagmanager.com', 'connect.facebook.net', 'telegram.org'],
        'style-src': ['fonts.googleapis.com', 'cdnjs.cloudflare.com'],
        'font-src': ['fonts.gstatic.com', 'cdnjs.cloudflare.com'],
        'frame-src': ['www.youtube.com'],
        'connect-src': ['www.google-analytics.com', 'www.facebook.com'],
    }
    directives = {
        part.split(' ', 1)[0]: part
        for part in CSP_POLICY.split('; ')
        if ' ' in part
    }
    for name, origins in required.items():
        assert name in directives, f"{name} direktivasi yo'q"
        for origin in origins:
            assert origin in directives[name], f"{origin} {name} da yo'q"

    assert "object-src 'none'" in CSP_POLICY
    # Alpine.js o'lik shablon bilan birga o'chirildi — unsafe-eval kerak emas
    assert 'unsafe-eval' not in CSP_POLICY


def test_dead_base_v2_template_is_removed():
    """base_v2.html hech qayerda ishlatilmasdi va Alpine.js CDN'ini olib kelardi"""
    import os

    assert not os.path.exists('templates/base_v2.html')


def _template_files():
    import glob
    return sorted(glob.glob('templates/**/*.html', recursive=True))


def test_no_template_has_inline_event_handlers():
    """Bosqich 2 yakunlandi: birorta shablonda onclick= va shunga o'xshash
    atributlar qolmasligi kerak — CSP nonce ularni qamrab ololmaydi."""
    topilgan = {}
    for path in _template_files():
        html = open(path, encoding='utf-8').read()
        handlers = re.findall(r'\son[a-z]+="[^"]*"', html)
        if handlers:
            topilgan[path] = handlers
    assert not topilgan, f'inline handler qaytdi: {topilgan}'


def test_no_template_has_executable_inline_script():
    """Bajariladigan inline <script> qolmasligi kerak.

    <script type="application/ld+json"> va "application/json" data-bloklari
    bajarilmaydi, shuning uchun ular hisobga olinmaydi.
    """
    topilgan = {}
    for path in _template_files():
        html = open(path, encoding='utf-8').read()
        bad = [
            attrs for attrs in re.findall(r'<script([^>]*)>', html)
            if 'src=' not in attrs and 'json' not in attrs
        ]
        if bad:
            topilgan[path] = bad
    assert not topilgan, f'inline skript qoldi: {topilgan}'


def test_script_src_no_longer_allows_unsafe_inline():
    """Inline skriptlar tugagach 'unsafe-inline' olib tashlanishi kerak,
    aks holda CSP XSS'dan himoya qilmaydi."""
    from config import CSP_POLICY

    script_src = next(p for p in CSP_POLICY.split('; ') if p.startswith('script-src'))
    assert "'unsafe-inline'" not in script_src, script_src
    assert "'unsafe-eval'" not in CSP_POLICY

    # style-src da hozircha qoladi: 126 ta style="" atributi bor
    style_src = next(p for p in CSP_POLICY.split('; ') if p.startswith('style-src'))
    assert "'unsafe-inline'" in style_src


def test_static_urls_are_versioned():
    """/static/ bir yillik immutable kesh bilan beriladi, shuning uchun URL
    fayl o'zgarganda o'zgarishi shart — aks holda JS tuzatishi yetib bormaydi."""
    from flask import url_for

    with app.test_request_context():
        url = url_for('static', filename='js/site.js')

    assert '?v=' in url, f'versiyasiz static URL: {url}'
    assert re.search(r'\?v=\d+$', url), url


def test_form_scripts_render_inside_content_block():
    """{% extends %} shablonida blokdan tashqaridagi teg umuman render
    qilinmaydi — skript jimgina yuklanmay qolardi."""
    from extensions import db

    with app.app_context():
        db.create_all()

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'admin'

        portfolio = client.get('/admin/portfolio/new').get_data(as_text=True)
        service = client.get('/admin/services/new').get_data(as_text=True)

    assert 'js/admin-portfolio-form.js' in portfolio
    assert 'js/admin-service-form.js' in service
    # Ikkalasi ham #ai-generate-btn ishlatadi, shuning uchun aralashmasligi shart
    assert 'js/admin-service-form.js' not in portfolio
    assert 'js/admin-portfolio-form.js' not in service


def test_admin_common_script_is_loaded_everywhere():
    """admin.js base_admin.html dan yuklanadi va data-* handlerlarni ulaydi"""
    js = open('static/js/admin.js', encoding='utf-8').read()
    base = open('templates/admin/base_admin.html', encoding='utf-8').read()

    assert 'js/admin.js' in base
    for hook in ('[data-confirm]', '[data-modal-open]', '[data-modal-hide]',
                 '[data-autosubmit]', '[data-print]', '[data-reload]',
                 '[data-topic]', '[data-filter-input]', '[data-save-note]',
                 '[data-crm-status]', '[data-order-status]', '[data-order-details]'):
        assert hook in js, f'{hook} uchun listener yo\'q'


def test_base_template_loads_application_js_externally():
    """Katta inline bloklar tashqi fayllarga chiqarilgan bo'lishi kerak"""
    import os

    html = open('templates/base.html', encoding='utf-8').read()
    assert "js/site.js" in html
    assert "js/chatbot.js" in html
    for path in ('static/js/site.js', 'static/js/chatbot.js'):
        assert os.path.exists(path), f"{path} yo'q"
        source = open(path, encoding='utf-8').read()
        # Tashqi .js fayl Jinja orqali render qilinmaydi — shablon sintaksisi
        # u yerda matn bo'lib qolib, jimgina buziladi.
        assert '{{' not in source and '{%' not in source, f"{path} da Jinja sintaksisi bor"


def test_vapid_key_is_passed_through_data_attribute():
    """VAPID kaliti inline JS o'rniga body data-atributidan olinadi"""
    html = open('templates/base.html', encoding='utf-8').read()
    site_js = open('static/js/site.js', encoding='utf-8').read()
    assert 'data-vapid-key=' in html
    assert 'document.body.dataset.vapidKey' in site_js


def test_csp_allows_meta_pixel_form_and_frame_fallbacks():
    """Brauzerda tasdiqlangan: Pixel /tr/ ga form POST va iframe ishlatadi.

    form-action 'self' bu POSTni bloklab kelgan — Pixel qisman ishlamagan.
    """
    from config import CSP_BASELINE_POLICY, CSP_POLICY

    for policy in (CSP_POLICY, CSP_BASELINE_POLICY):
        form_action = next(p for p in policy.split('; ') if p.startswith('form-action'))
        assert 'https://www.facebook.com' in form_action, f"form-action Pixelni bloklaydi: {form_action}"

    frame_src = next(p for p in CSP_POLICY.split('; ') if p.startswith('frame-src'))
    assert 'https://www.facebook.com' in frame_src
    assert 'https://www.youtube.com' in frame_src


def test_services_page_js_is_external_and_jinja_free():
    """Bosh sahifa (services.html) skriptlari tashqi faylda bo'lishi kerak"""
    import os

    html = open('templates/services.html', encoding='utf-8').read()
    assert 'js/services.js' in html
    assert os.path.exists('static/js/services.js')

    source = open('static/js/services.js', encoding='utf-8').read()
    assert '{{' not in source and '{%' not in source, 'services.js da Jinja sintaksisi bor'

    # JSON-LD data-bloklari qoladi: ular bajarilmaydi va script-src ularga tegmaydi
    assert html.count('<script type="application/ld+json">') == 2


def test_services_handlers_became_data_attributes():
    """18 ta inline handler data-atribut + addEventListener ga o'tgan bo'lishi kerak"""
    html = open('templates/services.html', encoding='utf-8').read()
    js = open('static/js/services.js', encoding='utf-8').read()

    assert html.count('data-fb-addtocart=') == 4, 'Pixel AddToCart tugmalari'
    assert html.count('data-calc-input') == 9, 'kalkulyator inputlari'

    for hook in ('[data-fb-addtocart]', '[data-calc-input]', '.type-card', '.btn-calc-apply'):
        assert hook in js, f'{hook} uchun listener yo\'q'

    # Pixel yuklanmagan sahifada ham xato bermasligi kerak
    assert "typeof fbq === 'undefined'" in js


def test_portfolio_data_block_is_valid_json():
    """Ma'lumot bajariladigan skript emas, JSON data-blokida bo'lishi kerak.

    <script type="application/json"> bajarilmaydi, shuning uchun CSP
    script-src unga taalluqli emas — inline JS'siz ma'lumot uzatish yo'li.
    """
    import json
    import re as _re

    from extensions import db

    with app.app_context():
        db.create_all()

    with app.test_client() as client:
        resp = client.get('/portfolio')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)

    match = _re.search(
        r'<script type="application/json" id="portfolios-data">(.*?)</script>',
        html, _re.DOTALL)
    assert match, 'portfolios-data bloki topilmadi'

    payload = json.loads(match.group(1))
    assert set(payload) == {'items', 'useFallback', 'orderUrl'}
    assert isinstance(payload['items'], list)
    assert isinstance(payload['useFallback'], bool)
    assert payload['orderUrl'].startswith('/')


def test_portfolio_modal_lookup_tolerates_string_ids():
    """data-atributdan kelgan id doim satr; baza id'lari esa son.

    Qat'iy `p.id === projectId` taqqoslash hech bir modalni ochmasdi.
    """
    js = open('static/js/portfolio.js', encoding='utf-8').read()
    assert 'String(p.id) === String(projectId)' in js
    assert 'p.id === projectId' not in js


def test_portfolio_handlers_became_delegated_listeners():
    """66 ta inline handler bitta delegatsiyaga yig'ilgan bo'lishi kerak"""
    html = open('templates/portfolio.html', encoding='utf-8').read()
    js = open('static/js/portfolio.js', encoding='utf-8').read()

    assert 'data-modal-id=' in html
    assert 'data-modal-close' in html
    # stopPropagation endi umuman kerak emas — delegatsiya buni hal qiladi
    assert 'stopPropagation' not in html

    assert "e.target.closest('[data-modal-id]')" in js
    assert "e.target.closest('[data-modal-close]')" in js
    assert '{{' not in js and '{%' not in js, 'portfolio.js da Jinja sintaksisi bor'

    # Baza bo'sh bo'lganda ko'rsatiladigan namoyish loyihalari saqlanib qolgan
    assert js.count("id: 'manual-") == 12


def test_tma_page_js_is_external_and_jinja_free():
    """Telegram Mini App skripti tashqi faylda bo'lishi kerak"""
    import os

    html = open('templates/tma.html', encoding='utf-8').read()
    assert 'js/tma.js' in html
    assert os.path.exists('static/js/tma.js')

    js = open('static/js/tma.js', encoding='utf-8').read()
    assert '{{' not in js and '{%' not in js, 'tma.js da Jinja sintaksisi bor'


def test_tma_handlers_became_data_attributes():
    """24 ta inline handler data-atribut + addEventListener ga o'tgan bo'lishi kerak"""
    html = open('templates/tma.html', encoding='utf-8').read()
    js = open('static/js/tma.js', encoding='utf-8').read()

    kutilgan = {
        'data-tab=': 8,
        'data-calc-input': 6,
        'data-order-name=': 5,
        'data-order-price=': 5,
        'data-calc-order': 1,
        'data-modal-close': 1,
        'data-href=': 1,
    }
    for atribut, son in kutilgan.items():
        assert html.count(atribut) == son, f'{atribut}: {html.count(atribut)} != {son}'

    for hook in ('[data-tab]', '[data-calc-input]', '[data-order-name]',
                 '[data-calc-order]', '[data-modal-close]', '[data-href]'):
        assert hook in js, f'{hook} uchun listener yo\'q'

    # Modal fonini bosish faqat fonning o'zida yopishi kerak, ichida emas
    assert 'e.target === orderModal' in js
    assert "getElementById('modal-submit-btn')" in js


def test_tma_prices_kept_their_apostrophes():
    """onclick ichida narx \' bilan escape qilingan edi.

    data-atributga ko'chirishda escape olib tashlanishi kerak, aks holda
    modalda "so\'m" ko'rinardi.
    """
    html = open('templates/tma.html', encoding='utf-8').read()

    assert 'data-order-price="300,000 - 3,000,000 so\'m"' in html
    # Ikki belgili ketma-ketlik: teskari chiziq + apostrof
    assert (chr(92) + "'") not in html, 'escape qilingan apostrof qoldi'
