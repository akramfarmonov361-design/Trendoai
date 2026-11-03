# image_fetcher.py — backward compatibility module alias
# Haqiqiy modul services/image_fetcher.py da joylashgan.
import sys
import services.image_fetcher

# sys.modules dagi bitta instansiyaga yo'naltirish
sys.modules[__name__] = services.image_fetcher
