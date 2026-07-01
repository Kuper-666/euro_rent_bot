import os
import re
import json
import logging
import threading
import time
import hashlib
from urllib.parse import unquote
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
from email_newsletter import add_email_subscriber, remove_email_subscriber, get_active_subscribers
from listing_features import (
    cmd_set_city, cmd_remove_city, cmd_my_city, cmd_trend, cmd_holygrail,
    get_user_city, filter_by_city, detect_city, record_listing, is_holy_grail,
    format_holy_grail_alert, extract_price, record_price, extract_score,
    POPULAR_CITIES, list_cities, set_user_city
)
from scheduler import update_last_activity, run_scheduler
from web import app

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Словарь для хранения ссылок из постов (message_id -> url)
_pending_listings = {}
PENDING_FILE = "pending_listings.json"


def _load_pending_listings():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_pending_listings(data):
    with open(PENDING_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def get_keyboard():
    keyboard = [
        [KeyboardButton("Старт"), KeyboardButton("Помощь"), KeyboardButton("Оплата")],
        [KeyboardButton("PDF"), KeyboardButton("VIP")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def kb(update, chat_type=None):
    """Reply-keyboard только в личке. В группе — None.
    chat_type: override для случаев, когда update.effective_chat != целевой чат."""
    if chat_type is None:
        chat_type = update.effective_chat.type if update and update.effective_chat else None
    if chat_type == "private":
        return get_keyboard()
    return None


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

        # Определяем город и цену для трендов
        city_key = detect_city(listing_text)
        price = extract_price(listing_text)
        if city_key and price:
            record_price(city_key, price)
        record_listing(
            url=listing_text[:200],
            city=city_key or "",
            price=price or 0,
            score=extract_score(result) if result else 5,
            text=listing_text,
        )

        # Добавляем примечание о городе
        city_note = ""
        if city_key:
            ci = POPULAR_CITIES[city_key]
            city_note = f"\n\n🏙 Город: {ci['emoji']} {ci['name']}"
            if price and ci.get("avg_price"):
                ratio = price / ci["avg_price"]
                if ratio < 0.75:
                    city_note += f"\n🔥 Цена {price} EUR — ниже средней ({ratio:.0%})"
                elif ratio < 0.9:
                    city_note += f"\n💰 Цена {price} EUR — ниже средней"

        if is_admin:
            save_data(data)
        else:
            use_check(user)
            save_data(data)

        remaining = calc_remaining(user)
        safe_result = escape_markdown(result, version=2)
        safe_footer = escape_markdown(get_msg(lang, "affiliate_footer"), version=2)
        remaining_text = "∞" if user["balance"] == -1 else escape_markdown(str(remaining), version=2)
        admin_note = escape_markdown("\n\nАдмин: проверка бесплатная", version=2) if is_admin else ""
        safe_balance = escape_markdown(f"\n\nОсталось проверок: ", version=2) + remaining_text
        safe_share = escape_markdown(f"\n\n{get_msg(lang, 'share_text')}\nhttps://t.me/{context.bot.username}?start=ref_{user_id}", version=2)

        full_text = safe_result + city_note + safe_footer + admin_note + safe_balance + safe_share
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
                reply_markup=kb(update)
            )
        else:
            await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=kb(update))


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
    update_last_activity(user_id)
    data = load_data()
    user = get_user_data(data, user_id)

    followup = check_followups(user, lang)
    if followup:
        await update.message.reply_text(followup, reply_markup=kb(update))

    pdf_state = user.get("pdf_state")
    if pdf_state == "awaiting_data":
        user.pop("pdf_state", None)
        pdf_data = parse_pdf_data(update.message.text)
        if not pdf_data:
            await update.message.reply_text("❌ Не удалось распознать данные. Попробуйте ещё раз.", reply_markup=kb(update))
            return
        await update.message.reply_text(get_msg(lang, "pdf_generating"), reply_markup=kb(update))
        try:
            pdf_bytes = generate_mieterprofil_pdf(pdf_data)
            await update.message.reply_document(
                document=BytesIO(pdf_bytes),
                filename="Mieterprofil.pdf",
                caption=get_msg(lang, "pdf_done"),
                reply_markup=kb(update)
            )
        except Exception as e:
            await update.message.reply_text(get_msg(lang, "pdf_error").format(e), reply_markup=kb(update))
        return

    vip_state = user.get("vip_state")
    if vip_state == "awaiting_criteria":
        user.pop("vip_state", None)
        user["vip"] = True
        user["vip_criteria"] = update.message.text
        save_data(data)
        await update.message.reply_text(
            f"✅ *VIP активирован!*\n\nКритерии сохранены:\n{update.message.text}\n\nЯ буду присылать подборку каждый день!",
            reply_markup=kb(update),
            parse_mode="Markdown"
        )
        return

    if not can_use(user):
        await update.message.reply_text(get_msg(lang, "limit_reached"), reply_markup=kb(update))
        return

    user_text = update.message.text

    if user_text and is_url(user_text):
        await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=kb(update))
        listing_text = fetch_url_text(user_text)
        if listing_text.startswith("ERROR"):
            await update.message.reply_text(
                "❌ Не удалось загрузить страницу (сайт блокирует парсер).\n\n"
                "Скопируйте текст объявления и отправьте его сюда.",
                reply_markup=kb(update)
            )
            return
    elif user_text:
        listing_text = user_text
    else:
        await update.message.reply_text(get_msg(lang, "send_listing"), reply_markup=kb(update))
        return

    if len(listing_text) < 10:
        await update.message.reply_text("❌ Текст слишком короткий. Отправьте полное объявление.", reply_markup=kb(update))
        return

    user_city = get_user_city(user_id)
    if user_city:
        detected = detect_city(listing_text)
        if detected and detected != user_city:
            user_city_info = POPULAR_CITIES.get(user_city, {})
            city_name = user_city_info.get("name", user_city)
            await update.message.reply_text(
                get_msg(lang, "city_filter_skip").format(user_city=city_name),
                reply_markup=kb(update),
            )
            return

    allowed, wait = check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(
            f"⏳ Подождите {int(wait)} сек. перед следующим анализом.",
            reply_markup=kb(update)
        )
        return

    await update.message.reply_text(get_msg(lang, "analyzing"), reply_markup=kb(update))
    await process_listing(update, context, listing_text, user_id, lang)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    lang = get_lang(update)
    data = load_data()
    user = get_user_data(data, user_id)

    if not can_use(user):
        await update.message.reply_text(get_msg(lang, "limit_reached"), reply_markup=kb(update))
        return

    save_data(data)

    allowed, wait = check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(
            f"⏳ Подождите {int(wait)} сек. перед следующим анализом.",
            reply_markup=kb(update)
        )
        return

    await update.message.reply_text(get_msg(lang, "ocr_processing"), reply_markup=kb(update))

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    listing_text = ocr_from_photo(bytes(photo_bytes))

    if not listing_text or listing_text.startswith("ERROR"):
        await update.message.reply_text("❌ Не удалось распознать текст. Попробуйте отправить текст или ссылку.", reply_markup=kb(update))
        return

    await update.message.reply_text(get_msg(lang, "analyzing"), reply_markup=kb(update))
    await process_listing(update, context, listing_text, user_id, lang)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_lang(update)
    user_id = str(update.effective_user.id)

    data_prefix = query.data.split(":")[0] if ":" in query.data else query.data

    # Кнопка "Ещё одно объявление" — в личку
    if data_prefix == "new":
        await query.edit_message_reply_markup(reply_markup=None)
        data = load_data()
        user = get_user_data(data, user_id)
        remaining = calc_remaining(user)
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                "🔍 Готов к анализу!\n\n"
                "Отправьте ссылку на объявление или текст.\n"
                f"Осталось проверок: {remaining}"
            ),
            reply_markup=kb(update, chat_type="private"),
        )

    # Кнопка "Проанализировать" из группы — отправляем в ЛИЧКУ
    elif data_prefix in ("analyze_ad", "analyze_rss"):
        await query.edit_message_reply_markup(reply_markup=None)
        data = load_data()
        user = get_user_data(data, user_id)

        if not can_use(user):
            await context.bot.send_message(
                chat_id=int(user_id),
                text=(
                    "❌ У вас закончились проверки.\n\n"
                    "Пакеты:\n"
                    "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
                    "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
                    "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19"
                ),
            )
            return

        remaining = calc_remaining(user)
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                "🔍 Анализ готов!\n\n"
                "Отправьте ссылку на объявление или текст прямо сюда, в личку.\n\n"
                f"📊 Осталось проверок: {remaining}"
            ),
            reply_markup=kb(update, chat_type="private"),
        )

    # Кнопка "Пропустить"
    elif data_prefix == "skip_ad":
        await query.answer("Ок", show_alert=False)

    # Кнопка "Скопировать"
    elif data_prefix == "copy":
        await query.answer("Скопируйте текст выше", show_alert=True)

    # Кнопка "Поделиться"
    elif data_prefix == "share":
        bot_username = context.bot.username
        share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=🏠+EuroRent+AI+-+AI-бот+для+разбора+объявлений+по+аренде+в+Европе!"
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"📤 {get_msg(lang, 'share_text')}\n\n{share_url}",
            reply_markup=kb(update, chat_type="private"),
        )

    # Кнопка "PDF"
    elif data_prefix == "pdf":
        await context.bot.send_message(
            chat_id=int(user_id),
            text=get_msg(lang, "pay_pdf"),
            reply_markup=kb(update, chat_type="private"),
        )

    # Кнопки оплаты
    elif data_prefix.startswith("show_pay_"):
        plan = data_prefix.replace("show_pay_", "")
        msg_key = f"pay_{plan}" if plan != "pdf" else "pay_pdf"
        if plan == "vip":
            msg_key = "vip_intro"
        await context.bot.send_message(
            chat_id=int(user_id),
            text=get_msg(lang, msg_key),
            reply_markup=kb(update, chat_type="private"),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)

    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {"free_used": 0, "balance": 0}
        data[user_id]["ref_code"] = f"ref_{hashlib.sha256(f'{user_id}eurorent2024'.encode()).hexdigest()[:8]}"
        save_data(data)

    if context.args and len(context.args) > 0:
        payload = context.args[0]
        if payload.startswith("analyze_"):
            url = unquote(payload[len("analyze_"):])
            if is_url(url):
                await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=kb(update))
                listing_text = fetch_url_text(url)
                if listing_text.startswith("ERROR"):
                    await update.message.reply_text(
                        "❌ Не удалось загрузить страницу (сайт блокирует парсер).\n\n"
                        "Скопируйте текст объявления и отправьте его сюда.",
                        reply_markup=kb(update)
                    )
                    return
                await process_listing(update, context, listing_text, user_id=user_id, lang=lang)
                return
        elif payload.startswith("ref_"):
            ref_code = payload
            referrer_id = None
            for uid, u in data.items():
                if u.get("ref_code") == ref_code:
                    referrer_id = uid
                    break
            if referrer_id and referrer_id != user_id:
                referrer = data.setdefault(referrer_id, {"free_used": 0, "balance": 0})
                referrals = referrer.setdefault("referrals", [])
                if user_id not in referrals:
                    referrals.append(user_id)
                    reward = {1: 1, 3: 3, 5: 5, 10: -1}.get(len(referrals), 0)
                    if reward == -1:
                        referrer["balance"] = -1
                        referrer["last_paid_at"] = time.time()
                    elif reward > 0:
                        referrer["balance"] = referrer.get("balance", 0) + reward
                    save_data(data)
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 Ваш друг присоединился!\nПриглашено: {len(referrals)} чел."
                        )
                    except Exception:
                        pass

    logo_path = os.path.join(os.path.dirname(__file__), "icons", "start.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)
    await update.message.reply_text(get_msg(lang, "start"), reply_markup=kb(update))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    icon_path = os.path.join(os.path.dirname(__file__), "icons", "help.png")
    if os.path.exists(icon_path):
        with open(icon_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)
    await update.message.reply_text(get_msg(lang, "help"), reply_markup=kb(update))


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
            await update.message.reply_photo(photo=photo)
    await update.message.reply_text(text, reply_markup=kb(update))


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
        await update.message.reply_text("Не удалось создать счёт. У вас достаточно Stars?", reply_markup=kb(update))


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
        await update.message.reply_text("Не удалось создать счёт. У вас достаточно Stars?", reply_markup=kb(update))


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
        await update.message.reply_text("Не удалось создать счёт. У вас достаточно Stars?", reply_markup=kb(update))


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
            await update.message.reply_photo(photo=photo)
    await update.message.reply_text(text, reply_markup=kb(update))


async def pay_stars_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_invoice(
        title="PDF заявление (Mieterprofil)",
        description="Готовое PDF-заявление на аренду для арендодателя.",
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
    await update.message.reply_text(get_msg(lang, "pdf_need_data"), reply_markup=kb(update))


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
            await update.message.reply_photo(photo=photo)
    await update.message.reply_text(text, reply_markup=kb(update))


async def pay_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "vip_intro"), reply_markup=kb(update))


