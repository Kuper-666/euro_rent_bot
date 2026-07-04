"""
Фильтр по городу, детектор трендов, уведомления о "святых граалях".
"""

import os
import json
import re
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

CITIES_FILE = "cities_config.json"
TRENDS_FILE = "price_trends.json"
HISTORY_FILE = "listing_history.json"

POPULAR_CITIES = {
    "berlin": {"name": "Берлин", "name_en": "Berlin", "name_de": "Berlin", "avg_price": 850, "emoji": "🇩🇪"},
    "munich": {"name": "Мюнхен", "name_en": "Munich", "name_de": "München", "avg_price": 1100, "emoji": "🇩🇪"},
    "hamburg": {"name": "Гамбург", "name_en": "Hamburg", "name_de": "Hamburg", "avg_price": 780, "emoji": "🇩🇪"},
    "frankfurt": {"name": "Франкфурт", "name_en": "Frankfurt", "name_de": "Frankfurt", "avg_price": 900, "emoji": "🇩🇪"},
    "cologne": {"name": "Кёльн", "name_en": "Cologne", "name_de": "Köln", "avg_price": 750, "emoji": "🇩🇪"},
    "vienna": {"name": "Вена", "name_en": "Vienna", "name_de": "Wien", "avg_price": 800, "emoji": "🇦🇹"},
    "amsterdam": {"name": "Амстердам", "name_en": "Amsterdam", "name_de": "Amsterdam", "avg_price": 1200, "emoji": "🇳🇱"},
    "barcelona": {"name": "Барселона", "name_en": "Barcelona", "name_de": "Barcelona", "avg_price": 900, "emoji": "🇪🇸"},
    "madrid": {"name": "Мадрид", "name_en": "Madrid", "name_de": "Madrid", "avg_price": 750, "emoji": "🇪🇸"},
    "lisbon": {"name": "Лиссабон", "name_en": "Lisbon", "name_de": "Lissabon", "avg_price": 700, "emoji": "🇵🇹"},
    "porto": {"name": "Порту", "name_en": "Porto", "name_de": "Porto", "avg_price": 600, "emoji": "🇵🇹"},
    "prague": {"name": "Прага", "name_en": "Prague", "name_de": "Praha", "avg_price": 650, "emoji": "🇨🇿"},
    "warsaw": {"name": "Варшава", "name_en": "Warsaw", "name_de": "Warszawa", "avg_price": 550, "emoji": "🇵🇱"},
    "krakow": {"name": "Краков", "name_en": "Kraków", "name_de": "Krakau", "avg_price": 500, "emoji": "🇵🇱"},
    "paris": {"name": "Париж", "name_en": "Paris", "name_de": "Paris", "avg_price": 1300, "emoji": "🇫🇷"},
    "lyon": {"name": "Лион", "name_en": "Lyon", "name_de": "Lyon", "avg_price": 800, "emoji": "🇫🇷"},
    "rome": {"name": "Рим", "name_en": "Rome", "name_de": "Roma", "avg_price": 850, "emoji": "🇮🇹"},
    "milan": {"name": "Милан", "name_en": "Milan", "name_de": "Mailand", "avg_price": 900, "emoji": "🇮🇹"},
    "dublin": {"name": "Дублин", "name_en": "Dublin", "name_de": "Dublin", "avg_price": 1400, "emoji": "🇮🇪"},
    "budapest": {"name": "Будапешт", "name_en": "Budapest", "name_de": "Budapest", "avg_price": 500, "emoji": "🇭🇺"},
    "zurich": {"name": "Цюрих", "name_en": "Zurich", "name_de": "Zürich", "avg_price": 1500, "emoji": "🇨🇭"},
}


