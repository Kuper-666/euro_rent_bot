import os
import logging
import threading
import time
from io import BytesIO
from telegram.helpers import escape_markdown
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, PreCheckoutQueryHandler, filters, ContextTypes
)
from groq import Groq

from config import TELEGRAM_TOKEN, GROQ_API_KEY, WEBHOOK_URL, AFFILIATE_REVOLUT, AFFILIATE_WISE, FREE_LIMIT
from messages import get_msg
from utils import (
    load_data, save_data, get_lang, get_user_data,
    can_use, use_check, is_url, fetch_url_text, ocr_from_photo,
    calc_remaining, check_rate_limit, sanitize_pdf_input
)
from pdf_generator import generate_mieterprofil_pdf
from web import app

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def get_keyboard():
    keyboard = [
        [KeyboardButton("Старт"), KeyboardButton("Помощь"), KeyboardButton("Оплата")],
        [KeyboardButton("PDF"), KeyboardButton("VIP")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_analysis_inline_buttons():
    keyboard = [
        [
            InlineKeyboardButton("📋 Скопировать перевод", callback_data="copy"),
            InlineKeyboardButton("🔍 Ещё одно объявление", callback_data="new"),
        ],
        [
            InlineKeyboardButton("📄 Получить PDF", callback_data="pdf"),
            InlineKeyboardButton("🌐 Поделиться", callback_data="share"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def split_message(text: str, max_len: int = 4000) -> list:
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts


async def process_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, listing_text: str, user_id: str, lang: str) -> None:
    data = load_data()
    user = get_user_data(data, user_id)

    is_admin = False
    if update.effective_chat.type in ["group", "supergroup"]:
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
            if member.status in ["administrator", "creator"]:
                is_admin = True
        except Exception:
            pass

    try:
        system_prompt = get_msg(lang, "system_prompt")
        full_prompt = f"{system_prompt}\n\nListing text:\n{listing_text}"
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}]
        )
        result = response.choices[0].message.content

        if is_admin:
            save_data(data)
        else:
            use_check(user)
            save_data(data)

        remaining = calc_remaining(user)
        safe_result = escape_markdown(result, version=2)
        safe_footer = escape_markdown(get_msg(lang, "affiliate_footer"), version=2)
        remaining_text = "\\u221e" if user["balance"] == -1 else escape_markdown(str(remaining), version=2)
        admin_note = escape_markdown("\n\nАдмин: проверка бесплатная", version=2) if is_admin else ""
        safe_balance = escape_markdown(f"\n\nОсталось проверок: ", version=2) + remaining_text
        safe_share = escape_markdown(f"\n\n{get_msg(lang, 'share_text')}\nhttps://t.me/{context.bot.username}?start=ref_{user_id}", version=2)

        full_text = safe_result + safe_footer + admin_note + safe_balance + safe_share
        parts = split_message(full_text)
        for i, part in enumerate(parts):
            markup = get_analysis_inline_buttons() if i == len(parts) - 1 else None
            await update.message.reply_text(part, reply_markup=markup, parse_mode="MarkdownV2")

    except Exception as e:
        if "insufficient_quota" in str(e) or "429" in str(e):
            await update.message.reply_text(
                "Извините, анализатор сейчас перегружен.\n\n"
                "Попробуйте отправить объявление через 5-10 минут — я обязательно отвечу!\n\n"
                "А пока можете:\n"
                "- Прочитать /help о тарифах\n"
                "- Отправить ссылку позже",
                reply_markup=get_keyboard()
            )
        else:
            await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=get_keyboard())