async def pay_done_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["vip"] = True
    user["vip_state"] = "awaiting_criteria"
    save_data(data)
    await update.message.reply_text(get_msg(lang, "vip_ask_criteria"), reply_markup=kb(update))


async def pay_done_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] += 3
    user["last_paid_at"] = time.time()
    save_data(data)
    remaining = user["balance"] + max(0, FREE_LIMIT - user["free_used"])
    await update.message.reply_text(get_msg(lang, "pay_done_3").format(remaining), reply_markup=kb(update))


async def pay_done_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] += 10
    user["last_paid_at"] = time.time()
    save_data(data)
    remaining = user["balance"] + max(0, FREE_LIMIT - user["free_used"])
    await update.message.reply_text(get_msg(lang, "pay_done_9").format(remaining), reply_markup=kb(update))


async def pay_done_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    user["balance"] = -1
    user["last_paid_at"] = time.time()
    save_data(data)
    await update.message.reply_text(get_msg(lang, "pay_done_19"), reply_markup=kb(update))


def parse_pdf_data(text: str) -> dict:
    text = sanitize_pdf_input(text)
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    data = {}
    keys = ["name", "dob", "phone", "email", "address", "employer", "income", "occupants"]
    for i, key in enumerate(keys):
        if i < len(lines):
            line = lines[i]
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
        await update.message.reply_text("Не удалось создать счёт. Проверьте баланс Stars.", reply_markup=kb(update))


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
        await update.message.reply_text("Не удалось создать счёт. Проверьте баланс Stars.", reply_markup=kb(update))


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
        await update.message.reply_text("Не удалось создать счёт. Проверьте баланс Stars.", reply_markup=kb(update))


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
    payload = update.message.successful_payment.invoice_payload

    if payload == "pay_stars_3":
        user["balance"] += 3
        user["last_paid_at"] = time.time()
        save_data(data)
        remaining = user["balance"] + max(0, FREE_LIMIT - user["free_used"])
        await update.message.reply_text(
            f"Оплата подтверждена! Добавлены 3 проверки. Осталось: {remaining}",
            reply_markup=kb(update)
        )
    elif payload == "pay_stars_9":
        user["balance"] += 10
        user["last_paid_at"] = time.time()
        save_data(data)
        remaining = user["balance"] + max(0, FREE_LIMIT - user["free_used"])
        await update.message.reply_text(
            f"Оплата подтверждена! Добавлено 10 проверок. Осталось: {remaining}",
            reply_markup=kb(update)
        )
    elif payload == "pay_stars_19":
        user["balance"] = -1
        user["last_paid_at"] = time.time()
        save_data(data)
        await update.message.reply_text(
            "Оплата подтверждена! Безлимит на месяц активирован!",
            reply_markup=kb(update)
        )
    elif payload == "pay_stars_pdf":
        user["pdf_paid"] = True
        user["pdf_state"] = "awaiting_data"
        save_data(data)
        await update.message.reply_text(
            "Оплата PDF подтверждена! Отправьте данные для заявления.",
            reply_markup=kb(update)
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
                f"Полезные ссылки и подборки по аренде можно найти в закрепленных сообщениях.\n\n"
                f"Как анализировать объявления:\n"
                f"Просто отправьте ссылку или текст объявления сюда в чат.\n"
                f"Я перенаправлю вас в личку с ботом, где он сделает полный разбор за 5 секунд!\n\n"
                f"Или начните сразу: /start"
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
            f"Привет, {first_name}! 👋\n\n"
            f"Я EuroRent AI — бот для анализа объявлений об аренде в Европе.\n\n"
            f"Что я умею:\n"
            f"🔍 Разбираю объявления за 5 секунд\n"
            f"💰 Считаю реальную цену со всеми комиссиями\n"
            f"📄 Подсказываю нужные документы\n"
            f"⚠️ Предупреждаю о мошенниках\n"
            f"🌍 Работаю с 30+ сайтами по всей Европе\n\n"
            f"Как пользоваться:\n"
            f"Просто отправьте ссылку на объявление сюда в чат — "
            f"я перенаправлю вас в личку с ботом для полного разбора!"
        )