def _load_json(path: str, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def _save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================================
# 1. ФИЛЬТР ПО ГОРОДУ
# ============================================================================

def get_user_city(user_id: str) -> Optional[str]:
    """Возвращает ключ города пользователя (например 'berlin')"""
    cities = _load_json(CITIES_FILE)
    return cities.get(user_id)


def set_user_city(user_id: str, city_key: str) -> bool:
    """Устанавливает город для пользователя"""
    city_key = city_key.lower().strip()
    if city_key not in POPULAR_CITIES:
        return False
    cities = _load_json(CITIES_FILE)
    cities[user_id] = city_key
    _save_json(CITIES_FILE, cities)
    return True


def remove_user_city(user_id: str) -> bool:
    """Удаляет фильтр города"""
    cities = _load_json(CITIES_FILE)
    if user_id in cities:
        del cities[user_id]
        _save_json(CITIES_FILE, cities)
        return True
    return False


def get_city_info(city_key: str) -> Optional[dict]:
    """Информация о городе"""
    return POPULAR_CITIES.get(city_key.lower())


def list_cities() -> str:
    """Список доступных городов"""
    lines = []
    for key, info in sorted(POPULAR_CITIES.items(), key=lambda x: x[1]["avg_price"]):
        lines.append(f"{info['emoji']} {info['name']} ({info['name_en']}) — ~{info['avg_price']} EUR/мес")
    return "\n".join(lines)


def detect_city(text: str) -> Optional[str]:
    """Определяет город из текста объявления (EN/RU/DE + романизации)"""
    text_lower = text.lower()
    for key, info in POPULAR_CITIES.items():
        names = [
            info["name_en"].lower(),
            info["name"].lower(),
            info.get("name_de", "").lower(),
        ]
        # Добавляем частые романизации
        if key == "munich":
            names.extend(["muenchen", "munchen"])
        elif key == "cologne":
            names.extend(["koln", "koeln"])
        elif key == "zurich":
            names.extend(["zuerich"])
        elif key == "vienna":
            names.extend(["wien"])
        elif key == "lisbon":
            names.extend(["lisboa", "lissabon"])
        elif key == "milan":
            names.extend(["milano"])
        elif key == "krakow":
            names.extend(["kraków", "krakau"])
        elif key == "porto":
            names.extend(["oporto"])
        for name in names:
            if name and name in text_lower:
                return key
    return None


def filter_by_city(entries: list[dict], city_key: str) -> list[dict]:
    """Фильтрует объявления по городу"""
    if not city_key:
        return entries
    city_info = POPULAR_CITIES.get(city_key.lower())
    if not city_info:
        return entries
    city_name_en = city_info["name_en"].lower()
    city_name_ru = city_info["name"].lower()
    filtered = []
    for entry in entries:
        text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
        if city_name_en in text or city_name_ru in text:
            filtered.append(entry)
    return filtered


# ============================================================================
# 2. ДЕТЕКТОР ТРЕНДОВ (ЦЕНА РАСТЕТ / ПАДАЕТ)
# ============================================================================

def extract_price(text: str) -> Optional[int]:
    """Извлекает цену из текста объявления (EUR)"""
    patterns = [
        r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:EUR|€|евро)',
        r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:pro\s*Monat|monatlich)',
        r'(?:Kaltmiete|Warmmiete|Total):?\s*(\d{1,3}(?:[.,]\d{3})*)',
        r'(\d{1,3}(?:[.,]\d{3})*)\s*/\s*month',
        r'price[:\s]*(\d{1,3}(?:[.,]\d{3})*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(".", "").replace(",", "")
            try:
                return int(price_str)
            except ValueError:
                continue
    return None


