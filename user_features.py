"""
Избранное, трекер заявок, профиль пользователя.
Хранение в Supabase с JSON fallback.
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
_sb = None


def _get_sb():
    global _sb
    if _sb is None and SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        _sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _sb


# ── Избранное ──────────────────────────────────────────────────

def add_favorite(user_id: str, url: str, title: str = "", price: str = "") -> bool:
    """Сохраняет объявление в избранное."""
    sb = _get_sb()
    if sb:
        try:
            sb.table("Favorites").insert({
                "user_id": user_id,
                "listing_url": url,
                "listing_title": title,
                "price": price,
            }).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase add_favorite error: {e}")
    return False


def get_favorites(user_id: str) -> list[dict]:
    """Получает список избранных объявлений."""
    sb = _get_sb()
    if sb:
        try:
            result = sb.table("Favorites").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"Supabase get_favorites error: {e}")
    return []


def remove_favorite(user_id: str, fav_id: int) -> bool:
    """Удаляет объявление из избранного по ID."""
    sb = _get_sb()
    if sb:
        try:
            sb.table("Favorites").delete().eq("id", fav_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase remove_favorite error: {e}")
    return False


# ── Трекер заявок ──────────────────────────────────────────────

STATUSES = {
    "saved": "💾 Сохранено",
    "applied": "📤 Отправлено",
    "viewed": "👀 Просмотрено",
    "interview": "🤝 Приглашение",
    "rejected": "❌ Отказ",
    "accepted": "🎉 Принято",
}


def add_tracker_entry(user_id: str, url: str, title: str = "") -> int | None:
    """Добавляет заявку в трекер. Возвращает ID записи."""
    sb = _get_sb()
    if sb:
        try:
            result = sb.table("ApplicationTracker").insert({
                "user_id": user_id,
                "listing_url": url,
                "listing_title": title,
                "status": "saved",
            }).execute()
            if result.data:
                return result.data[0].get("id")
        except Exception as e:
            logger.warning(f"Supabase add_tracker_entry error: {e}")
    return None


def get_tracker_entries(user_id: str) -> list[dict]:
    """Получает все заявки пользователя."""
    sb = _get_sb()
    if sb:
        try:
            result = sb.table("ApplicationTracker").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"Supabase get_tracker_entries error: {e}")
    return []


def update_tracker_status(user_id: str, entry_id: int, status: str) -> bool:
    """Обновляет статус заявки."""
    if status not in STATUSES:
        return False
    sb = _get_sb()
    if sb:
        try:
            sb.table("ApplicationTracker").update({
                "status": status,
                "updated_at": datetime.now().isoformat(),
            }).eq("id", entry_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase update_tracker_status error: {e}")
    return False


def remove_tracker_entry(user_id: str, entry_id: int) -> bool:
    """Удаляет заявку из трекера."""
    sb = _get_sb()
    if sb:
        try:
            sb.table("ApplicationTracker").delete().eq("id", entry_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase remove_tracker_entry error: {e}")
    return False


# ── Профиль пользователя ───────────────────────────────────────

PROFILE_FIELDS = ["full_name", "profession", "income", "employer", "move_in_date", "occupants", "pets", "rental_duration", "preferred_letter_lang"]


def get_profile(user_id: str) -> dict:
    """Получает профиль пользователя."""
    sb = _get_sb()
    if sb:
        try:
            result = sb.table("UserProfiles").select("*").eq("user_id", user_id).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning(f"Supabase get_profile error: {e}")
    return {"user_id": user_id}


def save_profile(user_id: str, data: dict) -> bool:
    """Сохраняет профиль пользователя."""
    sb = _get_sb()
    if sb:
        try:
            row = {"user_id": user_id}
            for field in PROFILE_FIELDS:
                row[field] = data.get(field, "")
            existing = sb.table("UserProfiles").select("user_id").eq("user_id", user_id).execute()
            if existing.data:
                sb.table("UserProfiles").update(row).eq("user_id", user_id).execute()
            else:
                sb.table("UserProfiles").insert(row).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase save_profile error: {e}")
    return False


# ── Фильтры ────────────────────────────────────────────────────

def get_user_filters(user_id: str) -> dict:
    """Получает фильтры пользователя из Supabase Users."""
    sb = _get_sb()
    if sb:
        try:
            result = sb.table("Users").select("filter_furnished,filter_pets,filter_parking").eq("user_id", user_id).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning(f"Supabase get_user_filters error: {e}")
    return {"filter_furnished": False, "filter_pets": False, "filter_parking": False}


def save_user_filters(user_id: str, furnished: bool = False, pets: bool = False, parking: bool = False) -> bool:
    """Сохраняет фильтры пользователя."""
    sb = _get_sb()
    if sb:
        try:
            sb.table("Users").update({
                "filter_furnished": furnished,
                "filter_pets": pets,
                "filter_parking": parking,
            }).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase save_user_filters error: {e}")
    return False
