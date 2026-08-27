"""Thin Gemini wrapper using the official google-genai SDK with model and API-key fallback."""

import os
from google import genai
from google.genai import types

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
        "gemini-3.7-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
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


def _format_contents(prompt, history=None):
    """Convert history and prompt into types.Content objects or standard content list."""
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
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=" ".join(text_parts))],
                )
            )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
    )
    return contents


def generate_text(prompt, system_instruction=None, history=None):
    """Generate a text reply, trying available keys and text-safe models."""
    candidates = _candidate_models()
    last_error = None

    for api_key in _candidate_api_keys() or [None]:
        if not api_key:
            continue

        try:
            client = genai.Client(api_key=api_key)
        except Exception as init_err:
            last_error = init_err
            continue

        for model_id in candidates:
            try:
                config_kwargs = {}
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction

                config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
                contents = _format_contents(prompt, history=history)

                response = client.models.generate_content(
                    model=model_id,
                    contents=contents,
                    config=config,
                )

                text = (getattr(response, "text", "") or "").strip()
                _mark_working(model_id, api_key)
                return text, model_id

            except Exception as exc:
                last_error = exc
                if _is_fallback_error(exc):
                    print(f"Gemini {model_id} failed ({type(exc).__name__}: {str(exc)[:100]}), trying next...")
                    continue
                raise

    raise last_error if last_error else RuntimeError("No Gemini models or API keys configured")
