"""
TrendoAI markazlashtirilgan kengaytmalar (Flask Extensions) moduli.
Sirkulyar importlarning oldini olish uchun kengaytmalar shu yerda yaratiladi.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

try:
    from flask_migrate import Migrate
    migrate = Migrate()
except ImportError:
    migrate = None

db = SQLAlchemy()
csrf = CSRFProtect()
