"""Thin Gemini wrapper with model and API-key fallback."""

import os

import google.generativeai as genai

from config import GEMINI_MODEL, GEMINI_MODEL_BACKUP

_FALLBACK_TRIGGERS = (
    "403",
    "404",
    "429",
    "denied",
    "not available",
    "no longer available",
    "quota",
    "resourceexhausted",
)

_preferred_model = None
_preferred_key = None


def _candidate_models():
    """Return ordered text model ids to try."""
    chain = []
    for candidate in (
        _preferred_model,
        GEMINI_MODEL,
        GEMINI_MODEL_BACKUP,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ):
        candidate = (candidate or "").strip()
        if candidate and "live" not in candidate.lower() and candidate not in chain:
            chain.append(candidate)
    return chain


def _candidate_api_keys():
    """Return ordered API keys to try."""
    chain = []
    for candidate in (
        _preferred_key,
        os.getenv("GEMINI_API_KEY"),
        os.getenv("GEMINI_API_KEY2"),
        os.getenv("GEMINI_API_KEY3"),
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


def generate_text(prompt, system_instruction=None, history=None):
    """Generate a text reply, trying available keys and text-safe models."""
    candidates = _candidate_models()
    last_error = None

    for api_key in _candidate_api_keys() or [None]:
        if api_key:
            genai.configure(api_key=api_key)

        for model_id in candidates:
            try:
                kwargs = {}
                if system_instruction:
                    kwargs["system_instruction"] = system_instruction
                model = genai.GenerativeModel(model_id, **kwargs)

                if history is not None:
                    chat = model.start_chat(history=history)
                    response = chat.send_message(prompt)
                else:
                    response = model.generate_content(prompt)

                text = (getattr(response, "text", "") or "").strip()
                _mark_working(model_id, api_key)
                return text, model_id

            except Exception as exc:
                last_error = exc
                if _is_fallback_error(exc):
                    print(f"Gemini {model_id} failed ({type(exc).__name__}: {str(exc)[:100]}), trying next...")
                    continue
                raise

    raise last_error if last_error else RuntimeError("No Gemini models configured")
