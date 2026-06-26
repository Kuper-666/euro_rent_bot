import os
import asyncio
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID", "-1004303604754"))

bot = Bot(token=TELEGRAM_TOKEN)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

GREETINGS = [
    "Доброе утро! Вот свежие объявления:",
    "Новый день — новые варианты!",
    "Свежие объявления с немецких площадок:",
    "Подборка квартир на сегодня:",
    "Горячие предложения дня:",
]

TIPS = [
    "Совет: проверьте Nebenkosten перед оплатой!",
    "Не забудьте спросить про Kaution!",
    "Проверьте Mindestmietdauer!",
    "Уточните, включены ли коммунальные услуги!",
    "Попросите фото при заселении!",
]


def parse_kleinanzeigen():
    url = "https://www.kleinanzeigen.de/s-wohnung-mieten/berlin/k0l208"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("article", class_="aditem")
        results = []
        for item in items[:8]:
            try:
                title = item.find("h2", class_="text-module-begin")
                price = item.find("div", class_="aditem-main--middle--price-shipping")
                link = item.find("a", class_="ellipsis")
                t = title.text.strip() if title else "Без названия"
                p = price.text.strip() if price else "Цена не указана"
                l = link["href"] if link else ""
                if l and not l.startswith("http"):
                    l = "https://www.kleinanzeigen.de" + l
                results.append({"source": "Kleinanzeigen", "title": t, "price": p, "link": l})
            except Exception:
                continue
        return results
    except Exception:
        return []


def parse_immowelt():
    url = "https://www.immowelt.de/classified-search/wohnung-mieten/berlin"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("div", class_="list-entry")
        results = []
        for item in items[:8]:
            try:
                title = item.find("h2", class_="list-entry-title")
                price = item.find("div", class_="list-entry-price")
                link = item.find("a", class_="list-entry-link")
                t = title.text.strip() if title else "Без названия"
                p = price.text.strip() if price else "Цена не указана"
                l = link["href"] if link else ""
                if l and not l.startswith("http"):
                    l = "https://www.immowelt.de" + l
                results.append({"source": "Immowelt", "title": t, "price": p, "link": l})
            except Exception:
                continue
        return results
    except Exception:
        return []


def parse_immoscout():
    url = "https://www.immobilienscout24.de/Suche/de/berlin/wohnung-mieten"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("div", class_="result-list-entry")
        results = []
        for item in items[:8]:
            try:
                title = item.find("h2", class_="result-list-entry-title")
                price = item.find("div", class_="result-list-entry-price")
                link = item.find("a", class_="result-list-entry-link")
                t = title.text.strip() if title else "Без названия"
                p = price.text.strip() if price else "Цена не указана"
                l = link["href"] if link else ""
                if l and not l.startswith("http"):
                    l = "https://www.immobilienscout24.de" + l
                results.append({"source": "ImmoScout24", "title": t, "price": p, "link": l})
            except Exception:
                continue
        return results
    except Exception:
        return []


async def send_daily_post():
    today = datetime.now().strftime("%d.%m.%Y")

    all_results = []
    all_results.extend(parse_kleinanzeigen())
    all_results.extend(parse_immowelt())
    all_results.extend(parse_immoscout())

    if not all_results:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=f"Доброе утро! ({today})\nСегодня нет свежих объявлений. Загляните позже!"
        )
        return

    random.shuffle(all_results)
    chosen = all_results[:3]

    greeting = random.choice(GREETINGS)
    tip = random.choice(TIPS)

    post_text = f"🏠 {greeting}\n\n"
    for entry in chosen:
        post_text += (
            f"📍 {entry['title']}\n"
            f"💰 {entry['price']}\n"
            f"🔗 {entry['link']}\n\n"
        )

    post_text += f"💡 {tip}\n\n"
    post_text += "Отправьте ссылку боту в личку для полного анализа!"

    keyboard = [[InlineKeyboardButton("🚀 Открыть бота", url="https://t.me/expat_rent_bot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(chat_id=GROUP_ID, text=post_text, reply_markup=reply_markup)
    print(f"Digest sent for {today}!")


if __name__ == "__main__":
    asyncio.run(send_daily_post())
