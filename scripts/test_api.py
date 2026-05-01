import os
import sys

import google.generativeai as genai
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API key looks like: {api_key[:10] if api_key else None}...")

if not api_key:
    print("ERROR: GEMINI_API_KEY is missing.")
    raise SystemExit(1)

genai.configure(api_key=api_key)

print("\n=== Available Gemini Models ===")
try:
    count = 0
    for model in genai.list_models():
        if "gemini" in model.name:
            print(model.name)
            count += 1
            if count >= 15:
                break
except Exception as exc:
    print("Failed to list models:", type(exc).__name__, str(exc))

print("\n=== Testing generate_content ===")
for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite"]:
    try:
        model = genai.GenerativeModel(model_name)
        print(f"Testing {model_name}:")
        print(model.generate_content("salom").text)
        print("OK: success")
    except Exception as exc:
        print(f"ERROR: failed with {model_name}: {type(exc).__name__}: {exc}")
