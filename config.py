import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
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

# Channel posting
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# Email newsletter
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
NEWSLETTER_FROM = os.getenv("NEWSLETTER_FROM", "EuroRent AI <noreply@eurorent.ai>")

# Travel time calculator (OpenStreetMap OSRM)
OSRM_URL = os.getenv("OSRM_URL", "http://router.project-osrm.org")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and GROQ_API_KEY environment variables")
