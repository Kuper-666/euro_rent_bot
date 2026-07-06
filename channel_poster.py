"""
Автопостинг объявлений в Telegram-канал(ы).

Источники:
  1. Web-сканеры (Immowelt, WG-Gesucht, Rightmove) — основной источник
  2. Google Alerts RSS — запасной источник

Фильтрация:
  - Город, цена, тренды
  - AI-оценка >= 4/10
  - Holy Grail (>= 8/10 + низкая цена) → срочное уведомление

Расписание: раз в час (через scheduler.py)
"""

import dns_fix  # noqa: F401 — патч DNS для Windows (запускается как отдельный cron)
import os
import json
import asyncio
import random
import re
import logging
import time
from datetime import datetime, timezone
from groq import Groq
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from config import TELEGRAM_TOKEN, GROQ_API_KEY
from rent_scanner.formatting import create_url_token
from listing_features import (
    POPULAR_CITIES, detect_city, extract_price,
    record_listing, is_holy_grail, format_holy_grail_alert,
    record_price, get_trend, format_trend,
    is_good_deal,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
CHANNEL_ID = int(CHANNEL_ID) if CHANNEL_ID else None

CITY_CHANNELS = {}
_raw = os.environ.get("CITY_CHANNELS", "")
if _raw:
    try:
        CITY_CHANNELS = {k: int(v) for k, v in json.loads(_raw).items()}
    except Exception:
        logger.warning("Invalid CITY_CHANNELS JSON")

POSTED_FILE = "posted_listings.json"
MAX_POSTED_HISTORY = 500

# Городы для сканирования (ключ -> макс.цена)
SCAN_CITIES = {
    "berlin": 2000,
    "munich": 2500,
    "hamburg": 2000,
}

CHANNEL_SYSTEM_PROMPT = (
    "Ты — эксперт по аренде жилья в Европе. "
    "Сделай краткий анализ объявления (3-5 предложений). "
    "Выдели: реальную цену, скрытые платежи, район, риски. "
    "Оценка от 1 до 10. "
    "Отвечай на русском, кратко и по делу."
)

bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


POSTED_TABLE = "PostedListings"


def _get_sb():
    """Возвращает Supabase client или None."""
    try:
        from services.supabase_client import get_supabase
        return get_supabase()
    except Exception:
        return None


def load_posted():
    """Загружает список опубликованных URL из Supabase или JSON."""
    sb = _get_sb()
    if sb:
        try:
            result = sb.table(POSTED_TABLE).select("url").execute()
            urls = [r["url"] for r in (result.data or [])]
            return {"urls": urls, "last_run": ""}
        except Exception as e:
            logger.debug("Supabase load_posted failed: %s", e)
    # Fallback: локальный JSON
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"urls": [], "last_run": ""}


def save_posted(data):
    """Сохраняет URL в Supabase или JSON."""
    sb = _get_sb()
    if sb:
        try:
            # Сохраняем только новые URL (без дубликатов)
            for url in data["urls"][-MAX_POSTED_HISTORY:]:
                try:
                    sb.table(POSTED_TABLE).insert({"url": url}).execute()
                except Exception:
                    pass  # Уже существует (UNIQUE constraint)
            return
        except Exception as e:
            logger.debug("Supabase save_posted failed: %s", e)
    # Fallback: локальный JSON
    data["urls"] = data["urls"][-MAX_POSTED_HISTORY:]
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def fetch_web_listings() -> list[dict]:
    """Сканирует порталы недвижимости и возвращает объявления."""
    from web_scanner.parsers import scan_all_portals

    all_entries = []
    for city, max_price in SCAN_CITIES.items():
        try:
            listings = scan_all_portals(city, max_price)
            for l in listings:
                text = f"{l.title} {l.text}"
                all_entries.append({
                    "url": l.url,
                    "title": l.title,
                    "summary": l.text[:500],
                    "source": l.portal,
                    "city": city,
                    "price": l.price,
                })
            logger.info("Web scan %s: %d listings", city, len(listings))
        except Exception as e:
            logger.error("Web scan error for %s: %s", city, e)
        time.sleep(0.5)

    return all_entries


def fetch_rss_entries() -> list[dict]:
    """Запасной источник — Google Alerts RSS."""
    import feedparser

    RSS_FEED_URL = "https://www.google.com/alerts/feeds/15276190721492704538/14744967623754419043"
    entries = []
    try:
        feed = feedparser.parse(RSS_FEED_URL)
        for entry in feed.entries:
            url = entry.get("link", "")
            if not url:
                continue
            title = strip_html(entry.get("title", ""))
            summary = strip_html(entry.get("summary", ""))[:500]
            entries.append({"url": url, "title": title, "summary": summary, "source": "rss"})
    except Exception as e:
        logger.error("RSS feed error: %s", e)
    return entries


def analyze_listing(title: str, summary: str, url: str) -> str | None:
    if not groq_client:
        return None
    text = f"Объявление: {title}\n\nОписание: {summary}\n\nСсылка: {url}"
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CHANNEL_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("GROQ analysis error: %s", e)
        return None


