import os
import sys

import google.generativeai as genai
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not found in environment variables.")
    raise SystemExit(1)

genai.configure(api_key=api_key)

print(f"Checking available models for key ending in ...{api_key[-4:]}")

try:
    print("\nAvailable models that support generateContent:")
    found = False
    for model in genai.list_models():
        if "generateContent" not in model.supported_generation_methods:
            continue

        display_name = (
            getattr(model, "display_name", None)
            or getattr(model, "displayName", None)
            or ""
        )
        suffix = f" (DisplayName: {display_name})" if display_name else ""
        print(f"- {model.name}{suffix}")
        found = True

    if not found:
        print("ERROR: No models found that support generateContent.")
    else:
        print("\nOK: List complete.")
except Exception as exc:
    print(f"ERROR: Error listing models: {exc}")
    raise SystemExit(1)
