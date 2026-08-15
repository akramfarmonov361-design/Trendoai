import json
from extensions import db


class Service(db.Model):
    """Xizmatlar modeli"""
    __tablename__ = 'service'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    full_description = db.Column(db.Text)
    price = db.Column(db.String(100))
    icon = db.Column(db.String(50))
    image_url = db.Column(db.String(500))
    features = db.Column(db.Text)  # JSON string sifatida saqlanadi
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    meta_desc = db.Column(db.String(300))
    discount_percent = db.Column(db.Integer, default=0)
    discount_until = db.Column(db.String(50))

    def __repr__(self):
        return f'<Service {self.title}>'

    def get_features_list(self):
        if not self.features:
            return []
        try:
            return json.loads(self.features)
        except Exception:
            return [f.strip() for f in self.features.split(',') if f.strip()]
