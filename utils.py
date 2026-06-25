import os
import json
import re
import requests
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
from io import BytesIO
from telegram import Update

from config import DATA_FILE, FREE_LIMIT
from messages import DEFAULT_LANG, MESSAGES


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


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
    if user["balance"] == -1:
        return True
    if user["balance"] > 0:
        return True
    if user["free_used"] < FREE_LIMIT:
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
    return str(FREE_LIMIT - user["free_used"])
