from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class LeadRecord:
    source: str
    message_id: int
    link: str
    text: str
    score: int
    keywords: tuple[str, ...]
    message_date: str

class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                link TEXT NOT NULL,
                text TEXT NOT NULL,
                score INTEGER NOT NULL,
                keywords_json TEXT NOT NULL,
                message_date TEXT NOT NULL,
                notified_at TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(source, message_id)
            );
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                metric TEXT NOT NULL,
                value INTEGER NOT NULL DEFAULT 0,
                UNIQUE(date, metric)
            );
        """)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def add_subscriber(self, chat_id: int) -> None:
        self._conn.execute("INSERT INTO subscribers(chat_id, created_at) VALUES(?, ?) ON CONFLICT(chat_id) DO NOTHING", (chat_id, utc_now()))
        self._conn.commit()

    def remove_subscriber(self, chat_id: int) -> None:
        self._conn.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
        self._conn.commit()

    def subscribers(self) -> list[int]:
        rows = self._conn.execute("SELECT chat_id FROM subscribers ORDER BY created_at").fetchall()
        return [int(row["chat_id"]) for row in rows]

    def stats(self) -> dict:
        subs = self._conn.execute("SELECT COUNT(*) as cnt FROM subscribers").fetchone()["cnt"]
        leads = self._conn.execute("SELECT COUNT(*) as cnt FROM leads").fetchone()["cnt"]
        return {"subscribers": subs, "leads": leads}

    def record_or_should_retry(self, lead: LeadRecord) -> bool:
        existing = self._conn.execute("SELECT notified_at FROM leads WHERE source = ? AND message_id = ?", (lead.source, lead.message_id)).fetchone()
        if existing:
            return existing["notified_at"] is None

        self._conn.execute("""
            INSERT INTO leads(source, message_id, link, text, score, keywords_json, message_date, notified_at, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """, (lead.source, lead.message_id, lead.link, lead.text, lead.score, json.dumps(list(lead.keywords)), lead.message_date, utc_now()))
        self._conn.commit()
        return True

    def mark_notified(self, source: str, message_id: int) -> None:
        self._conn.execute("UPDATE leads SET notified_at = ? WHERE source = ? AND message_id = ?", (utc_now(), source, message_id))
        self._conn.commit()

    def inc_metric(self, metric: str, value: int = 1) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._conn.execute("""
            INSERT INTO metrics(date, metric, value) VALUES(?, ?, ?)
            ON CONFLICT(date, metric) DO UPDATE SET value = value + ?
        """, (today, metric, value, value))
        self._conn.commit()

    def get_metric(self, metric: str, date: str = None) -> int:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = self._conn.execute("SELECT value FROM metrics WHERE date = ? AND metric = ?", (date, metric)).fetchone()
        return row["value"] if row else 0

    def full_stats(self) -> dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        subs = self._conn.execute("SELECT COUNT(*) as cnt FROM subscribers").fetchone()["cnt"]
        total_leads = self._conn.execute("SELECT COUNT(*) as cnt FROM leads").fetchone()["cnt"]
        notified = self._conn.execute("SELECT COUNT(*) as cnt FROM leads WHERE notified_at IS NOT NULL").fetchone()["cnt"]

        by_source = {}
        for row in self._conn.execute("SELECT source, COUNT(*) as cnt FROM leads GROUP BY source ORDER BY cnt DESC").fetchall():
            by_source[row["source"]] = row["cnt"]

        by_day = {}
        for row in self._conn.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as cnt
            FROM leads WHERE created_at >= DATE('now', '-7 days')
            GROUP BY day ORDER BY day
        """).fetchall():
            by_day[row["day"]] = row["cnt"]

        score_dist = {}
        for row in self._conn.execute("SELECT score, COUNT(*) as cnt FROM leads GROUP BY score ORDER BY score").fetchall():
            score_dist[row["score"]] = row["cnt"]

        today_found = self.get_metric("found", today)
        today_delivered = self.get_metric("delivered", today)
        today_errors = self.get_metric("errors", today)
        today_skipped = self.get_metric("skipped", today)

        return {
            "subscribers": subs,
            "total_leads": total_leads,
            "total_notified": notified,
            "by_source": by_source,
            "by_day": by_day,
            "score_distribution": score_dist,
            "today": {
                "found": today_found,
                "delivered": today_delivered,
                "errors": today_errors,
                "skipped": today_skipped,
            },
        }
