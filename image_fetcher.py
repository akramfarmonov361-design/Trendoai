# image_fetcher.py
"""
Unsplash API orqali mavzuga mos rasm olish.
TrendoAI uchun moslashtirilgan.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"


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


def get_image_for_topic(topic, width=1200, height=630):
    """
    Berilgan mavzu bo'yicha Unsplash'dan rasm URL'ini oladi.
    
    Args:
        topic: Qidiruv so'zi (masalan, "artificial intelligence")
        width: Rasm kengligi
        height: Rasm balandligi
        
    Returns:
        str: Rasm URL'i yoki None
    """
    if not UNSPLASH_ACCESS_KEY:
        print("⚠️ UNSPLASH_ACCESS_KEY topilmadi!")
        return get_fallback_image(topic)
    
    # Mavzuni inglizchaga tarjima qilish uchun kalit so'zlar
    topic_keywords = {
        'sun\'iy intellekt': 'artificial intelligence',
        'ai': 'artificial intelligence',
        'dasturlash': 'programming code',
        'python': 'python programming',
        'texnologiya': 'technology',
        'telegram': 'messaging app',
        'web': 'web development',
        'mobile': 'mobile app',
        'kiberxavfsizlik': 'cybersecurity',
        'startap': 'startup business',
        'biznes': 'business',
        'robot': 'robotics',
        'cloud': 'cloud computing',
        'data': 'data science',
        'blockchain': 'blockchain',
        'iot': 'internet of things',
    }
    
    # Mavzudan kalit so'z ajratib olish
    search_query = "technology"  # default
    topic_lower = topic.lower()
    
    for uz_word, en_word in topic_keywords.items():
        if uz_word in topic_lower:
            search_query = en_word
            break
    
    try:
        headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
        }
        params = {
            "query": search_query,
            "per_page": 10,
            "orientation": "landscape"
        }
        
        response = requests.get(UNSPLASH_API_URL, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                # Random rasm tanlash
                import random
                photo = random.choice(data["results"])
                
                # O'lchamli URL olish
                raw_url = photo["urls"]["raw"]
                sized_url = f"{raw_url}&w={width}&h={height}&fit=crop&q=80"
                
                print(f"✅ Rasm topildi: {search_query}")
                return sized_url
        
        print(f"⚠️ Unsplash javob: {response.status_code}")
        return get_fallback_image(topic)
        
    except Exception as e:
        print(f"❌ Unsplash xatosi: {e}")
        return get_fallback_image(topic)


def get_fallback_image(topic):
    """
    Unsplash ishlamasa, Picsum yordamida random rasm qaytaradi.
    """
    import random
    random_id = random.randint(1, 1000)
    return f"https://picsum.photos/seed/{random_id}/1200/630"


def get_category_image(category):
    """
    Kategoriya bo'yicha standart rasm URL'ini qaytaradi.
    """
    category_images = {
        'Texnologiya': 'technology',
        'Sun\'iy Intellekt': 'artificial intelligence robot',
        'Dasturlash': 'programming code',
        'Biznes': 'business office',
        'Startaplar': 'startup team',
        'Kiberxavfsizlik': 'cybersecurity lock',
        'Mobile': 'mobile phone app',
        'Web': 'web design laptop'
    }
    
    search_term = category_images.get(category, 'technology')
    return get_image_for_topic(search_term)


if __name__ == "__main__":
    # Test
    print("Testing Unsplash API...")
    url = get_image_for_topic("sun'iy intellekt")
    print(f"Result: {url}")
