import os
import asyncio
import random
import feedparser
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID", "-1004303604754"))

bot = Bot(token=TELEGRAM_TOKEN)

RSS_FEED_URL = "https://www.google.com/alerts/feeds/15276190721492704538/14744967623754419043"


async def send_daily_post():
    try:
        feed = feedparser.parse(RSS_FEED_URL)

        if not feed.entries:
            await bot.send_message(
                chat_id=GROUP_ID,
                text="Доброе утро! Сегодня нет свежих объявлений. Загляните позже!"
            )
            print("RSS пуста.")
            return

        random.shuffle(feed.entries)
        chosen = feed.entries[:2]

        post_text = "Доброе утро! Свежие объявления:\n\n"
        for entry in chosen:
            title = entry.title
            link = entry.link
            summary = entry.summary if hasattr(entry, "summary") else "Подробнее по ссылке"
            post_text += f"{title}\n{summary[:250]}...\n{link}\n\n"

        post_text += "Отправьте ссылку боту в личку для анализа!"

        keyboard = [[InlineKeyboardButton("Открыть бота", url="https://t.me/expat_rent_bot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await bot.send_message(chat_id=GROUP_ID, text=post_text, reply_markup=reply_markup)
        print("Дайджест отправлен!")

    except Exception as e:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=f"Ошибка RSS: {e}\nЗагляните на сайты сами!"
        )
        print(f"Ошибка RSS: {e}")


if __name__ == "__main__":
    asyncio.run(send_daily_post())
