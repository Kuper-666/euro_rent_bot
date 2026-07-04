"""
Умный постер + Слушатель ответов.

Делает три вещи:
1. Парсит название группы (ключевые слова + язык).
2. Заглядывает внутрь группы (читает последние 10-15 сообщений).
   Если там есть реальные объявления об аренде — группа считается подходящей.
3. Запускается как вечный слушатель. Ждёт комментариев к своим постам
   и отвечает на релевантные вопросы в группах.

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

from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat
from dotenv import load_dotenv
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

DetectorFactory.seed = 0
load_dotenv()

logger = logging.getLogger(__name__)

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("USER_SESSION_PATH", "sessions/scanner_user")

# ── Настройки фильтрации ──────────────────────────────────────────
ALLOWED_LANGUAGES = {"ru", "en", "de"}
GROUP_KEYWORDS = [
    "wohnung", "miete", "rent", "apartment",
    "аренда", "квартира", "жильё", "housing",
    "wg", "zimmer",
]
STOP_WORDS = ["kaufen", "verkauf", "sale", "buy", "купить", "продажа"]
RENT_KEYWORDS = [
    "wohnung", "miete", "zimmer", "аренда", "квартир",
    "кв.м", "€", "m²", "м²", "mieten", "rent", "flat", "apartment",
    "nebenkosten", "kaution", "warmmiete", "kaltmiete",
]

# ── Сообщения для постинга ────────────────────────────────────────
POST_MESSAGES = [
    "Привет! Я использую бота @EuroRentAIBot для проверки объявлений – он за 5 секунд находит скрытые платежи. Может, кому пригодится.",
    "Кто ищет квартиру? Я нашел полезного бота – @EuroRentAIBot. Бесплатно 3 проверки.",
    "Столкнулись с Nebenkosten? Бот @EuroRentAIBot помогает разобраться. Рекомендую.",
    "Переезжаете? @EuroRentAIBot анализирует объявления и показывает реальную цену. Проверил на себе – работает!",
]

# ── Ответы на комментарии ─────────────────────────────────────────
REPLY_MESSAGES = [
    "Да, я тоже им пользуюсь, очень удобно. Просто кидаешь ссылку в @EuroRentAIBot.",
    "Согласен! Этот бот реально экономит время на переводе и подсчетах.",
    "Если нужно быстро проверить риски, @EuroRentAIBot помогает. Рекомендую.",
]

# ── Триггеры для ответов на вопросы ───────────────────────────────
QUESTION_TRIGGERS = [
    "как найти квартиру", "помогите с арендой", "immoscout",
    "nebenkosten", "как проверить", "сколько стоит", "аренда в",
    "ищу квартиру", "ищу жильё", "ищу жилье",
]

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
        return False

    if recent_messages:
        rent_count = sum(
            1 for msg in recent_messages
            if msg and any(kw in msg.lower() for kw in RENT_KEYWORDS)
        )
        if rent_count < 2:
            return False

    return True


def should_reply(text: str) -> bool:
    """Проверяет, стоит ли отвечать на сообщение."""
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in QUESTION_TRIGGERS)


class SmartPoster:
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.storage = PosterStorage()
        self._reply_cooldown: dict[int, float] = {}
        self.COOLDOWN_SECONDS = 300

    def _can_reply(self, chat_id: int) -> bool:
        last = self._reply_cooldown.get(chat_id, 0)
        return (datetime.now().timestamp() - last) >= self.COOLDOWN_SECONDS

    def _mark_replied(self, chat_id: int):
        self._reply_cooldown[chat_id] = datetime.now().timestamp()

    async def _get_recent_messages(self, chat_id: int, limit: int = 15) -> list[str]:
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

        self._register_reply_listener()

        stats = self.storage.stats()
        logger.info(f"Stats: {stats['posts']} posts, {stats['replies']} replies, {stats['groups']} groups")

        logger.info("Listener started. Waiting for comments...")
        await self.client.run_until_disconnected()

    def _register_reply_listener(self):
        @self.client.on(events.NewMessage)
        async def reply_listener(event):
            if event.out or event.is_private:
                return

            chat_id = event.chat_id
            text = event.raw_text or ""
            if not text.strip():
                return

            if event.reply_to_msg_id:
                try:
                    original_msg = await event.client.get_messages(
                        chat_id, ids=event.reply_to_msg_id
                    )
                    if original_msg and original_msg.out:
                        if not self._can_reply(chat_id):
                            return
                        await asyncio.sleep(random.uniform(5, 15))
                        reply = random.choice(REPLY_MESSAGES)
                        await event.reply(reply)
                        self._mark_replied(chat_id)
                        self.storage.log_reply(chat_id, event.chat.title or "", text[:100], reply)
                        logger.info(f"Replied to comment in {event.chat.title}")
                        return
                except Exception as e:
                    logger.warning(f"Error checking reply context: {e}")

            if should_reply(text):
                if not self._can_reply(chat_id):
                    return
                await asyncio.sleep(random.uniform(10, 20))
                reply = random.choice(REPLY_MESSAGES) + " Попробуйте @EuroRentAIBot."
                await event.reply(reply)
                self._mark_replied(chat_id)
                self.storage.log_reply(chat_id, event.chat.title or "", text[:100], reply)
                logger.info(f"Replied to question in {event.chat.title}")

    async def scan_and_post(self):
        logger.info("Scanning dialogs for target groups...")
        eligible_groups = []

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

            recent = await self._get_recent_messages(chat_id)

            if not is_relevant_chat(title, recent):
                continue

            eligible_groups.append(entity)

        if not eligible_groups:
            logger.info("No new suitable groups found after filtering.")
            return

        selected = random.sample(eligible_groups, min(3, len(eligible_groups)))
        logger.info(f"Found {len(eligible_groups)} suitable groups, selected {len(selected)}.")

        for entity in selected:
            try:
                msg = random.choice(POST_MESSAGES)
                await self.client.send_message(entity, msg)
                self.storage.mark_sent(entity.id, entity.title or "")
                self.storage.log_post(entity.id, entity.title or "", msg)
                logger.info(f"Posted to {entity.title}")
                await asyncio.sleep(random.uniform(3, 6))
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
