"""
Meta Ads, Facebook Pixel, Conversions API (CAPI) va XML Feed integratsiya testlari.
"""
from app import app
from config import FACEBOOK_PIXEL_ID, FB_CONVERSIONS_API_TOKEN
from services.meta_capi import _hash_field, track_meta_event

def test_meta_config():
    assert FACEBOOK_PIXEL_ID == "1192818429057379"
    if FB_CONVERSIONS_API_TOKEN:
        assert isinstance(FB_CONVERSIONS_API_TOKEN, str)

def test_meta_capi_hashing():
    assert _hash_field("+998901234567") is not None
    assert _hash_field("test@trendoai.uz") is not None
    assert _hash_field(None) is None

def test_meta_capi_track_execution():
    with app.test_request_context('/order'):
        track_meta_event("Lead", user_data={"phone": "+998901234567", "email": "test@trendoai.uz"})

def test_facebook_catalog_feed():
    from extensions import db
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        response = client.get('/facebook-catalog.xml')
        assert response.status_code == 200
        assert 'xml' in response.mimetype
        assert b'<rss' in response.data
        assert b'<channel>' in response.data
        assert b'Trendo' in response.data
        assert b'<g:id>' in response.data

def test_facebook_feed_alias():
    from extensions import db
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        response = client.get('/facebook-feed.xml')
        assert response.status_code == 200
        assert 'xml' in response.mimetype

def test_facebook_lead_webhook_get():
    with app.test_client() as client:
        # Valid challenge
        resp = client.get('/api/webhook/facebook-leads?hub.mode=subscribe&hub.verify_token=trendoai_lead_secret_2026&hub.challenge=test_challenge_123')
        assert resp.status_code == 200
        assert resp.get_data(as_text=True) == 'test_challenge_123'

        # Invalid token
        resp_bad = client.get('/api/webhook/facebook-leads?hub.mode=subscribe&hub.verify_token=wrong_token')
        assert resp_bad.status_code == 403

def test_facebook_lead_webhook_post_empty():
    with app.test_client() as client:
        resp = client.post('/api/webhook/facebook-leads', json={})
        assert resp.status_code == 200
        assert resp.json.get('status') == 'received'


class _FakePortfolio:
    def __init__(self, title="", slug="", video_url=None):
        self.title = title
        self.slug = slug
        self.video_url = video_url


def test_feed_video_comes_only_from_database():
    """Feed videoni sarlavhadan taxmin qilmasligi kerak.

    Ilgari "luxe" so'zini ko'rsa luxe-core-demo.mp4 ni qo'shardi, natijada
    feed videoni va'da qilardi, loyiha sahifasi esa `video_url` bo'sh
    bo'lgani uchun pleyerni ko'rsatmasdi — feed saytga zid tushardi.
    """
    from routes.web.seo import _resolve_feed_video

    site = "https://trendoai.uz"

    # Sarlavhada "luxe" bor, lekin bazada video yo'q -> bo'sh
    guessable = _FakePortfolio(title="Luxe Core - Premium brend", slug="luxe-core-7")
    assert _resolve_feed_video(guessable, site) == ""

    # Bazada nisbiy havola bor -> to'liq URL
    relative = _FakePortfolio(video_url="/static/videos/luxe-core-demo.mp4")
    assert _resolve_feed_video(relative, site) == f"{site}/static/videos/luxe-core-demo.mp4"

    # Bazada absolyut havola bor -> o'zgarishsiz
    absolute = _FakePortfolio(video_url="https://cdn.example.com/a.mp4")
    assert _resolve_feed_video(absolute, site) == "https://cdn.example.com/a.mp4"

    # MP4 bo'lmagan havola (YouTube) feedga tushmaydi
    youtube = _FakePortfolio(video_url="https://youtube.com/watch?v=abc")
    assert _resolve_feed_video(youtube, site) == ""

    assert _resolve_feed_video(None, site) == ""


def test_catalog_cache_clears_the_meta_feed_key():
    """Loyiha yangilanganda katalog feedi keshi ham tozalanishi kerak.

    Feed bir soatga keshlanadi (ttl=3600), admin paneldagi o'zgarish esa
    ilgari faqat `portfolio:*` kalitlarini tozalardi. Natijada loyihaga
    video qo'shilgach, feed bir soatgacha eski holicha qolar edi.
    """
    from services.cache_service import (
        CATALOG_FEED_CACHE_KEY,
        cache_get,
        cache_set,
        clear_catalog_cache,
    )

    cache_set(CATALOG_FEED_CACHE_KEY, "<rss>eski</rss>", ttl=3600)
    cache_set("portfolio:1:", "eski ro'yxat", ttl=3600)
    assert cache_get(CATALOG_FEED_CACHE_KEY) is not None

    clear_catalog_cache()

    assert cache_get(CATALOG_FEED_CACHE_KEY) is None
    assert cache_get("portfolio:1:") is None


def _make_portfolio(**kwargs):
    from models.portfolio import Portfolio
    defaults = {"description": "tavsif", "category": "web", "is_published": True}
    defaults.update(kwargs)
    return Portfolio(**defaults)


def test_meta_video_supplementary_feed():
    """Meta katalogiga video faqat qo'shimcha CSV orqali yetadi.

    Asosiy XML feed video yubora olmaydi: Meta'ning maydoni `video[0].url`,
    kvadrat qavslar esa XML teg nomida taqiqlangan. Shuning uchun
    `<g:video_link>` yozilgani bilan Meta uni umuman o'qimaydi.
    """
    from app import create_app
    from extensions import db

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        db.session.add(_make_portfolio(title="Nisbiy", slug="n-1", video_url="/static/videos/a.mp4"))
        db.session.add(_make_portfolio(title="Absolyut", slug="a-2", video_url="https://cdn.example.com/b.mp4"))
        db.session.add(_make_portfolio(title="Videosiz", slug="v-3"))
        db.session.add(_make_portfolio(title="YouTube", slug="y-4", video_url="https://youtube.com/watch?v=x"))
        db.session.commit()

        response = app.test_client().get("/feed/meta-videos.csv")
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("text/csv")

        rows = response.get_data(as_text=True).strip().splitlines()

        # Ustun nomlari Meta spetsifikatsiyasidagidek bo'lishi shart.
        assert rows[0] == "id,video[0].url"

        # Nisbiy yo'l to'liq URL ga aylanadi, absolyut o'zgarishsiz qoladi.
        assert "https://trendoai.uz/static/videos/a.mp4" in rows[1]
        assert "https://cdn.example.com/b.mp4" in rows[2]

        # Videosiz va YouTube havolali loyihalar tushmaydi: bo'sh qiymat
        # yuborilsa Meta mavjud ma'lumotni o'chirib yuborishi mumkin, YouTube
        # esa pleyer havolasi — Meta uni qabul qilmaydi.
        assert len(rows) == 3
        assert "youtube" not in response.get_data(as_text=True).lower()

        db.session.remove()
        db.drop_all()


def test_catalog_cache_clears_the_video_feed_key():
    from services.cache_service import (
        CATALOG_VIDEO_FEED_CACHE_KEY,
        cache_get,
        cache_set,
        clear_catalog_cache,
    )

    cache_set(CATALOG_VIDEO_FEED_CACHE_KEY, "id,video[0].url", ttl=3600)
    assert cache_get(CATALOG_VIDEO_FEED_CACHE_KEY) is not None

    clear_catalog_cache()

    assert cache_get(CATALOG_VIDEO_FEED_CACHE_KEY) is None

