from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from datetime import datetime, timezone
from typing import Iterable

from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.tl.custom.message import Message

from .config import RuntimeConfig
from .filters import match_text
from .formatting import format_lead
from .sources import Source, enabled_sources
from .storage import LeadRecord, Storage

LOGGER = logging.getLogger("rent_scanner")

class RentScanner:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        config.user_session_path.parent.mkdir(parents=True, exist_ok=True)
        config.bot_session_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage = Storage(config.database_path)
        self.sources = enabled_sources()
        self.user_client = TelegramClient(str(config.user_session_path), config.api_id, config.api_hash)
        self.bot_client = TelegramClient(str(config.bot_session_path), config.api_id, config.api_hash)

    async def run(self) -> None:
        self._register_bot_commands()
        await self.user_client.start()
        await self.bot_client.start(bot_token=self.config.bot_token)

        if self.config.target_chat_id is not None:
            self.storage.add_subscriber(self.config.target_chat_id)

        active_sources = await self._register_source_handlers()
        LOGGER.info("Monitoring %s Telegram sources", len(active_sources))

        if self.config.send_catch_up and self.config.catch_up_limit > 0:
            await self._catch_up(active_sources)

        await self._wait_until_stopped()

    async def shutdown(self) -> None:
        await self.user_client.disconnect()
        await self.bot_client.disconnect()
        self.storage.close()

    def _register_bot_commands(self) -> None:
        @self.bot_client.on(events.NewMessage(pattern=r"^/start"))
        async def start(event: events.NewMessage.Event) -> None:
            chat_id = int(event.chat_id)
            self.storage.add_subscriber(chat_id)
            await event.respond(
                "✅ Чат подписан на новые объявления.\n\n"
                f"Chat ID: <code>{chat_id}</code>\n"
                "Команды: /status, /stop",
                parse_mode="html"
            )

        @self.bot_client.on(events.NewMessage(pattern=r"^/stop"))
        async def stop(event: events.NewMessage.Event) -> None:
            self.storage.remove_subscriber(int(event.chat_id))
            await event.respond("✅ Чат отписан от уведомлений.")

        @self.bot_client.on(events.NewMessage(pattern=r"^/status"))
        async def status(event: events.NewMessage.Event) -> None:
            stats = self.storage.stats()
            await event.respond(
                f"Статус:\n- источников: {len(self.sources)}\n- подписчиков: {stats['subscribers']}\n- объявлений в базе: {stats['leads']}"
            )

    async def _register_source_handlers(self) -> list[tuple[Source, object]]:
        active: list[tuple[Source, object]] = []
        for source in self.sources:
            try:
                entity = await self.user_client.get_entity(source.handle)
            except (ValueError, RPCError) as exc:
                LOGGER.warning("Не удалось найти канал %s: %s", source.handle, exc)
                continue
            active.append((source, entity))

            @self.user_client.on(events.NewMessage(chats=entity))
            async def on_message(event: events.NewMessage.Event, source: Source = source) -> None:
                await self._process_message(source, event.message)

        return active

    async def _catch_up(self, active_sources: Iterable[tuple[Source, object]]) -> None:
        buffered: list[tuple[datetime, Source, Message]] = []
        for source, entity in active_sources:
            try:
                async for message in self.user_client.iter_messages(entity, limit=self.config.catch_up_limit):
                    message_date = message.date or datetime.now(timezone.utc)
                    buffered.append((message_date, source, message))
            except RPCError as exc:
                LOGGER.warning("Не удалось прогрузить историю %s: %s", source.handle, exc)

        for _, source, message in sorted(buffered, key=lambda item: item[0]):
            await self._process_message(source, message)

    async def _process_message(self, source: Source, message: Message) -> None:
        text = message.message or ""
        if not text.strip():
            return

        match = match_text(text)
        if not match.accepted:
            return

        link = f"https://t.me/{source.username}/{message.id}"
        message_date = (message.date or datetime.now(timezone.utc)).isoformat()
        lead = LeadRecord(
            source=source.handle,
            message_id=int(message.id),
            link=link,
            text=text,
            score=match.score,
            keywords=match.matched_keywords,
            message_date=message_date,
        )

        if not self.storage.record_or_should_retry(lead):
            return

        subscribers = self.storage.subscribers()
        if not subscribers:
            LOGGER.warning("Найдено объявление, но нет подписанных чатов: %s", link)
            return

        body = format_lead(source, lead)
        delivered = False
        for chat_id in subscribers:
            try:
                await self.bot_client.send_message(chat_id, body, parse_mode="html", link_preview=False)
                delivered = True
            except RPCError as exc:
                LOGGER.warning("Не удалось доставить объявление в %s: %s", chat_id, exc)

        if delivered:
            self.storage.mark_notified(lead.source, lead.message_id)
            LOGGER.info("✅ Объявление доставлено из %s (ID: %s)", source.handle, message.id)

    async def _wait_until_stopped(self) -> None:
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass
        await stop_event.wait()

async def run_app() -> None:
    config = RuntimeConfig.from_env()
    logging.basicConfig(level=getattr(logging, config.log_level, logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = RentScanner(config)
    try:
        await app.run()
    finally:
        await app.shutdown()

def cli() -> None:
    parser = argparse.ArgumentParser(description="Telegram scanner for rental listings.")
    args = parser.parse_args()
    asyncio.run(run_app())
