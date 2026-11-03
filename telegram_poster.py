# telegram_poster.py — backward compatibility module alias
# Haqiqiy modul services/telegram_poster.py da joylashgan.
import sys
import services.telegram_poster

# sys.modules dagi bitta instansiyaga yo'naltirish
sys.modules[__name__] = services.telegram_poster
