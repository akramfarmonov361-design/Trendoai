"""
SEO and marketing content generation helpers for TrendoAI using the official google-genai SDK.
"""

import json
import os
import re
import time
from datetime import datetime

from google import genai
from google.genai import types

from config import (
    AI_RETRY_ATTEMPTS,
    AI_RETRY_DELAY,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_MODEL_BACKUP,
)

GEMINI_API_KEY2 = os.getenv("GEMINI_API_KEY2")
GEMINI_API_KEY3 = os.getenv("GEMINI_API_KEY3")

current_api_key = GEMINI_API_KEY
current_model_name = GEMINI_MODEL
LAST_AI_ERROR = None
TEXT_MODEL_FALLBACKS = [
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]
TEXT_UNSUPPORTED_MODEL_PARTS = ("live", "native-audio", "tts", "image")

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


def _is_text_generation_model(model_name):
    """Return True only for models suitable for text generate_content calls."""
    normalized = (model_name or "").strip().lower()
    return bool(normalized) and not any(part in normalized for part in TEXT_UNSUPPORTED_MODEL_PARTS)


def _build_text_model_candidates():
    candidates = []
    skipped = []

    for model_name in [GEMINI_MODEL, GEMINI_MODEL_BACKUP, *TEXT_MODEL_FALLBACKS]:
        model_name = (model_name or "").strip()
        if not model_name or model_name in candidates:
            continue

        if _is_text_generation_model(model_name):
            candidates.append(model_name)
        else:
            skipped.append(model_name)

    if skipped:
        print(f"[ai] Skipping non-text Gemini models for post generation: {', '.join(skipped)}")

    return candidates


def _build_api_key_candidates():
    candidates = []
    for api_key in [GEMINI_API_KEY, GEMINI_API_KEY2, GEMINI_API_KEY3]:
        if api_key and api_key not in candidates:
            candidates.append(api_key)
    return candidates


def _is_permission_error(exc):
    message = str(exc).lower()
    exc_name = exc.__class__.__name__.lower()
    return "permissiondenied" in exc_name or "403" in message or "denied access" in message


def _is_model_config_error(exc):
    message = str(exc).lower()
    return (
        "404" in message
        and ("not found" in message or "not supported" in message or "models/" in message)
    )


def _get_client(api_key):
    """Create a client instance for the specified api_key."""
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as exc:
        print(f"[ai] genai.Client initialization failed: {exc}")
        return None


def _switch_to_next_api_key(model_candidates):
    global current_api_key, current_model_name

    api_keys = _build_api_key_candidates()
    try:
        current_key_index = api_keys.index(current_api_key)
    except ValueError:
        current_key_index = -1

    if current_key_index + 1 < len(api_keys):
        next_key = api_keys[current_key_index + 1]
        print(f"[ai] Switching to backup API key #{current_key_index + 2}")
        current_api_key = next_key
        current_model_name = model_candidates[0]
        return True

    return False


def _reset_to_primary_config():
    global current_api_key, current_model_name

    api_keys = _build_api_key_candidates()
    model_candidates = _build_text_model_candidates()

    if api_keys:
        current_api_key = api_keys[0]
    if model_candidates:
        current_model_name = model_candidates[0]


def _switch_to_backup(prefer_next_key=False):
    """Switch through text-safe backup models first, then to a backup API key."""
    global current_api_key, current_model_name

    model_candidates = _build_text_model_candidates()

    if prefer_next_key:
        return _switch_to_next_api_key(model_candidates)

    try:
        current_index = model_candidates.index(current_model_name)
    except ValueError:
        current_index = -1

    if current_index + 1 < len(model_candidates):
        next_model = model_candidates[current_index + 1]
        print(f"[ai] Switching to backup model: {next_model}")
        current_model_name = next_model
        return True

    return _switch_to_next_api_key(model_candidates)


