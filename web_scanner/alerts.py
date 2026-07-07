"""
Сканер порталов недвижимости — хранение в Supabase и доставка алертов.
"""
import os
import json
import logging
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
_sb = None

LOCAL_SEEN_FILE = "web_listings_seen.json"


def _get_sb():
    global _sb
    if _sb is None and SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        _sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _sb


def _load_local_seen() -> set:
    if os.path.exists(LOCAL_SEEN_FILE):
        try:
            with open(LOCAL_SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def _save_local_seen(urls: set):
    trimmed = list(urls)[-5000:]
    with open(LOCAL_SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False)


def is_new_listing(url: str) -> bool:
    """Проверяет, есть ли уже такой URL в БД."""
    sb = _get_sb()
    if not sb:
        return url not in _load_local_seen()
    try:
        result = sb.table("WebListings").select("id").eq("url", url).execute()
        return len(result.data) == 0
    except Exception as e:
        logger.warning("is_new_listing error: %s", e)
        return url not in _load_local_seen()


def save_listing(listing) -> bool:
    """Сохраняет объявление в Supabase (либо локально, если Supabase недоступен)."""
    sb = _get_sb()
    if not sb:
        seen = _load_local_seen()
        seen.add(listing.url)
        _save_local_seen(seen)
        return True
    try:
        sb.table("WebListings").insert({
            "portal": listing.portal,
            "url": listing.url,
            "title": listing.title,
            "price": listing.price,
            "city": listing.city,
        }).execute()
        return True
    except Exception as e:
        logger.warning("save_listing error: %s", e)
        seen = _load_local_seen()
        seen.add(listing.url)
        _save_local_seen(seen)
        return False


def get_matching_subscriptions(city: str, price: float) -> list[dict]:
    """Находит подписчиков, которым подходит это объявление."""
    sb = _get_sb()
    if not sb:
        return []
    try:
        result = sb.table("AlertSubscriptions").select("*").eq("active", True).execute()
        matches = []
        for sub in result.data or []:
            sub_city = (sub.get("city", "")).lower()
            max_price = sub.get("max_price", 0) or 999999
            if (not sub_city or sub_city == city.lower()) and (price <= max_price or price == 0):
                matches.append(sub)
        return matches
    except Exception as e:
        logger.warning("get_matching_subscriptions error: %s", e)
        return []


def run_web_scan(city: str = "berlin", max_price: int = 0) -> int:
    """Запускает сканирование всех порталов. Возвращает кол-во новых объявлений."""
    from web_scanner.parsers import scan_all_portals

    listings = scan_all_portals(city, max_price)
    new_count = 0

    for listing in listings:
        if is_new_listing(listing.url):
            save_listing(listing)
            new_count += 1

            # Проверяем подписчиков
            subs = get_matching_subscriptions(listing.city, listing.price)
            for sub in subs:
                try:
                    _send_alert(sub, listing)
                except Exception as e:
                    logger.warning("Alert send error: %s", e)

    logger.info("Web scan complete: %d new listings from %d total", new_count, len(listings))
    return new_count


def _send_alert(subscription: dict, listing) -> None:
    """Отправляет алерт подписчику через бота."""
    # Импортируем здесь чтобы избежать circular imports
    from storage import get_user
    user_id = subscription.get("user_id", "")
    if not user_id:
        return

    text = (
        f"🔔 <b>Новое объявление!</b>\n\n"
        f"📌 {listing.title}\n"
        f"💰 {listing.price:.0f} EUR/мес\n"
        f"🏙 {listing.city}\n"
        f"🌐 {listing.portal}\n\n"
        f"🔗 {listing.url}"
    )

    try:
        from telegram import Bot
        bot_token = os.getenv("TELEGRAM_TOKEN")
        if bot_token:
            bot = Bot(token=bot_token)
            asyncio.create_task(bot.send_message(
                chat_id=int(user_id),
                text=text,
                parse_mode="HTML",
            ))
    except Exception as e:
        logger.warning("Failed to send alert to %s: %s", user_id, e)
