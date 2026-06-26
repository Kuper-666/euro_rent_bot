import os
import logging
import threading
import time
from io import BytesIO
from telegram.helpers import escape_markdown
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from groq import Groq

from config import TELEGRAM_TOKEN, GROQ_API_KEY, WEBHOOK_URL, AFFILIATE_REVOLUT, AFFILIATE_WISE
from messages import get_msg
from utils import (
    load_data, save_data, get_lang, get_user_data,
    can_use, use_check, is_url, fetch_url_text, ocr_from_photo,
    calc_remaining
)
from pdf_generator import generate_mieterprofil_pdf
from web import app

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def get_keyboard():
    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/help"), KeyboardButton("/pay")]
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


def check_followups(user: dict, lang: str) -> str:
    now = time.time()
    last_paid = user.get("last_paid_at", 0)
    if not last_paid:
        return ""

    balance = user.get("balance", 0)
    days_since = (now - last_paid) / 86400

    if balance == 1 and 2.5 <= days_since <= 4:
        return (
            "Вы использовали 1 проверку из пакета.\n"
            "Хотите купить пакет на 5 проверок со скидкой 40%?\n"
            "Отправьте /pay_9"
        )

    if balance == 0 and 6 <= days_since <= 8:
        return (
            "Ваш анализ всё ещё доступен.\n"
            "Вы можете оформить подписку и получать подборки ежедневно!\n"
            "Подробнее: /pay"
        )

    return ""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    lang = get_lang(update)
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
    elif user_text:
        listing_text = user_text
    else:
        await update.message.reply_text(get_msg(lang, "send_listing"), reply_markup=get_keyboard())
        return

    await update.message.reply_text(get_msg(lang, "analyzing"), reply_markup=get_keyboard())

    try:
        system_prompt = get_msg(lang, "system_prompt")
        full_prompt = f"{system_prompt}\n\nListing text:\n{listing_text}"
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}]
        )
        result = response.choices[0].message.content

        use_check(user)
        remaining = calc_remaining(user)
        save_data(data)

        safe_result = escape_markdown(result, version=2)
        safe_footer = escape_markdown(get_msg(lang, "affiliate_footer"), version=2)
        remaining_text = "∞" if user["balance"] == -1 else str(remaining)
        balance_note = f"\n\n📊 Осталось проверок: {remaining_text}"
        share_invite = f"\n\n💬 {get_msg(lang, 'share_text')}\nhttps://t.me/{context.bot.username}?start=ref_{user_id}"

        await update.message.reply_text(
            safe_result + safe_footer + balance_note + share_invite,
            reply_markup=get_analysis_inline_buttons(),
            parse_mode="MarkdownV2"
        )

    except Exception as e:
        await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=get_keyboard())


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    lang = get_lang(update)
    data = load_data()
    user = get_user_data(data, user_id)

    if not can_use(user):
        await update.message.reply_text(get_msg(lang, "limit_reached"), reply_markup=get_keyboard())
        return

    await update.message.reply_text(get_msg(lang, "ocr_processing"), reply_markup=get_keyboard())

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        listing_text = ocr_from_photo(bytes(photo_bytes))

        if not listing_text or listing_text.startswith("ERROR"):
            await update.message.reply_text("❌ Не удалось распознать текст. Попробуйте отправить текст или ссылку.", reply_markup=get_keyboard())
            return

        await update.message.reply_text(get_msg(lang, "analyzing"), reply_markup=get_keyboard())

        system_prompt = get_msg(lang, "system_prompt")
        full_prompt = f"{system_prompt}\n\nListing text (from OCR):\n{listing_text}"
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}]
        )
        result = response.choices[0].message.content

        use_check(user)
        remaining = calc_remaining(user)
        save_data(data)

        safe_result = escape_markdown(result, version=2)
        safe_footer = escape_markdown(get_msg(lang, "affiliate_footer"), version=2)
        remaining_text = "∞" if user["balance"] == -1 else str(remaining)
        balance_note = f"\n\n📊 Осталось проверок: {remaining_text}"
        share_invite = f"\n\n💬 {get_msg(lang, 'share_text')}\nhttps://t.me/{context.bot.username}?start=ref_{user_id}"

        await update.message.reply_text(
            safe_result + safe_footer + balance_note + share_invite,
            reply_markup=get_analysis_inline_buttons(),
            parse_mode="MarkdownV2"
        )

    except Exception as e:
        await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=get_keyboard())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_lang(update)

    if query.data == "new":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(get_msg(lang, "send_listing"), reply_markup=get_keyboard())

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
    await update.message.reply_text(get_msg(lang, "start"), reply_markup=get_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
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
    keyboard = [
        [InlineKeyboardButton("🔹 3€ — 1 проверка", callback_data="show_pay_3")],
        [InlineKeyboardButton("💎 9€ — 5 проверок (−40%)", callback_data="show_pay_9")],
        [InlineKeyboardButton("👑 19€ — безлимит/мес", callback_data="show_pay_19")],
        [InlineKeyboardButton("📄 5€ — PDF заявление", callback_data="show_pay_pdf")],
        [InlineKeyboardButton("⭐ 15€/мес — VIP подборки", callback_data="show_pay_vip")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите тариф:", reply_markup=reply_markup)


async def pay_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "pay_3"), reply_markup=get_keyboard())


async def pay_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "pay_9"), reply_markup=get_keyboard())


async def pay_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "pay_19"), reply_markup=get_keyboard())


async def pay_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "pay_pdf"), reply_markup=get_keyboard())


async def pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    if user.get("pdf_paid"):
        user["pdf_state"] = "awaiting_data"
        save_data(data)
        await update.message.reply_text(get_msg(lang, "pdf_need_data"), reply_markup=get_keyboard())
    else:
        await update.message.reply_text(get_msg(lang, "pdf_intro"), reply_markup=get_keyboard())


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

    if user.get("vip"):
        await update.message.reply_text("⭐ VIP уже активирован! Критерии: " + user.get("vip_criteria", "не заданы"), reply_markup=get_keyboard())
    else:
        await update.message.reply_text(get_msg(lang, "vip_intro"), reply_markup=get_keyboard())


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

    user["balance"] += 1
    user["last_paid_at"] = time.time()
    save_data(data)
    remaining = user["balance"] + (FREE_LIMIT - user["free_used"])
    await update.message.reply_text(get_msg(lang, "pay_done_3").format(remaining), reply_markup=get_keyboard())


async def pay_done_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] += 5
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


def run_flask():
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask started in background")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("revolut", revolut_command))
    application.add_handler(CommandHandler("pay", pay_command))
    application.add_handler(CommandHandler("pay_3", pay_3))
    application.add_handler(CommandHandler("pay_9", pay_9))
    application.add_handler(CommandHandler("pay_19", pay_19))
    application.add_handler(CommandHandler("pay_pdf", pay_pdf))
    application.add_handler(CommandHandler("pdf", pdf_command))
    application.add_handler(CommandHandler("pay_done_pdf", pay_done_pdf))
    application.add_handler(CommandHandler("vip", vip_command))
    application.add_handler(CommandHandler("pay_vip", pay_vip))
    application.add_handler(CommandHandler("pay_done_vip", pay_done_vip))
    application.add_handler(CommandHandler("pay_done_3", pay_done_3))
    application.add_handler(CommandHandler("pay_done_9", pay_done_9))
    application.add_handler(CommandHandler("pay_done_19", pay_done_19))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Starting bot polling...")
    application.run_polling(drop_pending_updates=True)
