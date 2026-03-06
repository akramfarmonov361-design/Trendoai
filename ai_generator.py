"""
SEO and marketing content generation helpers for TrendoAI.
"""

import json
import os
import re
import time
from datetime import datetime

import google.generativeai as genai

try:
    from google import genai as google_genai_sdk
    from google.genai import types as google_genai_types
except ImportError:
    google_genai_sdk = None
    google_genai_types = None

from config import (
    AI_RETRY_ATTEMPTS,
    AI_RETRY_DELAY,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_MODEL_BACKUP,
)

GEMINI_API_KEY2 = os.getenv("GEMINI_API_KEY2")

current_api_key = GEMINI_API_KEY
current_model_name = GEMINI_MODEL
realtime_client = None
LAST_AI_ERROR = None

SPECIFIC_MODEL_PATTERN = re.compile(
    r"\b(?:GPT-\d+(?:\.\d+)?(?:\s+[A-Za-z-]+)?|Gemini\s+\d+(?:\.\d+)?(?:\s+[A-Za-z-]+)?|Claude\s+(?:Opus|Sonnet|Haiku)\s*\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


def _set_last_ai_error(message):
    """Store the most recent AI generation error for diagnostics."""
    global LAST_AI_ERROR
    LAST_AI_ERROR = (message or "").strip() or None


def get_last_ai_error():
    return LAST_AI_ERROR


def _refresh_realtime_client(api_key):
    """Initialize the Google Search grounded client when the newer SDK is available."""
    global realtime_client

    realtime_client = None
    if not google_genai_sdk or not api_key:
        return

    try:
        realtime_client = google_genai_sdk.Client(api_key=api_key)
    except Exception as exc:
        print(f"[ai] Grounded Gemini client init failed: {exc}")
        realtime_client = None



def _configure_api(api_key):
    """Configure the legacy SDK and refresh the grounded client."""
    global current_api_key

    if not api_key:
        return False

    genai.configure(api_key=api_key)
    _refresh_realtime_client(api_key)
    current_api_key = api_key
    return True



def _switch_to_backup():
    """Switch to a backup model first, then to a backup API key if available."""
    global current_api_key, current_model_name, model

    if current_model_name != GEMINI_MODEL_BACKUP:
        print(f"[ai] Switching to backup model: {GEMINI_MODEL_BACKUP}")
        current_model_name = GEMINI_MODEL_BACKUP
        model = genai.GenerativeModel(current_model_name)
        return True

    if GEMINI_API_KEY2 and current_api_key != GEMINI_API_KEY2:
        print("[ai] Switching to backup API key: GEMINI_API_KEY2")
        _configure_api(GEMINI_API_KEY2)
        current_model_name = GEMINI_MODEL
        model = genai.GenerativeModel(current_model_name)
        return True

    return False


_configure_api(GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)



def _retry_with_backoff(func, *args, **kwargs):
    """Run a function with exponential backoff and backup model/key fallback."""
    global model
    last_exception = None
    _set_last_ai_error(None)

    for attempt in range(AI_RETRY_ATTEMPTS):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            _set_last_ai_error(str(exc))
            wait_time = AI_RETRY_DELAY * (2 ** attempt)
            print(f"[ai] Error ({attempt + 1}/{AI_RETRY_ATTEMPTS}): {exc}")
            print(f"[ai] Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)

    if _switch_to_backup():
        print("[ai] Retrying with backup configuration...")
        for attempt in range(AI_RETRY_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exception = exc
                _set_last_ai_error(str(exc))
                wait_time = AI_RETRY_DELAY * (2 ** attempt)
                print(f"[ai] Backup error ({attempt + 1}/{AI_RETRY_ATTEMPTS}): {exc}")
                time.sleep(wait_time)

        if _switch_to_backup():
            print("[ai] Retrying with secondary backup configuration...")
            for _ in range(AI_RETRY_ATTEMPTS):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    _set_last_ai_error(str(exc))
                    time.sleep(AI_RETRY_DELAY)

    print(f"[ai] All retries failed. Last error: {last_exception}")
    _set_last_ai_error(f"All retries failed: {last_exception}")
    return None


def _parse_json_response(response_text):
    """Safely extract JSON from a model response."""
    cleaned = (response_text or "").strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"[ai] JSON parse error: {exc}")
        try:
            match = re.search(r"\{.*\}", response_text or "", re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass

        print(f"[ai] Raw response preview: {cleaned[:200]}...")
        return None


def _response_to_text(response):
    """Extract text safely from both legacy and newer Gemini SDK responses."""
    if response is None:
        return ""

    try:
        response_text = getattr(response, "text", None)
        if isinstance(response_text, str) and response_text.strip():
            return response_text.strip()
    except Exception as exc:
        print(f"[ai] Could not read response.text directly: {exc}")

    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return ""

        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []
        collected = []
        for part in parts:
            text_part = getattr(part, "text", None)
            if text_part:
                collected.append(text_part)

        return "\n".join(collected).strip()
    except Exception as exc:
        print(f"[ai] Could not extract response parts: {exc}")
        return ""


def _build_fallback_keywords(topic, title):
    phrases = []
    seen = set()

    for raw in [topic or "", title or ""]:
        for piece in re.split(r"[:,()]+", raw):
            cleaned = re.sub(r"\s+", " ", piece).strip(" -")
            if not cleaned:
                continue

            key = cleaned.lower()
            if key in seen:
                continue

            seen.add(key)
            phrases.append(cleaned)

    for generic in ["AI", "biznes", "texnologiya"]:
        if generic.lower() not in seen:
            phrases.append(generic)
            seen.add(generic.lower())

    return ", ".join(phrases[:5])


def _coerce_post_payload(response_text, topic):
    """Fallback when the model returns Markdown/plain text instead of JSON."""
    body = (response_text or "").strip()
    if not body:
        return None

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return None

    title = None
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break

    if not title:
        title = lines[0].strip("* ").strip()

    if len(body) < 400 or not title:
        return None

    if lines[0].strip("# ").strip() != title:
        body = f"# {title}\n\n{body}"

    return {
        "title": title[:120],
        "keywords": _build_fallback_keywords(topic, title),
        "content": body,
    }


def _should_use_grounding():
    return bool(realtime_client and google_genai_types)



def _generate_grounded_response(prompt):
    """Generate content using Google Search grounding when supported."""
    if not _should_use_grounding():
        return None

    tool = google_genai_types.Tool(google_search=google_genai_types.GoogleSearch())
    config = google_genai_types.GenerateContentConfig(tools=[tool])

    return realtime_client.models.generate_content(
        model=current_model_name,
        contents=prompt,
        config=config,
    )



def _extract_grounding_sources(response):
    """Extract grounded web sources from a grounded Gemini response."""
    sources = []
    seen_urls = set()

    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return sources

        metadata = getattr(candidates[0], "grounding_metadata", None)
        chunks = getattr(metadata, "grounding_chunks", None) or []

        for chunk in chunks:
            web_data = getattr(chunk, "web", None)
            url = getattr(web_data, "uri", None)
            title = getattr(web_data, "title", None)

            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            sources.append(
                {
                    "title": title or url,
                    "url": url,
                }
            )
    except Exception as exc:
        print(f"[ai] Could not extract grounding sources: {exc}")

    return sources



def _add_freshness_note(content, current_date_str):
    note = (
        f"_Ushbu maqola {current_date_str} holatiga ko'ra tayyorlandi. "
        "Tez ozgaradigan versiya, narx va reliz malumotlari vaqt otishi bilan yangilanishi mumkin._"
    )

    body = (content or "").strip()
    if not body:
        return note

    if note in body:
        return body

    return f"{note}\n\n{body}"



def _append_sources_section(content, sources):
    if not sources:
        return content

    body = (content or "").rstrip()
    if "## Manbalar" in body:
        return body

    lines = ["## Manbalar"]
    for source in sources[:5]:
        lines.append(f"- [{source['title']}]({source['url']})")

    return f"{body}\n\n" + "\n".join(lines)



def _contains_unrequested_model_versions(topic, content):
    topic_lower = (topic or "").lower()
    for match in SPECIFIC_MODEL_PATTERN.finditer(content or ""):
        if match.group(0).lower() not in topic_lower:
            return True
    return False



def _build_seo_prompt(topic, current_date_str, use_grounding):
    if use_grounding:
        realtime_rules = """
    - Google Search grounding ishlayapti. Tez ozgaradigan faktlar, model nomlari, versiyalar, narx, benchmark va reliz holatlarini faqat qidiruv orqali tasdiqlangan bo'lsa yozing.
    - "Eng songgi", "eng kuchli", "yangi chiqdi" kabi davolarni faqat tasdiqlanganda ishlating.
    - Muhim faktlar real vaqtga mos bo'lsin va maqola ichida bugungi holat sifatida yozilsin.
"""
    else:
        realtime_rules = """
    - Google Search grounding mavjud emas. Shuning uchun aniq model versiyasi, reliz sanasi, benchmark, narx yoki "eng songgi" kabi davolarni yozmang.
    - Tasdiqlanmagan model nomi va versiyalarni toqimang. Kerak bolsa umumiy iboralarni ishlating: "zamonaviy AI modellari", "yangi avlod vositalari".
"""

    return f"""
    Siz TrendoAI uchun professional SEO-maqola yozuvchi ekspertisiz.

    === MUHIM KONTEKST ===
    Bugungi sana: {current_date_str}
    Maqola aynan shu sana holatiga mos bo'lsin.
    Eski yoki kelajakdan yozilgandek gapirmang.
    "2025 yakunlanmoqda" yoki tasdiqlanmagan "2026 yilning eng yangi modeli" kabi iboralarni ishlatmang.
{realtime_rules}
    - Mavzudan tashqari aniq model versiyalarini o'zingiz qo'shmang.
    - Agar biror faktga ishonchingiz komil bo'lmasa, umumiy va amaliy tushuntirish bering.

    === 80/20 QOIDASI ===
    - 80% foydali va amaliy ma'lumot bering.
    - 20% TrendoAI haqida faqat oxirida yengil eslatma bo'lsin.

    Maqola oxirida shunday yozing:
    "Agar sizga ham [mavzu boyicha xizmat] kerak bolsa, TrendoAI jamoasi yordam beradi. Bepul konsultatsiya uchun: t.me/Akramjon1984"

    === VAZIFA ===
    "{topic}" mavzusida professional maqola yozing.

    === SEO TALABLARI ===
    SARLAVHA:
    - Asosiy kalit soz sarlavhada bo'lsin.
    - Raqam yoki aniq foyda bo'lsa ishlating.
    - Yil faqat haqiqatan zarur va tekshirilgan bo'lsa ishlatilsin.
    - Noaniq hype yoki clickbait ishlatmang.

    KALIT SOZLAR:
    - 1-kalit: asosiy qidiruv sozi
    - 2-kalit: shu sozning variant shakli
    - 3-kalit: tegishli texnologiya yoki vosita
    - 4-kalit: muammo yoki yechimga oid ibora
    - 5-kalit: mahalliy yoki biznes konteksti

    KONTENT ICHIDA SEO:
    - Birinchi 100 sozda asosiy kalit soz bo'lsin.
    - Har bir H2 yoki H3 sarlavhada kalit sozning tabiiy varianti bo'lsin.
    - Kalit sozlar suniy emas, tabiiy ishlatilsin.
    - 1000-1500 soz uzunlikda yozing.

    === KONTENT TALABLARI ===
    1. O'zbek tilida, lotin alifbosida yozing.
    2. Professional, aniq va tushunarli til ishlating.
    3. Amaliy misollar, jarayonlar va ehtiyotkor statistik yondashuv bering.
    4. Faqat Markdown format ishlating.
    5. HTML teg ishlatmang.
    6. Tekshirilmagan release, benchmark yoki versiya iddaolarini yozmang.

    === STRUKTURA ===
    - Kirish: muammo va kontekst
    - Asosiy qism: 4-5 bo'lim
    - Xulosa: qisqa yakun + TrendoAI eslatmasi

    JSON formatida javob bering:
    {{
      "title": "SEO uchun qisqa va aniq sarlavha",
      "keywords": "asosiy kalit, variant kalit, texnologiya, muammo yechim, mahalliy",
      "content": "To'liq SEO-optimallashtirilgan Markdown maqola"
    }}

    Faqat JSON qaytaring.
    """



def generate_post_for_seo(topic):
    """Generate an SEO blog post for the given topic."""
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    use_grounding = _should_use_grounding()
    prompt = _build_seo_prompt(topic, current_date_str, use_grounding)
    _set_last_ai_error(None)

    def _generate():
        response = None
        used_grounding = False

        if use_grounding:
            try:
                response = _generate_grounded_response(prompt)
                used_grounding = response is not None
            except Exception as exc:
                print(f"[ai] Grounded generation failed, falling back to legacy SDK: {exc}")

        if response is None:
            response = model.generate_content(prompt)

        response_text = _response_to_text(response)
        parsed = _parse_json_response(response_text)
        if not parsed:
            parsed = _coerce_post_payload(response_text, topic)

        return {
            "parsed": parsed,
            "grounded": used_grounding,
            "sources": _extract_grounding_sources(response) if used_grounding else [],
            "response_text": response_text,
        }

    generated = _retry_with_backoff(_generate)
    if not generated:
        if not get_last_ai_error():
            _set_last_ai_error("AI modeli hech qanday javob qaytarmadi.")
        return None

    result = generated.get("parsed")
    if result and all(key in result for key in ["title", "keywords", "content"]):
        result["content"] = _add_freshness_note(result["content"], current_date_str)
        result["content"] = _append_sources_section(result["content"], generated.get("sources", []))

        if not generated.get("grounded") and _contains_unrequested_model_versions(topic, result["content"]):
            print("[ai] Rejecting stale post because it mentioned unverified model versions without grounding.")
            _set_last_ai_error("AI javobi tekshirilmagan model versiyalarini tilga oldi.")
            return None

        _set_last_ai_error(None)
        return result

    print("[ai] AI response had an invalid format")
    preview = (generated.get("response_text") or "").strip().replace("\n", " ")
    preview = preview[:240] + ("..." if len(preview) > 240 else "")
    if preview:
        _set_last_ai_error(f"AI javobi JSON formatida emas. Preview: {preview}")
    else:
        _set_last_ai_error("AI bosh yoki yaroqsiz javob qaytardi.")
    return None


def generate_marketing_post_for_telegram():
    """Generate a short marketing post for the Telegram channel."""
    prompt = """
    TrendoAI uchun Telegram kanaliga qisqa va jalb qiluvchi post yozing.

    Talablar:
    - 150-200 soz
    - Professional va qiziqarli ohang
    - Oquvchini blogga kirishga undaydigan CTA bo'lsin
    - Tekshirilmagan model versiyalari yoki "eng songgi" kabi davolarni ishlatmang

    Faqat post matnini yozing.
    """

    def _generate():
        response = model.generate_content(prompt)
        return response.text.strip()

    return _retry_with_backoff(_generate)



def generate_custom_content(prompt_text):
    """Generate custom content from an arbitrary prompt."""
    def _generate():
        response = model.generate_content(prompt_text)
        return response.text.strip()

    return _retry_with_backoff(_generate)



def generate_portfolio_content(title, category):
    """Generate portfolio content for a project."""
    category_names = {
        "bot": "Telegram Bot",
        "web": "Web Sayt",
        "ai": "AI Yechim",
        "mobile": "Mobile Ilova",
    }

    cat_name = category_names.get(category, category)

    prompt = f"""
    Siz TrendoAI uchun professional portfolio kontenti yozuvchisiz.

    Vazifa: "{title}" nomli {cat_name} loyihasi uchun professional marketing kontenti yarating.

    MUHIM TALABLAR:
    1. O'zbek tilida (lotin alifbosi) yozing.
    2. Professional va ishonchli ohangda bo'lsin.
    3. Mijozlarni jalb qiluvchi, ammo realistik bo'lsin.

    JSON formatida javob bering:
    {{
      "description": "Loyiha haqida qisqa tavsif (2-3 jumla)",
      "technologies": "Python, Flask, PostgreSQL",
      "features": "Tolov tizimi, Admin panel, Real-time xabarlar",
      "details": "## Loyiha haqida\\n\\nBatafsil malumot markdown formatida.",
      "meta_description": "SEO uchun meta tavsif",
      "meta_keywords": "telegram bot, python"
    }}

    Faqat JSON qaytaring.
    """

    def _generate():
        response = model.generate_content(prompt)
        return _parse_json_response(response.text)

    result = _retry_with_backoff(_generate)
    if result:
        return result

    print("[ai] Portfolio response had an invalid format")
    return None


if __name__ == "__main__":
    print("=" * 60)
    print("TrendoAI AI Generator Test")
    print("=" * 60)

    print("\nGenerating marketing post...")
    marketing_text = generate_marketing_post_for_telegram()
    if marketing_text:
        print("OK")
        print("-" * 40)
        print(marketing_text)
    else:
        print("FAILED")