# gunicorn.conf.py
# TrendoAI uchun Gunicorn konfiguratsiya fayli
# APScheduler to'g'ri ishlashi uchun preload_app = True

import os

workers = 1          # Bitta worker — scheduler ikkilanishi oldini olish
threads = 8          # 8 ta thread (async vazifalar uchun)
timeout = 0          # Timeout yo'q (scheduler uchun kerak)
preload_app = True   # Ilovani oldindan yuklash — scheduler faqat 1 marta ishga tushadi
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
