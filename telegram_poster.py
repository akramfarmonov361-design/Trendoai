"""
Telegram channel posting helpers for TrendoAI.
"""

import time
import requests

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    TELEGRAM_ADMIN_ID,
    TELEGRAM_MAX_MESSAGE_LENGTH,
    TELEGRAM_RETRY_ATTEMPTS,
)


def _clean_env_value(value):
    """Strip whitespace and optional wrapping quotes from env values."""
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ("'", '"'):
        cleaned = cleaned[1:-1].strip()

    return cleaned or None


BOT_TOKEN = _clean_env_value(TELEGRAM_BOT_TOKEN)
CHANNEL_ID = _clean_env_value(TELEGRAM_CHANNEL_ID)
ADMIN_ID = _clean_env_value(TELEGRAM_ADMIN_ID)


def _telegram_api_url(method):
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


def _extract_error_description(response):
    try:
        data = response.json()
        if isinstance(data, dict):
            return data.get("description", "Unknown Telegram error")
    except Exception:
        pass
    return response.text or "Unknown Telegram error"


def _truncate_message(message, max_length=TELEGRAM_MAX_MESSAGE_LENGTH):
    """Trim text to Telegram length limits with a readable suffix."""
    message = str(message or "")
    if len(message) <= max_length:
        return message

    suffix = "\n\n... (davomi saytda)"
    truncated = message[: max_length - len(suffix)]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated + suffix


def _is_parse_error(description):
    text = (description or "").lower()
    return "parse entities" in text or "can't parse" in text


def _is_photo_url_error(description):
    text = (description or "").lower()
    indicators = [
        "failed to get http url content",
        "wrong file identifier/http url specified",
        "webpage media empty",
        "type of the web page content",
        "file is too big",
        "image_process_failed",
        "photo_invalid_dimensions",
    ]
    return any(indicator in text for indicator in indicators)


def _send_text(chat_id, message, parse_mode="Markdown", disable_web_page_preview=False, chat_label="chat"):
    """Send a text message with retry and parse-mode fallback."""
    if not BOT_TOKEN or not chat_id:
        print(f"[telegram] Missing BOT_TOKEN or {chat_label} id.")
        return False

    payload_base = {
        "chat_id": chat_id,
        "text": _truncate_message(message),
        "disable_web_page_preview": disable_web_page_preview,
    }

    parse_candidates = [parse_mode] if parse_mode else [None]
    if parse_mode is not None:
        parse_candidates.append(None)

    last_error = None

    for candidate_parse_mode in parse_candidates:
        payload = dict(payload_base)
        if candidate_parse_mode:
            payload["parse_mode"] = candidate_parse_mode

        for attempt in range(TELEGRAM_RETRY_ATTEMPTS):
            try:
                response = requests.post(_telegram_api_url("sendMessage"), data=payload, timeout=30)
            except requests.exceptions.Timeout:
                last_error = "Timeout"
                print(f"[telegram] Timeout sending to {chat_label} ({attempt + 1}/{TELEGRAM_RETRY_ATTEMPTS})")
            except requests.exceptions.RequestException as exc:
                last_error = str(exc)
                print(f"[telegram] Network error sending to {chat_label} ({attempt + 1}/{TELEGRAM_RETRY_ATTEMPTS}): {exc}")
            else:
                if response.status_code == 200:
                    print(f"[telegram] Message sent to {chat_label}.")
                    return True

                description = _extract_error_description(response)
                last_error = description

                if _is_parse_error(description) and candidate_parse_mode is not None:
                    print("[telegram] Parse error detected, retrying without parse_mode.")
                    break

                print(f"[telegram] API error sending to {chat_label}: {description}")

            if attempt < TELEGRAM_RETRY_ATTEMPTS - 1:
                wait_time = 2 * (attempt + 1)
                time.sleep(wait_time)

    print(f"[telegram] Failed to send message to {chat_label}. Last error: {last_error}")
    return False


def send_to_telegram_channel(message, parse_mode="Markdown"):
    """Send text message to Telegram channel."""
    return _send_text(
        chat_id=CHANNEL_ID,
        message=message,
        parse_mode=parse_mode,
        disable_web_page_preview=False,
        chat_label="channel",
    )


