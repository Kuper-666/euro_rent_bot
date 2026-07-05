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
import random
import pytz
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Модульный bot создаётся лениво
_bot = None
_app_loop = None


def set_bot(bot_instance, app_loop=None):
    """Устанавливает bot и event loop из основного приложения."""
    global _bot, _app_loop
    _bot = bot_instance
    _app_loop = app_loop


def _run_async(coro):
    """Запускает корутину на основном event loop (безопасно из потока)."""
    if _app_loop and _app_loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, _app_loop)
    else:
        logger.warning("No event loop available, skipping async task")


# ============================================================================
# 1. ВОЗВРАТ НЕАКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

async def return_inactive_users():
    """Если юзер оплатил, но не писал 7 дней — напомнить."""
    if not _bot:
        return

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
        try:
            await _bot.send_message(
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
    if not _bot:
        return

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

        try:
            await _bot.send_message(
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
    from storage import load_data, save_data
    data = load_data()
    if user_id in data:
        data[user_id]["last_activity"] = time.time()
        save_data(data)


# ============================================================================
# 4. ЕЖЕНЕДЕЛЬНЫЙ EMAIL-ДАЙДЖЕСТ
# ============================================================================

async def weekly_email_digest():
    """Отправляет еженедельный email-дайджест."""
    from email_newsletter import run_weekly_digest
    await run_weekly_digest()


# ============================================================================
# 5. ПОСТЫ В ГРУППУ (10:00 и 18:00 по Берлину)
# ============================================================================

GROUP_ID = int(os.environ.get("GROUP_ID", "0"))


async def send_group_digest():
    """Отправляет дайджест в основную группу."""
    logger.info(f"send_group_digest called. bot={bool(_bot)}, GROUP_ID={GROUP_ID}")
    if not _bot:
        logger.error("send_group_digest: bot is None, skipping")
        return
    if not GROUP_ID:
        logger.warning("GROUP_ID not set, skipping group digest")
        return
    try:
        from daily_poster import send_daily_post
        logger.info(f"send_group_digest: calling send_daily_post for GROUP_ID={GROUP_ID}")
        await send_daily_post()
        logger.info("send_group_digest: send_daily_post completed")
    except Exception as e:
        logger.error(f"Failed to send group digest: {e}", exc_info=True)


# ============================================================================
# 6. ПРОМО-СООБЩЕНИЕ В ГРУППУ (15:00 по Берлину)
# ============================================================================

PROMO_MESSAGES = [
    (
        "👋 *EuroRent AI — твой помощник по аренде в Европе!*\n\n"
        "🔑 Чем я умею:\n"
        "• Перевожу объявления с любого портала\n"
        "• Нахожу скрытые платежи (Nebenkosten, Service Charge)\n"
        "• Подсказываю документы (Schufa, NIE, Garant)\n"
        "• Проверяю на мошенников и фейки\n\n"
        "🎁 *Первые 3 проверки — бесплатно!*\n"
        "Просто отправь ссылку или текст в этот чат."
    ),
    (
        "🏠 *Ищешь квартиру в Европе?*\n\n"
        "Я могу проверить любое объявление за 5 секунд:\n"
        "💰 Реальная цена со всеми комиссиями\n"
        "📋 Какие документы нужны\n"
        "🚨 Есть ли риски\n\n"
        "🎁 *3 бесплатные проверки!* Просто кинь ссылку."
    ),
    (
        "💡 *Знаешь ли ты, что большинство объявлений скрывают реальную стоимость?*\n\n"
        "Nebenkosten, Kaution, Provision — всё это можно узнать до переезда.\n\n"
        "Отправь мне ссылку на объявление — я покажу реальную цену.\n\n"
        "🎁 *Первые 3 проверки бесплатно!*"
    ),
    (
        "⚠️ *Не попадись на мошенников!*\n\n"
        "Каждый день кто-то теряет депозит из-за фейковых объявлений.\n\n"
        "Я проверю:\n"
        "✅ Существует ли объявление\n"
        "✅ Нормальная ли цена\n"
        "✅ Не просит ли хозяин лишнего\n\n"
        "🎁 *Попробуй бесплатно — отправь ссылку!*"
    ),
]


async def send_promo_to_group():
    if not _bot or not GROUP_ID:
        return
    text = random.choice(PROMO_MESSAGES)
    try:
        await _bot.send_message(chat_id=GROUP_ID, text=text, parse_mode="Markdown")
        logger.info("Promo sent to group")
    except Exception as e:
        logger.error(f"Failed to send promo: {e}")


# ============================================================================
# ПЛАНИРОВЩИК
# ============================================================================

def _job_error_handler(job, exception):
    """Обработчик ошибок для всех APScheduler jobs."""
    logger.error(f"APScheduler job '{job.name}' failed: {exception}", exc_info=True)


def run_scheduler():
    """Запускает планировщик в фоновом потоке."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.events import EVENT_JOB_ERROR

    # --- Группа: 10:00 и 18:00 по Берлину (APScheduler) ---
    apscheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Berlin"))
    apscheduler.add_job(lambda: _run_async(send_group_digest()), CronTrigger(hour=10, minute=0), name="group_digest_10")
    apscheduler.add_job(lambda: _run_async(send_group_digest()), CronTrigger(hour=18, minute=0), name="group_digest_18")
    apscheduler.add_job(lambda: _run_async(send_promo_to_group()), CronTrigger(hour=15, minute=0), name="promo_15")
    apscheduler.add_listener(_job_error_handler, EVENT_JOB_ERROR)
    apscheduler.start()
    logger.info("APScheduler: group posts at 10:00, 18:00, promo at 15:00 Berlin time")

    # --- Личные задачи (каждые N часов) ---
    import schedule as sched_lib
    sched_lib.every(1).hours.do(lambda: _run_async(remind_last_free_check()))
    sched_lib.every(6).hours.do(lambda: _run_async(return_inactive_users()))
    sched_lib.every().monday.at("10:00").do(lambda: _run_async(weekly_email_digest()))

    logger.info("Scheduler started")
    while True:
        sched_lib.run_pending()
        time.sleep(60)
