import os
import json
import logging

logger = logging.getLogger(__name__)

DATA_FILE = "users_data.json"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = "Users"

_supabase = None
_storage_mode = None


def _get_mode():
    global _storage_mode
    if _storage_mode is None:
        if SUPABASE_URL and SUPABASE_KEY:
            _storage_mode = "supabase"
            logger.info("Using Supabase for storage")
        else:
            _storage_mode = "json"
            logger.info("Supabase not configured, using JSON file")
    return _storage_mode


def _get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


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
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, DATA_FILE)
    except Exception as e:
        logger.error(f"JSON save error: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def load_data():
    if _get_mode() == "supabase":
        try:
            sb = _get_supabase()
            result = sb.table(SUPABASE_TABLE).select("*").execute()
            data = {}
            for row in result.data:
                uid = str(row.get("user_id", ""))
                if not uid:
                    continue
                data[uid] = {
                    "free_used": row.get("free_used", 0),
                    "balance": row.get("balance", 0),
                    "pdf_paid": row.get("pdf_paid", False),
                    "vip": row.get("vip", False),
                    "vip_criteria": row.get("vip_criteria", ""),
                    "vip_state": row.get("vip_state", ""),
                    "pdf_state": row.get("pdf_state", ""),
                    "pdf_started_at": row.get("pdf_started_at", 0),
                    "last_paid_at": row.get("last_paid_at", 0),
                    "last_activity": row.get("last_activity", 0),
                    "last_reminder": row.get("last_reminder", 0),
                    "last_limit_reminder": row.get("last_limit_reminder", 0),
                    "ref_code": row.get("ref_code", ""),
                    "referrals": row.get("referrals", []),
                    "timezone": row.get("timezone", ""),
                }
            return data
        except Exception as e:
            logger.error(f"Supabase load error: {e}, falling back to JSON")
            return _load_json()
    return _load_json()


def save_data(data):
    if _get_mode() == "supabase":
        try:
            sb = _get_supabase()
            existing = {}
            result = sb.table(SUPABASE_TABLE).select("id,user_id").execute()
            for row in result.data:
                uid = str(row.get("user_id", ""))
                if uid:
                    existing[uid] = row["id"]

            for uid, info in data.items():
                row_data = {
                    "user_id": uid,
                    "free_used": info.get("free_used", 0),
                    "balance": info.get("balance", 0),
                    "pdf_paid": info.get("pdf_paid", False),
                    "vip": info.get("vip", False),
                    "vip_criteria": info.get("vip_criteria", ""),
                    "vip_state": info.get("vip_state", ""),
                    "pdf_state": info.get("pdf_state", ""),
                    "pdf_started_at": info.get("pdf_started_at", 0),
                    "last_paid_at": info.get("last_paid_at", 0),
                    "last_activity": info.get("last_activity", 0),
                    "last_reminder": info.get("last_reminder", 0),
                    "last_limit_reminder": info.get("last_limit_reminder", 0),
                    "ref_code": info.get("ref_code", ""),
                    "referrals": info.get("referrals", []),
                    "timezone": info.get("timezone", ""),
                }
                if uid in existing:
                    sb.table(SUPABASE_TABLE).update(row_data).eq("id", existing[uid]).execute()
                else:
                    sb.table(SUPABASE_TABLE).insert(row_data).execute()
            return
        except Exception as e:
            logger.error(f"Supabase save error: {e}, falling back to JSON")
    _save_json(data)
