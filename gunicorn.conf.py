# gunicorn.conf.py
# TrendoAI uchun Gunicorn konfiguratsiya fayli
# APScheduler to'g'ri ishlashi uchun preload_app = True

import os

workers = 1          # Bitta worker — scheduler ikkilanishi oldini olish
threads = 8          # 8 ta thread (async vazifalar uchun)

# gthread worker'da heartbeat asosiy tsikldan yuboriladi, shuning uchun uzoq
# davom etuvchi AI so'rovi worker'ni o'ldirmaydi. timeout=0 esa osilib qolgan
# worker'ni umuman qayta ishga tushirmasdi — sekin-asta 8 ta thread tugab,
# xizmat javob bermay qolardi.
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
graceful_timeout = 30
preload_app = False  # Ilova worker darajasida yuklanadi, bu timeout xatolarining oldini oladi
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
