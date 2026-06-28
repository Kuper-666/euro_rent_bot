import os
import asyncio
import random
import re
import feedparser
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID", "-1004303604754"))

bot = Bot(token=TELEGRAM_TOKEN)

RSS_FEED_URL = "https://www.google.com/alerts/feeds/15276190721492704538/14744967623754419043"


def strip_html(text: str) -> str:
    clean = re.sub(r'<[^>]+>', '', text)
    return clean.strip()


async def send_daily_post():
    try:
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

        post_text = (
            f"Доброе утро! Свежее объявление:\n\n"
            f"{title}\n"
            f"{summary[:300]}\n\n"
            f"Ссылка: {link}\n\n"
            f"Хотите полный разбор?"
        )

        keyboard = [
            [InlineKeyboardButton("Да, проанализировать", callback_data=f"analyze_rss")],
            [InlineKeyboardButton("Нет, спасибо", callback_data="skip_rss")],
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
