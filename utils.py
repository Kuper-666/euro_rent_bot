import re
import time
import hashlib
import requests
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
from io import BytesIO
from telegram import Update
from collections import OrderedDict

from config import FREE_LIMIT, SUBSCRIPTION_DAYS, GROQ_RATE_LIMIT_SECONDS
from messages import DEFAULT_LANG, MESSAGES
from storage import load_data, save_data


class LimitedDict(OrderedDict):
    def __init__(self, max_size=10000, ttl=3600):
        super().__init__()
        self.max_size = max_size
        self.ttl = ttl

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        elif len(self) >= self.max_size:
            self._cleanup()
            if len(self) >= self.max_size:
                self.popitem(last=False)
        super().__setitem__(key, (value, time.time()))

    def __getitem__(self, key):
        value, ts = super().__getitem__(key)
        if self.ttl and time.time() - ts > self.ttl:
            del self[key]
            raise KeyError(key)
        return value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def _cleanup(self):
        now = time.time()
        stale = [k for k, (_, ts) in self.items() if now - ts > self.ttl]
        for k in stale:
            del self[k]


_last_groq_call = LimitedDict(max_size=10000, ttl=3600)


def get_lang(update: Update) -> str:
    try:
        from utils import load_data, get_user_data
        user_id = str(update.effective_user.id)
        data = load_data()
        user = get_user_data(data, user_id)
        saved = user.get("lang")
        if saved and saved in MESSAGES:
            return saved
    except Exception:
        pass
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
        user["total_checks"] = user.get("total_checks", 0) + 1
        return
    if user["balance"] > 0:
        user["balance"] -= 1
    else:
        user["free_used"] += 1
    user["total_checks"] = user.get("total_checks", 0) + 1


def is_url(text: str) -> bool:
    return bool(re.match(r'https?://', text.strip()))


def resolve_redirect_url(url: str) -> str:
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    if parsed.hostname and "google" in parsed.hostname and "/url" in parsed.path:
        params = parse_qs(parsed.query)
        if "url" in params:
            return params["url"][0]
    return url


def fetch_url_text(url: str) -> str:
    url = resolve_redirect_url(url)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "meta", "noscript", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 5]
        result = "\n".join(lines)
        if len(result) > 6000:
            result = result[:6000] + "... (текст сокращён для анализа)"
        return result
    except requests.exceptions.Timeout:
        return "ERROR: Timeout — сайт не ответил за 10 секунд"
    except requests.exceptions.ConnectionError:
        return "ERROR: Не удалось подключиться к сайту"
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
    return str(max(0, FREE_LIMIT - user.get("free_used", 0)))


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


def clean_text(text: str) -> str:
    return text.replace('\xa0', ' ').replace('\u200b', '').strip()


def validate_pdf_data(data: dict) -> tuple[bool, str]:
    required_fields = ["name", "dob", "phone", "email", "address", "employer", "income", "occupants"]
    missing = [f for f in required_fields if not data.get(f, "").strip()]
    if missing:
        return False, f"Отсутствуют данные: {', '.join(missing)}"
    if len(data.get("name", "").strip()) < 3:
        return False, "Имя должно быть минимум 3 символа"
    if len(data.get("email", "").strip()) < 5 or "@" not in data.get("email", ""):
        return False, "Некорректный email"
    if len(data.get("phone", "").strip()) < 5:
        return False, "Некорректный номер телефона"
    return True, ""


def is_pdf_state_expired(user: dict, timeout_seconds: int = 1800) -> bool:
    if user.get("pdf_state") != "awaiting_data":
        return False
    pdf_started = user.get("pdf_started_at", 0)
    if not pdf_started:
        return True
    return (time.time() - pdf_started) > timeout_seconds


def hash_user_id(user_id: str, salt: str = "eurorent2024") -> str:
    return hashlib.sha256(f"{user_id}{salt}".encode()).hexdigest()[:16]
