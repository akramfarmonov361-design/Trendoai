from extensions import db


class Order(db.Model):
    """Xizmatga buyurtma modeli"""
    __tablename__ = 'order'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service = db.Column(db.String(50), nullable=False)
    service_name = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.String(50), nullable=True)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='new')  # new, contacted, in_progress, completed, cancelled
    admin_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Order {self.id} - {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'service': self.service,
            'service_name': self.service_name,
            'budget': self.budget,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class BotOrder(db.Model):
    """Telegram bot orqali kelgan menyu buyurtmalari"""
    __tablename__ = 'bot_order'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True)  # #TRD-0001
    tg_id = db.Column(db.BigInteger, nullable=False)
    tg_username = db.Column(db.String(100))
    customer_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    items_json = db.Column(db.Text)  # JSON: [{"id":1, "name":"...", "qty":2, "price":25000}]
    total_amount = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='new')  # new -> confirmed -> preparing -> delivering -> done / cancelled
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    def __repr__(self):
        return f'<BotOrder {self.order_number or self.id}>'