def send_photo_to_channel(photo_url, caption=""):
    """Send photo + caption to Telegram channel with robust fallback behavior."""
    if not BOT_TOKEN or not CHANNEL_ID:
        print("[telegram] Missing BOT_TOKEN or CHANNEL_ID.")
        return False

    if not photo_url:
        print("[telegram] photo_url is empty, sending text only.")
        return send_to_telegram_channel(caption)

    caption = _truncate_message(caption, 1024)
    last_error = None

    parse_candidates = ["Markdown", None]
    for candidate_parse_mode in parse_candidates:
        payload = {
            "chat_id": CHANNEL_ID,
            "photo": photo_url,
            "caption": caption,
        }
        if candidate_parse_mode:
            payload["parse_mode"] = candidate_parse_mode

        for attempt in range(TELEGRAM_RETRY_ATTEMPTS):
            try:
                response = requests.post(_telegram_api_url("sendPhoto"), data=payload, timeout=30)
            except requests.exceptions.Timeout:
                last_error = "Timeout"
                print(f"[telegram] Photo send timeout ({attempt + 1}/{TELEGRAM_RETRY_ATTEMPTS})")
            except requests.exceptions.RequestException as exc:
                last_error = str(exc)
                print(f"[telegram] Photo send network error ({attempt + 1}/{TELEGRAM_RETRY_ATTEMPTS}): {exc}")
            else:
                if response.status_code == 200:
                    print("[telegram] Photo sent to channel.")
                    return True

                description = _extract_error_description(response)
                last_error = description

                if _is_parse_error(description) and candidate_parse_mode is not None:
                    print("[telegram] Photo caption parse error, retrying without parse_mode.")
                    break

                if _is_photo_url_error(description):
                    print("[telegram] Photo URL failed, falling back to text message.")
                    return send_to_telegram_channel(caption)

                print(f"[telegram] Photo send API error: {description}")

            if attempt < TELEGRAM_RETRY_ATTEMPTS - 1:
                wait_time = 2 * (attempt + 1)
                time.sleep(wait_time)

    print(f"[telegram] Failed to send photo. Last error: {last_error}")
    print("[telegram] Falling back to text message.")
    return send_to_telegram_channel(caption)


def send_admin_alert(message, parse_mode="HTML"):
    """Send system alerts directly to admin chat."""
    if parse_mode == "HTML":
        prefixed_message = f"<b>TrendoAI tizim xabari</b>\n\n{message}"
    else:
        prefixed_message = f"TrendoAI tizim xabari\n\n{message}"

    return _send_text(
        chat_id=ADMIN_ID,
        message=prefixed_message,
        parse_mode=parse_mode,
        disable_web_page_preview=True,
        chat_label="admin",
    )


def send_to_admin(message, parse_mode="Markdown"):
    """Backward-compatible helper used by app.py order flow."""
    return _send_text(
        chat_id=ADMIN_ID,
        message=message,
        parse_mode=parse_mode,
        disable_web_page_preview=True,
        chat_label="admin",
    )


def send_portfolio_to_channel(portfolio_item):
    """Send portfolio item to Telegram channel."""
    if not BOT_TOKEN or not CHANNEL_ID:
        print("[telegram] Missing Telegram configuration for portfolio posting.")
        return False

    emoji = portfolio_item.emoji or "🚀"
    title = portfolio_item.title
    description = portfolio_item.description

    tech_tags = ""
    if portfolio_item.technologies:
        tech_list = [item.strip() for item in portfolio_item.technologies.split(",") if item.strip()]
        if tech_list:
            tech_tags = " | ".join([f"#{item.replace(' ', '')}" for item in tech_list])

    category_tag = f"#{portfolio_item.category}" if portfolio_item.category else ""

    link_text = ""
    if portfolio_item.link:
        link_text = f"\n🔗 [Loyihani ko'rish]({portfolio_item.link})"

    site_link = (
        f"https://trendoai.uz/portfolio/project/{portfolio_item.slug}"
        if portfolio_item.slug
        else "https://trendoai.uz/portfolio"
    )

    caption = (
        f"{emoji} *Yangi loyiha: {title}*\n\n"
        f"{description}\n\n"
        f"🛠 *Texnologiyalar:*\n"
        f"{tech_tags or '-'}\n\n"
        f"🏷 {category_tag} #TrendoAI\n\n"
        f"👉 [Batafsil ma'lumot]({site_link}){link_text}"
    )

    if portfolio_item.image_url:
        return send_photo_to_channel(portfolio_item.image_url, caption)
    return send_to_telegram_channel(caption)


if __name__ == "__main__":
    print("=" * 60)
    print("TrendoAI Telegram Poster Test")
    print("=" * 60)

    test_message = (
        "Salom!\\n\\n"
        "Bu TrendoAI test xabari.\\n"
        "#test #TrendoAI"
    )

    print("Testing send_to_telegram_channel...")
    result = send_to_telegram_channel(test_message)
    print("OK" if result else "FAILED")