def check_followups(user: dict, lang: str) -> str:
    now = time.time()
    last_paid = user.get("last_paid_at", 0)
    free_used = user.get("free_used", 0)
    balance = user.get("balance", 0)

    if balance == -1:
        return ""

    if balance > 0 and last_paid:
        days_since = (now - last_paid) / 86400
        if 2.5 <= days_since <= 4:
            return (
                "Вы использовали часть проверок из пакета.\n"
                "Хотите докупить? /pay\n"
            )

    if free_used >= FREE_LIMIT and balance == 0:
        return (
            "Все бесплатные проверки использованы.\n\n"
            "Пакеты и цены:\n"
            "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
            "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
            "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19\n\n"
            "Подробнее: /pay"
        )

    return ""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.replace('\xa0', ' ').strip().lower()
    lang = get_lang(update)

    btn_map = {
        "старт": start, "start": start,
        "помощь": help_command, "help": help_command,
        "оплата": pay_command, "pay": pay_command, "оплатить": pay_command,
        "pdf": pdf_command, "пдф": pdf_command,
        "vip": vip_command, "вип": vip_command,
    }
    if text in btn_map:
        await btn_map[text](update, context)
        return

    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)

    followup = check_followups(user, lang)
    if followup:
        await update.message.reply_text(followup, reply_markup=get_keyboard())

    pdf_state = user.get("pdf_state")
    if pdf_state == "awaiting_data":
        user.pop("pdf_state", None)
        pdf_data = parse_pdf_data(update.message.text)
        if not pdf_data:
            await update.message.reply_text("❌ Не удалось распознать данные. Попробуйте ещё раз.", reply_markup=get_keyboard())
            return
        await update.message.reply_text(get_msg(lang, "pdf_generating"), reply_markup=get_keyboard())
        try:
            pdf_bytes = generate_mieterprofil_pdf(pdf_data)
            await update.message.reply_document(
                document=BytesIO(pdf_bytes),
                filename="Mieterprofil.pdf",
                caption=get_msg(lang, "pdf_done"),
                reply_markup=get_keyboard()
            )
        except Exception as e:
            await update.message.reply_text(get_msg(lang, "pdf_error").format(e), reply_markup=get_keyboard())
        return

    vip_state = user.get("vip_state")
    if vip_state == "awaiting_criteria":
        user.pop("vip_state", None)
        user["vip"] = True
        user["vip_criteria"] = update.message.text
        save_data(data)
        await update.message.reply_text(
            f"✅ *VIP активирован!*\n\nКритерии сохранены:\n{update.message.text}\n\nЯ буду присылать подборку каждый день!",
            reply_markup=get_keyboard(),
            parse_mode="Markdown"
        )
        return

    if not can_use(user):
        await update.message.reply_text(get_msg(lang, "limit_reached"), reply_markup=get_keyboard())
        return

    user_text = update.message.text

    if user_text and is_url(user_text):
        await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=get_keyboard())
        listing_text = fetch_url_text(user_text)
        if listing_text.startswith("ERROR"):
            await update.message.reply_text(
                "❌ Не удалось загрузить страницу (сайт блокирует парсер).\n\n"
                "Скопируйте текст объявления и отправьте его сюда.",
                reply_markup=get_keyboard()
            )
            return
    elif user_text:
        listing_text = user_text
    else:
        await update.message.reply_text(get_msg(lang, "send_listing"), reply_markup=get_keyboard())
        return

    if len(listing_text) < 10:
        await update.message.reply_text("❌ Текст слишком короткий. Отправьте полное объявление.", reply_markup=get_keyboard())
        return

    allowed, wait = check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(
            f"⏳ Подождите {int(wait)} сек. перед следующим анализом.",
            reply_markup=get_keyboard()
        )
        return

    await update.message.reply_text(get_msg(lang, "analyzing"), reply_markup=get_keyboard())
    await process_listing(update, context, listing_text, user_id, lang)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    lang = get_lang(update)
    data = load_data()
    user = get_user_data(data, user_id)

    if not can_use(user):
        await update.message.reply_text(get_msg(lang, "limit_reached"), reply_markup=get_keyboard())
        return

    allowed, wait = check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(
            f"⏳ Подождите {int(wait)} сек. перед следующим анализом.",
            reply_markup=get_keyboard()
        )
        return

    await update.message.reply_text(get_msg(lang, "ocr_processing"), reply_markup=get_keyboard())

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    listing_text = ocr_from_photo(bytes(photo_bytes))

    if not listing_text or listing_text.startswith("ERROR"):
        await update.message.reply_text("❌ Не удалось распознать текст. Попробуйте отправить текст или ссылку.", reply_markup=get_keyboard())
        return

    await update.message.reply_text(get_msg(lang, "analyzing"), reply_markup=get_keyboard())
    await process_listing(update, context, listing_text, user_id, lang)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_lang(update)

    if query.data == "new":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(get_msg(lang, "send_listing"), reply_markup=get_keyboard())

    elif query.data == "analyze_ad":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Отправьте текст объявления или ссылку в личку боту!", reply_markup=get_keyboard())

    elif query.data == "skip_ad":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.answer("Ок", show_alert=False)

    elif query.data == "analyze_rss":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Отправьте ссылку на объявление сюда, и я сделаю разбор!",
            reply_markup=get_keyboard()
        )

    elif query.data == "skip_rss":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.answer("Хорошо, как известите!", show_alert=False)

    elif query.data == "share":
        bot_username = context.bot.username
        share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=🏠+ExpatRentBot+-+AI-бот+для+разбора+объявлений+по+аренде+в+Европе!"
        await query.message.reply_text(
            f"📤 {get_msg(lang, 'share_text')}\n\n{share_url}",
            reply_markup=get_keyboard()
        )

    elif query.data == "copy":
        await query.answer("Скопируйте текст выше 👆", show_alert=True)

    elif query.data == "pdf":
        user_id = str(update.effective_user.id)
        data = load_data()
        user = get_user_data(data, user_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(get_msg(lang, "pay_pdf"), reply_markup=get_keyboard())

    elif query.data.startswith("show_pay_"):
        await query.edit_message_reply_markup(reply_markup=None)
        plan = query.data.replace("show_pay_", "")
        msg_key = f"pay_{plan}" if plan != "pdf" else "pay_pdf"
        if plan == "vip":
            msg_key = "vip_intro"
        await query.message.reply_text(get_msg(lang, msg_key), reply_markup=get_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)

    if context.args and len(context.args) > 0:
        payload = context.args[0]
        if payload.startswith("analyze_"):
            url = payload[len("analyze_"):]
            if is_url(url):
                await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=get_keyboard())
                listing_text = fetch_url_text(url)
                if listing_text.startswith("ERROR"):
                    await update.message.reply_text(
                        "❌ Не удалось загрузить страницу (сайт блокирует парсер).\n\n"
                        "Скопируйте текст объявления и отправьте его сюда.",
                        reply_markup=get_keyboard()
                    )
                    return
                await process_listing(update, context, listing_text, user_id=str(update.effective_user.id), lang=lang)
                return

    logo_path = os.path.join(os.path.dirname(__file__), "icons", "start.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=get_msg(lang, "start"), reply_markup=get_keyboard())
    else:
        await update.message.reply_text(get_msg(lang, "start"), reply_markup=get_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    icon_path = os.path.join(os.path.dirname(__file__), "icons", "help.png")
    if os.path.exists(icon_path):
        with open(icon_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=get_msg(lang, "help"), reply_markup=get_keyboard())
    else:
        await update.message.reply_text(get_msg(lang, "help"), reply_markup=get_keyboard())


async def revolut_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Для оплаты депозита вам понадобится европейский счёт.\n\n"
        "Откройте Revolut по моей ссылке и получите бонус:\n"
        f"{AFFILIATE_REVOLUT}\n\n"
        "Или Wise:\n"
        f"{AFFILIATE_WISE}"
    )
    keyboard = [
        [InlineKeyboardButton("Открыть Revolut", url=AFFILIATE_REVOLUT)],
        [InlineKeyboardButton("Открыть Wise", url=AFFILIATE_WISE)],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Оплата через Telegram Stars:\n\n"
        "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
        "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
        "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19\n\n"
        "Нажми команду выше для оплаты."
    )
    icon_path = os.path.join(os.path.dirname(__file__), "icons", "pay.png")
    if os.path.exists(icon_path):
        with open(icon_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=text, reply_markup=get_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_keyboard())


async def pay_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="3 проверки объявлений",
            description="Доступ к 3 проверкам объявлений об аренде.",
            payload="pay_stars_3",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="3 проверки", amount=300)],
            need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт. У вас достаточно Stars?", reply_markup=get_keyboard())


