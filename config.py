import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

DATA_FILE = "users_data.json"
FREE_LIMIT = 3

AFFILIATE_REVOLUT = "https://revolut.com/referral/?referral-code=radik5f35!JUL1-26-VR-EE&geo-redirect"
AFFILIATE_WISE = "https://wise.com/invite/arhc/radikm15"

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and GROQ_API_KEY environment variables")
