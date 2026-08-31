import pytest
from app import create_app
from extensions import db
from models.post import Post
from models.order import Order

@pytest.fixture
def app():
    # Test uchun ilova muhiti (in-memory bazasi bilan)
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

def test_post_slug_generation(app):
    with app.app_context():
        # Yangi post yaratamiz
        post = Post(title="O'zbekistonda AI", content="...", topic="AI", category="Tech")
        db.session.add(post)
        db.session.commit()
        
        post.slug = post.generate_slug()
        # slugify o'zbek tilidagi O' ni o-zbekistonda-ai kabi qilishi mumkin
        assert "zbekistonda-ai" in post.slug

def test_post_reading_time_calculation(app):
    with app.app_context():
        # Uzoq matn (200 ta so'z)
        long_content = "soz " * 200
        post = Post(title="Test", content=long_content)
        reading_time = post.calculate_reading_time()
        # TrendoAI 200 ta so'zni qancha hisoblashiga qarab: (200/200 = 1 minut bo'lishi mumkin)
        assert reading_time == 1

def test_order_creation(app):
    with app.app_context():
        order = Order(
            name="Ali Valiyev", 
            phone="+998901234567", 
            service="ai_bot",       # Majburiy qator qo'shildi
            service_name="AI Chatbot",
            message="Bizga shoshilinch kerak",
            status="new"
        )
        db.session.add(order)
        db.session.commit()
        
        saved_order = Order.query.first()
        assert saved_order.name == "Ali Valiyev"
        assert saved_order.service == "ai_bot"
