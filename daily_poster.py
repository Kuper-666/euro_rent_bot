import os
import json
import asyncio
import logging
import random
import re
import time
import secrets
import feedparser
import pytz
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LISTINGS_TABLE = "PendingListings"

bot = Bot(token=TELEGRAM_TOKEN)

if not GROUP_ID:
    logger.warning("GROUP_ID not set. Daily post will not work.")

RSS_FEED_URL = "https://www.google.com/alerts/feeds/15276190721492704538/14744967623754419043"

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None and SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def get_greeting():
    hour = datetime.now(pytz.timezone("Europe/Berlin")).hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 17:
        return "Добрый день"
    elif 17 <= hour < 22:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def strip_html(text: str) -> str:
    clean = re.sub(r'<[^>]+>', '', text)
    return clean.strip()


PENDING_FILE_FALLBACK = "pending_listings.json"


def _load_local_pending() -> dict:
    if os.path.exists(PENDING_FILE_FALLBACK):
        try:
            with open(PENDING_FILE_FALLBACK, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_local_pending(data: dict):
    now = time.time()
    data = {k: v for k, v in data.items() if now - v.get("ts", 0) < 3600}
    if len(data) > 500:
        sorted_items = sorted(data.items(), key=lambda x: x[1].get("ts", 0), reverse=True)
        data = dict(sorted_items[:500])
    with open(PENDING_FILE_FALLBACK, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def store_listing(url: str, title: str = "") -> str:
    """Сохраняет ссылку в Supabase (с локальным fallback) и возвращает короткий ID для callback_data."""
    sb = _get_supabase()
    short_id = secrets.token_urlsafe(6)[:8]
    if sb:
        try:
            sb.table(LISTINGS_TABLE).insert({
                "short_id": short_id,
                "url": url,
                "title": title,
                "created_at": datetime.now().isoformat()
            }).execute()
            return short_id
        except Exception as e:
            logger.warning(f"Supabase store_listing failed, falling back to local file: {e}")

    pending = _load_local_pending()
    pending[short_id] = {"url": url, "title": title, "ts": time.time()}
    _save_local_pending(pending)
    return short_id


def get_listing(short_id: str) -> dict:
    """Получает ссылку из Supabase (с локальным fallback) по короткому ID."""
    sb = _get_supabase()
    if sb:
        try:
            result = sb.table(LISTINGS_TABLE).select("url, title").eq("short_id", short_id).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning(f"Supabase get_listing failed, falling back to local file: {e}")

    return _load_local_pending().get(short_id, {})


async def send_daily_post():
    try:
        me = await bot.get_me()
        bot_username = me.username

        feed = feedparser.parse(RSS_FEED_URL)

        if not feed.entries:
            await bot.send_message(
                chat_id=GROUP_ID,
                text=f"{get_greeting()}! Сегодня нет свежих объявлений. Загляните позже!"
            )
            return

        random.shuffle(feed.entries)
        entry = feed.entries[0]

        title = strip_html(entry.title)
        link = entry.link
        summary = strip_html(entry.summary) if hasattr(entry, "summary") else "Подробнее по ссылке"

        short_id = store_listing(link, title)

        post_text = (
            f"{get_greeting()}! Свежее объявление:\n\n"
            f"{title}\n"
            f"{summary[:300]}\n\n"
            f"Ссылка: {link}\n\n"
            f"Хотите полный разбор?"
        )

        keyboard = [
            [InlineKeyboardButton("🔍 Да, проанализировать", callback_data=f"analyze_rss:{short_id}")],
            [InlineKeyboardButton("❌ Нет, спасибо", callback_data="skip_ad")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await bot.send_message(chat_id=GROUP_ID, text=post_text, reply_markup=reply_markup)
        logger.info("Дайджест отправлен!")

    except Exception as e:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=f"Ошибка: {e}"
        )
        logger.error(f"Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(send_daily_post())