async def handle_group_listing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    text = update.message.text or ""

    greeting_pattern = re.compile(
        r'^(?i:привет|здравствуй|hello|hi|добрый день|доброе утро|добрый вечер|ку|хай|hey|hallo|servus|cześć|witaj)\b'
    )
    if greeting_pattern.match(text.strip()):
        return

    bot_username = context.bot.username
    user_id = str(update.effective_user.id)

    is_url = text.strip().startswith(("http://", "https://", "t.me/"))
    is_long_text = len(text.strip()) > 30

    if not is_url and not is_long_text:
        return

    lang = get_lang(update)
    deep_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Проанализировать в боте", url=deep_link)]
    ])

    await update.message.reply_text(
        get_msg(lang, "group_redirect"),
        reply_markup=keyboard,
    )


def get_cities_keyboard():
    cities = sorted(POPULAR_CITIES.items(), key=lambda x: x[1]["avg_price"])
    keyboard = []
    row = []
    for key, info in cities:
        row.append(InlineKeyboardButton(
            f"{info['emoji']} {info['name_en']}",
            callback_data=f"select_city:{key}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Снять фильтр", callback_data="select_city:remove")])
    return InlineKeyboardMarkup(keyboard)


async def cmd_cities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    user_id = str(update.effective_user.id)
    current_city = get_user_city(user_id)
    current_name = ""
    if current_city and current_city in POPULAR_CITIES:
        ci = POPULAR_CITIES[current_city]
        current_name = f"\n\nТекущий город: {ci['emoji']} {ci['name']}" if lang == "ru" else f"\n\nCurrent city: {ci['emoji']} {ci['name_en']}"

    await update.message.reply_text(
        f"🏙 Выберите город для фильтрации объявлений:{current_name}\n\n"
        f"{list_cities()}\n\n"
        "Нажмите на кнопку или используйте /set_city <город>",
        reply_markup=get_cities_keyboard(),
    )


