import re
from extensions import db


class Post(db.Model):
    """Blog post modeli"""
    __tablename__ = 'post'
    __table_args__ = (
        db.Index('ix_post_published_created', 'is_published', 'created_at'),
        db.Index('ix_post_published_views', 'is_published', 'views'),
        db.Index('ix_post_category_published_created', 'category', 'is_published', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=True)
    content = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Texnologiya')
    keywords = db.Column(db.String(250), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    image_prompt = db.Column(db.Text, nullable=True)
    views = db.Column(db.Integer, default=0)
    reading_time = db.Column(db.Integer, default=5)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    def __repr__(self):
        return f'<Post {self.title}>'

    def calculate_reading_time(self):
        """O'qish vaqtini hisoblash (250 so'z/daqiqa)"""
        word_count = len((self.content or '').split())
        return max(1, round(word_count / 250))

    def generate_slug(self):
        """URL uchun slug yaratish"""
        slug = (self.title or '').lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        return f"{slug}-{self.id}"

    def to_dict(self):
        """API uchun dict formatiga o'tkazish"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'topic': self.topic,
            'category': self.category,
            'keywords': self.keywords,
            'image_prompt': self.image_prompt,
            'views': self.views,
            'reading_time': self.reading_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
