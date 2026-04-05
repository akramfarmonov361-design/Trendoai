from app import app, db, MenuCategory, MenuItem

def init_demo_db():
    with app.app_context():
        # Jadvallarni yaratish (yangi qo'shilganlari uchun)
        db.create_all()
        
        # Kategoriyalar mavjudligini tekshirish
        if MenuCategory.query.count() == 0:
            print("Demo kategoriyalar qo'shilmoqda...")
            c1 = MenuCategory(name="Fast Food", emoji="🍔", order_index=1)
            c2 = MenuCategory(name="Ichimliklar", emoji="🥤", order_index=2)
            c3 = MenuCategory(name="IT Xizmatlar", emoji="💻", order_index=3)
            db.session.add_all([c1, c2, c3])
            db.session.commit()
            
            print("Demo mahsulotlar qo'shilmoqda...")
            m1 = MenuItem(name="Cheeseburger", description="Mol go'shtli mazzali burger", price=25000, category="Fast Food", emoji="🍔", order_index=1)
            m2 = MenuItem(name="Pepperoni Pizza", description="Katta o'lchamli pitsa", price=75000, category="Fast Food", emoji="🍕", order_index=2)
            m3 = MenuItem(name="Coca Cola 1L", description="Yaxna ichimlik", price=12000, category="Ichimliklar", emoji="🥤", order_index=1)
            m4 = MenuItem(name="Web Sayt Yaratish", description="Landing page yoki korporativ sayt", price=1500000, category="IT Xizmatlar", emoji="🌐", order_index=1)
            m5 = MenuItem(name="Telegram Bot", description="Sotuv uchun tayyor bot", price=800000, category="IT Xizmatlar", emoji="🤖", order_index=2)
            
            db.session.add_all([m1, m2, m3, m4, m5])
            db.session.commit()
            print("To'liq muvaffaqiyatli yakunlandi!")
        else:
            print("Bazaga allaqachon ma'lumot kiritilgan.")

if __name__ == '__main__':
    init_demo_db()