def extract_score(analysis: str) -> int:
    match = re.search(r'(\d+)(?:\s*/\s*10|\s*из\s*10)', analysis)
    if match:
        return int(match.group(1))
    match = re.search(r'(?:оценка|рейтинг|score)[:\s]*(\d+)', analysis, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 5


def format_channel_post(entry: dict, analysis: str, bot_username: str,
                        city_key: str = None, price: float = None,
                        trend_info: str = "", is_deal: bool = False,
                        portal: str = "") -> str:
    city_info = POPULAR_CITIES.get(city_key, {}) if city_key else {}
    city_label = f"{city_info.get('emoji', '')} {city_info.get('name', '')}" if city_info else ""

    header = "🏠 Найдено объявление"
    if is_deal:
        header = "🔥 ВЫГОДНАЯ СДЕЛКА"
    if city_label:
        header += f" — {city_label}"

    portal_line = f"🌐 Источник: {portal}\n" if portal else ""

    price_line = ""
    if price and city_info.get("avg_price"):
        ratio = price / city_info["avg_price"]
        if ratio < 0.75:
            price_line = f"💰 {price:.0f} EUR/мес ({ratio:.0%} от средней в городе!)\n"
        elif ratio < 0.9:
            price_line = f"💰 {price:.0f} EUR/мес (ниже средней)\n"
        else:
            price_line = f"💰 {price:.0f} EUR/мес\n"
    elif price:
        price_line = f"💰 {price:.0f} EUR/мес\n"

    trend_line = f"\n{trend_info}" if trend_info else ""

    return (
        f"{header}\n\n"
        f"📌 {entry['title']}\n\n"
        f"{portal_line}{price_line}"
        f"{analysis}\n"
        f"{trend_line}\n\n"
        f"🔗 {entry['url']}"
    )


async def post_to_channel(chat_id: int, text: str, bot_username: str, listing_url: str):
    if not bot or not chat_id:
        return False

    analyze_url = f"https://t.me/{bot_username}?start=an_{create_url_token(listing_url)}"
    keyboard = [
        [InlineKeyboardButton("🔍 Полный анализ", url=analyze_url)],
        [InlineKeyboardButton("🤖 Начать с ботом", url=f"https://t.me/{bot_username}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        return True
    except Exception as e:
        logger.error("Failed to post to %s: %s", chat_id, e)
        return False


async def send_holy_grail_alert(entry: dict, bot_username: str):
    if not bot:
        return
    alert_text = format_holy_grail_alert(entry, bot_username)
    city = entry.get("city", "")
    channel_ids = set()

    if CHANNEL_ID:
        channel_ids.add(CHANNEL_ID)
    if city in CITY_CHANNELS:
        channel_ids.add(CITY_CHANNELS[city])

    analyze_url = f"https://t.me/{bot_username}?start=an_{create_url_token(entry['url'])}"
    keyboard = [
        [InlineKeyboardButton("⚡ ЗАБРАТЬ!", url=analyze_url)],
        [InlineKeyboardButton("🤖 Анализ в боте", url=f"https://t.me/{bot_username}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for cid in channel_ids:
        try:
            await bot.send_message(chat_id=cid, text=alert_text, reply_markup=reply_markup)
            logger.info("Holy grail alert sent to %s", cid)
        except Exception as e:
            logger.error("Failed to send holy grail to %s: %s", cid, e)


async def run_channel_post():
    posted = load_posted()

    # 1. Сканируем порталы
    entries = fetch_web_listings()

    # 2. Добавляем RSS как запасной источник
    rss_entries = fetch_rss_entries()
    entries.extend(rss_entries)

    if not entries:
        logger.info("No entries found from any source")
        return

    # 3. Фильтруем уже опубликованные
    new_entries = [e for e in entries if e["url"] not in posted["urls"]]
    if not new_entries:
        logger.info("All %d entries already posted", len(entries))
        return

    # 4. Сортируем: сначала с ценой, потом случайно
    new_entries.sort(key=lambda e: (0 if e.get("price") else 1, random.random()))

    # 5. Берём до 5 на постинг
    to_post = new_entries[:5]
    logger.info("Processing %d new entries (from %d total)", len(to_post), len(entries))

    me = await bot.get_me()
    bot_username = me.username

    posted_count = 0
    for entry in to_post:
        full_text = f"{entry['title']} {entry['summary']}"
        city_key = entry.get("city") or detect_city(full_text)
        price = entry.get("price") or extract_price(full_text)
        portal = entry.get("source", "")

        analysis = analyze_listing(entry["title"], entry["summary"], entry["url"])
        if not analysis:
            continue

        score = extract_score(analysis)

        is_grail, grail_reason = record_listing(
            url=entry["url"],
            city=city_key or "",
            price=price or 0,
            score=score,
            text=full_text,
        )

        if score < 4:
            logger.info("Skipping low-score (%d/10): %s", score, entry["title"][:50])
            continue

        deal = is_good_deal(city_key, price) if city_key and price else False
        trend_text = format_trend(city_key) if city_key and price else ""

        text = format_channel_post(
            entry, analysis, bot_username,
            city_key=city_key, price=price,
            trend_info=trend_text, is_deal=deal, portal=portal,
        )

        main_channel = CHANNEL_ID
        city_channel = CITY_CHANNELS.get(city_key) if city_key else None

        if main_channel:
            success = await post_to_channel(main_channel, text, bot_username, entry["url"])
            if success:
                posted_count += 1

        if city_channel and city_channel != main_channel:
            await post_to_channel(city_channel, text, bot_username, entry["url"])

        if is_grail:
            await send_holy_grail_alert({
                "url": entry["url"],
                "city": city_key,
                "price": price,
                "score": score,
                "grail_reason": grail_reason,
            }, bot_username)

        posted["urls"].append(entry["url"])
        logger.info("Posted: %s (score: %d/10, city: %s, portal: %s)",
                     entry["title"][:50], score, city_key or "?", portal)
        await asyncio.sleep(2)

    posted["last_run"] = datetime.now(timezone.utc).isoformat()
    save_posted(posted)
    logger.info("Done. Posted %d/%d listings", posted_count, len(to_post))


if __name__ == "__main__":
    asyncio.run(run_channel_post())
