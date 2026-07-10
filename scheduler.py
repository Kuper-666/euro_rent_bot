"""
Планировщик задач бота через job_queue (встроенный в python-telegram-bot).

Все задачи выполняются на основном event loop через Application.job_queue.
Нет отдельных потоков, нет APScheduler, нет schedule — чистый asyncio.

Запуск: register_jobs(application) вызывается в bot.py после создания Application.
"""

import os
import time
import asyncio
import logging
import random
import pytz
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Ссылка на application заполняется при register_jobs
_application = None


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def _get_bot():
    """Возвращает bot из Application."""
    if _application:
        return _application.bot
    return None


async def _safe_send(chat_id, text, parse_mode=None, reply_markup=None):
    """Отправка сообщения с обработкой ошибок."""
    bot = _get_bot()
    if not bot:
        return
    try:
        await bot.send_message(chat_id=chat_id, text=text,
                               parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        logger.warning("Failed to send to %s: %s", chat_id, e)


# ============================================================================
# 1. ВОЗВРАТ НЕАКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ (каждые 6 часов)
# ============================================================================

async def return_inactive_users(context=None):
    """Если юзер оплатил, но не писал 7 дней — напомнить."""
    from storage import load_data, save_data
    data = load_data()
    now = time.time()
    seven_days = 7 * 86400
    sent = 0

    for user_id, user in data.items():
        balance = user.get("balance", 0)
        last_paid = user.get("last_paid_at", 0)
        last_activity = user.get("last_activity", 0)

        if balance <= 0 or not last_paid:
            continue
        if last_paid < now - seven_days:
            continue
        if last_activity and (now - last_activity) < seven_days:
            continue
        if not last_activity and (now - last_paid) < seven_days:
            continue

        remaining = user.get("balance", 0)
        await _safe_send(
            int(user_id),
            f"👋 Привет! Давно не виделись.\n\n"
            f"У тебя есть {remaining} проверок. "
            f"Хочешь проанализировать новое объявление?\n\n"
            f"Просто отправь ссылку или текст — я разберу за 5 секунд!"
        )
        sent += 1
        user["last_reminder"] = now
        await asyncio.sleep(0.3)

    if sent:
        save_data(data)
        logger.info("Inactive reminders sent: %d", sent)


# ============================================================================
# 2. НАПОМИНАНИЕ О ПОСЛЕДНЕЙ БЕСПЛАТНОЙ ПРОВЕРКЕ (каждый час)
# ============================================================================

async def remind_last_free_check(context=None):
    """Напомнить тем, у кого осталась 1 бесплатная проверка."""
    from storage import load_data, save_data
    from config import FREE_LIMIT
    data = load_data()
    sent = 0

    for user_id, user in data.items():
        if user.get("balance", 0) > 0:
            continue
        if user.get("free_used", 0) != FREE_LIMIT - 1:
            continue
        if user.get("last_limit_reminder", 0) > time.time() - 86400:
            continue

        await _safe_send(
            int(user_id),
            "⚠️ Осталась последняя бесплатная проверка!\n\n"
            "После неё потребуется покупка.\n\n"
            "Пакеты:\n"
            "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
            "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
            "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19"
        )
        sent += 1
        user["last_limit_reminder"] = time.time()
        await asyncio.sleep(0.3)

    if sent:
        save_data(data)
        logger.info("Limit reminders sent: %d", sent)


# ============================================================================
# 3. ОБНОВЛЕНИЕ ПОСЛЕДНЕЙ АКТИВНОСТИ
# ============================================================================

def update_last_activity(user_id: str):
    """Вызывается при каждом сообщении пользователя."""
    from storage import load_data, save_data
    data = load_data()
    if user_id in data:
        data[user_id]["last_activity"] = time.time()
        save_data(data)


# ============================================================================
# 4. ЕЖЕНЕДЕЛЬНЫЙ EMAIL-ДАЙДЖЕСТ (понедельник 10:00)
# ============================================================================

async def weekly_email_digest(context=None):
    from email_newsletter import run_weekly_digest
    await run_weekly_digest()


# ============================================================================
# 5. СКАНИРОВАНИЕ ПОРТАЛОВ (каждый час)
# ============================================================================

async def scan_web_portals(context=None):
    try:
        from web_scanner.alerts import run_web_scan
        new_count = run_web_scan(city="berlin", max_price=2000)
        if new_count > 0:
            logger.info("Web scan: %d new listings found", new_count)
    except Exception as e:
        logger.error("Web scan error: %s", e)


# ============================================================================
# 5.1 СКАНИРОВАНИЕ TELEGRAM КАНАЛОВ (каждый час)
# ============================================================================

async def scan_telegram_channels(context=None):
    try:
        from rent_scanner.channel_scanner import run_channel_scan
        try:
            from rent_scanner.app import RentScanner
            from rent_scanner.config import RuntimeConfig
            config = RuntimeConfig.from_env()
            scanner = RentScanner(config)
            bot = _get_bot()
            stats = await run_channel_scan(scanner.user_client, bot)
            logger.info("Telegram channel scan: %s", stats)
        except Exception as e:
            logger.debug("RentScanner not available: %s", e)
    except Exception as e:
        logger.error("Telegram channel scan error: %s", e)


# ============================================================================
# 6. ПОСТЫ В ГРУППУ (10:00 и 18:00 по Берлину)
# ============================================================================

GROUP_ID = int(os.environ.get("GROUP_ID", "0"))


async def send_group_digest(context=None):
    """Отправляет дайджест в основную группу."""
    if not GROUP_ID:
        return
    try:
        from daily_poster import send_daily_post
        await send_daily_post()
    except Exception as e:
        logger.error("Failed to send group digest: %s", e)


# ============================================================================
# 7. ПРОМО-СООБЩЕНИЕ В ГРУППУ (15:00 по Берлину)
# ============================================================================

PROMO_MESSAGES = [
    "👋 *EuroRent AI — твой помощник по аренде в Европе!*\n\n"
    "🔑 Чем я умею:\n"
    "• Перевожу объявления с любого портала\n"
    "• Нахожу скрытые платежи (Nebenkosten, Service Charge)\n"
    "• Подсказываю документы (Schufa, NIE, Garant)\n"
    "• Проверяю на мошенников и фейки\n\n"
    "🎁 *Первые 3 проверки — бесплатно!*\n"
    "Просто отправь ссылку или текст в этот чат.",

    "🏠 *Ищешь квартиру в Европе?*\n\n"
    "Я могу проверить любое объявление за 5 секунд:\n"
    "💰 Реальная цена со всеми комиссиями\n"
    "📋 Какие документы нужны\n"
    "🚨 Есть ли риски\n\n"
    "🎁 *3 бесплатные проверки!* Просто кинь ссылку.",

    "💡 *Знаешь ли ты, что большинство объявлений скрывают реальную стоимость?*\n\n"
    "Nebenkosten, Kaution, Provision — всё это можно узнать до переезда.\n\n"
    "Отправь мне ссылку на объявление — я покажу реальную цену.\n\n"
    "🎁 *Первые 3 проверки бесплатно!*",

    "⚠️ *Не попадись на мошенников!*\n\n"
    "Каждый день кто-то теряет депозит из-за фейковых объявлений.\n\n"
    "Я проверю:\n"
    "✅ Существует ли объявление\n"
    "✅ Нормальная ли цена\n"
    "✅ Не просит ли хозяин лишнего\n\n"
    "🎁 *Попробуй бесплатно — отправь ссылку!*",
]


async def send_promo_to_group(context=None):
    if not GROUP_ID:
        return
    text = random.choice(PROMO_MESSAGES)
    await _safe_send(GROUP_ID, text, parse_mode="Markdown")


# ============================================================================
# 8. АВТОПОСТИНГ В КАНАЛ (раз в час)
# ============================================================================

async def run_channel_poster(context=None):
    try:
        from channel_poster import run_channel_post
        await run_channel_post()
    except Exception as e:
        logger.error("Channel poster error: %s", e, exc_info=True)


# ============================================================================
# РЕГИСТРАЦИЯ ЗАДАЧ
# ============================================================================

def register_jobs(application):
    """Регистрирует все задачи в job_queue приложения.

    Вызывается из bot.py после создания Application.
    job_queue.run_repeating() создаёт задачу, которая повторяется
    с заданным интервалом. Если задача завершается с ошибкой,
    следующий запуск всё равно произойдёт.
    """
    jq = application.job_queue

    # Группа: 10:00 и 18:00 по Берлину
    berlin = pytz.timezone("Europe/Berlin")
    jq.run_daily(send_group_digest, time=berlin.localize(datetime(2026, 1, 1, 10, 0)).time(),
                 name="group_digest_10")
    jq.run_daily(send_group_digest, time=berlin.localize(datetime(2026, 1, 1, 18, 0)).time(),
                 name="group_digest_18")

    # Промо: 15:00 по Берлину
    jq.run_daily(send_promo_to_group, time=berlin.localize(datetime(2026, 1, 1, 15, 0)).time(),
                 name="promo_15")

    # Каждый час: канал, порталы, напоминания
    jq.run_repeating(run_channel_poster, interval=3600, first=60,
                     name="channel_poster_hourly")
    jq.run_repeating(scan_web_portals, interval=3600, first=120,
                     name="scan_web_portals")
    jq.run_repeating(scan_telegram_channels, interval=3600, first=180,
                     name="scan_telegram_channels")
    jq.run_repeating(remind_last_free_check, interval=3600, first=240,
                     name="remind_last_free_check")

    # Каждые 6 часов: возврат неактивных
    jq.run_repeating(return_inactive_users, interval=21600, first=300,
                     name="return_inactive_users")

    # Понедельник 10:00: email-дайджест
    jq.run_daily(weekly_email_digest, time=berlin.localize(datetime(2026, 1, 1, 10, 0)).time(),
                 days=(0,), name="weekly_email_digest")

    logger.info("All jobs registered in job_queue")
