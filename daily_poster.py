import os
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROUP_ID = os.environ.get("GROUP_ID", "-1001234567890")

bot = Bot(token=TELEGRAM_TOKEN)


async def send_daily_post():
    ad_text = (
        "Доброе утро! Вот свежее объявление для анализа:\n\n"
        "Квартира в Берлине, 2 комнаты, 65 кв.м\n"
        "Холодная: 950 EUR, тёплая: 1200 EUR\n"
        "Каution: 2 мес, Nebenkosten: 250 EUR\n"
        "Контакт: Herr Schmidt\n\n"
        "Хотите, чтобы я проанализировал это объявление? "
        "Просто отправьте ссылку или текст боту в личку!"
    )

    keyboard = [
        [InlineKeyboardButton("Открыть бота", url="https://t.me/expat_rent_bot")],
        [InlineKeyboardButton("Помощь", url="https://t.me/expat_rent_bot?start=help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=int(GROUP_ID),
        text=ad_text,
        reply_markup=reply_markup,
    )
    print("Post sent!")


if __name__ == "__main__":
    asyncio.run(send_daily_post())
