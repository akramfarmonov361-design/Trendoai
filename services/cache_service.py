"""
TrendoAI Kesh Xizmati (Redis + In-Memory Thread-Safe Fallback).
Agar REDIS_URL berilgan bo'lsa, Redis ishlatiladi.
Aks holda yoki Redis ishlamay qolganda xavfsiz In-Memory keshiga o'tiladi.
"""
import json
import pickle
import threading
import time
from config import REDIS_URL, CACHE_DEFAULT_TIMEOUT
from utils.logger import setup_logger
logger = setup_logger("cache_service")


_redis_client = None
_redis_available = False

if REDIS_URL:
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=False, socket_timeout=2)
        _redis_client.ping()
        _redis_available = True
        logger.info("[cache] Redis ulanishi muvaffaqiyatli!")
    except Exception as exc:
        logger.info(f"[cache] Redis ulanish xatosi (In-Memory rejimga o'tiladi): {exc}")
        _redis_client = None
        _redis_available = False

_IN_MEMORY_CACHE = {}
_IN_MEMORY_LOCK = threading.Lock()
DEFAULT_TTL = CACHE_DEFAULT_TIMEOUT or 60


def get_redis_client():
    """Sog'lom Redis klientini qaytaradi, bo'lmasa ``None``.

    Boshqa xizmatlar Redis mavjudligini ushbu funksiya orqali tekshiradi;
    ular cache modulining ichki holatiga bevosita bog'lanmaydi.
    """
    if _redis_available and _redis_client:
        return _redis_client
    return None


def cache_get(key, is_testing=False):
    """Keshdan qiymatni olish."""
    if is_testing:
        return None

    if _redis_available and _redis_client:
        try:
            data = _redis_client.get(key)
            if data is not None:
                return pickle.loads(data)
        except Exception as e:
            logger.info(f"[cache] Redis get xatosi: {e}")

    with _IN_MEMORY_LOCK:
        entry = _IN_MEMORY_CACHE.get(key)
        if entry is None:
            return None
        stored_at, ttl, value = entry
        if time.time() - stored_at >= ttl:
            _IN_MEMORY_CACHE.pop(key, None)
            return None
        return value


def cache_set(key, value, ttl=None, is_testing=False):
    """Keshga qiymat saqlash."""
    if is_testing:
        return

    effective_ttl = ttl or DEFAULT_TTL

    if _redis_available and _redis_client:
        try:
            _redis_client.setex(key, effective_ttl, pickle.dumps(value))
            return
        except Exception as e:
            logger.info(f"[cache] Redis set xatosi: {e}")

    with _IN_MEMORY_LOCK:
        _IN_MEMORY_CACHE[key] = (time.time(), effective_ttl, value)


def cache_delete(key):
    """Keshdan kalitni o'chirish."""
    if _redis_available and _redis_client:
        try:
            _redis_client.delete(key)
        except Exception:
            pass

    with _IN_MEMORY_LOCK:
        _IN_MEMORY_CACHE.pop(key, None)


def clear_list_cache():
    """Barcha keshni yoki ro'yxat keshini tozalash."""
    if _redis_available and _redis_client:
        try:
            # delete trendo_* or flush
            for k in _redis_client.scan_iter("trendo:*"):
                _redis_client.delete(k)
        except Exception:
            pass

    with _IN_MEMORY_LOCK:
        _IN_MEMORY_CACHE.clear()

# Portfolio ro'yxati va Meta katalog feedi bir xil ma'lumotdan quriladi,
# shuning uchun ular birga eskiradi.
CATALOG_FEED_CACHE_KEY = "meta_catalog_feed_xml"
_PORTFOLIO_CACHE_CATEGORIES = ('', 'bot', 'web', 'ai', 'mobile')
_PORTFOLIO_CACHE_MAX_PAGES = 10


def clear_catalog_cache():
    """Portfolio ro'yxati va Meta katalog feedi keshini tozalaydi.

    Feed bir soatga keshlanadi (``ttl=3600``). Ilgari admin paneldagi
    o'zgarish faqat ``portfolio:*`` kalitlarini tozalardi, feed esa eski
    holicha qolardi — ya'ni loyihaga video yoki rasm qo'shilgach, Meta bir
    soatgacha eski katalogni ko'rar edi. Xizmatlar ham feedga kiradi,
    shuning uchun ular o'zgarganda ham shu funksiya chaqiriladi.
    """
    for category in _PORTFOLIO_CACHE_CATEGORIES:
        for page in range(1, _PORTFOLIO_CACHE_MAX_PAGES):
            cache_delete(f"portfolio:{page}:{category}")
    cache_delete(CATALOG_FEED_CACHE_KEY)
