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
