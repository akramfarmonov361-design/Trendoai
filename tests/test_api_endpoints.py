import pytest
from app import create_app
from extensions import db

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_api_health_endpoint(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.is_json
    
    data = response.get_json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data

def test_homepage_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"TrendoAI" in response.data or b"trendoai" in response.data.lower()

def test_admin_redirects_if_not_logged_in(client):
    response = client.get('/admin')
    # Login qilmagan admin /admin/login ga redirect (302) bo'lishi kerak
    assert response.status_code == 302
    assert "/admin/login" in response.headers.get("Location", "")


def test_api_health_reports_database_state(client):
    """Health check bazaga tegib ko'rishi kerak, aks holda Render baza
    yiqilganini sezmaydi va servisni qayta ishga tushirmaydi."""
    data = client.get('/api/health').get_json()
    assert data["database"] == "ok"


def test_api_health_returns_503_when_database_is_down(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("baza yo'q")

    monkeypatch.setattr(db.session, "execute", boom)

    response = client.get('/api/health')
    assert response.status_code == 503

    data = response.get_json()
    assert data["status"] == "error"
    assert data["database"] == "error"


def test_daily_post_guard_blocks_second_run_same_day(app):
    """Ichki APScheduler va tashqi cron bir kunda ishga tushsa, ikkinchisi
    to'xtashi kerak — aks holda kuniga ikkita post chiqib ketadi."""
    from models.post import Post
    from scheduler import _post_published_recently

    with app.app_context():
        assert _post_published_recently() is False

        db.session.add(Post(title="Sinov", content="matn", topic="sinov mavzu"))
        db.session.commit()

        assert _post_published_recently() is True


def test_guard_handles_timezone_aware_database_clock():
    """Postgres `now()` ni tz-aware qaytaradi, `created_at` esa naive.

    Ularni ayirish TypeError beradi va qalqon jim ravishda ishlamay qolardi —
    ya'ni takrorlanish himoyasi aynan production'da o'chiq bo'lardi.
    """
    from datetime import datetime, timedelta, timezone
    from scheduler import _strip_tz

    aware = datetime(2026, 9, 1, 4, 0, tzinfo=timezone.utc)
    naive = datetime(2026, 8, 31, 4, 0)

    # Tuzatishdan oldin bu qator TypeError bilan yiqilardi.
    delta = _strip_tz(aware) - _strip_tz(naive)
    assert delta == timedelta(hours=24)

    # Naive qiymatlar o'zgarishsiz qaytadi.
    assert _strip_tz(naive) == naive
    assert _strip_tz(None) is None


def test_cron_generate_sync_reports_the_real_outcome(client, app, monkeypatch):
    """sync=1 da endpoint haqiqiy natijani qaytarishi kerak.

    Fon rejimida u ish boshlanmasdan turib `success: true` qaytarardi, ya'ni
    post chiqmagani chaqiruvchiga hech qachon ko'rinmasdi — 2026-09-01 da
    kunlik post aynan shunday jimgina yo'qolgan.
    """
    import scheduler as scheduler_module

    app.config["CRON_SECRET"] = "test-cron-secret"
    headers = {"X-Cron-Secret": "test-cron-secret"}

    # True -> post yaratildi
    monkeypatch.setattr(scheduler_module, "generate_and_publish_post", lambda *a, **k: True)
    response = client.post("/api/cron/generate?sync=1", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    # None -> takrorlanish qalqoni to'sdi, bu xato emas
    monkeypatch.setattr(scheduler_module, "generate_and_publish_post", lambda *a, **k: None)
    response = client.post("/api/cron/generate?sync=1", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["skipped"] is True

    # False -> generatsiya yiqildi, chaqiruvchi buni bilishi shart
    monkeypatch.setattr(scheduler_module, "generate_and_publish_post", lambda *a, **k: False)
    response = client.post("/api/cron/generate?sync=1", headers=headers)
    assert response.status_code == 500
    assert response.get_json()["success"] is False


def test_cron_generate_still_requires_the_secret(client, app):
    app.config["CRON_SECRET"] = "test-cron-secret"
    assert client.post("/api/cron/generate?sync=1").status_code == 401

