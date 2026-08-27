import os
import sys

from dotenv import load_dotenv
from google import genai

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not found in environment variables.")
    raise SystemExit(1)

client = genai.Client(api_key=api_key)

print(f"Checking available models for key ending in ...{api_key[-4:]}")

try:
    print("\nAvailable models:")
    found = False
    for model in client.models.list():
        display_name = getattr(model, "display_name", "") or ""
        suffix = f" (DisplayName: {display_name})" if display_name else ""
        print(f"- {model.name}{suffix}")
        found = True

    if not found:
        print("ERROR: No models found.")
    else:
        print("\nOK: List complete.")
except Exception as exc:
    print(f"ERROR: Error listing models: {exc}")
    raise SystemExit(1)
