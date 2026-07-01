"""
Планировщик автоматических задач бота.
- Возврат неактивных пользователей (7 дней)
- Напоминание о последней бесплатной проверке
- Еженедельный email-дайджест
- Посты в группу в 10:00 и 18:00 по Берлину

Запуск: python scheduler.py (или интегрирован в bot.py как фоновый поток)
"""

import os
import time
import asyncio
import logging
import schedule
import pytz
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from config import TELEGRAM_TOKEN
from storage import load_data, save_data
from email_newsletter import get_active_subscribers, run_weekly_digest

logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None


# ============================================================================
# 1. ВОЗВРАТ НЕАКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

async def return_inactive_users():
    """Если юзер оплатил, но не писал 7 дней — напомнить."""
    if not bot:
        return

    data = load_data()
    now = time.time()
    seven_days = 7 * 86400
    sent = 0

    for user_id, user in data.items():
        balance = user.get("balance", 0)
        last_paid = user.get("last_paid_at", 0)
        last_activity = user.get("last_activity", 0)

        # Только для платящих, у кого нет активности 7+ дней
        if balance <= 0 or not last_paid:
            continue
        if last_paid < now - seven_days:
            continue
        if last_activity and (now - last_activity) < seven_days:
            continue
        if not last_activity and (now - last_paid) < seven_days:
            continue

        remaining = user.get("balance", 0)
        try:
            await bot.send_message(
                chat_id=int(user_id),
                text=(
                    f"👋 Привет! Давно не виделись.\n\n"
                    f"У тебя есть {remaining} проверок. "
                    f"Хочешь проанализировать новое объявление?\n\n"
                    f"Просто отправь ссылку или текст — я разберу за 5 секунд!"
                ),
            )
            sent += 1
            user["last_reminder"] = now
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"Failed to send inactive reminder to {user_id}: {e}")

    if sent:
        save_data(data)
        logger.info(f"Inactive reminders sent: {sent}")


# ============================================================================
# 2. НАПОМИНАНИЕ О ПОСЛЕДНЕЙ БЕСПЛАТНОЙ ПРОВЕРКЕ
# ============================================================================

async def remind_last_free_check():
    """Напомнить тем, у кого осталась 1 бесплатная проверка."""
    if not bot:
        return

    data = load_data()
    from config import FREE_LIMIT
    sent = 0

    for user_id, user in data.items():
        if user.get("balance", 0) > 0:
            continue
        if user.get("free_used", 0) != FREE_LIMIT - 1:
            continue
        if user.get("last_limit_reminder", 0) > time.time() - 86400:
            continue

        try:
            await bot.send_message(
                chat_id=int(user_id),
                text=(
                    f"⚠️ Осталась последняя бесплатная проверка!\n\n"
                    f"После неё потребуется покупка.\n\n"
                    f"Пакеты:\n"
                    f"3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
                    f"10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
                    f"Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19"
                ),
            )
            sent += 1
            user["last_limit_reminder"] = time.time()
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"Failed to send limit reminder to {user_id}: {e}")

    if sent:
        save_data(data)
        logger.info(f"Limit reminders sent: {sent}")


# ============================================================================
# 3. ОБНОВЛЕНИЕ ПОСЛЕДНЕЙ АКТИВНОСТИ
# ============================================================================

def update_last_activity(user_id: str):
    """Вызывается при каждом сообщении пользователя."""
    data = load_data()
    if user_id in data:
        data[user_id]["last_activity"] = time.time()
        save_data(data)


# ============================================================================
# 4. ЕЖЕНЕДЕЛЬНЫЙ EMAIL-ДАЙДЖЕСТ
# ============================================================================

async def weekly_email_digest():
    """Отправляет еженедельный email-дайджест."""
    await run_weekly_digest()


# ============================================================================
# 5. ПОСТЫ В ГРУППУ (10:00 и 18:00 по Берлину)
# ============================================================================

GROUP_ID = int(os.environ.get("GROUP_ID", "0"))


async def send_group_digest():
    """Отправляет дайджест в основную группу."""
    if not bot:
        return
    if not GROUP_ID:
        logger.warning("GROUP_ID not set, skipping group digest")
        return
    try:
        from daily_poster import send_daily_post
        await send_daily_post()
        logger.info("Group digest sent")
    except Exception as e:
        logger.error(f"Failed to send group digest: {e}")


def _run_group_digest():
    """Обёртка для APScheduler — запускает async-функцию."""
    asyncio.run(send_group_digest())


# ============================================================================
# ПЛАНИРОВЩИК
# ============================================================================

def run_scheduler():
    """Запускает планировщик в фоновом потоке."""
    # --- Группа: 10:00 и 18:00 по Берлину (APScheduler) ---
    apscheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Berlin"))
    apscheduler.add_job(_run_group_digest, CronTrigger(hour=10, minute=0))
    apscheduler.add_job(_run_group_digest, CronTrigger(hour=18, minute=0))
    apscheduler.start()
    logger.info("APScheduler: group posts at 10:00 and 18:00 Berlin time")

    # --- Личные задачи (schedule) ---
    schedule.every(1).hours.do(lambda: asyncio.run(remind_last_free_check()))
    schedule.every(6).hours.do(lambda: asyncio.run(return_inactive_users()))
    schedule.every().monday.at("10:00").do(lambda: asyncio.run(weekly_email_digest()))

    logger.info("Scheduler started")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import threading

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler running in background")

    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
