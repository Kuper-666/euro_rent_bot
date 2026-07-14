"""Хендлеры платежей: инвойсы, precheckout, successful_payment."""
import os
import time
import logging
import asyncio
from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes

from config import PDF_PRICE, VIP_PRICE, FREE_LIMIT
from storage import save_user, get_user
from utils import get_lang
from messages import get_msg
from services.keyboards import kb

logger = logging.getLogger(__name__)


async def pay_stars_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="3 проверки объявлений", description="Доступ к 3 проверкам.",
            payload="pay_stars_3", provider_token="", currency="XTR",
            prices=[LabeledPrice(label="3 проверки", amount=300)], need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт.", reply_markup=kb(update))


async def pay_stars_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="10 проверок объявлений", description="Доступ к 10 проверкам.",
            payload="pay_stars_9", provider_token="", currency="XTR",
            prices=[LabeledPrice(label="10 проверок", amount=900)], need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт.", reply_markup=kb(update))


async def pay_stars_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="Безлимит на месяц", description="Безлимитные проверки на 1 месяц.",
            payload="pay_stars_19", provider_token="", currency="XTR",
            prices=[LabeledPrice(label="Безлимит/мес", amount=1900)], need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт.", reply_markup=kb(update))


async def pay_stars_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="PDF заявление (Mieterprofil)", description="Готовое PDF-заявление.",
            payload="pay_stars_pdf", provider_token="", currency="XTR",
            prices=[LabeledPrice(label="PDF заявление", amount=PDF_PRICE * 100)],
            need_name=False, need_phone_number=False, need_email=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт.", reply_markup=kb(update))


async def pay_stars_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="VIP-подписка", description="Безлимитные проверки на 1 месяц.",
            payload="pay_stars_vip", provider_token="", currency="XTR",
            prices=[LabeledPrice(label="VIP/мес", amount=VIP_PRICE * 100)], need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт.", reply_markup=kb(update))


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    valid = {"pay_stars_3", "pay_stars_9", "pay_stars_19", "pay_stars_pdf", "pay_stars_vip"}
    if query.invoice_payload in valid:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Неизвестный способ оплаты.")


async def _save_paid_user(user_id: str, user: dict, update: Update, context: ContextTypes.DEFAULT_TYPE, success_text: str) -> None:
    """
    Сохраняет пользователя после оплаты и отвечает ему.

    КРИТИЧНО: на этом этапе Telegram Stars уже списаны — если save_user
    не сработает и мы просто промолчим, пользователь заплатил и ничего
    не получил, без единого слова объяснения. Поэтому: несколько попыток
    сохранения, и если все провалились — явно говорим пользователю, что
    произошла ошибка (а не тихо ничего не отвечаем), и шлём алерт админу
    с деталями для ручного зачисления.
    """
    last_error = None
    for attempt in range(3):
        try:
            await asyncio.to_thread(save_user, user_id, user)
            await update.message.reply_text(success_text, reply_markup=kb(update))
            return
        except Exception as e:
            last_error = e
            logger.error("save_user after payment failed (attempt %d) for user=%s: %s", attempt + 1, user_id, e)
            if attempt < 2:
                await asyncio.sleep(1 * (attempt + 1))

    # Все попытки провалились — Stars списаны, баланс не сохранён.
    logger.critical(
        "PAYMENT NOT CREDITED: user=%s payload_user_data=%s error=%s",
        user_id, user, last_error,
    )
    try:
        await update.message.reply_text(
            "⚠️ Оплата прошла, но произошла техническая ошибка при начислении.\n\n"
            "Мы уже получили уведомление и зачислим вручную в ближайшее время. "
            "Если этого не произошло в течение часа — напишите в поддержку.",
            reply_markup=kb(update),
        )
    except Exception:
        pass
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚨 Оплата не зачислена!\nuser_id={user_id}\ndata={user}\nerror={last_error}",
            )
        except Exception:
            pass


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    payload = update.message.successful_payment.invoice_payload

    try:
        user = await asyncio.to_thread(get_user, user_id)
    except Exception as e:
        logger.error("get_user after payment failed for user=%s: %s", user_id, e)
        user = {}

    if payload == "pay_stars_3":
        user["balance"] = user.get("balance", 0) + 3
        user["last_paid_at"] = time.time()
        remaining = user["balance"] + max(0, FREE_LIMIT - user.get("free_used", 0))
        await _save_paid_user(user_id, user, update, context, f"✅ +3 проверки. Осталось: {remaining}")

    elif payload == "pay_stars_9":
        user["balance"] = user.get("balance", 0) + 10
        user["last_paid_at"] = time.time()
        remaining = user["balance"] + max(0, FREE_LIMIT - user.get("free_used", 0))
        await _save_paid_user(user_id, user, update, context, f"✅ +10 проверок. Осталось: {remaining}")

    elif payload == "pay_stars_19":
        user["balance"] = -1
        user["last_paid_at"] = time.time()
        await _save_paid_user(user_id, user, update, context, "✅ Безлимит на месяц!")

    elif payload == "pay_stars_pdf":
        user["pdf_paid"] = True
        user["pdf_state"] = "awaiting_data"
        user["pdf_started_at"] = time.time()
        await _save_paid_user(user_id, user, update, context, "✅ PDF оплачен! Отправьте данные.")

    elif payload == "pay_stars_vip":
        user["vip"] = True
        user["vip_state"] = "awaiting_criteria"
        user["last_paid_at"] = time.time()
        await _save_paid_user(user_id, user, update, context, "✅ VIP активирован! Отправьте критерии поиска.")


