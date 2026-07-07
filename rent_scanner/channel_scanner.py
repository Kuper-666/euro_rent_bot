"""
Сканер Telegram каналов для поиска объявлений об аренде.

Функции:
1. Сканирование каналов каждые 60 минут
2. Автоподписка на релевантные каналы
3. Извлечение объявлений из сообщений
4. Отправка алертов подписчикам
"""
import os
import json
import re
import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

CHANNELS_FILE = os.path.join(os.path.dirname(__file__), "channels.json")
SUBSCRIBED_FILE = os.path.join(os.path.dirname(__file__), "subscribed_channels.json")
MAX_AUTO_SUBS_PER_DAY = 5


def _load_channels() -> dict:
    """Загружает список каналов из JSON."""
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channels": [], "scan_keywords": [], "price_patterns": [], "exclude_keywords": []}


def _load_subscribed() -> dict:
    """Загружает список подписанных каналов."""
    if os.path.exists(SUBSCRIBED_FILE):
        with open(SUBSCRIBED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"subscribed": [], "last_reset": ""}


def _save_subscribed(data: dict):
    """Сохраняет список подписанных каналов."""
    with open(SUBSCRIBED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _reset_daily_counter():
    """Сбрасывает счётчик подписок при смене дня."""
    data = _load_subscribed()
    today = datetime.now(timezone.utc).date().isoformat()
    if data.get("last_reset") != today:
        data["subscribed_today"] = 0
        data["last_reset"] = today
        _save_subscribed(data)


def _is_rental_listing(text: str, keywords: list, exclude: list) -> bool:
    """Проверяет, является ли сообщение объявлением об аренде."""
    text_lower = text.lower()

    # Исключаем нерелевантные
    for word in exclude:
        if word in text_lower:
            return False

    # Ищем ключевые слова аренды
    for kw in keywords:
        if kw in text_lower:
            return True

    return False


def _extract_price(text: str, patterns: list) -> Optional[float]:
    """Извлекает цену из текста."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(".", "").replace(",", ".")
            try:
                return float(price_str)
            except ValueError:
                continue
    return None


def _extract_url(text: str) -> Optional[str]:
    """Извлекает URL из текста."""
    url_pattern = r'https?://[^\s<>"]+'
    match = re.search(url_pattern, text)
    if match:
        return match.group(0)
    return None


async def scan_channel(client, channel, keywords: list, price_patterns: list, exclude: list) -> list[dict]:
    """Сканирует один канал и возвращает найденные объявления."""
    listings = []
    try:
        entity = await client.get_entity(channel["username"])
        async for message in client.iter_messages(entity, limit=15):
            if not message.text:
                continue

            text = message.text
            if not _is_rental_listing(text, keywords, exclude):
                continue

            price = _extract_price(text, price_patterns)
            url = _extract_url(text) or f"https://t.me/{channel['username']}/{message.id}"

            listings.append({
                "url": url,
                "title": text[:100],
                "text": text[:500],
                "price": price or 0,
                "city": channel.get("city", ""),
                "channel": channel["username"],
                "message_id": message.id,
                "date": message.date.isoformat() if message.date else "",
            })

        logger.info("Scanned %s: %d listings found", channel["username"], len(listings))
    except Exception as e:
        logger.warning("Error scanning %s: %s", channel["username"], e)

    return listings


async def auto_subscribe(client, channel_username: str) -> bool:
    """Подписывается на канал с лимитом 5 подписок в день."""
    _reset_daily_counter()
    data = _load_subscribed()

    # Проверяем лимит
    if data.get("subscribed_today", 0) >= MAX_AUTO_SUBS_PER_DAY:
        logger.info("Daily subscribe limit reached (%d)", MAX_AUTO_SUBS_PER_DAY)
        return False

    # Проверяем, не подписаны ли уже
    if channel_username in data.get("subscribed", []):
        return True

    try:
        entity = await client.get_entity(channel_username)
        await client(JoinChannelRequest(entity))
        logger.info("Subscribed to %s", channel_username)

        # Сохраняем
        if channel_username not in data.get("subscribed", []):
            data.setdefault("subscribed", []).append(channel_username)
        data["subscribed_today"] = data.get("subscribed_today", 0) + 1
        _save_subscribed(data)
        return True
    except FloodWaitError as e:
        logger.warning("Flood wait on subscribe to %s: %ds", channel_username, e.seconds)
        return False
    except Exception as e:
        if "private" in str(e).lower() or "channel" in str(e).lower():
            logger.warning("Channel %s is private or inaccessible", channel_username)
        else:
            logger.warning("Failed to subscribe to %s: %s", channel_username, e)
        return False


async def check_subscription(client, channel_username: str) -> bool:
    """Проверяет, подписан ли клиент на канал."""
    try:
        entity = await client.get_entity(channel_username)
        # Если можем получить entity — канал доступен
        return True
    except Exception:
        return False


def match_listing_to_subscribers(listing: dict, subscribers: list[dict]) -> list[dict]:
    """Находит подписчиков, которым подходит объявление."""
    matches = []
    listing_city = listing.get("city", "").lower()
    listing_price = listing.get("price", 0)

    for sub in subscribers:
        sub_city = sub.get("city", "").lower()
        max_price = sub.get("max_price", 0) or 999999

        if sub_city and sub_city != listing_city:
            continue
        if listing_price > 0 and listing_price > max_price:
            continue

        matches.append(sub)

    return matches


async def run_channel_scan(client, bot_client=None) -> dict:
    """Запускает полное сканирование всех каналов с автоподпиской."""
    config = _load_channels()
    channels = config.get("channels", [])
    keywords = config.get("scan_keywords", [])
    price_patterns = config.get("price_patterns", [])
    exclude = config.get("exclude_keywords", [])

    stats = {
        "channels_scanned": 0,
        "listings_found": 0,
        "alerts_sent": 0,
        "auto_subscribed": 0,
    }

    for channel in channels:
        if not channel.get("active", True):
            continue

        username = channel.get("username", "")
        if not username:
            continue

        # Автоподписка если ещё не подписаны
        subscribed = await check_subscription(client, username)
        if not subscribed:
            if await auto_subscribe(client, username):
                stats["auto_subscribed"] += 1
                await asyncio.sleep(3)  # Задержка после подписки

        # Сканирование
        listings = await scan_channel(client, channel, keywords, price_patterns, exclude)
        stats["channels_scanned"] += 1
        stats["listings_found"] += len(listings)

        # Обработка объявлений
        for listing in listings:
            await _process_listing(listing, bot_client)
            stats["alerts_sent"] += 1

        # Задержка между каналами
        await asyncio.sleep(2)

    logger.info("Scan complete: %s", stats)
    return stats


async def _process_listing(listing: dict, bot_client=None):
    """Обрабатывает найденное объявление: сохраняет в БД, отправляет алерты и в группу."""
    try:
        from services.supabase_client import get_supabase
        sb = get_supabase()
        if not sb:
            return

        # Проверяем дедупликацию
        existing = sb.table("WebListings").select("id").eq("url", listing["url"]).limit(1).execute()
        if existing.data:
            return

        # Сохраняем
        sb.table("WebListings").insert({
            "portal": listing.get("channel", "telegram"),
            "url": listing["url"],
            "title": listing.get("title", ""),
            "price": listing.get("price", 0),
            "city": listing.get("city", ""),
        }).execute()

        # Отправляем в группу
        group_id = int(os.environ.get("GROUP_ID", "0"))
        if group_id and bot_client:
            try:
                price_text = f"💰 {listing.get('price', 0):.0f} EUR/мес" if listing.get("price") else ""
                city_text = f"🏙 {listing.get('city', '').title()}" if listing.get("city") else ""
                lines = [f"📌 {listing.get('title', '')[:120]}"]
                if price_text:
                    lines.append(price_text)
                if city_text:
                    lines.append(city_text)
                lines.append(f"🌐 {listing.get('channel', 'Telegram')}")
                lines.append(f"🔗 {listing['url']}")
                await bot_client.send_message(
                    chat_id=group_id,
                    text="\n".join(lines),
                )
            except Exception as e:
                logger.warning("Failed to send to group: %s", e)

        # Отправляем алерты подписчикам
        if bot_client:
            from web_scanner.alerts import get_matching_subscriptions
            subs = get_matching_subscriptions(listing.get("city", ""), listing.get("price", 0))
            for sub in subs:
                user_id = sub.get("user_id", "")
                if user_id:
                    try:
                        await bot_client.send_message(
                            chat_id=int(user_id),
                            text=(
                                f"🔔 <b>Новое объявление!</b>\n\n"
                                f"📌 {listing.get('title', '')[:100]}\n"
                                f"💰 {listing.get('price', 0):.0f} EUR/мес\n"
                                f"🏙 {listing.get('city', '?')}\n"
                                f"🌐 {listing.get('channel', 'Telegram')}\n\n"
                                f"🔗 {listing['url']}"
                            ),
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.warning("Failed to send alert to %s: %s", user_id, e)

    except Exception as e:
        logger.warning("Error processing listing: %s", e)