def _retry_with_backoff(func, *args, **kwargs):
    """Run a function with exponential backoff and backup model/key fallback."""
    last_exception = None
    _set_last_ai_error(None)

    while True:
        client = _get_client(current_api_key)
        if not client:
            _set_last_ai_error("No valid Gemini API key configured.")
            break

        for attempt in range(AI_RETRY_ATTEMPTS):
            try:
                return func(client=client, model_name=current_model_name, *args, **kwargs)
            except Exception as exc:
                last_exception = exc
                _set_last_ai_error(str(exc))
                if _is_permission_error(exc) or _is_model_config_error(exc):
                    print(f"[ai] Configuration error: {exc}")
                    break

                wait_time = AI_RETRY_DELAY * (2 ** attempt)
                print(f"[ai] Error ({attempt + 1}/{AI_RETRY_ATTEMPTS}): {exc}")
                print(f"[ai] Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

        prefer_next_key = bool(last_exception and _is_permission_error(last_exception))
        if not _switch_to_backup(prefer_next_key=prefer_next_key):
            break

        print(
            f"[ai] Retrying with model '{current_model_name}' "
            f"and API key ending ...{current_api_key[-4:] if current_api_key else 'none'}"
        )

    print(f"[ai] All retries failed. Last error: {last_exception}")
    _set_last_ai_error(f"All retries failed: {last_exception}")
    _reset_to_primary_config()
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
    """Extract text safely from Gemini SDK responses."""
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

    if body.startswith("{") or body.startswith("```"):
        print("[ai] Javob buzuq JSON'ga o'xshaydi — markdown deb qabul qilinmadi")
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

    Maqola oxirida shunday yozing (markdown link sintaksisi bilan):
    "Agar sizga ham [mavzu boyicha xizmat] kerak bolsa, TrendoAI jamoasi yordam beradi. Bepul konsultatsiya uchun arizangizni qoldiring: [trendoai.uz/order](https://trendoai.uz/order)"

    === VAZIFA ===
    "{topic}" mavzusida 2026-yilning eng zamonaviy IT va AI trendlariga asoslangan, o'ta amaliy va professional SEO maqola yozing.

    === KONTENT VA SIFAT TALABLARI ===
    1. O'zbek tilida, lotin alifbosida, o'quvchiga darhol foyda beradigan uslubda yozing.
    2. Nazariy quruq gaplar o'rniga, **haqiqiy loyihalar, arxitektura, bosqichma-bosqich qo'llanma (Step-by-Step), jadvallar yoki kod/sozlama misollarini** keltiring.
    3. Bizneslar uchun bu texnologiya **qanday qilib daromadni 2-3x oshirishi yoki xarajatlarni 50% ga tejashi (ROI)** mumkinligini aniq tushuntiring.
    4. Faqat toza Markdown format ishlating (H2, H3, ro'yxatlar, jadvallar, qalin matn). HTML teglar ishlatmang.
    5. Uzunligi: 1000–1500 so'z atrofida bo'lsin.

    === STRUKTURA VA FORMATLASH ===
    1. **Boshlanishida TL;DR bloki:**
       > 💡 **Qisqacha xulosa (TL;DR):** [Mavzuning eng muhim 2-3 ta amaliy xulosasi, yangi trend va biznesga beradigan foydasi]
    
    2. **Kirish:** Muammoning dolzarbligi va 2026-yildagi yangi imkoniyatlar (birinchi 100 so'zda asosiy kalit so'z).
    
    3. **Asosiy qism (4-5 ta H2/H3 bo'lim):**
       - Bosqichma-bosqich amalga oshirish yo'l xaritasi (Roadmap).
       - Taqqoslash jadvallari (masalan: Eskicha usul vs Yangi AI avtomatlashtirish).
       - Haqiqiy amaliy keys yoki arxitektura chizmasi.
    
    4. **FAQ Bo'limi (Google Rich Snippet uchun):**
       ### ❓ Tez-tez so'raladigan savollar
       **1. [Savol 1]?**
       [Aniq va qisqa javob].
       **2. [Savol 2]?**
       [Aniq va qisqa javob].
       **3. [Savol 3]?**
       [Aniq va qisqa javob].
    
    5. **Xulosa va TrendoAI CTA:**
       > 🚀 **Amaliyotga tadbiq etish:** Agar sizga ham [mavzu bo'yicha xizmat] kerak bo'lsa, TrendoAI jamoasi yordam beradi. Bepul konsultatsiya olish uchun: [trendoai.uz/order](https://trendoai.uz/order)

    JSON formatida javob bering:
    {{
      "title": "SEO uchun jozibali, qisqa va aniq sarlavha",
      "meta_description": "Google qidiruvi uchun 140-160 belgilik qiziqarli meta tavsif",
      "keywords": "asosiy kalit, variant kalit, texnologiya, muammo yechim, mahalliy",
      "content": "To'liq SEO-optimallashtirilgan Markdown maqola"
    }}

    Faqat toza JSON qaytaring.
    """


def generate_post_for_seo(topic):
    """Generate an SEO blog post for the given topic."""
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    _set_last_ai_error(None)

    def _generate(client, model_name):
        # 1. Search Grounding bilan urinib ko'rish
        response = None
        used_grounding = False

        try:
            tool = types.Tool(google_search=types.GoogleSearch())
            config = types.GenerateContentConfig(tools=[tool])
            prompt = _build_seo_prompt(topic, current_date_str, use_grounding=True)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            used_grounding = True
        except Exception as exc:
            print(f"[ai] Grounded generation failed, trying standard generation: {exc}")
            used_grounding = False
            prompt = _build_seo_prompt(topic, current_date_str, use_grounding=False)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )

        response_text = _response_to_text(response)
        parsed = _parse_json_response(response_text)
        if not parsed:
            parsed = _coerce_post_payload(response_text, topic)

        if not parsed:
            preview = response_text.strip().replace("\n", " ")[:160]
            raise ValueError(f"AI javobi yaroqsiz formatda: {preview}")

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

    def _generate(client, model_name):
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return _response_to_text(response)

    return _retry_with_backoff(_generate)


def generate_custom_content(prompt_text):
    """Generate custom content from an arbitrary prompt."""
    def _generate(client, model_name):
        response = client.models.generate_content(
            model=model_name,
            contents=prompt_text,
        )
        return _response_to_text(response)

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

    def _generate(client, model_name):
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return _parse_json_response(_response_to_text(response))

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

