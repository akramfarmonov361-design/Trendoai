# telegram_poster.py
"""
Telegram kanaliga xabar yuborish moduli.
TrendoAI uchun moslashtirilgan.
"""
import os
import time
import requests
from config import (
    TELEGRAM_BOT_TOKEN, 
    TELEGRAM_CHANNEL_ID, 
    TELEGRAM_ADMIN_ID,
    TELEGRAM_MAX_MESSAGE_LENGTH,
    TELEGRAM_RETRY_ATTEMPTS
)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def _truncate_message(message, max_length=TELEGRAM_MAX_MESSAGE_LENGTH):
    """Xabarni maksimal uzunlikka qisqartiradi."""
    if len(message) <= max_length:
        return message
    
    truncated = message[:max_length - 50]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + "\n\n... (davomi saytda)"


def send_to_telegram_channel(message, parse_mode="Markdown"):
    """
    Telegram kanaliga xabar yuboradi.
    
    Args:
        message: Yuboriladigan xabar matni
        parse_mode: Formatlash turi ("Markdown" yoki "HTML")
        
    Returns:
        bool: Muvaffaqiyatli yuborildi yoki yo'q
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("❌ Xato: Telegram token yoki kanal ID'si topilmadi.")
        print("   .env faylda TELEGRAM_BOT_TOKEN va TELEGRAM_CHANNEL_ID ni tekshiring.")
        return False
    
    message = _truncate_message(message)
    
    payload = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': message,
        'parse_mode': parse_mode,
        'disable_web_page_preview': False
    }
    
    last_error = None
    
    for attempt in range(TELEGRAM_RETRY_ATTEMPTS):
        try:
            response = requests.post(TELEGRAM_API_URL, data=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Xabar TrendoAI kanalga muvaffaqiyatli yuborildi.")
                return True
            
            error_data = response.json()
            error_description = error_data.get('description', 'Noma\'lum xato')
            
            if 'parse entities' in error_description.lower():
                print(f"⚠️ Markdown xatosi. Oddiy text sifatida yuborilmoqda...")
                payload['parse_mode'] = None
                continue
            
            print(f"❌ Telegram xatosi: {error_description}")
            last_error = error_description
            
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout xatosi (urinish {attempt + 1}/{TELEGRAM_RETRY_ATTEMPTS})")
            last_error = "Timeout"
            
        except requests.exceptions.RequestException as e:
            print(f"🔌 Tarmoq xatosi (urinish {attempt + 1}/{TELEGRAM_RETRY_ATTEMPTS}): {e}")
            last_error = str(e)
        
        if attempt < TELEGRAM_RETRY_ATTEMPTS - 1:
            wait_time = 2 * (attempt + 1)
            print(f"   ⏳ {wait_time} soniya kutilmoqda...")
            time.sleep(wait_time)
    
    print(f"❌ Barcha urinishlar muvaffaqiyatsiz. Oxirgi xato: {last_error}")
    return False


def send_photo_to_channel(photo_url, caption=""):
    """Telegram kanaliga rasm yuboradi."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("❌ Xato: Telegram sozlamalari topilmadi.")
        return False
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    payload = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'photo': photo_url,
        'caption': _truncate_message(caption, 1024),
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(api_url, data=payload, timeout=30)
        if response.status_code == 200:
            print("✅ Rasm TrendoAI kanalga muvaffaqiyatli yuborildi.")
            return True
        else:
            print(f"❌ Rasm yuborishda xato: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Rasm yuborishda xato: {e}")
        return False



def send_admin_alert(message, parse_mode="HTML"):
    """
    Tizimdagi krizis holatlar va xatoliklarni bevosita Adminga yuborish.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_ID:
        print("❌ Xato: Telegram token yoki Admin ID topilmadi.")
        return False
    
    # Xabarni qisqartirish
    message = _truncate_message(str(message))
    
    payload = {
        'chat_id': TELEGRAM_ADMIN_ID,
        'text': f"🚨 <b>TrendoAI Tizim Xabari</b>\n\n{message}",
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(TELEGRAM_API_URL, data=payload, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Alert(ogohlantirish) Adminga muvaffaqiyatli yuborildi.")
            return True
        else:
            print(f"❌ Adminga alert yuborishda xato: {response.text}")
            return False
            
    except Exception as e:
        print(f"🔌 Alert yuborishda tarmoq xatosi: {e}")
        return False



def send_portfolio_to_channel(portfolio_item):
    """
    Portfolio loyihasini Telegram kanalga yuborish.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("❌ Xato: Telegram sozlamalari topilmadi.")
        return False

    # Formatlash
    emoji = portfolio_item.emoji or "🚀"
    title = portfolio_item.title
    description = portfolio_item.description
    
    # Texnologiyalar
    tech_tags = ""
    if portfolio_item.technologies:
        tech_list = [t.strip() for t in portfolio_item.technologies.split(',')]
        tech_tags = " | ".join([f"#{t.replace(' ', '')}" for t in tech_list])

    # Kategoriya (hashtag)
    category_tag = f"#{portfolio_item.category}" if portfolio_item.category else ""
    
    # Havola
    link_text = ""
    if portfolio_item.link:
        link_text = f"\n🔗 [Loyihani ko'rish]({portfolio_item.link})"
    
    # Saytdagi batafsil havola
    site_link = f"https://trendoai.uz/portfolio/project/{portfolio_item.slug}" if portfolio_item.slug else "https://trendoai.uz/portfolio"

    caption = f"""{emoji} *Yangi Loyiha: {title}*

{description}

🛠 *Texnologiyalar:*
{tech_tags}

🏷 {category_tag} #TrendoAI

👉 [Batafsil ma'lumot]({site_link}){link_text}"""

    # Rasm bilan yuborish
    if portfolio_item.image_url:
        return send_photo_to_channel(portfolio_item.image_url, caption)
    else:
        return send_to_telegram_channel(caption)


# Test uchun
if __name__ == '__main__':
    print("=" * 60)
    print("🔥 TrendoAI — Telegram Poster Test")
    print("=" * 60)
    
    test_message = """
🔥 *Salom Dunyo!*

Bu `TrendoAI` dan test xabari.

✅ Retry mehanizmi ishlaydi
✅ Xabar uzunligi tekshiriladi
✅ Xatolar boshqariladi

#test #TrendoAI
"""
    
    print("\n📤 Test xabari yuborilmoqda...")
    result = send_to_telegram_channel(test_message)
    
    if result:
        print("\n✅ Test muvaffaqiyatli!")
    else:
        print("\n❌ Test muvaffaqiyatsiz. .env faylni tekshiring.")