import re
import markdown2
from extensions import db


class Portfolio(db.Model):
    """Portfolio loyihalar modeli (SEO-optimized)"""
    __tablename__ = 'portfolio'
    __table_args__ = (
        db.Index('ix_portfolio_published_created', 'is_published', 'created_at'),
        db.Index('ix_portfolio_category_published_created', 'category', 'is_published', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='web')
    emoji = db.Column(db.String(10), default='🚀')
    technologies = db.Column(db.String(250))
    link = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    is_featured = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=True)
    meta_description = db.Column(db.Text)
    meta_keywords = db.Column(db.String(250))
    details = db.Column(db.Text)
    features = db.Column(db.Text)
    price = db.Column(db.String(100), nullable=True)
    client_name = db.Column(db.String(100), nullable=True)
    problem = db.Column(db.Text, nullable=True)
    solution = db.Column(db.Text, nullable=True)
    result = db.Column(db.Text, nullable=True)
    demo_url = db.Column(db.String(500), nullable=True)
    gallery_images = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @property
    def safe_price(self):
        """Safely get price"""
        try:
            return self.price or ''
        except Exception:
            return ''

    def __repr__(self):
        return f'<Portfolio {self.title}>'

    def generate_slug(self):
        """URL uchun slug yaratish"""
        slug = (self.title or '').lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        return f"{slug}-{self.id}"

    def to_dict(self):
        details = getattr(self, 'details', None) or ''
        features = getattr(self, 'features', None) or ''
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'category': self.category,
            'emoji': self.emoji,
            'technologies': [t.strip() for t in self.technologies.split(',')] if self.technologies else [],
            'link': self.link,
            'image_url': self.image_url,
            'is_featured': self.is_featured,
            'details': details,
            'details_html': markdown2.markdown(details) if details else "",
            'features': [f.strip() for f in features.split(',')] if features else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
