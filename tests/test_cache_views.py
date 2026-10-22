"""Kesh payload'lari va portfolio xatolik yo'li uchun regressiya testlari.

Bu testlar ikkita real xatoni qulflaydi:

1. SQLAlchemy ``Pagination``/ORM obyektlarini Redis'ga pickle qilib
   bo'lmaydi — kesh jimgina in-memory rejimga qaytardi. Endi keshga faqat
   plain dict yoziladi va u pickle round-trip'dan o'tishi shart.
2. ``portfolio_item`` ichida baza xatosi yuz berganda ``redirect``/
   ``url_for`` import qilinmagani uchun NameError (500) chiqardi.
"""
import pickle
import types

import pytest

from app import create_app
from extensions import db
from models.portfolio import Portfolio
from models.post import Post
from routes.web import blog as blog_routes
from routes.web import portfolio_routes
from services.cache_service import (
    cache_delete,
    cache_delete_prefix,
    cache_get,
    cache_set,
)
from services.view_models import (
    blog_page,
    item_namespaces,
    page_namespace,
    portfolio_page,
)


@pytest.fixture
def app():
    application = create_app()
    application.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


def _seed():
    db.session.add(
        Post(
            title="Birinchi post",
            slug="birinchi-post",
            content="Matn",
            topic="mavzu",
            category="AI",
            views=7,
            reading_time=2,
        )
    )
    db.session.add(
        Portfolio(
            title="Birinchi loyiha",
            slug="birinchi-loyiha",
            description="Tavsif",
            category="web",
            technologies="Flask, JS",
        )
    )
    db.session.commit()


def _pickle_cache(monkeypatch, module):
    """Redis kabi qat'iy pickle saqlaydigan soxta kesh."""
    store = {}

    def fake_get(key, is_testing=False):
        raw = store.get(key)
        return pickle.loads(raw) if raw is not None else None

    def fake_set(key, value, ttl=None, is_testing=False):
        store[key] = pickle.dumps(value)

    monkeypatch.setattr(module, "cache_get", fake_get)
    monkeypatch.setattr(module, "cache_set", fake_set)
    return store


def test_portfolio_page_payload_is_picklable(app):
    _seed()
    pagination = Portfolio.query.paginate(page=1, per_page=12, error_out=False)

    payload = portfolio_page(pagination, lambda item: "/static/img/portfolio/test.webp")
    restored = pickle.loads(pickle.dumps(payload))
    page = page_namespace(restored)

    assert page.total == 1
    assert page.items[0].title == "Birinchi loyiha"
    assert page.items[0].technologies == "Flask, JS"
    assert page.items[0]._resolved_img.endswith("test.webp")
    assert restored["json_items"][0]["technologies"] == ["Flask", "JS"]


def test_blog_page_payload_is_picklable(app):
    _seed()
    pagination = Post.query.paginate(page=1, per_page=10, error_out=False)

    payload = blog_page(pagination, Post.query.all())
    restored = pickle.loads(pickle.dumps(payload))
    page = page_namespace(restored)

    assert page.items[0].slug == "birinchi-post"
    assert page.items[0].views == 7
    assert item_namespaces(restored["popular"])[0].title == "Birinchi post"


def test_portfolio_route_renders_from_pickled_cache(app, monkeypatch):
    _seed()
    store = _pickle_cache(monkeypatch, portfolio_routes)
    client = app.test_client()

    first = client.get("/portfolio")
    assert first.status_code == 200
    assert store, "portfolio keshga yozilmadi"

    second = client.get("/portfolio")
    assert second.status_code == 200
    assert "Birinchi loyiha".encode() in second.data
    assert b"portfolios-data" in second.data


def test_blog_route_renders_from_pickled_cache(app, monkeypatch):
    _seed()
    store = _pickle_cache(monkeypatch, blog_routes)
    client = app.test_client()

    first = client.get("/blog")
    assert first.status_code == 200
    assert store, "blog keshga yozilmadi"

    second = client.get("/blog")
    assert second.status_code == 200
    assert "Birinchi post".encode() in second.data


def test_cache_delete_prefix_removes_only_matching_keys():
    cache_set("pytest-prefix:a", 1, ttl=60)
    cache_set("pytest-prefix:b", 2, ttl=60)
    cache_set("pytest-other:c", 3, ttl=60)

    try:
        cache_delete_prefix("pytest-prefix:")

        assert cache_get("pytest-prefix:a") is None
        assert cache_get("pytest-prefix:b") is None
        assert cache_get("pytest-other:c") == 3
    finally:
        cache_delete("pytest-other:c")


def test_portfolio_detail_db_error_redirects_instead_of_500(app, monkeypatch):
    class BrokenQuery:
        def filter_by(self, *args, **kwargs):
            raise RuntimeError("baza yo'q")

    class BrokenPortfolio:
        query = BrokenQuery()

    monkeypatch.setattr(portfolio_routes, "Portfolio", BrokenPortfolio)

    response = app.test_client().get("/portfolio/project/mavjud-emas")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/portfolio")
