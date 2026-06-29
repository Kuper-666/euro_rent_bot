import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

FREE_LIMIT = 3
SUBSCRIPTION_DAYS = 30
GROQ_RATE_LIMIT_SECONDS = 10
GROQ_MIN_TEXT_LENGTH = 10
GROQ_MAX_TEXT_LENGTH = 10000

AFFILIATE_REVOLUT = "https://revolut.com/referral/?referral-code=radik5f35!JUL1-26-VR-EE&geo-redirect"
AFFILIATE_WISE = "https://wise.com/invite/arhc/radikm15"

PDF_PRICE = 5
VIP_PRICE = 15

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and GROQ_API_KEY environment variables")
