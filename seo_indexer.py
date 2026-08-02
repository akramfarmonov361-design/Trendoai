"""
Google Search Console & IndexNow Auto-Indexing Helper for TrendoAI.
Supports IndexNow (Bing, Yandex, Seznam) and Google Sitemap Ping.
"""

import json
import threading
import requests
from config import SITE_URL

INDEXNOW_KEY = "trendoai_indexnow_key_2026"


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
        print(f"[seo_indexer] IndexNow ping status: {res.status_code} for {len(urls)} URLs")
    except Exception as exc:
        print(f"[seo_indexer] IndexNow ping failed: {exc}")

    # 2. Google Sitemap Ping
    try:
        sitemap_url = f"{SITE_URL}/sitemap.xml"
        google_ping_url = f"https://www.google.com/ping?sitemap={sitemap_url}"
        res = requests.get(google_ping_url, timeout=5)
        print(f"[seo_indexer] Google sitemap ping status: {res.status_code}")
    except Exception as exc:
        print(f"[seo_indexer] Google sitemap ping failed: {exc}")


def ping_search_engines(urls):
    """Trigger background indexing ping for given URL or list of URLs."""
    thread = threading.Thread(target=_async_ping, args=(urls,), daemon=True)
    thread.start()
    return True
