import os
import json
import asyncio
import random
import re
import time
import feedparser
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID") or "-1004303604754")

bot = Bot(token=TELEGRAM_TOKEN)

RSS_FEED_URL = "https://www.google.com/alerts/feeds/15276190721492704538/14744967623754419043"

PENDING_FILE = "pending_listings.json"


def strip_html(text: str) -> str:
    clean = re.sub(r'<[^>]+>', '', text)
    return clean.strip()


def load_pending():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r") as f:
            return json.load(f)
    return {}


def save_pending(data):
    # Очищаем записи старше 1 часа
    now = time.time()
    data = {k: v for k, v in data.items() if now - v.get("ts", 0) < 3600}
    with open(PENDING_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def store_listing(url: str, title: str = "") -> str:
    """Сохраняет ссылку и возвращает короткий ID для callback_data."""
    pending = load_pending()
    short_id = f"rss_{len(pending) + 1}_{int(time.time()) % 10000}"
    pending[short_id] = {"url": url, "title": title, "ts": time.time()}
    save_pending(pending)
    return short_id


async def send_daily_post():
    try:
        me = await bot.get_me()
        bot_username = me.username

        feed = feedparser.parse(RSS_FEED_URL)

        if not feed.entries:
            await bot.send_message(
                chat_id=GROUP_ID,
                text="Доброе утро! Сегодня нет свежих объявлений. Загляните позже!"
            )
            return

        random.shuffle(feed.entries)
        entry = feed.entries[0]

        title = entry.title
        link = entry.link
        summary = strip_html(entry.summary) if hasattr(entry, "summary") else "Подробнее по ссылке"

        # Сохраняем ссылку и получаем ID для кнопки
        short_id = store_listing(link, title)

        post_text = (
            f"Доброе утро! Свежее объявление:\n\n"
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
        print("Дайджест отправлен!")

    except Exception as e:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=f"Ошибка: {e}"
        )
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(send_daily_post())
