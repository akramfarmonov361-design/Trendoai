"""Thin Gemini wrapper with automatic primary → backup model fallback.

The bot and the site chat both want to try GEMINI_MODEL first (cheap
preference) but transparently fall through to GEMINI_MODEL_BACKUP when
the primary returns 403 (project not approved for that model) or 404
(model retired). Without this, switching to a newer/cheaper id risks
breaking production every time Google reshuffles their model catalog.

The first model id that successfully returns text gets cached for the
rest of the process, so we don't repeat the failing primary call on
every request.
"""

import google.generativeai as genai

from config import GEMINI_MODEL, GEMINI_MODEL_BACKUP

# Errors that mean "this model id won't work, try the next one" rather
# than "the API is broken" or "you ran out of quota".
_FALLBACK_TRIGGERS = ("403", "404", "denied", "not available", "no longer available")

_preferred_model = None


def _candidate_models():
    """Return ordered list of model ids to try (no duplicates, drops empties)."""
    chain = []
    for candidate in (_preferred_model, GEMINI_MODEL, GEMINI_MODEL_BACKUP):
        candidate = (candidate or "").strip()
        if candidate and candidate not in chain:
            chain.append(candidate)
    return chain


def _is_fallback_error(exc):
    msg = str(exc).lower()
    return any(trigger in msg for trigger in _FALLBACK_TRIGGERS)


def _mark_working(model_id):
    global _preferred_model
    _preferred_model = model_id


def generate_text(prompt, system_instruction=None, history=None):
    """Generate a text reply, falling back to the backup model on 403/404.

    Args:
        prompt: str — the user's last message
        system_instruction: optional system prompt for the model
        history: optional list of {'role': 'user'|'model', 'parts': [text]}
                 for multi-turn chat. If provided, uses start_chat().

    Returns:
        (text, model_id_used)

    Raises:
        The last exception if all candidate models fail.
    """
    candidates = _candidate_models()
    last_error = None

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
            _mark_working(model_id)
            return text, model_id

        except Exception as e:
            last_error = e
            if _is_fallback_error(e):
                print(f"⚠️ Model {model_id} failed ({type(e).__name__}: {str(e)[:80]}), trying next...")
                continue
            # Non-fallback error (quota, network, etc.) — don't waste a
            # round-trip on the backup, bubble up so the caller can show
            # the right message.
            raise

    raise last_error if last_error else RuntimeError("No Gemini models configured")