async def pay_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="10 проверок объявлений",
            description="Доступ к 10 проверкам объявлений об аренде.",
            payload="pay_stars_9",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="10 проверок", amount=900)],
            need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт. У вас достаточно Stars?", reply_markup=get_keyboard())


async def pay_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="Безлимит на месяц",
            description="Безлимитные проверки объявлений на 1 месяц.",
            payload="pay_stars_19",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Безлимит/мес", amount=1900)],
            need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт. У вас достаточно Stars?", reply_markup=get_keyboard())


async def pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    icon_path = os.path.join(os.path.dirname(__file__), "icons", "pdf.png")
    if user.get("pdf_paid"):
        user["pdf_state"] = "awaiting_data"
        save_data(data)
        text = get_msg(lang, "pdf_need_data")
    else:
        text = "PDF-заявление (Mieterprofil) — 500 Stars (~5EUR)\n\nОплатите: /pay_stars_pdf\n\nПосле оплаты отправьте данные."

    if os.path.exists(icon_path):
        with open(icon_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=text, reply_markup=get_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_keyboard())


async def pay_stars_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_invoice(
        title="PDF заявление (Mieterprofil)",
        description="Готовое PDF-заявление на аренду для房东.",
        payload="pay_stars_pdf",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="PDF заявление", amount=500)],
        need_name=False,
        need_phone_number=False,
        need_email=False,
    )


