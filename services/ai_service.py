import json
import os
import re
import time
from datetime import datetime
from google import genai
from google.genai import types
from utils.logger import setup_logger

logger = setup_logger("ai_service")

from config import (
    AI_RETRY_ATTEMPTS,
    AI_RETRY_DELAY,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_MODEL_BACKUP,
)

# AI Service Errors & States
LAST_AI_ERROR = None
_preferred_model = None
_preferred_key = None

_FALLBACK_TRIGGERS = (
    "403", "404", "429", "denied", "not available", 
    "no longer available", "quota", "resourceexhausted"
)
TEXT_UNSUPPORTED_MODEL_PARTS = ("live", "native-audio", "tts", "image")
SPECIFIC_MODEL_PATTERN = re.compile(
    r"\b(?:GPT-\d+(?:\.\d+)?(?:\s+[A-Za-z-]+)?|Gemini\s+\d+(?:\.\d+)?(?:\s+[A-Za-z-]+)?|Claude\s+(?:Opus|Sonnet|Haiku)\s*\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

def get_last_ai_error():
    return LAST_AI_ERROR

def _set_last_ai_error(message):
    global LAST_AI_ERROR
    LAST_AI_ERROR = (message or "").strip() or None

def _is_text_generation_model(model_name):
    normalized = (model_name or "").strip().lower()
    return bool(normalized) and not any(part in normalized for part in TEXT_UNSUPPORTED_MODEL_PARTS)

def _candidate_models(only_text=True):
    chain = []
    candidates = [
        _preferred_model, GEMINI_MODEL, GEMINI_MODEL_BACKUP,
        "gemini-3.7-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"
    ]
    for candidate in candidates:
        candidate = (candidate or "").strip()
        if candidate and candidate not in chain:
            if only_text and not _is_text_generation_model(candidate):
                continue
            chain.append(candidate)
    return chain

def _candidate_api_keys():
    chain = []
    for candidate in (
        _preferred_key, GEMINI_API_KEY, os.getenv("GEMINI_API_KEY2"), os.getenv("GEMINI_API_KEY3")
    ):
        candidate = (candidate or "").strip()
        if candidate and candidate not in chain:
            chain.append(candidate)
    return chain

def _is_fallback_error(exc):
    msg = str(exc).lower()
    return any(trigger in msg for trigger in _FALLBACK_TRIGGERS)

def _mark_working(model_id, api_key):
    global _preferred_model, _preferred_key
    _preferred_model = model_id
    _preferred_key = api_key

def _format_contents(prompt, history=None):
    if not history:
        return prompt
    contents = []
    for item in history:
        role = "user" if item.get("role") == "user" else "model"
        parts = item.get("parts")
        if not parts:
            c = item.get("content")
            parts = [c] if c else []
        text_parts = [p if isinstance(p, str) else getattr(p, "text", str(p)) for p in parts if p]
        if text_parts:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=" ".join(text_parts))]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
    return contents

def _response_to_text(response):
    if response is None: return ""
    try:
        response_text = getattr(response, "text", None)
        if isinstance(response_text, str) and response_text.strip(): return response_text.strip()
    except Exception: pass
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates: return ""
        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []
        return "\n".join([getattr(p, "text", "") for p in parts if getattr(p, "text", "")]).strip()
    except Exception: return ""

# ----------------- UNIVERSAL GENERATION ENGINE -----------------

def generate_text(prompt, system_instruction=None, history=None, use_grounding=False, parse_json=False):
    """
    Generate text using available API keys and models with built-in retry and fallback logic.
    """
    _set_last_ai_error(None)
    candidates = _candidate_models()
    last_error = None
    api_keys = _candidate_api_keys()

    for api_key in api_keys:
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            last_error = e
            continue

        for model_id in candidates:
            # Try generation with backoff mechanism
            for attempt in range(AI_RETRY_ATTEMPTS):
                try:
                    config_kwargs = {}
                    if system_instruction:
                        config_kwargs["system_instruction"] = system_instruction
                    
                    used_grounding = False
                    if use_grounding:
                        try:
                            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
                            used_grounding = True
                        except Exception as e:
                            logger.error(f"[ai_service] Grounding setup failed, fallback to normal: {e}")
                            if "tools" in config_kwargs: del config_kwargs["tools"]
                            used_grounding = False

                    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
                    contents = _format_contents(prompt, history=history)

                    response = client.models.generate_content(model=model_id, contents=contents, config=config)
                    text = _response_to_text(response)
                    
                    _mark_working(model_id, api_key)
                    
                    if parse_json:
                        return {"text": text, "response": response, "grounded": used_grounding}
                    return text, model_id

                except Exception as exc:
                    last_error = exc
                    if _is_fallback_error(exc):
                        logger.warning(f"[ai_service] Gemini {model_id} failed with key ...{api_key[-4:]}, trying next fallback...")
                        break # break retry loop, try next model
                    
                    wait_time = AI_RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"[ai_service] Error ({attempt + 1}/{AI_RETRY_ATTEMPTS}): {exc}. Waiting {wait_time}s...")
                    time.sleep(wait_time)

    err_msg = f"All models and keys failed. Last error: {last_error}"
    logger.error(err_msg)
    _set_last_ai_error(err_msg)
    if parse_json:
        return None
    raise RuntimeError(err_msg)

