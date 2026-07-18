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
from zoneinfo import ZoneInfo
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Ссылка на application — устанавливается в register_jobs(), служит
# fallback'ом для _get_bot() на случай прямого вызова job-функции без
# CallbackContext (например, из админ-команды). Обычный путь через
# job_queue всегда передаёт настоящий context с context.bot — это основной
# источник bot в _get_bot(), _application лишь подстраховка.
_application = None


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def _get_bot(context=None):
    """
    Возвращает bot из переданного CallbackContext.

    РАНЬШЕ здесь читалась модульная переменная `_application`, которую
    должен был выставлять внешний код (аналог set_application() из старой
    APScheduler-версии) — но при переходе на job_queue эта установка нигде
    не была добавлена, поэтому `_application` всегда оставалась None, и
    _get_bot() всегда возвращал None. Из-за этого _safe_send() тихо ничего
    не отправляла ни разу: return_inactive_users, remind_last_free_check и
    send_promo_to_group годами выполнялись "успешно" (без ошибок, иногда
    даже логируя "sent: N"), но ни одно сообщение реально не уходило.

    job_queue уже передаёт в каждый callback настоящий CallbackContext с
    рабочим context.bot — используем его напрямую, без глобального стейта.
    """
    if context is not None and getattr(context, "bot", None) is not None:
        return context.bot
    if _application:
        return _application.bot
    return None


async def _safe_send(chat_id, text, parse_mode=None, reply_markup=None, context=None):
    """Отправка сообщения с обработкой ошибок."""
    bot = _get_bot(context)
    if not bot:
        logger.warning("_safe_send: no bot available (context=%s), message to %s not sent", context, chat_id)
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
    # load_data/save_data — синхронный full-table scan/overwrite Supabase.
    # Эта задача крутится на ОСНОВНОМ event loop бота (см. _run_async выше),
    # поэтому без to_thread она замораживает бота для ВСЕХ живых
    # пользователей на время запроса, а не только влияет на рассылку.
    data = await asyncio.to_thread(load_data)
    now = time.time()
    seven_days = 7 * 86400
    sent = 0

    for user_id, user in data.items():
        balance = user.get("balance", 0)
        last_paid = user.get("last_paid_at", 0)
        last_activity = user.get("last_activity", 0)

        if balance <= 0 or not last_paid:
            continue
        # Не напоминаем бесконечно давно оплатившим — после ~2 месяцев без
        # активности это уже не "давно не виделись", а скорее ушедший
        # пользователь, для которого разовое напоминание вряд ли поможет.
        #
        # РАНЬШЕ здесь стояло `if last_paid < now - seven_days: continue` —
        # то есть пропускались все, кто оплатил РАНЬШЕ чем 7 дней назад.
        # Но ниже требуется last_activity/last_paid старше 7 дней — то есть
        # функция одновременно требовала "оплатил недавно (< 7 дней)" И
        # "не появлялся давно (>= 7 дней)", что почти никогда не совпадает
        # одновременно. Из-за этого основной сценарий, для которого функция
        # существует — "оплатил и пропал больше недели назад" — никогда не
        # проходил фильтр.
        sixty_days = 60 * 86400
        if last_paid < now - sixty_days:
            continue
        if last_activity and (now - last_activity) < seven_days:
            continue
        if not last_activity and (now - last_paid) < seven_days:
            continue
        # last_reminder записывался, но нигде не проверялся — без этой
        # проверки неактивный пользователь получал бы одно и то же "давно
        # не виделись" каждые 6 часов (интервал этой задачи) до тех пор,
        # пока не появится в боте. Раз в 7 дней достаточно.
        if user.get("last_reminder", 0) > now - seven_days:
            continue

        remaining = user.get("balance", 0)
        await _safe_send(
            int(user_id),
            f"👋 Привет! Давно не виделись.\n\n"
            f"У тебя есть {remaining} проверок. "
            f"Хочешь проанализировать новое объявление?\n\n"
            f"Просто отправь ссылку или текст — я разберу за 5 секунд!",
            context=context,
        )
        sent += 1
        user["last_reminder"] = now
        await asyncio.sleep(0.3)

    if sent:
        await asyncio.to_thread(save_data, data)
        logger.info("Inactive reminders sent: %d", sent)


# ============================================================================
# 2. НАПОМИНАНИЕ О ПОСЛЕДНЕЙ БЕСПЛАТНОЙ ПРОВЕРКЕ (каждый час)
# ============================================================================

async def remind_last_free_check(context=None):
    """Напомнить тем, у кого осталась 1 бесплатная проверка."""
    from storage import load_data, save_data
    from config import FREE_LIMIT
    data = await asyncio.to_thread(load_data)
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
            "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19",
            context=context,
        )
        sent += 1
        user["last_limit_reminder"] = time.time()
        await asyncio.sleep(0.3)

    if sent:
        await asyncio.to_thread(save_data, data)
        logger.info("Limit reminders sent: %d", sent)


# ============================================================================
# 3. ОБНОВЛЕНИЕ ПОСЛЕДНЕЙ АКТИВНОСТИ
# ============================================================================

def update_last_activity(user_id: str):
    """
    Вызывается при каждом сообщении пользователя.

    Раньше делала load_data()/save_data() — полный скан и перезапись ВСЕЙ
    таблицы Users на каждое сообщение от любого пользователя. Заменено на
    точечный get_user/save_user (SELECT/UPDATE по одному user_id), как и
    остальной код после фикса get_lang().
    """
    from storage import get_user, save_user
    user = get_user(user_id)
    if not user:
        return
    user["last_activity"] = time.time()
    save_user(user_id, user)


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
        # run_web_scan делает синхронные requests-запросы (до 15с таймаут
        # каждый) на несколько порталов подряд — может занимать десятки
        # секунд. Эта задача крутится на ОСНОВНОМ event loop бота
        # (_run_async), поэтому без to_thread всё это время бот не отвечает
        # ни одному живому пользователю.
        new_count = await asyncio.to_thread(run_web_scan, "berlin", 2000)
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
            bot = _get_bot(context)
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
    await _safe_send(GROUP_ID, text, parse_mode="Markdown", context=context)


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