async def pay_done_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["pdf_paid"] = True
    user["pdf_state"] = "awaiting_data"
    save_data(data)
    await update.message.reply_text(get_msg(lang, "pdf_need_data"), reply_markup=get_keyboard())


async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    icon_path = os.path.join(os.path.dirname(__file__), "icons", "vip.png")
    if user.get("vip"):
        text = "VIP уже активирован! Критерии: " + user.get("vip_criteria", "не заданы")
    else:
        text = get_msg(lang, "vip_intro")

    if os.path.exists(icon_path):
        with open(icon_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=text, reply_markup=get_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_keyboard())


async def pay_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "vip_intro"), reply_markup=get_keyboard())


async def pay_done_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["vip"] = True
    user["vip_state"] = "awaiting_criteria"
    save_data(data)
    await update.message.reply_text(get_msg(lang, "vip_ask_criteria"), reply_markup=get_keyboard())


async def pay_done_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] += 3
    user["last_paid_at"] = time.time()
    save_data(data)
    remaining = user["balance"] + (FREE_LIMIT - user["free_used"])
    await update.message.reply_text(get_msg(lang, "pay_done_3").format(remaining), reply_markup=get_keyboard())


async def pay_done_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] += 10
    user["last_paid_at"] = time.time()
    save_data(data)
    remaining = user["balance"] + (FREE_LIMIT - user["free_used"])
    await update.message.reply_text(get_msg(lang, "pay_done_9").format(remaining), reply_markup=get_keyboard())


async def pay_done_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] = -1
    user["last_paid_at"] = time.time()
    save_data(data)
    await update.message.reply_text(get_msg(lang, "pay_done_19"), reply_markup=get_keyboard())


def parse_pdf_data(text: str) -> dict:
    text = sanitize_pdf_input(text)
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    data = {}
    keys = ["name", "dob", "phone", "email", "address", "employer", "income", "occupants"]
    for i, key in enumerate(keys):
        if i < len(lines):
            line = lines[i]
            import re
            line = re.sub(r'^[1-8]\.\s+', '', line)
            data[key] = line
    return data


async def pay_stars_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="3 проверки объявлений",
            description="Доступ к 3 проверкам объявлений об аренде.",
            payload="pay_stars_3",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="3 проверки", amount=300)],
            need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт. Проверьте баланс Stars.", reply_markup=get_keyboard())


async def pay_stars_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="10 проверок объявлений",
            description="Доступ к 10 проверкам объявлений об аренде.",
            payload="pay_stars_9",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="10 проверок", amount=900)],
            need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт. Проверьте баланс Stars.", reply_markup=get_keyboard())


