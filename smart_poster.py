"""
Умный постер.

Делает следующее:
1. Парсит название группы (ключевые слова + язык).
2. Заглядывает внутрь группы (читает последние 10-15 сообщений).
   Если там есть реальные объявления об аренде — группа считается подходящей.
3. Постит честное сообщение от лица создателя бота (2-3 группы за запуск)
   и запоминает, куда уже постил, чтобы не повторяться.

Переменные окружения:
  TELEGRAM_API_ID      — API ID из my.telegram.org
  TELEGRAM_API_HASH    — API Hash из my.telegram.org
  USER_SESSION_PATH    — путь к файлу сессии (по умолчанию sessions/scanner_user)

Запуск: python smart_poster.py
"""

import os
import asyncio
import random
import re
import sqlite3
import logging
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat
from dotenv import load_dotenv
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
from typing import Optional

DetectorFactory.seed = 0
load_dotenv()

logger = logging.getLogger(__name__)

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("USER_SESSION_PATH", "sessions/scanner_user")

# ── Настройки фильтрации ──────────────────────────────────────────
ALLOWED_LANGUAGES = {"ru", "en", "de", "it", "pl", "cs"}
GROUP_KEYWORDS = [
    "wohnung", "miete", "rent", "apartment",
    "аренда", "квартира", "жильё", "housing",
    "wg", "zimmer",
    "affitto", "stanze", "appartament",
    "wynajem", "mieszkanie", "pokoje",
    "pronájem", "bydlení", "nemovitost",
]
STOP_WORDS = ["kaufen", "verkauf", "sale", "buy", "купить", "продажа"]
RENT_KEYWORDS = [
    "wohnung", "miete", "zimmer", "аренда", "квартир",
    "кв.м", "€", "m²", "м²", "mieten", "rent", "flat", "apartment",
    "nebenkosten", "kaution", "warmmiete", "kaltmiete",
]

# ── Сообщения для постинга (мультиязычные) ────────────────────────
POST_MESSAGES = {
    "ru": [
        "Привет! Я разработчик бота @expat_rent_bot — он за 5 секунд проверяет объявления об аренде и находит скрытые платежи. Первые 3 проверки бесплатно, если кому пригодится.",
        "Кто ищет квартиру? Сделал бота @expat_rent_bot — переводит объявления, считает реальную цену с учётом всех платежей. Бесплатно 3 проверки.",
        "Если сталкивались с непонятными Nebenkosten в объявлениях — я сделал бота @expat_rent_bot, который разбирает это автоматически.",
        "Переезжаете и разбираете объявления об аренде? Мой бот @expat_rent_bot анализирует их и показывает реальную цену за 5 секунд.",
    ],
    "uk": [
        "Привіт! Я розробник бота @expat_rent_bot — він за 5 секунд перевіряє оголошення про оренду і знаходить приховані платежі. Перші 3 перевірки безкоштовно.",
        "Хто шукає квартиру? Зробив бота @expat_rent_bot — перекладає оголошення, рахує реальну ціну з усіма платежами. Безкоштовно 3 перевірки.",
        "Якщо стикалися з незрозумілими Nebenkosten — я зробив бота @expat_rent_bot, який розбирає це автоматично.",
    ],
    "de": [
        "Hallo! Ich bin der Entwickler von @expat_rent_bot — er prüft Mietangebote in 5 Sekunden und findet versteckte Gebühren. Die ersten 3 Prüfungen sind kostenlos.",
        "Wer sucht eine Wohnung? Ich habe @expat_rent_bot gebaut — übersetzt Angebote, berechnet den echten Preis inkl. aller Nebenkosten. 3 kostenlose Prüfungen.",
        "Wenn ihr euch mit unverständlichen Nebenkosten abmüsst — mein Bot @expat_rent_bot analysiert das automatisch.",
    ],
    "en": [
        "Hi! I built @expat_rent_bot — it checks rental listings in 5 seconds and finds hidden fees. First 3 checks are free!",
        "Looking for an apartment? @expat_rent_bot translates listings, calculates the real price with all fees. 3 free checks.",
        "Tired of confusing Nebenkosten? My bot @expat_rent_bot breaks it all down automatically.",
    ],
    "it": [
        "Ciao! Ho creato @expat_rent_bot — controlla gli annunci di affitto in 5 secondi e trova le spese nascoste. I primi 3 controlli sono gratis!",
        "Cerchi un appartamento? @expat_rent_bot traduce gli annunci, calcola il prezzo reale con tutte le spese. 3 controlli gratuiti.",
        "Se ti confondono le spese accessorie — il mio bot @expat_rent_bot le analizza automaticamente.",
    ],
    "pl": [
        "Cześć! Stworzyłem @expat_rent_bot — sprawdza oferty wynajmu w 5 sekund i znajduje ukryte opłaty. Pierwsze 3 sprawdzenia za darmo!",
        "Szukasz mieszkania? @expat_rent_bot tłumaczy oferty, oblicza realną cenę ze wszystkimi opłatami. 3 darmowe sprawdzenia.",
        "Jeśli męczą Cię niezrozumiałe Nebenkosten — mój bot @expat_rent_bot analizuje to automatycznie.",
    ],
    "cs": [
        "Ahoj! Vytvořil jsem @expat_rent_bot — kontroluje nabídky pronájmu za 5 sekund a najde skryté poplatky. První 3 kontroly zdarma!",
        "Hledáte byt? @expat_rent_bot překládá nabídky, počítá skutečnou cenu se všemi poplatky. 3 kontroly zdarma.",
        "Pokud vás mátou nesrozumitelné Nebenkosten — můj bot @expat_rent_bot je analyzuje automaticky.",
    ],
}

