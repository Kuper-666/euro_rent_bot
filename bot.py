import os
import logging
import threading
from io import BytesIO
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from groq import Groq

from config import TELEGRAM_TOKEN, GROQ_API_KEY, WEBHOOK_URL
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
        [KeyboardButton("/start"), KeyboardButton("/help"), KeyboardButton("/pay_done_3")]
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    lang = get_lang(update)
    data = load_data()
    user = get_user_data(data, user_id)

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

        footer = get_msg(lang, "affiliate_footer")
        balance_note = f"\n\n📊 *Осталось проверок:* {remaining}" if user["balance"] != -1 else ""
        share_invite = f"\n\n💬 {get_msg(lang, 'share_text')}\nhttps://t.me/{context.bot.username}?start=ref_{user_id}"

        await update.message.reply_text(
            result + footer + balance_note + share_invite,
            reply_markup=get_analysis_inline_buttons(),
            parse_mode="Markdown"
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

        footer = get_msg(lang, "affiliate_footer")
        balance_note = f"\n\n📊 *Осталось проверок:* {remaining}" if user["balance"] != -1 else ""
        share_invite = f"\n\n💬 {get_msg(lang, 'share_text')}\nhttps://t.me/{context.bot.username}?start=ref_{user_id}"

        await update.message.reply_text(
            result + footer + balance_note + share_invite,
            reply_markup=get_analysis_inline_buttons(),
            parse_mode="Markdown"
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
        await query.message.reply_text(get_msg(lang, "pay_pdf"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "start"), reply_markup=get_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "help"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    text = (
        "💳 *Выберите тариф:*\n\n"
        "🔹 /pay_3 — *3€* за 1 проверку\n"
        "💎 /pay_9 — *9€* за 5 проверок \\(\\-40%\\)\n"
        "👑 /pay_19 — *19€* за безлимит на месяц\n\n"
        "📄 /pay_pdf — *5€* за PDF\\-заявление\n"
        "⭐ /pay_vip — *15€/мес* ежедневные подборки"
    )
    await update.message.reply_text(text, reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "pay_3"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "pay_9"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "pay_19"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "pay_pdf"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    if user.get("pdf_paid"):
        user["pdf_state"] = "awaiting_data"
        save_data(data)
        await update.message.reply_text(get_msg(lang, "pdf_need_data"), reply_markup=get_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(get_msg(lang, "pdf_intro"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_done_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["pdf_paid"] = True
    user["pdf_state"] = "awaiting_data"
    save_data(data)
    await update.message.reply_text(get_msg(lang, "pdf_need_data"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    if user.get("vip"):
        await update.message.reply_text("⭐ VIP уже активирован! Критерии: " + user.get("vip_criteria", "не заданы"), reply_markup=get_keyboard())
    else:
        await update.message.reply_text(get_msg(lang, "vip_intro"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "vip_intro"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_done_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["vip"] = True
    user["vip_state"] = "awaiting_criteria"
    save_data(data)
    await update.message.reply_text(get_msg(lang, "vip_ask_criteria"), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_done_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] += 1
    save_data(data)
    remaining = user["balance"] + (FREE_LIMIT - user["free_used"])
    await update.message.reply_text(get_msg(lang, "pay_done_3").format(remaining), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_done_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] += 5
    save_data(data)
    remaining = user["balance"] + (FREE_LIMIT - user["free_used"])
    await update.message.reply_text(get_msg(lang, "pay_done_9").format(remaining), reply_markup=get_keyboard(), parse_mode="Markdown")


async def pay_done_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] = -1
    save_data(data)
    await update.message.reply_text(get_msg(lang, "pay_done_19"), reply_markup=get_keyboard(), parse_mode="Markdown")


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
