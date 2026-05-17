import os
from dotenv import load_dotenv

load_dotenv(override=False)  # env vars from GitHub Actions take priority

GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
INSTAGRAM_USERNAME  = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD  = os.getenv("INSTAGRAM_PASSWORD", "")
NEWS_TOPIC          = os.getenv("NEWS_TOPIC", "world news")
POST_COUNT          = int(os.getenv("POST_COUNT", "5"))
POST_INTERVAL_HOURS = int(os.getenv("POST_INTERVAL_HOURS", "6"))

# Official Instagram Graph API
IG_USER_ID      = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
IG_APP_SECRET   = os.getenv("IG_APP_SECRET", "")
IMGBB_API_KEY   = os.getenv("IMGBB_API_KEY", "")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set in .env — get a free key at https://console.groq.com")
if not IG_USER_ID or not IG_ACCESS_TOKEN:
    raise ValueError("IG_USER_ID and IG_ACCESS_TOKEN must be set in .env")
if not IMGBB_API_KEY or IMGBB_API_KEY == "your_imgbb_key_here":
    raise ValueError("IMGBB_API_KEY not set — get a free key at https://imgbb.com/api")
