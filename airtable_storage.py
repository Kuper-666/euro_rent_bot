import os
import json
import logging

logger = logging.getLogger(__name__)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appPEyp9IWHWjoBKk")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Users")
DATA_FILE = "users_data.json"

_table = None
_use_airtable = None


def _has_airtable():
    global _use_airtable
    if _use_airtable is None:
        _use_airtable = bool(AIRTABLE_API_KEY)
        if _use_airtable:
            logger.info("Using Airtable for storage")
        else:
            logger.info("Airtable not configured, using JSON file")
    return _use_airtable


def _get_table():
    global _table
    if _table is None:
        from pyairtable import Table
        _table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    return _table


def _load_json():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_json(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def load_data():
    if not _has_airtable():
        return _load_json()
    try:
        data = {}
        table = _get_table()
        records = table.all()
        for record in records:
            fields = record["fields"]
            uid = str(fields.get("user_id", ""))
            if not uid:
                continue
            data[uid] = {
                "free_used": fields.get("free_used", 0),
                "balance": fields.get("balance", 0),
                "pdf_paid": fields.get("pdf_paid", False),
                "vip": fields.get("vip", False),
                "vip_criteria": fields.get("vip_criteria", ""),
                "_record_id": record["id"],
            }
        return data
    except Exception as e:
        logger.error(f"Airtable load error: {e}, falling back to JSON")
        return _load_json()


def save_data(data):
    if not _has_airtable():
        _save_json(data)
        return
    try:
        table = _get_table()
        existing = {}
        for record in table.all():
            uid = str(record["fields"].get("user_id", ""))
            if uid:
                existing[uid] = record["id"]
        for uid, info in data.items():
            fields = {
                "user_id": uid,
                "free_used": info.get("free_used", 0),
                "balance": info.get("balance", 0),
                "pdf_paid": info.get("pdf_paid", False),
                "vip": info.get("vip", False),
                "vip_criteria": info.get("vip_criteria", ""),
            }
            if uid in existing:
                table.update(existing[uid], fields)
            else:
                table.create(fields)
    except Exception as e:
        logger.error(f"Airtable save error: {e}, falling back to JSON")
        _save_json(data)