async def handle_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_lang(update)
    user_id = str(update.effective_user.id)
    data_payload = query.data.split(":")[1] if ":" in query.data else ""

    if data_payload == "remove":
        from listing_features import remove_user_city
        remove_user_city(user_id)
        await query.edit_message_text("✅ Фильтр города снят. Показываю все объявления.")
        return

    if data_payload in POPULAR_CITIES:
        set_user_city(user_id, data_payload)
        info = POPULAR_CITIES[data_payload]
        await query.edit_message_text(
            get_msg(lang, "city_selected").format(emoji=info["emoji"], name=info["name"])
        )


async def subscribe_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "📧 Подписка на недельный дайджест\n\n"
            "Отправьте свою почту:\n/subscribe_email your@email.com\n\n"
            "Каждую неделю вы будете получать подборку лучших объявлений!"
        )
        return

    email = context.args[0].strip()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        await update.message.reply_text("❌ Некорректный email. Попробуйте ещё раз.")
        return

    if add_email_subscriber(email, user_id):
        await update.message.reply_text(
            f"✅ Вы подписались на дайджест!\n\n"
            f"Email: {email}\n"
            f"Частота: 1 раз в неделю (понедельник)\n\n"
            f"Отписаться: /unsubscribe_email"
        )
    else:
        await update.message.reply_text("ℹ️ Этот email уже подписан на дайджест.")


