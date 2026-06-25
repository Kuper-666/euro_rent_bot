import os
import logging
from pyairtable import Table

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appPEyp9IWHWjoBKk")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Users")

logger = logging.getLogger(__name__)

_table = None


def _get_table():
    global _table
    if _table is None:
        if not AIRTABLE_API_KEY:
            raise RuntimeError("Set AIRTABLE_API_KEY environment variable")
        _table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    return _table


def load_data() -> dict:
    data = {}
    try:
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
    except Exception as e:
        logger.error(f"Airtable load error: {e}")
    return data


def save_data(data: dict):
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
        logger.error(f"Airtable save error: {e}")