async def pay_stars_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="Безлимит на месяц",
            description="Безлимитные проверки объявлений на 1 месяц.",
            payload="pay_stars_19",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Безлимит/мес", amount=1900)],
            need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт. Проверьте баланс Stars.", reply_markup=get_keyboard())


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    valid_payloads = {"pay_stars_3", "pay_stars_9", "pay_stars_19", "pay_stars_pdf", "pay_stars_vip"}
    if query.invoice_payload in valid_payloads:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Неизвестный способ оплаты. Попробуйте снова.")


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)
    payload = update.message.successful_payment.invoice_payload

    if payload == "pay_stars_3":
        user["balance"] += 3
        user["last_paid_at"] = time.time()
        save_data(data)
        remaining = user["balance"] + (FREE_LIMIT - user["free_used"])
        await update.message.reply_text(
            f"Оплата подтверждена! Добавлены 3 проверки. Осталось: {remaining}",
            reply_markup=get_keyboard()
        )
    elif payload == "pay_stars_9":
        user["balance"] += 10
        user["last_paid_at"] = time.time()
        save_data(data)
        remaining = user["balance"] + (FREE_LIMIT - user["free_used"])
        await update.message.reply_text(
            f"Оплата подтверждена! Добавлено 10 проверок. Осталось: {remaining}",
            reply_markup=get_keyboard()
        )
    elif payload == "pay_stars_19":
        user["balance"] = -1
        user["last_paid_at"] = time.time()
        save_data(data)
        await update.message.reply_text(
            "Оплата подтверждена! Безлимит на месяц активирован!",
            reply_markup=get_keyboard()
        )
    elif payload == "pay_stars_pdf":
        user["pdf_paid"] = True
        user["pdf_state"] = "awaiting_data"
        save_data(data)
        await update.message.reply_text(
            "Оплата PDF подтверждена! Отправьте данные для заявления.",
            reply_markup=get_keyboard()
        )


def run_flask():
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    new_member = update.chat_member.new_chat_member
    old_member = update.chat_member.old_chat_member

    if old_member.status != "member" and new_member.status == "member":
        if new_member.user.id != context.bot.id:
            welcome_text = (
                f"Добро пожаловать, {new_member.user.full_name}!\n\n"
                f"Этот чат создан для экспатов в Европе. "
                f"Полезные ссылки и подборки по аренде можно найти в закрепленных сообщениях.\n"
                f"Бот EuroRent AI всегда поможет с анализом объявлений.\n\n"
                f"Начните с /start"
            )
            msg = await update.effective_chat.send_message(welcome_text)
            try:
                await msg.pin()
            except Exception:
                pass


async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.pin()
            await update.message.reply_text("Сообщение закреплено!")
        except Exception:
            await update.message.reply_text("Не удалось закрепить. Проверьте права бота в чате.")
    else:
        await update.message.reply_text("Чтобы закрепить пост, ответьте на него и напишите /pin")


async def group_greeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type in ["group", "supergroup"]:
        first_name = update.effective_user.first_name
        await update.message.reply_text(
            f"Привет, {first_name}! Рад тебя видеть в чате.\n"
            "Кидай ссылку на любое объявление об аренде, я разберу его за 5 секунд!"
        )


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask started in background")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("revolut", revolut_command))
    application.add_handler(CommandHandler("pay", pay_command))
    application.add_handler(CommandHandler("pdf", pdf_command))
    application.add_handler(CommandHandler("pay_done_pdf", pay_done_pdf))
    application.add_handler(CommandHandler("vip", vip_command))
    application.add_handler(CommandHandler("pay_vip", pay_vip))
    application.add_handler(CommandHandler("pay_done_vip", pay_done_vip))
    application.add_handler(CommandHandler("pay_done_3", pay_done_3))
    application.add_handler(CommandHandler("pay_done_9", pay_done_9))
    application.add_handler(CommandHandler("pay_done_19", pay_done_19))
    application.add_handler(CommandHandler("pay_stars_3", pay_stars_3))
    application.add_handler(CommandHandler("pay_stars_9", pay_stars_9))
    application.add_handler(CommandHandler("pay_stars_19", pay_stars_19))
    application.add_handler(CommandHandler("pay_stars_pdf", pay_stars_pdf))
    application.add_handler(CommandHandler("pay_3", pay_3))
    application.add_handler(CommandHandler("pay_9", pay_9))
    application.add_handler(CommandHandler("pay_19", pay_19))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(CommandHandler("pin", pin_message))
    application.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r'(?i)^(привет|здравствуй|hello|hi|добрый день|доброе утро|добрый вечер|ку|хай)'),
        group_greeting
    ))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.ChatType.GROUP & filters.Entity("url"), handle_message))

    logging.info("Starting bot polling...")
    application.run_polling(drop_pending_updates=True)