async def send_daily_admin_report(context=None):
    """
    Ежедневная сводка админу: новые пользователи, анализы (успешные/
    неудачные), платежи, сработавшие алерты за сутки, плюс текущее
    состояние health-check. Раз в день, не троттлится (в отличие от
    alert_admin) — это плановый отчёт, а не реакция на конкретный сбой.

    ВАЖНО: метрики читаются из metrics.py, который хранит события в
    локальном JSONL-файле на эфемерном диске Render — если бот
    перезапускался в течение дня, часть событий могла быть потеряна
    (см. docstring metrics.py). Отчёт остаётся полезным индикатором
    тренда, но не абсолютно точным счётчиком.
    """
    admin_id = os.getenv("ADMIN_ID", "")
    if not admin_id or not context or not context.application:
        return

    from metrics import get_daily_summary
    from health import run_health_checks

    summary = get_daily_summary(hours=24)

    webhook_url = os.getenv("WEBHOOK_URL", "")
    token = os.getenv("TELEGRAM_TOKEN", "")
    health_line = "—"
    if webhook_url:
        try:
            ok, checks = await run_health_checks(context.application, webhook_url, token)
            if ok:
                health_line = "✅ всё в порядке"
            else:
                failed = [name for name, c in checks.items() if not c.get("ok")]
                health_line = f"⚠️ проблемы: {', '.join(failed)}"
        except Exception as e:
            health_line = f"⚠️ не удалось проверить: {str(e)[:100]}"

    alerts_text = ", ".join(summary["alerts_fired"]) if summary["alerts_fired"] else "нет"

    text = (
        f"📊 <b>Отчёт за сутки</b>\n\n"
        f"👤 Новых пользователей: {summary['new_users']}\n"
        f"✅ Анализов успешно: {summary['analyses_completed']}\n"
        f"❌ Анализов с ошибкой: {summary['analyses_failed']}\n"
        f"📷 Анализов по фото: {summary['photos_analyzed']}\n"
        f"📄 PDF сгенерировано: {summary['pdfs_generated']}\n"
        f"📝 Писем сгенерировано: {summary['letters_generated']}\n"
        f"💳 Оплат: {summary['payments_completed']}\n\n"
        f"🚨 Алерты за сутки: {alerts_text}\n"
        f"🩺 Health-check сейчас: {health_line}"
    )

    try:
        await context.application.bot.send_message(
            chat_id=int(admin_id), text=text, parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Failed to send daily admin report: %s", e)


def register_jobs(application):
    """Регистрирует все задачи в job_queue приложения.

    Вызывается из bot.py после создания Application.
    job_queue.run_repeating() создаёт задачу, которая повторяется
    с заданным интервалом. Если задача завершается с ошибкой,
    следующий запуск всё равно произойдёт.
    """
    jq = application.job_queue
    global _application
    _application = application

    # Группа: 10:00 и 18:00 по Берлину.
    #
    # ВАЖНО: используем zoneinfo, не pytz — pytz.timezone(...).localize(...)
    # "замораживает" DST-офсет на момент создания объекта (здесь — зима,
    # 1 января), и job_queue переиспользует этот же tzinfo для вычисления
    # времени запуска в течение всего года, включая лето, когда офсет
    # должен быть другим (CEST = UTC+2, а не CET = UTC+1). zoneinfo.ZoneInfo
    # пересчитывает офсет правильно для любой даты с одним и тем же объектом.
    #
    # Также используем .timetz(), а не .time() — .time() отбрасывает tzinfo
    # целиком, из-за чего PTB интерпретирует время как UTC (см. документацию
    # JobQueue.run_daily: "If the timezone is None, the default timezone of
    # the bot will be used, which is UTC"), а не как Europe/Berlin.
    berlin = ZoneInfo("Europe/Berlin")
    jq.run_daily(send_group_digest, time=datetime(2026, 1, 1, 10, 0, tzinfo=berlin).timetz(),
                 name="group_digest_10")
    jq.run_daily(send_group_digest, time=datetime(2026, 1, 1, 18, 0, tzinfo=berlin).timetz(),
                 name="group_digest_18")

    # Промо: 15:00 по Берлину
    jq.run_daily(send_promo_to_group, time=datetime(2026, 1, 1, 15, 0, tzinfo=berlin).timetz(),
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

    # Понедельник 10:00: email-дайджест.
    # ВАЖНО: в python-telegram-bot v20+ дни недели в run_daily идут
    # 0=воскресенье..6=суббота (изменено с 0=понедельник в более старых
    # версиях) — days=(0,) запускало бы задачу по ВОСКРЕСЕНЬЯМ, а не по
    # понедельникам. Понедельник — это 1.
    jq.run_daily(weekly_email_digest, time=datetime(2026, 1, 1, 10, 0, tzinfo=berlin).timetz(),
                 days=(1,), name="weekly_email_digest")

    # Ежедневный отчёт админу — 23:00 по Берлину, конец дня.
    jq.run_daily(send_daily_admin_report, time=datetime(2026, 1, 1, 23, 0, tzinfo=berlin).timetz(),
                 name="daily_admin_report")

    logger.info("All jobs registered in job_queue")
