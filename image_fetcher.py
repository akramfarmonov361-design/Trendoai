# image_fetcher.py
"""
Unsplash API orqali mavzuga mos rasm olish.
TrendoAI uchun moslashtirilgan.
"""
import os
import random
import re
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"


def _extract_unsplash_photo_id(image_url):
    """Extract Unsplash photo id from a stored image URL."""
    if not image_url:
        return None

    try:
        host = urlparse(image_url).netloc.lower()
        if "unsplash.com" not in host:
            return None

        match = re.search(r"photo-([A-Za-z0-9_-]+)", image_url)
        if match:
            return match.group(1)
    except Exception:
        return None

    return None


def _build_excluded_unsplash_ids(exclude_image_urls):
    excluded_ids = set()
    if not exclude_image_urls:
        return excluded_ids

    for url in exclude_image_urls:
        photo_id = _extract_unsplash_photo_id(url)
        if photo_id:
            excluded_ids.add(photo_id)

    return excluded_ids


def build_image_prompt(topic, title=None, category=None):
    """Create an editable image generation prompt for a blog post."""
    topic_text = (topic or "technology").strip()
    title_text = (title or "").strip()
    category_text = (category or "").strip()

    focus_parts = [part for part in [title_text, topic_text, category_text] if part]
    focus = ", ".join(focus_parts[:2]) if focus_parts else "technology"

    return (
        f"Professional editorial hero image about {focus}. "
        "Photorealistic, modern, high detail, cinematic lighting, 16:9 composition. "
        "Clean background, no people unless necessary, no text, no watermark, no logo."
    )


def get_image_for_topic(topic, width=1200, height=630, exclude_image_urls=None):
    """
    Berilgan mavzu bo'yicha Unsplash'dan rasm URL'ini oladi.

    Args:
        topic: Qidiruv so'zi (masalan, "artificial intelligence")
        width: Rasm kengligi
        height: Rasm balandligi
        exclude_image_urls: oldin ishlatilgan URL ro'yxati

    Returns:
        str: Rasm URL'i yoki fallback URL
    """
    if not UNSPLASH_ACCESS_KEY:
        print("[image] UNSPLASH_ACCESS_KEY topilmadi")
        return get_fallback_image(topic)

    excluded_ids = _build_excluded_unsplash_ids(exclude_image_urls)

    topic_keywords = {
        "sun'iy intellekt": "artificial intelligence",
        "ai": "artificial intelligence",
        "dasturlash": "programming code",
        "python": "python programming",
        "texnologiya": "technology",
        "telegram": "messaging app",
        "web": "web development",
        "mobile": "mobile app",
        "kiberxavfsizlik": "cybersecurity",
        "startap": "startup business",
        "biznes": "business",
        "robot": "robotics",
        "cloud": "cloud computing",
        "data": "data science",
        "blockchain": "blockchain",
        "iot": "internet of things",
    }

    search_query = "technology"
    topic_lower = (topic or "").lower()

    for uz_word, en_word in topic_keywords.items():
        if uz_word in topic_lower:
            search_query = en_word
            break

    try:
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        params = {
            "query": search_query,
            "per_page": 30,
            "orientation": "landscape",
        }

        response = requests.get(UNSPLASH_API_URL, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get("results") or []
            if results:
                available_results = [
                    photo for photo in results
                    if photo.get("id") not in excluded_ids
                ]

                if not available_results:
                    print("[image] Topilgan Unsplash rasmlari allaqachon ishlatilgan")
                    return get_fallback_image(topic)

                photo = random.choice(available_results)
                raw_url = (photo.get("urls") or {}).get("raw")
                if raw_url:
                    sized_url = f"{raw_url}&w={width}&h={height}&fit=crop&q=80"
                    print(f"[image] Rasm topildi: {search_query}")
                    return sized_url

        print(f"[image] Unsplash javob: {response.status_code}")
        return get_fallback_image(topic)

    except Exception as e:
        print(f"[image] Unsplash xatosi: {e}")
        return get_fallback_image(topic)


def get_fallback_image(topic):
    """
    Unsplash ishlamasa, Picsum yordamida random rasm qaytaradi.
    """
    random_id = random.randint(1, 1000)
    return f"https://picsum.photos/seed/{random_id}/1200/630"


def get_category_image(category):
    """
    Kategoriya bo'yicha standart rasm URL'ini qaytaradi.
    """
    category_images = {
        "Texnologiya": "technology",
        "Sun'iy Intellekt": "artificial intelligence robot",
        "Dasturlash": "programming code",
        "Biznes": "business office",
        "Startaplar": "startup team",
        "Kiberxavfsizlik": "cybersecurity lock",
        "Mobile": "mobile phone app",
        "Web": "web design laptop",
    }

    search_term = category_images.get(category, "technology")
    return get_image_for_topic(search_term)


if __name__ == "__main__":
    print("Testing Unsplash API...")
    url = get_image_for_topic("sun'iy intellekt")
    print(f"Result: {url}")
