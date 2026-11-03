"""
Google Search Console & IndexNow Auto-Indexing Helper for TrendoAI.
Supports IndexNow (Bing, Yandex, Seznam) and Google Sitemap Ping.
"""

import os
import re
import threading
import requests
from config import SITE_URL
from utils.logger import setup_logger
logger = setup_logger("seo_indexer")


# IndexNow spetsifikatsiyasi kalitga faqat [a-zA-Z0-9-] va 8-128 belgi ruxsat beradi.
# Eski qiymat ("trendoai_indexnow_key_2026") pastki chiziq tutgani uchun
# spetsifikatsiyaga mos emas edi va submission rad etilishi mumkin edi.
DEFAULT_INDEXNOW_KEY = "trendoai-indexnow-2026"
INDEXNOW_KEY_PATTERN = re.compile(r"[A-Za-z0-9-]{8,128}")

_raw_indexnow_key = (os.getenv("INDEXNOW_KEY") or DEFAULT_INDEXNOW_KEY).strip()
if INDEXNOW_KEY_PATTERN.fullmatch(_raw_indexnow_key):
    INDEXNOW_KEY = _raw_indexnow_key
else:
    logger.info(
        f"[seo_indexer] INDEXNOW_KEY='{_raw_indexnow_key}' spetsifikatsiyaga mos emas "
        f"(faqat A-Z a-z 0-9 - va 8-128 belgi), '{DEFAULT_INDEXNOW_KEY}' ishlatiladi."
    )
    INDEXNOW_KEY = DEFAULT_INDEXNOW_KEY


def get_indexnow_key():
    return INDEXNOW_KEY


def _async_ping(urls):
    """Background thread handler for search engine indexing pings."""
    if not urls:
        return

    if isinstance(urls, str):
        urls = [urls]

    site_host = SITE_URL.replace("https://", "").replace("http://", "").strip("/")
    key_location = f"{SITE_URL}/{INDEXNOW_KEY}.txt"

    # 1. IndexNow API Ping (Bing, Yandex, Naver, Seznam)
    try:
        indexnow_payload = {
            "host": site_host,
            "key": INDEXNOW_KEY,
            "keyLocation": key_location,
            "urlList": urls,
        }
        res = requests.post(
            "https://api.indexnow.org/indexnow",
            json=indexnow_payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=5,
        )
        logger.info(f"[seo_indexer] IndexNow ping status: {res.status_code} for {len(urls)} URLs")
    except Exception as exc:
        logger.error(f"[seo_indexer] IndexNow ping failed: {exc}")

    # Google sitemap ping endpoint'i (google.com/ping?sitemap=) 2024-yil yanvarda
    # butunlay o'chirilgan — chaqiruv 404 qaytarardi va status log'i chalg'itardi.
    # Google uchun sitemap robots.txt orqali va Search Console'da e'lon qilinadi.


def ping_search_engines(urls):
    """Trigger background indexing ping for given URL or list of URLs."""
    thread = threading.Thread(target=_async_ping, args=(urls,), daemon=True)
    thread.start()
    return True
