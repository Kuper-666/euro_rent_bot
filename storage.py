import os
import json
import logging

logger = logging.getLogger(__name__)

DATA_FILE = "users_data.json"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_json(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def load_data():
    if _get_mode() == "supabase":
        try:
            sb = _get_supabase()
            result = sb.table("users").select("*").execute()
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
                    "last_paid_at": row.get("last_paid_at", 0),
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
            result = sb.table("users").select("id,user_id").execute()
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
                    "last_paid_at": info.get("last_paid_at", 0),
                }
                if uid in existing:
                    sb.table("users").update(row_data).eq("id", existing[uid]).execute()
                else:
                    sb.table("users").insert(row_data).execute()
            return
        except Exception as e:
            logger.error(f"Supabase save error: {e}, falling back to JSON")
    _save_json(data)
