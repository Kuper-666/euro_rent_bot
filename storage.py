import os
import json
import time
import logging

from alerting import alert_admin

logger = logging.getLogger(__name__)

DATA_FILE = "users_data.json"
SUPABASE_TABLE = "Users"

_storage_mode = None


def _get_mode():
    global _storage_mode
    if _storage_mode is None:
        if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
            _storage_mode = "supabase"
        else:
            _storage_mode = "json"
            logger.warning("Supabase not configured, using JSON file")
    return _storage_mode


def _get_supabase():
    from services.supabase_client import get_supabase
    return get_supabase()


# Алиас для обратной совместимости
_get_sb = _get_supabase


def _load_json():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"JSON load error: {e}, returning empty data")
    return {}


def _save_json(data):
    import tempfile
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=".", suffix=".tmp")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, DATA_FILE)
    except Exception as e:
        logger.error(f"JSON save error: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _user_to_row(uid: str, info: dict) -> dict:
    """Конвертирует пользовательский dict в строку Supabase."""
    # Приводим timestamp-поля к None если пустые (Supabase TIMESTAMPTZ не принимает "")
    created_at = info.get("created_at", "") or None
    last_paid_at = info.get("last_paid_at", 0) or None
    last_activity = info.get("last_activity", 0) or None

    return {
        "user_id": uid,
        "paid": info.get("pdf_paid", False),
        "count": info.get("free_used", 0),
        "lang": info.get("lang", ""),
        "created_at": created_at,
        "total_checks": info.get("total_checks", 0),
        "email": info.get("email", ""),
        "balance": info.get("balance", 0),
        "vip": info.get("vip", False),
        "ref_code": info.get("ref_code", ""),
        "referrals": json.dumps(info.get("referrals", [])),
        "last_paid_at": last_paid_at,
        "last_activity": last_activity,
        "filter_furnished": info.get("filter_furnished", False),
        "filter_pets": info.get("filter_pets", False),
        "filter_parking": info.get("filter_parking", False),
        "work_address": info.get("work_address", ""),
        "vip_criteria": info.get("vip_criteria", ""),
        "pdf_state": info.get("pdf_state", ""),
        "pdf_started_at": info.get("pdf_started_at", 0),
        "vip_state": info.get("vip_state", ""),
        "profile_state": info.get("profile_state", ""),
        "timezone": info.get("timezone", ""),
        "last_letter": info.get("last_letter", ""),
        "last_listing_url": info.get("last_listing_url", ""),
        "last_listing_text": info.get("last_listing_text", ""),
        "last_reminder": info.get("last_reminder", 0),
        "last_limit_reminder": info.get("last_limit_reminder", 0),
    }


def _row_to_user(row: dict) -> dict:
    """Конвертирует строку Supabase в пользовательский dict."""
    referrals_raw = row.get("referrals", "[]")
    if isinstance(referrals_raw, str):
        try:
            referrals_raw = json.loads(referrals_raw)
        except (json.JSONDecodeError, TypeError):
            referrals_raw = []
    return {
        "pdf_paid": row.get("paid", False),
        "free_used": row.get("count", 0),
        "lang": row.get("lang", ""),
        "created_at": row.get("created_at", ""),
        "total_checks": row.get("total_checks", 0),
        "email": row.get("email", ""),
        "balance": row.get("balance", 0),
        "vip": row.get("vip", False),
        "ref_code": row.get("ref_code", ""),
        "referrals": referrals_raw if isinstance(referrals_raw, list) else [],
        "last_paid_at": row.get("last_paid_at", 0),
        "last_activity": row.get("last_activity", 0),
        "filter_furnished": row.get("filter_furnished", False),
        "filter_pets": row.get("filter_pets", False),
        "filter_parking": row.get("filter_parking", False),
        "work_address": row.get("work_address", ""),
        "vip_criteria": row.get("vip_criteria", ""),
        "pdf_state": row.get("pdf_state", ""),
        "pdf_started_at": row.get("pdf_started_at", 0),
        "vip_state": row.get("vip_state", ""),
        "profile_state": row.get("profile_state", ""),
        "timezone": row.get("timezone", ""),
        "last_letter": row.get("last_letter", ""),
        "last_listing_url": row.get("last_listing_url", ""),
        "last_listing_text": row.get("last_listing_text", ""),
        "last_reminder": row.get("last_reminder", 0),
        "last_limit_reminder": row.get("last_limit_reminder", 0),
    }


def load_data():
    if _get_mode() == "supabase":
        for attempt in range(3):
            try:
                sb = _get_supabase()
                result = sb.table(SUPABASE_TABLE).select("*").execute()
                data = {}
                for row in result.data:
                    uid = str(row.get("user_id", ""))
                    if not uid:
                        continue
                    data[uid] = _row_to_user(row)
                return data
            except Exception as e:
                err_str = str(e)
                if "PGRST204" in err_str:
                    logger.error("Supabase schema mismatch, falling back to JSON: %s", e)
                    alert_admin(
                        "pgrst204",
                        "Supabase: колонка отсутствует в схеме (PGRST204). "
                        "Бот переключился на локальный JSON — данные не персистентны "
                        "между рестартами. Нужно применить миграцию в Supabase Dashboard.\n\n"
                        f"Детали: {err_str[:200]}",
                    )
                    return _load_json()
                logger.warning(f"Supabase load attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(1 * (attempt + 1))
        logger.error("Supabase load failed after 3 attempts, falling back to JSON")
        alert_admin(
            "supabase_load_down",
            "Supabase недоступен (3 попытки исчерпаны) — load_data() упал на "
            "локальный JSON. Проверь статус Supabase и сетевую доступность.",
        )
        return _load_json()
    return _load_json()


def save_data(data):
    if _get_mode() == "supabase":
        for attempt in range(3):
            try:
                sb = _get_supabase()
                # Получаем существующие user_id
                existing = set()
                result = sb.table(SUPABASE_TABLE).select("user_id").execute()
                for row in result.data:
                    uid = str(row.get("user_id", ""))
                    if uid:
                        existing.add(uid)

                # Обновляем или вставляем каждого пользователя
                for uid, info in data.items():
                    row_data = _user_to_row(uid, info)
                    if uid in existing:
                        sb.table(SUPABASE_TABLE).update(row_data).eq("user_id", uid).execute()
                    else:
                        sb.table(SUPABASE_TABLE).insert(row_data).execute()
                return
            except Exception as e:
                err_str = str(e)
                if "PGRST204" in err_str:
                    logger.error("Supabase schema mismatch, falling back to JSON: %s", e)
                    alert_admin(
                        "pgrst204",
                        "Supabase: колонка отсутствует в схеме (PGRST204). "
                        "Бот переключился на локальный JSON — данные не персистентны "
                        "между рестартами. Нужно применить миграцию в Supabase Dashboard.\n\n"
                        f"Детали: {err_str[:200]}",
                    )
                    break
                logger.warning(f"Supabase save attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(1 * (attempt + 1))
    _save_json(data)


def save_user(user_id: str, user_data: dict):
    """Сохраняет одного пользователя (атомарная операция для платежей)."""
    if _get_mode() == "supabase":
        for attempt in range(3):
            try:
                sb = _get_supabase()
                result = sb.table(SUPABASE_TABLE).select("user_id").eq("user_id", user_id).execute()
                row_data = _user_to_row(user_id, user_data)
                if result.data:
                    sb.table(SUPABASE_TABLE).update(row_data).eq("user_id", user_id).execute()
                else:
                    sb.table(SUPABASE_TABLE).insert(row_data).execute()
                return
            except Exception as e:
                err_str = str(e)
                # PGRST204 = column не существует в схеме — повторные попытки
                # бессмысленны, сразу fallback в JSON. Иначе 3 ретрая с sleep
                # блокируют вызывающий поток на несколько секунд зря.
                if "PGRST204" in err_str:
                    logger.error("Supabase schema mismatch (missing column), falling back to JSON: %s", e)
                    alert_admin(
                        "pgrst204",
                        "Supabase: колонка отсутствует в схеме (PGRST204). "
                        "Бот переключился на локальный JSON — данные не персистентны "
                        "между рестартами. Нужно применить миграцию в Supabase Dashboard.\n\n"
                        f"Детали: {err_str[:200]}",
                    )
                    break
                logger.warning(f"Supabase save_user attempt {attempt+1} for {user_id}: {e}")
                if attempt < 2:
                    time.sleep(1 * (attempt + 1))
    # Fallback
    data = _load_json()
    data[user_id] = user_data
    _save_json(data)


def get_user(user_id: str) -> dict:
    """Получает одного пользователя."""
    if _get_mode() == "supabase":
        for attempt in range(3):
            try:
                sb = _get_supabase()
                result = sb.table(SUPABASE_TABLE).select("*").eq("user_id", user_id).execute()
                if result.data:
                    return _row_to_user(result.data[0])
                return {}
            except Exception as e:
                err_str = str(e)
                if "PGRST204" in err_str:
                    logger.error("Supabase schema mismatch, falling back to JSON: %s", e)
                    alert_admin(
                        "pgrst204",
                        "Supabase: колонка отсутствует в схеме (PGRST204). "
                        "Бот переключился на локальный JSON — данные не персистентны "
                        "между рестартами. Нужно применить миграцию в Supabase Dashboard.\n\n"
                        f"Детали: {err_str[:200]}",
                    )
                    break
                logger.warning(f"Supabase get_user attempt {attempt+1} for {user_id}: {e}")
                if attempt < 2:
                    time.sleep(1 * (attempt + 1))
    data = _load_json()
    return data.get(user_id, {})