def extract_score(text: str) -> int:
    """Извлекает оценку (1-10) из текста анализа"""
    match = re.search(r'(\d+)(?:\s*/\s*10|\s*из\s*10)', text)
    if match:
        return int(match.group(1))
    match = re.search(r'(?:оценка|рейтинг|score)[:\s]*(\d+)', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 5


def record_price(city_key: str, price: int, url: str = ""):
    """Записывает цену для отслеживания тренда"""
    trends = _load_json(TRENDS_FILE)
    if city_key not in trends:
        trends[city_key] = {"prices": [], "avg": 0, "trend": "stable"}

    entry = {
        "price": price,
        "timestamp": time.time(),
        "url": url,
    }
    trends[city_key]["prices"].append(entry)

    # Храним только последние 200 записей
    trends[city_key]["prices"] = trends[city_key]["prices"][-200:]

    # Пересчитываем среднее и тренд
    prices = [p["price"] for p in trends[city_key]["prices"]]
    trends[city_key]["avg"] = round(sum(prices) / len(prices)) if prices else 0

    if len(prices) >= 5:
        recent = prices[-5:]
        older = prices[-15:-5] if len(prices) >= 15 else prices[:len(prices)//2]
        if older:
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            change_pct = ((recent_avg - older_avg) / older_avg) * 100
            if change_pct > 10:
                trends[city_key]["trend"] = "rising"
                trends[city_key]["trend_pct"] = round(change_pct, 1)
            elif change_pct < -10:
                trends[city_key]["trend"] = "falling"
                trends[city_key]["trend_pct"] = round(change_pct, 1)
            else:
                trends[city_key]["trend"] = "stable"
                trends[city_key]["trend_pct"] = round(change_pct, 1)

    _save_json(TRENDS_FILE, trends)


def get_trend(city_key: str) -> dict:
    """Получает тренд по городу"""
    trends = _load_json(TRENDS_FILE)
    city_data = trends.get(city_key, {})
    return {
        "city": city_key,
        "avg_price": city_data.get("avg", 0),
        "trend": city_data.get("trend", "unknown"),
        "trend_pct": city_data.get("trend_pct", 0),
        "data_points": len(city_data.get("prices", [])),
    }


def format_trend(city_key: str) -> str:
    """Форматирует тренд для отображения"""
    info = POPULAR_CITIES.get(city_key, {})
    city_name = info.get("name", city_key)
    trend = get_trend(city_key)

    if trend["trend"] == "rising":
        arrow = "📈 Растёт"
        emoji = "🔴"
        detail = f"+{trend['trend_pct']}% за последние недели"
    elif trend["trend"] == "falling":
        arrow = "📉 Падает"
        emoji = "🟢"
        detail = f"{trend['trend_pct']}% за последние недели"
    elif trend["trend"] == "stable":
        arrow = "➡️ Стабильно"
        emoji = "🟡"
        detail = f"~{trend['trend_pct']}%"
    else:
        arrow = "❓ Недостаточно данных"
        emoji = "⚪"
        detail = f"Точек: {trend['data_points']}"

    return (
        f"{emoji} Тренд в {city_name}:\n"
        f"{arrow}\n"
        f"Средняя цена: ~{trend['avg_price']} EUR/мес\n"
        f"{detail}"
    )


def is_good_deal(city_key: str, price: int) -> bool:
    """Проверяет, является ли цена выгодной сделкой"""
    info = POPULAR_CITIES.get(city_key, {})
    avg = info.get("avg_price", 0)
    if avg == 0:
        return False
    return price < avg * 0.75


# ============================================================================
# 3. УВЕДОМЛЕНИЯ О "СВЯТЫХ ГРААЛЯХ" (ИДЕАЛЬНЫЕ КВАРТИРЫ)
# ============================================================================

def _load_history() -> dict:
    return _load_json(HISTORY_FILE, {"listings": [], "alerts_sent": 0})


def _save_history(data: dict):
    data["listings"] = data["listings"][-500:]
    _save_json(HISTORY_FILE, data)


def is_holy_grail(score: int, price: int, city_key: str, text: str) -> tuple[bool, str]:
    """
    Определяет, является ли объявление "святым граалем".
    Возвращает (is_grail, reason).
    """
    reasons = []
    info = POPULAR_CITIES.get(city_key, {})
    avg_price = info.get("avg_price", 0)

    # Критерий 1: Высокая оценка
    if score >= 8:
        reasons.append(f"Высокая оценка ({score}/10)")
    else:
        return False, ""

    # Критерий 2: Хорошая цена
    if avg_price > 0 and price > 0:
        ratio = price / avg_price
        if ratio <= 0.7:
            reasons.append(f"Цена {price} EUR ({ratio:.0%} от средней)")
        elif ratio <= 0.85:
            reasons.append(f"Цена ниже средней")
        else:
            return False, ""

    # Критерий 3: Характеристики идеальной квартиры
    text_lower = text.lower()
    bonus_features = {
        "miete inkl": "Включены все платежи",
        "warmmiete": "Тёплая аренда",
        "möbliert": "Меблирована",
        "balcon": "Балкон",
        "balkon": "Балкон",
        "terrasse": "Терраса",
        "parkplatz": "Парковка",
        "boden": "Новый ремонт",
        "renoviert": "Реновирована",
        "ebd": "Без комиссии",
        "keine provision": "Без комиссии",
        "schufa": "Без Schufa",
    }
    found_bonuses = []
    for keyword, desc in bonus_features.items():
        if keyword in text_lower:
            found_bonuses.append(desc)
    if found_bonuses:
        reasons.append(f"Плюсы: {', '.join(found_bonuses[:3])}")

    if len(reasons) >= 2:
        return True, " | ".join(reasons)
    return False, ""


def record_listing(url: str, city: str, price: int, score: int, text: str = ""):
    """Записывает объявление в историю для анализа"""
    history = _load_history()
    entry = {
        "url": url,
        "city": city,
        "price": price,
        "score": score,
        "timestamp": time.time(),
        "is_holy_grail": False,
    }
    if price > 0 and city:
        record_price(city, price, url)

    is_grail, reason = is_holy_grail(score, price, city, text)
    if is_grail:
        entry["is_holy_grail"] = True
        entry["grail_reason"] = reason
        history["alerts_sent"] = history.get("alerts_sent", 0) + 1

    history["listings"].append(entry)
    _save_history(history)
    return is_grail, reason


def get_holy_grail_stats() -> dict:
    """Статистика по святым граалям"""
    history = _load_history()
    grails = [l for l in history["listings"] if l.get("is_holy_grail")]
    return {
        "total_listings": len(history["listings"]),
        "holy_grails": len(grails),
        "alerts_sent": history.get("alerts_sent", 0),
        "recent_grails": grails[-5:] if grails else [],
    }


def format_holy_grail_alert(entry: dict, bot_username: str) -> str:
    """Форматирует уведомление о святом граале"""
    from rent_scanner.formatting import create_url_token
    analyze_url = f"https://t.me/{bot_username}?start=an_{create_url_token(entry['url'])}"
    city_info = POPULAR_CITIES.get(entry.get("city", ""), {})
    city_name = city_info.get("name", entry.get("city", "Неизвестно"))

    return (
        f"🏆 СВЯТОЙ ГРААЛЬ НАЙДЕН!\n\n"
        f"📌 Город: {city_name}\n"
        f"💰 Цена: {entry.get('price', '?')} EUR/мес\n"
        f"⭐ Оценка: {entry.get('score', '?')}/10\n\n"
        f"📋 Причины:\n{entry.get('grail_reason', 'Идеальное сочетание цены и качества')}\n\n"
        f"🔗 {entry['url']}\n\n"
        f"⚡ Успей забрать! Полный анализ: {analyze_url}"
    )


# ============================================================================
# ИНТЕГРАЦИЯ С BOT.PY — КОМАНДЫ
# ============================================================================

async def cmd_set_city(update, context) -> None:
    """Команда /set_city berlin"""
    from storage import load_data, save_data
    user_id = str(update.effective_user.id)

    if not context.args:
        text = (
            "🏙 Выберите город для фильтрации объявлений:\n\n"
            f"{list_cities()}\n\n"
            "Использование: /set_city berlin"
        )
        await update.message.reply_text(text)
        return

    city_key = context.args[0].lower()
    if set_user_city(user_id, city_key):
        info = POPULAR_CITIES[city_key]
        await update.message.reply_text(
            f"✅ Город установлен: {info['emoji']} {info['name']}\n\n"
            f"Теперь я буду показывать объявления только из {info['name']}.\n"
            f"Средняя цена: ~{info['avg_price']} EUR/мес\n\n"
            f"Снять фильтр: /remove_city"
        )
    else:
        await update.message.reply_text(
            f"❌ Город не найден. Доступные города:\n\n{list_cities()}"
        )


async def cmd_remove_city(update, context) -> None:
    """Команда /remove_city"""
    user_id = str(update.effective_user.id)
    if remove_user_city(user_id):
        await update.message.reply_text("✅ Фильтр города снят. Показываю все объявления.")
    else:
        await update.message.reply_text("ℹ️ Фильтр города не был установлен.")


async def cmd_my_city(update, context) -> None:
    """Команда /my_city"""
    user_id = str(update.effective_user.id)
    city = get_user_city(user_id)
    if city:
        info = POPULAR_CITIES[city]
        trend = format_trend(city)
        await update.message.reply_text(
            f"🏙 Ваш город: {info['emoji']} {info['name']} ({info['name_en']})\n"
            f"Средняя цена: ~{info['avg_price']} EUR/мес\n\n"
            f"{trend}\n\n"
            f"Изменить: /set_city <город>\n"
            f"Снять: /remove_city"
        )
    else:
        await update.message.reply_text(
            "🏙 Фильтр города не установлен.\n\n"
            f"Доступные города:\n{list_cities()}\n\n"
            "Установить: /set_city berlin"
        )


async def cmd_trend(update, context) -> None:
    """Команда /trend berlin"""
    if not context.args:
        await update.message.reply_text(
            "📊 Узнать тренд цен по городу:\n\n"
            "/trend berlin\n/trend munich\n/trend vienna\n\n"
            f"Доступные города:\n{list_cities()}"
        )
        return

    city_key = context.args[0].lower()
    if city_key not in POPULAR_CITIES:
        await update.message.reply_text(f"❌ Город не найден. Доступные: {list_cities()}")
        return

    info = POPULAR_CITIES[city_key]
    trend = format_trend(city_key)
    history = _load_history()
    city_listings = [l for l in history["listings"] if l.get("city") == city_key]
    grails = [l for l in city_listings if l.get("is_holy_grail")]

    text = (
        f"{info['emoji']} {info['name']} ({info['name_en']})\n\n"
        f"{trend}\n\n"
        f"Всего объявлений: {len(city_listings)}\n"
        f"Святых граалей: {len(grails)}"
    )
    await update.message.reply_text(text)


async def cmd_holygrail(update, context) -> None:
    """Команда /holygrail — статистика святых граалей"""
    stats = get_holy_grail_stats()
    text = (
        f"🏆 Святые граали\n\n"
        f"Всего объявлений: {stats['total_listings']}\n"
        f"Идеальных: {stats['holy_grails']}\n"
        f"Уведомлений отправлено: {stats['alerts_sent']}\n"
    )
    if stats["recent_grails"]:
        text += "\nПоследние находки:\n"
        for g in stats["recent_grails"][-3:]:
            city = POPULAR_CITIES.get(g.get("city", ""), {}).get("name", "?")
            text += f"• {city} — {g.get('price', '?')} EUR ({g.get('score', '?')}/10)\n"

    text += "\nНастроить уведомления: /set_city <город>"
    await update.message.reply_text(text)
