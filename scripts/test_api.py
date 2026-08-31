import os
import sys
from utils.logger import setup_logger
logger = setup_logger("test_api")


from dotenv import load_dotenv
from google import genai

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
logger.info(f"API key looks like: {api_key[:10] if api_key else None}...")

if not api_key:
    logger.error("ERROR: GEMINI_API_KEY is missing.")
    raise SystemExit(1)

client = genai.Client(api_key=api_key)

logger.info("\n=== Available Gemini Models ===")
try:
    count = 0
    for model in client.models.list():
        if "gemini" in model.name:
            logger.info(model.name)
            count += 1
            if count >= 15:
                break
except Exception as exc:
    logger.error("Failed to list models:", type(exc).__name__, str(exc))

logger.info("\n=== Testing generate_content ===")
for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite"]:
    try:
        logger.info(f"Testing {model_name}:")
        resp = client.models.generate_content(model=model_name, contents="salom")
        logger.info(getattr(resp, "text", ""))
        logger.info("OK: success")
    except Exception as exc:
        logger.error(f"ERROR: failed with {model_name}: {type(exc).__name__}: {exc}")
