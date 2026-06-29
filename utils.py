import re
import time
import requests
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
from io import BytesIO
from telegram import Update

from config import FREE_LIMIT, SUBSCRIPTION_DAYS, GROQ_RATE_LIMIT_SECONDS
from messages import DEFAULT_LANG, MESSAGES
from storage import load_data, save_data

_last_groq_call: dict[str, float] = {}


def get_lang(update: Update) -> str:
    lang_code = update.effective_user.language_code
    if lang_code:
        short = lang_code.split("-")[0].lower()
        if short in MESSAGES:
            return short
    return DEFAULT_LANG


def get_user_data(data: dict, user_id: str) -> dict:
    if user_id not in data:
        data[user_id] = {"free_used": 0, "balance": 0}
    return data[user_id]


def can_use(user: dict) -> bool:
    if user.get("balance") == -1:
        last_paid = user.get("last_paid_at", 0)
        if last_paid and (time.time() - last_paid) > SUBSCRIPTION_DAYS * 86400:
            user["balance"] = 0
            return False
        return True
    if user.get("balance", 0) > 0:
        return True
    if user.get("free_used", 0) < FREE_LIMIT:
        return True
    return False


def use_check(user: dict):
    if user["balance"] == -1:
        return
    if user["balance"] > 0:
        user["balance"] -= 1
    else:
        user["free_used"] += 1


def is_url(text: str) -> bool:
    return bool(re.match(r'https?://', text.strip()))


def fetch_url_text(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 10]
        return "\n".join(lines[:200])
    except Exception as e:
        return f"ERROR: {e}"


def ocr_from_photo(photo_bytes: bytes) -> str:
    try:
        image = Image.open(BytesIO(photo_bytes))
        text = pytesseract.image_to_string(image, lang="eng+rus+ukr+deu+pol")
        return text.strip()
    except Exception as e:
        return f"ERROR: {e}"


def calc_remaining(user: dict) -> str:
    if user["balance"] == -1:
        return "∞"
    if user["balance"] > 0:
        return str(user["balance"])
    return str(FREE_LIMIT - user.get("free_used", 0))


def check_rate_limit(user_id: str) -> tuple[bool, float]:
    now = time.time()
    last = _last_groq_call.get(user_id, 0)
    elapsed = now - last
    if elapsed < GROQ_RATE_LIMIT_SECONDS:
        return False, GROQ_RATE_LIMIT_SECONDS - elapsed
    _last_groq_call[user_id] = now
    return True, 0


def sanitize_pdf_input(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\w\s.,@+\-()/üöäÜÖÄßéèêëàâîïôûùçñÿäëöüÉÈÊËÀÂÎÏÔÛÙÇÑÿÄËÖÜ\-\n\r]', '', text)
    lines = text.strip().split('\n')
    return '\n'.join(line.strip() for line in lines if line.strip())