SENT_HISTORY_FILE = "sent_groups_history.txt"
SMART_POSTER_DB = "data/smart_poster.db"


class PosterStorage:
    def __init__(self, db_path: str = SMART_POSTER_DB):
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sent_groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                sent_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                chat_title TEXT,
                message_text TEXT,
                post_type TEXT DEFAULT 'promo',
                sent_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                chat_title TEXT,
                trigger_text TEXT,
                reply_text TEXT,
                sent_at TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def is_sent(self, chat_id: int) -> bool:
        row = self._conn.execute("SELECT 1 FROM sent_groups WHERE chat_id = ?", (chat_id,)).fetchone()
        return row is not None

    def mark_sent(self, chat_id: int, title: str = ""):
        self._conn.execute(
            "INSERT OR IGNORE INTO sent_groups(chat_id, title, sent_at) VALUES(?, ?, ?)",
            (chat_id, title, datetime.now(timezone.utc).isoformat())
        )
        self._conn.commit()

    def get_sent_ids(self) -> set:
        rows = self._conn.execute("SELECT chat_id FROM sent_groups").fetchall()
        return {row["chat_id"] for row in rows}

    def log_post(self, chat_id: int, title: str, text: str, post_type: str = "promo"):
        self._conn.execute(
            "INSERT INTO posts(chat_id, chat_title, message_text, post_type, sent_at) VALUES(?, ?, ?, ?, ?)",
            (chat_id, title, text, post_type, datetime.now(timezone.utc).isoformat())
        )
        self._conn.commit()

    def log_reply(self, chat_id: int, title: str, trigger: str, reply: str):
        self._conn.execute(
            "INSERT INTO replies(chat_id, chat_title, trigger_text, reply_text, sent_at) VALUES(?, ?, ?, ?, ?)",
            (chat_id, title, trigger, reply, datetime.now(timezone.utc).isoformat())
        )
        self._conn.commit()

    def stats(self) -> dict:
        posts = self._conn.execute("SELECT COUNT(*) as c FROM posts").fetchone()["c"]
        replies = self._conn.execute("SELECT COUNT(*) as c FROM replies").fetchone()["c"]
        groups = self._conn.execute("SELECT COUNT(*) as c FROM sent_groups").fetchone()["c"]
        return {"posts": posts, "replies": replies, "groups": groups}

    def to_excel(self, path: str = "data/smart_poster_report.xlsx"):
        import pandas as pd
        posts_df = pd.read_sql("SELECT * FROM posts ORDER BY sent_at DESC", self._conn)
        replies_df = pd.read_sql("SELECT * FROM replies ORDER BY sent_at DESC", self._conn)
        groups_df = pd.read_sql("SELECT * FROM sent_groups ORDER BY sent_at DESC", self._conn)

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            if not posts_df.empty:
                posts_df.to_excel(writer, sheet_name="Posts", index=False)
            if not replies_df.empty:
                replies_df.to_excel(writer, sheet_name="Replies", index=False)
            if not groups_df.empty:
                groups_df.to_excel(writer, sheet_name="Groups", index=False)
        logger.info(f"Report exported to {path}")
        return path

    def close(self):
        self._conn.close()


def load_sent_history() -> set:
    storage = PosterStorage()
    ids = storage.get_sent_ids()
    storage.close()
    return ids


def save_sent_history(chat_id: int, history: set):
    storage = PosterStorage()
    storage.mark_sent(chat_id)
    storage.close()


