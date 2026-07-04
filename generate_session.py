"""
Генератор StringSession для Telethon.
Запусти один раз локально, скопируй вывод в TELEGRAM_SESSION_STRING на Render.

Usage: python generate_session.py
"""
import asyncio
from telethon.sessions import StringSession
from telethon import TelegramClient


async def main():
    api_id = int(input("TELEGRAM_API_ID: ").strip())
    api_hash = input("TELEGRAM_API_HASH: ").strip()
    phone = input("TELEGRAM_PHONE: ").strip()

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start(phone=phone)

    session_string = client.session.save()
    print()
    print("=" * 60)
    print("Скопируй эту строку и добавь на Render как")
    print("env var TELEGRAM_SESSION_STRING:")
    print("=" * 60)
    print(session_string)
    print("=" * 60)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
