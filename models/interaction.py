from datetime import datetime
from extensions import db


class PushSubscription(db.Model):
    """Web Push obunachilari"""
    __tablename__ = 'push_subscription'

    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<PushSubscription {self.id}>'

    def to_json(self):
        return {
            'endpoint': self.endpoint,
            'keys': {
                'p256dh': self.p256dh,
                'auth': self.auth,
            },
        }


class Lead(db.Model):
    """Lead Magnet va Chatbot orqali yig'ilgan sovuq klientlar (bazamiz)"""
    __tablename__ = 'lead'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)  # tel yoki telegram username
    source = db.Column(db.String(50), default='Lead Magnet')  # Lead Magnet, AI Chat, etc
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Lead {self.id} - {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact': self.contact,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
