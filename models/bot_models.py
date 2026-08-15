from extensions import db


class TelegramUser(db.Model):
    """Bot bilan muloqot qilgan foydalanuvchilar (marketing uchun)"""
    __tablename__ = 'telegram_user'

    id = db.Column(db.Integer, primary_key=True)
    tg_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=True)
    full_name = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    last_interaction = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f'<TelegramUser {self.tg_id}>'


class MenuCategory(db.Model):
    """Menyu kategoriyalari"""
    __tablename__ = 'menu_category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    emoji = db.Column(db.String(10), default='📋')
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<MenuCategory {self.name}>'


class MenuItem(db.Model):
    """Bot menyu elementlari"""
    __tablename__ = 'menu_item'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)  # so'mda
    category = db.Column(db.String(50), default='taom')
    emoji = db.Column(db.String(10), default='🍽')
    image_url = db.Column(db.String(500))
    is_available = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<MenuItem {self.name}>'