def detect_language(text: str) -> str:
    if not text or not text.strip():
        return "unknown"
    try:
        lang = detect(text)
        if lang in ALLOWED_LANGUAGES:
            return lang
    except LangDetectException:
        pass
    for word in text.split():
        if len(word) < 3:
            continue
        try:
            lang = detect(word)
            if lang in ALLOWED_LANGUAGES:
                return lang
        except LangDetectException:
            continue
    return "unknown"


def is_relevant_chat(title: str, recent_messages: list[str]) -> bool:
    """Проверяет группу по названию + по содержимому последних сообщений."""
    title_lower = title.lower()

    if any(stop in title_lower for stop in STOP_WORDS):
        return False
    if not any(kw in title_lower for kw in GROUP_KEYWORDS):
        return False

    lang = detect_language(title)
    if lang not in ALLOWED_LANGUAGES:
        for word in title.split():
            if len(word) >= 3:
                try:
                    wlang = detect(word)
                    if wlang in ALLOWED_LANGUAGES:
                        lang = wlang
                        break
                except LangDetectException:
                    continue
    if lang not in ALLOWED_LANGUAGES:
        return False

    # Проверяем содержимое последних сообщений на ключевые слова аренды
    if recent_messages:
        combined = " ".join(recent_messages).lower()
        has_rent_keyword = any(kw in combined for kw in RENT_KEYWORDS)
        has_price = any(symbol in combined for symbol in ["€", "eur", "евро", "zł", "pln"])
        if not has_rent_keyword and not has_price:
            return False

    return True



class SmartPoster:
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.storage = PosterStorage()

    async def _get_recent_messages(self, chat_id: int, limit: int = 5) -> list[str]:
        texts = []
        try:
            async for msg in self.client.iter_messages(chat_id, limit=limit):
                if msg.text:
                    texts.append(msg.text)
        except Exception as e:
            logger.warning(f"Failed to read messages from {chat_id}: {e}")
        return texts

    async def run(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            logger.error("Session not authorized. Run the scanner first.")
            await self.client.disconnect()
            return

        logger.info("Smart poster starting...")

        await self.scan_and_post()

        stats = self.storage.stats()
        logger.info(f"Stats: {stats['posts']} posts, {stats['groups']} groups")

        await self.client.run_until_disconnected()

    async def scan_and_post(self):
        logger.info("Scanning dialogs for target groups and channels...")
        eligible = []

        async for dialog in self.client.iter_dialogs():
            entity = dialog.entity
            if not isinstance(entity, (Chat, Channel)):
                continue

            if isinstance(entity, Channel) and not entity.megagroup:
                continue

            chat_id = entity.id
            title = entity.title or ""

            if self.storage.is_sent(chat_id):
                continue

            title_lower = title.lower()
            has_keyword = any(kw in title_lower for kw in GROUP_KEYWORDS)
            has_stop = any(s in title_lower for s in STOP_WORDS)

            if has_stop or not has_keyword:
                continue

            eligible.append(entity)

        if not eligible:
            logger.info("No new suitable targets found.")
            return

        selected = random.sample(eligible, min(3, len(eligible)))
        logger.info(f"Found {len(eligible)} eligible, posting to {len(selected)}.")

        for entity in selected:
            try:
                # Определяем язык группы по названию
                title = entity.title or ""
                group_lang = detect_language(title)
                if group_lang not in POST_MESSAGES:
                    group_lang = "ru"
                msg = random.choice(POST_MESSAGES[group_lang])
                await self.client.send_message(entity, msg)
                self.storage.mark_sent(entity.id, entity.title or "")
                self.storage.log_post(entity.id, entity.title or "", msg)
                logger.info(f"Posted to {entity.title} (lang={group_lang})")
                await asyncio.sleep(random.uniform(5, 10))
            except Exception as e:
                logger.error(f"Error posting to {entity.title}: {e}")


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    if "--export" in sys.argv:
        storage = PosterStorage()
        path = storage.to_excel()
        stats = storage.stats()
        print(f"Exported: {path}")
        print(f"Posts: {stats['posts']}, Replies: {stats['replies']}, Groups: {stats['groups']}")
        storage.close()
    elif "--stats" in sys.argv:
        storage = PosterStorage()
        stats = storage.stats()
        print(f"Posts: {stats['posts']}, Replies: {stats['replies']}, Groups: {stats['groups']}")
        storage.close()
    else:
        poster = SmartPoster()
        try:
            asyncio.run(poster.run())
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