# ----------------- DOMAIN SPECIFIC FUNCTIONS (SEO, Portfolio, etc.) -----------------

def _parse_json_response(response_text):
    cleaned = (response_text or "").strip()
    if cleaned.startswith("`json"): cleaned = cleaned[7:]
    elif cleaned.startswith("`"): cleaned = cleaned[3:]
    if cleaned.endswith("`"): cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try: return json.loads(cleaned)
    except Exception:
        try:
            match = re.search(r"\{.*\}", response_text or "", re.DOTALL)
            if match: return json.loads(match.group(0))
        except Exception: pass
        return None

def _extract_grounding_sources(response):
    sources = []
    seen = set()
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates: return sources
        chunks = getattr(getattr(candidates[0], "grounding_metadata", None), "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            url = getattr(web, "uri", None)
            title = getattr(web, "title", None)
            if url and url not in seen:
                seen.add(url)
                sources.append({"url": url, "title": title})
    except Exception: pass
    return sources

def _build_fallback_keywords(topic, title):
    phrases = []
    seen = set()
    for raw in [topic or "", title or ""]:
        for piece in re.split(r"[:,()]+", raw):
            cleaned = re.sub(r"\s+", " ", piece).strip(" -")
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                phrases.append(cleaned)
    for g in ["AI", "biznes", "texnologiya"]:
        if g.lower() not in seen: phrases.append(g); seen.add(g.lower())
    return ", ".join(phrases[:5])

def _coerce_post_payload(response_text, topic):
    body = (response_text or "").strip()
    if not body or body.startswith("{") or body.startswith("`"): return None
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines: return None
    title = next((line.lstrip("#").strip() for line in lines if line.startswith("#")), lines[0].strip("* "))
    if len(body) < 400 or not title: return None
    if lines[0].strip("# ").strip() != title: body = f"# {title}\n\n{body}"
    return {"title": title[:120], "keywords": _build_fallback_keywords(topic, title), "content": body}

def _append_sources_section(content, sources):
    if not sources: return content
    body = (content or "").rstrip()
    if "## Manbalar" in body: return body
    lines = ["## Manbalar"] + [f"- [{s['title']}]({s['url']})" for s in sources[:5]]
    return f"{body}\n\n" + "\n".join(lines)

def _contains_unrequested_model_versions(topic, content):
    topic_lower = (topic or "").lower()
    for match in SPECIFIC_MODEL_PATTERN.finditer(content or ""):
        if match.group(0).lower() not in topic_lower: return True
    return False

def generate_post_for_seo(topic):
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    realtime_rules = "- Google Search grounding ishlayapti. Tez ozgaradigan faktlar... faqat qidiruv orqali tasdiqlangan bo'lsa yozing."
    
    prompt = f"Siz TrendoAI uchun professional SEO maqola yozuvchisiz.\nMavzu: {topic}\nSana: {current_date_str}\n{realtime_rules}\nFaqat JSON formatida qaytaring: {{\"title\": \"...\", \"meta_description\": \"...\", \"keywords\": \"...\", \"content\": \"...\"}}"
    
    try:
        res = generate_text(prompt, use_grounding=True, parse_json=True)
        if not res: return None
        
        response_text = res["text"]
        parsed = _parse_json_response(response_text) or _coerce_post_payload(response_text, topic)
        
        if parsed and "content" in parsed:
            sources = _extract_grounding_sources(res["response"]) if res["grounded"] else []
            parsed["content"] = _append_sources_section(parsed["content"], sources)
            if not res["grounded"] and _contains_unrequested_model_versions(topic, parsed["content"]):
                _set_last_ai_error("AI javobi tekshirilmagan model versiyalarini tilga oldi.")
                return None
            return parsed
            
        _set_last_ai_error("AI javobi yaroqsiz formatda.")
    except Exception as e:
        logger.error(f"[generate_post_for_seo] Failed: {e}")
    return None

def generate_marketing_post_for_telegram():
    prompt = "TrendoAI uchun Telegram kanaliga qisqa va jalb qiluvchi post yozing. 150-200 so'z."
    try:
        text, _ = generate_text(prompt)
        return text
    except Exception: return None

def generate_custom_content(prompt_text):
    try:
        text, _ = generate_text(prompt_text)
        return text
    except Exception: return None

def generate_portfolio_content(title, category):
    prompt = f"Portfolio kontenti yozing. Mavzu: {title}. Kategoriya: {category}. Faqat JSON qaytaring: {{\"description\": \"...\", \"technologies\": \"...\", \"features\": \"...\", \"details\": \"...\", \"meta_description\": \"...\", \"meta_keywords\": \"...\"}}"
    try:
        res = generate_text(prompt, parse_json=True)
        if res: return _parse_json_response(res["text"])
    except Exception: pass
    return None
