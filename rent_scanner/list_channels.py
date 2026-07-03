import os
import sys
import io
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("USER_SESSION_PATH", "sessions/scanner_user")

async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Сессия не авторизована. Сначала запусти сканер для авторизации.")
        await client.disconnect()
        return
    print("📂 Сканирую твои подписки (диалоги)...")

    sources_code = []
    async for dialog in client.iter_dialogs():
        if dialog.is_channel or dialog.is_group:
            entity = dialog.entity
            username = getattr(entity, 'username', None)
            title = entity.title

            if username:
                sources_code.append(f'    Source("@{username}", "{title}", "из подписок пользователя"),')

    print("\n✅ Найдено каналов:", len(sources_code))
    print("\n📋 Скопируй этот код и вставь в `sources.py` вместо списка SOURCES:\n")
    print("SOURCES: list[Source] = [")
    for line in sources_code:
        print(line)
    print("]")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
