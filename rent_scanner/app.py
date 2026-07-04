from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import signal
from datetime import datetime, timezone
from typing import Iterable

from telethon import TelegramClient, events
from telethon.errors import RPCError, FloodWaitError
from telethon.tl.custom.message import Message
from telethon.tl.types import Channel, Chat

from .config import RuntimeConfig
from .filters import match_text
from .formatting import format_lead
from .sources import Source, enabled_sources
from .storage import LeadRecord, Storage

import os
from dotenv import load_dotenv

LOGGER = logging.getLogger("rent_scanner")

class RentScanner:
    MAX_AUTO_SUBS_PER_DAY = 3

    def __init__(self, config: RuntimeConfig):
        self.config = config
        config.user_session_path.parent.mkdir(parents=True, exist_ok=True)
        config.bot_session_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage = Storage(config.database_path)
        self.sources = enabled_sources()
        self.user_client = TelegramClient(str(config.user_session_path), config.api_id, config.api_hash)
        self.bot_client = TelegramClient(str(config.bot_session_path), config.api_id, config.api_hash)
        self._auto_sub_today = 0
        self._auto_sub_date = datetime.now(timezone.utc).date()

    async def run(self) -> None:
        self._register_bot_commands()
        load_dotenv()
        env_code = os.getenv("TELEGRAM_CODE", "").strip()

        await self.user_client.connect()
        if not await self.user_client.is_user_authorized():
            if not self.config.phone:
                raise RuntimeError("TELEGRAM_PHONE is required for first-time login")
            await self.user_client.send_code_request(self.config.phone)
            if env_code:
                code = env_code
            else:
                code = input("Please enter the code you received: ")
            await self.user_client.sign_in(self.config.phone, code)

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
            stats = self.storage.full_stats()
            top_sources = list(stats["by_source"].items())[:5]
            top_lines = "\n".join(f"  {src}: {cnt}" for src, cnt in top_sources) if top_sources else "  нет данных"
            day_lines = "\n".join(f"  {day}: {cnt}" for day, cnt in stats["by_day"].items()) if stats["by_day"] else "  нет данных"
            today = stats["today"]

            text = (
                f"📊 <b>Статистика сканера</b>\n\n"
                f"👥 Подписчиков: {stats['subscribers']}\n"
                f"📋 Всего объявлений: {stats['total_leads']}\n"
                f"📤 Доставлено: {stats['total_notified']}\n\n"
                f"📅 <b>Сегодня:</b>\n"
                f"  Найдено: {today['found']}\n"
                f"  Доставлено: {today['delivered']}\n"
                f"  Ошибок: {today['errors']}\n"
                f"  Пропущено: {today['skipped']}\n\n"
                f"🏆 <b>Топ каналов:</b>\n{top_lines}\n\n"
                f"📈 <b>По дням (7д):</b>\n{day_lines}\n\n"
                f"🔑 Источников: {len(self.sources)}"
            )
            await event.respond(text, parse_mode="html")

        @self.bot_client.on(events.NewMessage(pattern=r"^/add (.+)"))
        async def add_channel(event: events.NewMessage.Event) -> None:
            handle = event.pattern_match.group(1).strip()
            if not handle.startswith("@"):
                handle = f"@{handle}"
            if any(s.handle == handle for s in self.sources):
                await event.respond(f"ℹ️ {handle} уже добавлен.")
                return
            try:
                entity = await self.user_client.get_entity(handle)
                if not hasattr(entity, 'title'):
                    await event.respond("❌ Не удалось найти канал.")
                    return
                new_source = Source(
                    handle=handle,
                    title=entity.title,
                    reason="Добавлен вручную",
                    enabled=True,
                )
                self.sources.append(new_source)

                @self.user_client.on(events.NewMessage(chats=entity))
                async def new_handler(event: events.NewMessage.Event, src: Source = new_source) -> None:
                    await self._process_message(src, event.message)

                await event.respond(f"✅ Добавлен: {entity.title} ({handle})")
                LOGGER.info("Manual add: %s (%s)", handle, entity.title)
            except (ValueError, RPCError) as e:
                await event.respond(f"❌ Ошибка: {str(e)[:100]}")

        @self.bot_client.on(events.NewMessage(pattern=r"^/search (.+)"))
        async def search_channels(event: events.NewMessage.Event) -> None:
            query = event.pattern_match.group(1).strip()
            await event.respond(f"🔍 Ищу: {query}...")
            try:
                from telethon.tl.functions.messages import SearchRequest
                from telethon.tl.types import InputMessagesFilterEmpty

                result = await self.user_client(SearchRequest(
                    q=query,
                    filter=InputMessagesFilterEmpty(),
                    offset_date=None,
                    offset_id=0,
                    offset_peer=None,
                    limit=20,
                ))

                found = []
                seen = set()
                for msg in result.messages:
                    if not hasattr(msg, 'peer_id') or not msg.peer_id:
                        continue
                    chat_id = msg.peer_id.channel_id if hasattr(msg.peer_id, 'channel_id') else (
                        msg.peer_id.chat_id if hasattr(msg.peer_id, 'chat_id') else None
                    )
                    if not chat_id or chat_id in seen:
                        continue
                    seen.add(chat_id)
                    try:
                        entity = await self.user_client.get_entity(chat_id)
                        if not hasattr(entity, 'title'):
                            continue
                        title = entity.title
                        handle = f"@{entity.username}" if hasattr(entity, 'username') and entity.username else None
                        members = getattr(entity, 'participants_count', '?')
                        found.append(f"  {title} ({members} чел.) {handle or ''}")
                    except Exception:
                        continue

                if found:
                    text = f"🔍 Найдено {len(found)}:\n" + "\n".join(found[:10])
                else:
                    text = f"❌ Ничего не найдено по запросу: {query}"
                await event.respond(text)
            except Exception as e:
                await event.respond(f"❌ Ошибка поиска: {str(e)[:100]}")

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

        # ========== CHANNEL HUNTER: ищем новые каналы в тексте ==========
        await self._discover_channels(text)
        # =================================================================

        match = match_text(text)
        if not match.accepted:
            self.storage.inc_metric("skipped")
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

        self.storage.inc_metric("found")

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
            except FloodWaitError as exc:
                wait_seconds = min(exc.seconds, 300)
                LOGGER.warning("Flood wait %ds, sleeping...", wait_seconds)
                await asyncio.sleep(wait_seconds)
                try:
                    await self.bot_client.send_message(chat_id, body, parse_mode="html", link_preview=False)
                    delivered = True
                except RPCError as exc2:
                    LOGGER.warning("Не удалось доставить объявление в %s после retry: %s", chat_id, exc2)
                    self.storage.inc_metric("errors")
            except RPCError as exc:
                LOGGER.warning("Не удалось доставить объявление в %s: %s", chat_id, exc)
                self.storage.inc_metric("errors")

        if delivered:
            self.storage.mark_notified(lead.source, lead.message_id)
            self.storage.inc_metric("delivered")
            LOGGER.info("✅ Объявление доставлено из %s (ID: %s)", source.handle, message.id)

    async def _discover_channels(self, text: str) -> None:
        """Ищет @username в тексте и автоматически подписывается на новые каналы (макс 3/день)."""
        today = datetime.now(timezone.utc).date()
        if today != self._auto_sub_date:
            self._auto_sub_today = 0
            self._auto_sub_date = today

        if self._auto_sub_today >= self.MAX_AUTO_SUBS_PER_DAY:
            return

        found_channels = re.findall(r'@([A-Za-z0-9_]{5,32})', text)
        for channel_name in found_channels:
            if self._auto_sub_today >= self.MAX_AUTO_SUBS_PER_DAY:
                break

            handle = f"@{channel_name}"
            if any(s.handle == handle for s in self.sources):
                continue
            try:
                entity = await self.user_client.get_entity(handle)
                if not hasattr(entity, 'title'):
                    continue
                new_source = Source(
                    handle=handle,
                    title=entity.title,
                    reason="Найден автоматически",
                    enabled=True,
                )
                self.sources.append(new_source)
                self._auto_sub_today += 1

                @self.user_client.on(events.NewMessage(chats=entity))
                async def new_channel_handler(event: events.NewMessage.Event, src: Source = new_source) -> None:
                    await self._process_message(src, event.message)

                LOGGER.info("📡 Новый канал: %s (%s) [%d/%d сегодня]",
                            handle, entity.title, self._auto_sub_today, self.MAX_AUTO_SUBS_PER_DAY)
            except (ValueError, RPCError):
                pass

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