async def unsubscribe_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "📧 Отписка от дайджеста\n\n"
            "Отправьте свою почту:\n/unsubscribe_email your@email.com"
        )
        return

    email = context.args[0].strip()
    if remove_email_subscriber(email):
        await update.message.reply_text(f"✅ Вы отписались от дайджеста ({email}).")
    else:
        await update.message.reply_text("ℹ️ Этот email не найден в подписчиках.")


async def subscribers_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    subs = get_active_subscribers()
    await update.message.reply_text(f"📊 Email-подписчиков: {len(subs)}")


async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    args = context.args

    if not args:
        await update.message.reply_text(
            "Укажите ваш часовой пояс, например:\n"
            "/timezone Europe/London\n"
            "/timezone Europe/Riga\n"
            "/timezone Europe/Helsinki\n"
            "/timezone Europe/Berlin\n\n"
            "Список всех зон: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        )
        return

    tz_name = args[0]
    try:
        import pytz
        pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(
            f"❌ Часовой пояс \"{tz_name}\" не найден.\n\n"
            "Примеры:\n"
            "Europe/Berlin\n"
            "Europe/London\n"
            "Europe/Riga\n"
            "Europe/Helsinki\n"
            "America/New_York"
        )
        return

    data = load_data()
    user = get_user_data(data, user_id)
    user["timezone"] = tz_name
    save_data(data)

    await update.message.reply_text(
        f"✅ Часовой пояс сохранён: {tz_name}\n\n"
        "Когда запущу личный дайджест — посты будут приходить в удобное время."
    )

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask started in background")

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logging.info("Scheduler started in background")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    priv = filters.ChatType.PRIVATE

    application.add_handler(CommandHandler("start", start, priv))
    application.add_handler(CommandHandler("help", help_command, priv))
    application.add_handler(CommandHandler("revolut", revolut_command, priv))
    application.add_handler(CommandHandler("pay", pay_command, priv))
    application.add_handler(CommandHandler("pdf", pdf_command, priv))
    application.add_handler(CommandHandler("pay_done_pdf", pay_done_pdf, priv))
    application.add_handler(CommandHandler("vip", vip_command, priv))
    application.add_handler(CommandHandler("pay_vip", pay_vip, priv))
    application.add_handler(CommandHandler("pay_done_vip", pay_done_vip, priv))
    application.add_handler(CommandHandler("pay_done_3", pay_done_3, priv))
    application.add_handler(CommandHandler("pay_done_9", pay_done_9, priv))
    application.add_handler(CommandHandler("pay_done_19", pay_done_19, priv))
    application.add_handler(CommandHandler("pay_stars_3", pay_stars_3, priv))
    application.add_handler(CommandHandler("pay_stars_9", pay_stars_9, priv))
    application.add_handler(CommandHandler("pay_stars_19", pay_stars_19, priv))
    application.add_handler(CommandHandler("pay_stars_pdf", pay_stars_pdf, priv))
    application.add_handler(CommandHandler("pay_3", pay_3, priv))
    application.add_handler(CommandHandler("pay_9", pay_9, priv))
    application.add_handler(CommandHandler("pay_19", pay_19, priv))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(CommandHandler("pin", pin_message, priv))
    application.add_handler(CommandHandler("subscribe_email", subscribe_email, priv))
    application.add_handler(CommandHandler("unsubscribe_email", unsubscribe_email, priv))
    application.add_handler(CommandHandler("subscribers", subscribers_count, priv))
    application.add_handler(CommandHandler("timezone", set_timezone, priv))
    application.add_handler(CommandHandler("set_city", cmd_set_city, priv))
    application.add_handler(CommandHandler("remove_city", cmd_remove_city, priv))
    application.add_handler(CommandHandler("my_city", cmd_my_city, priv))
    application.add_handler(CommandHandler("trend", cmd_trend, priv))
    application.add_handler(CommandHandler("holygrail", cmd_holygrail, priv))
    application.add_handler(CommandHandler("cities", cmd_cities, priv))
    application.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CallbackQueryHandler(handle_city_selection, pattern=r'^select_city:'))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO & priv, handle_photo))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.Regex(r'^(?i:привет|здравствуй|hello|hi|добрый день|доброе утро|добрый вечер|ку|хай)'),
        group_greeting
    ))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, handle_group_listing))

    logging.info("Starting bot polling...")
    application.run_polling(drop_pending_updates=True)
