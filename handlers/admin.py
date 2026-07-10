"""Админ-команды: stats, ref_stats, metrics, subscribers, post_now, set_timezone."""
import os
import time
import json
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from storage import save_user, get_user
from utils import get_lang
from messages import get_msg
from services.keyboards import kb

logger = logging.getLogger(__name__)


def _admin_id() -> int:
    return int(os.getenv("ADMIN_ID", "0"))


def _is_admin(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == _admin_id()


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update): return
    from storage import load_data
    data = await asyncio.to_thread(load_data)

    total_users = len(data)
    total_free = sum(u.get("free_used", 0) for u in data.values())
    total_balance = sum(max(0, u.get("balance", 0)) for u in data.values())
    total_paid = sum(1 for u in data.values() if u.get("last_paid_at", 0) > 0)
    total_vip = sum(1 for u in data.values() if u.get("vip"))
    total_pdf = sum(1 for u in data.values() if u.get("pdf_paid"))
    total_checks = sum(u.get("total_checks", 0) for u in data.values())
    unlimited = sum(1 for u in data.values() if u.get("balance") == -1)

    top_users = sorted(
        [(uid, u.get("total_checks", 0), u.get("balance", 0))
         for uid, u in data.items()],
        key=lambda x: x[1], reverse=True
    )[:10]

    top_text = ""
    for uid, checks, bal in top_users:
        if checks > 0:
            status = "∞" if bal == -1 else str(bal)
            top_text += f"  {uid}: {checks} проверок (баланс: {status})\n"

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"🔍 Всего проверок: <b>{total_checks}</b>\n"
        f"🆓 Потрачено бесплатных: <b>{total_free}</b>\n"
        f"💰 Остаток балансов: <b>{total_balance}</b>\n"
        f"♾️ Безлимитных: <b>{unlimited}</b>\n\n"
        f"💳 Оплачивали: <b>{total_paid}</b>\n"
        f"💎 VIP: <b>{total_vip}</b>\n"
        f"📄 PDF: <b>{total_pdf}</b>\n\n"
        f"🏆 <b>Топ:</b>\n{top_text or '  Нет данных'}"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def ref_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update): return
    try:
        events = []
        with open("referral_events.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                events.append(json.loads(line.strip()))

        now = time.time()
        today = sum(1 for e in events if now - e.get("ts", 0) < 86400)
        week = sum(1 for e in events if now - e.get("ts", 0) < 604800)
        total = len(events)

        limit_shown = sum(1 for e in events if e.get("type") == "limit_ref_shown")
        aha_shown = sum(1 for e in events if e.get("type") == "aha_moment_shown")
        trigger5 = sum(1 for e in events if e.get("type") == "5check_trigger_shown")
        clicked = sum(1 for e in events if e.get("type") == "ref_link_clicked")
        confirmed = sum(1 for e in events if e.get("type") == "referral_confirmed")

        conv = f"{confirmed}/{clicked}" if clicked else "0/0"
        rate = f"{confirmed/clicked*100:.0f}%" if clicked else "0%"

        text = (
            f"📊 <b>Рефералы</b>\n\n"
            f"📅 Сегодня: {today}\n📈 7 дней: {week}\n📋 Всего: {total}\n\n"
            f"🔗 Ссылка показана: {limit_shown}\n"
            f"🎉 Aha-moment: {aha_shown}\n"
            f"📊 Триггер 5: {trigger5}\n"
            f"👆 Кликнуто: {clicked}\n"
            f"✅ Подтверждено: {confirmed}\n\n"
            f"💰 Конверсия: {conv} ({rate})"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def metrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update): return
    try:
        from rent_scanner.storage import Storage
        from rent_scanner.config import RuntimeConfig
        config = RuntimeConfig.from_env()
        storage = Storage(config.database_path)
        stats = storage.full_stats()

        top = list(stats["by_source"].items())[:5]
        top_text = "\n".join(f"  {src}: {cnt}" for src, cnt in top) if top else "  нет данных"
        today = stats["today"]

        text = (
            f"📊 <b>Сканер</b>\n\n"
            f"👥 Подписчиков: {stats['subscribers']}\n"
            f"📋 Всего: {stats['total_leads']}\n"
            f"📤 Доставлено: {stats['total_notified']}\n\n"
            f"📅 <b>Сегодня:</b>\n"
            f"  Найдено: {today['found']}\n"
            f"  Доставлено: {today['delivered']}\n"
            f"  Ошибок: {today['errors']}\n\n"
            f"🏆 <b>Топ:</b>\n{top_text}"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def subscribers_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update): return
    try:
        from email_newsletter import get_active_subscribers
        subs = get_active_subscribers()
        await update.message.reply_text(f"📧 Подписчиков: {len(subs)}")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update): return
    await update.message.reply_text("🔄 Отправляю дайджест...")
    try:
        from scheduler import send_group_digest
        await send_group_digest()
        await update.message.reply_text("✅ Дайджест отправлен!")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    args = context.args

    if not args:
        await update.message.reply_text("🕐 /timezone Europe/Berlin", reply_markup=kb(update))
        return

    tz = args[0]
    user = await asyncio.to_thread(get_user, user_id)
    user["timezone"] = tz
    await asyncio.to_thread(save_user, user_id, user)
    await update.message.reply_text(f"✅ Часовой пояс: {tz}", reply_markup=kb(update))
