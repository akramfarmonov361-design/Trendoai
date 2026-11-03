# seo_indexer.py — backward compatibility module alias
# Haqiqiy modul services/seo_indexer.py da joylashgan.
import sys
import services.seo_indexer

# sys.modules dagi bitta instansiyaga yo'naltirish
sys.modules[__name__] = services.seo_indexer