# ── Алиасы команд оплаты ───────────────────────────────────────

async def pay_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await pay_stars_3(update, context)

async def pay_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await pay_stars_9(update, context)

async def pay_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await pay_stars_19(update, context)


# ── Админ-подтверждения ────────────────────────────────────────

def _check_admin(update: Update) -> bool:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    return update.effective_user and update.effective_user.id == ADMIN_ID


async def pay_done_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_admin(update): return
    user_id = str(update.effective_user.id)
    user = await asyncio.to_thread(get_user, user_id)
    user["balance"] = user.get("balance", 0) + 3
    user["last_paid_at"] = time.time()
    await asyncio.to_thread(save_user, user_id, user)
    remaining = user["balance"] + max(0, FREE_LIMIT - user.get("free_used", 0))
    lang = await asyncio.to_thread(get_lang, update)
    await update.message.reply_text(get_msg(lang, "pay_done_3").format(remaining), reply_markup=kb(update))


async def pay_done_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_admin(update): return
    user_id = str(update.effective_user.id)
    user = await asyncio.to_thread(get_user, user_id)
    user["balance"] = user.get("balance", 0) + 10
    user["last_paid_at"] = time.time()
    await asyncio.to_thread(save_user, user_id, user)
    remaining = user["balance"] + max(0, FREE_LIMIT - user.get("free_used", 0))
    lang = await asyncio.to_thread(get_lang, update)
    await update.message.reply_text(get_msg(lang, "pay_done_9").format(remaining), reply_markup=kb(update))


async def pay_done_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_admin(update): return
    user_id = str(update.effective_user.id)
    user = await asyncio.to_thread(get_user, user_id)
    user["balance"] = -1
    user["last_paid_at"] = time.time()
    await asyncio.to_thread(save_user, user_id, user)
    lang = await asyncio.to_thread(get_lang, update)
    await update.message.reply_text(get_msg(lang, "pay_done_19"), reply_markup=kb(update))


async def pay_done_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_admin(update): return
    user_id = str(update.effective_user.id)
    user = await asyncio.to_thread(get_user, user_id)
    user["pdf_paid"] = True
    user["pdf_state"] = "awaiting_data"
    user["pdf_started_at"] = time.time()
    await asyncio.to_thread(save_user, user_id, user)
    lang = await asyncio.to_thread(get_lang, update)
    await update.message.reply_text(get_msg(lang, "pdf_need_data"), reply_markup=kb(update))


async def pay_done_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _check_admin(update): return
    user_id = str(update.effective_user.id)
    user = await asyncio.to_thread(get_user, user_id)
    user["vip"] = True
    user["vip_state"] = "awaiting_criteria"
    await asyncio.to_thread(save_user, user_id, user)
    lang = await asyncio.to_thread(get_lang, update)
    await update.message.reply_text(get_msg(lang, "vip_ask_criteria"), reply_markup=kb(update))


# ── Пакеты ─────────────────────────────────────────────────────

async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Оплата через Telegram Stars:\n\n"
        "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
        "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
        "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19\n\n"
        "Нажми команду выше для оплаты."
    )
    await update.message.reply_text(text, reply_markup=kb(update))


async def pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user = await asyncio.to_thread(get_user, user_id)
    lang = await asyncio.to_thread(get_lang, update)

    if user.get("pdf_paid"):
        user["pdf_state"] = "awaiting_data"
        await asyncio.to_thread(save_user, user_id, user)
        text = get_msg(lang, "pdf_need_data")
    else:
        text = f"PDF-заявление (Mieterprofil) — {PDF_PRICE * 100} Stars (~5EUR)\n\nОплатите: /pay_stars_pdf"

    await update.message.reply_text(text, reply_markup=kb(update))


async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user = await asyncio.to_thread(get_user, user_id)
    lang = await asyncio.to_thread(get_lang, update)

    if user.get("vip"):
        text = "VIP уже активирован! Критерии: " + user.get("vip_criteria", "не заданы")
    else:
        text = get_msg(lang, "vip_intro")

    await update.message.reply_text(text, reply_markup=kb(update))
