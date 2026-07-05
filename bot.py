import os
import re
import json
import logging
import threading
import time
import hashlib
import asyncio
import html
from datetime import datetime
from urllib.parse import unquote
from io import BytesIO
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, PreCheckoutQueryHandler, filters, ContextTypes
)
from groq import Groq

from config import TELEGRAM_TOKEN, GROQ_API_KEY, WEBHOOK_URL, AFFILIATE_REVOLUT, AFFILIATE_WISE, FREE_LIMIT, PDF_PRICE, VIP_PRICE
from messages import get_msg
from storage import save_user, get_user
from utils import (
    load_data, save_data, get_lang, get_user_data,
    can_use, use_check, is_url, fetch_url_text, ocr_from_photo,
    calc_remaining, check_rate_limit, sanitize_pdf_input,
    is_pdf_state_expired, validate_pdf_data
)
from user_features import (
    add_favorite, get_favorites, remove_favorite,
    add_tracker_entry, get_tracker_entries, update_tracker_status, remove_tracker_entry, STATUSES,
    get_profile, save_profile, PROFILE_FIELDS,
    get_user_filters, save_user_filters,
)
from letter_generator import generate_letter
from pdf_generator import generate_mieterprofil_pdf
from email_newsletter import add_email_subscriber, remove_email_subscriber, get_active_subscribers
from listing_features import (
    cmd_set_city, cmd_remove_city, cmd_my_city, cmd_trend, cmd_holygrail,
    get_user_city, filter_by_city, detect_city, record_listing, is_holy_grail,
    format_holy_grail_alert, extract_price, record_price, extract_score,
    POPULAR_CITIES, list_cities, set_user_city
)
from scheduler import update_last_activity, run_scheduler, set_bot
from web import app

client = Groq(api_key=GROQ_API_KEY)

_payment_lock = asyncio.Lock()
_flood_tracker = {}  # user_id -> (count, window_start)
MAX_MESSAGES_PER_MINUTE = 10
_last_flood_cleanup = 0
_greeting_cooldown = {}  # user_id -> last_greeting_time
GREETING_COOLDOWN = 3600  # 1 час

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

REFERRAL_LOG = "referral_events.jsonl"


def log_referral_event(event_type: str, user_id: str, extra: dict = None):
    import time as _time
    entry = {"ts": _time.time(), "type": event_type, "user_id": user_id}
    if extra:
        entry.update(extra)
    try:
        with open(REFERRAL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

# Словарь для хранения ссылок из постов (message_id -> url)
_pending_listings = {}
PENDING_FILE = "pending_listings.json"

# Токены для коротких deep links — используют общий модуль из rent_scanner
from rent_scanner.formatting import create_url_token, resolve_url_token


def _load_pending_listings():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_pending_listings(data):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def get_keyboard():
    keyboard = [
        [KeyboardButton("Старт"), KeyboardButton("Помощь"), KeyboardButton("Баланс")],
        [KeyboardButton("PDF"), KeyboardButton("VIP"), KeyboardButton("Мой язык")],
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
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user and update.effective_user.id == ADMIN_ID:
        is_admin = True
    if not is_admin and update.effective_chat.type in ["group", "supergroup"]:
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

        # Сохраняем URL для /favorite
        _last_analyzed_url[user_id] = listing_text[:200] if is_url(listing_text) else listing_text[:200]

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
            # Атомарное обновление пользователя
            user = get_user(user_id)
            if not can_use(user):
                ref_code = user.get("ref_code", "")
                ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
                await update.message.reply_text(
                    get_msg(lang, "limit_reached").format(ref_link),
                    reply_markup=kb(update)
                )
                log_referral_event("limit_ref_shown", user_id)
                return
            use_check(user)
            save_user(user_id, user)

            # Обработка реферала
            if user.get("free_used", 0) == 1 and user.get("referred_by"):
                referrer_id = user["referred_by"]
                referrer = get_user(referrer_id)
                referrals = referrer.setdefault("referrals", [])
                if user_id not in referrals:
                    referrals.append(user_id)
                    reward = {1: 1, 3: 3, 5: 5, 10: -1}.get(len(referrals), 0)
                    if reward == -1:
                        referrer["balance"] = -1
                        referrer["last_paid_at"] = time.time()
                    elif reward > 0:
                        referrer["balance"] = referrer.get("balance", 0) + reward
                    save_user(referrer_id, referrer)
                    try:
                        n = len(referrals)
                        progress = ""
                        if n < 3:
                            progress = f"Ещё {3 - n} друга до +3 проверок!"
                        elif n < 5:
                            progress = f"Ещё {5 - n} друзей до +5 проверок!"
                        elif n < 10:
                            progress = f"Ещё {10 - n} друзей до безлимита!"
                        else:
                            progress = "🎉 Безлимит активирован!"
                        ref_code = referrer.get("ref_code", "")
                        ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 Ваш друг сделал первую проверку!\n"
                                 f"Приглашено: {n} чел.\n\n"
                                 f"📊 {progress}\n\n"
                                 f"Ваша ссылка: {ref_link}"
                        )
                        log_referral_event("referral_confirmed", referrer_id, {"referred": user_id, "total": n})
                    except Exception:
                        pass
                    user.pop("referred_by", None)
                save_data(data)
                if user.get("free_used", 0) == 1:
                    ref_code = user.get("ref_code", "")
                    ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
                    aha_msg = (
                        f"🎉 Это была ваша первая проверка!\n\n"
                        f"Если пригодилось — пригласите друга, который тоже ищет квартиру, "
                        f"и получите +1 проверку бесплатно.\n\n"
                        f"Ваша ссылка: {ref_link}"
                    )
                    await update.message.reply_text(aha_msg, reply_markup=kb(update))
                    log_referral_event("aha_moment_shown", user_id)
                elif user.get("free_used", 0) % 5 == 0 and user.get("free_used", 0) > 0:
                    ref_code = user.get("ref_code", "")
                    ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
                    total_checks = user.get("free_used", 0) + user.get("balance", 0)
                    gentle_msg = (
                        f"📊 Вы уже сделали {total_checks} проверок с ботом!\n\n"
                        f"Если знаете кого-то в похожей ситуации — "
                        f"пригласите и получите +1 проверку бесплатно.\n\n"
                        f"Ваша ссылка: {ref_link}"
                    )
                    await update.message.reply_text(gentle_msg, reply_markup=kb(update))
                    log_referral_event("5check_trigger_shown", user_id, {"total_checks": total_checks})

        remaining = calc_remaining(user)
        # Убираем HTML-теги из ответа AI и экранируем спецсимволы
        clean_result = re.sub(r'<[^>]+>', '', result)
        safe_result = html.escape(clean_result)
        safe_footer = html.escape(get_msg(lang, "affiliate_footer"))
        remaining_text = "∞" if user["balance"] == -1 else html.escape(str(remaining))
        admin_note = html.escape("\n\nАдмин: проверка бесплатная") if is_admin else ""
        safe_balance = html.escape(f"\n\nОсталось проверок: ") + remaining_text
        ref_code = user.get("ref_code", "")
        share_url = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
        safe_share = f"\n\n{html.escape(get_msg(lang, 'share_text'))}\n<a href=\"{share_url}\">Поделиться с другом</a>" if share_url else ""

        # Travel time calculation
        work_address = user.get("work_address", "")
        travel_note = ""
        if work_address and city_key and city_key in POPULAR_CITIES:
            from travel_time import calc_travel_time
            city_name = POPULAR_CITIES[city_key].get("name", city_key)
            travel = calc_travel_time(work_address, city_name)
            if travel:
                travel_note = f"\n\n🚗 <b>До работы:</b> {travel['text']}"

        full_text = safe_result + city_note + travel_note + safe_footer + admin_note + safe_balance + safe_share
        parts = split_message(full_text)
        for i, part in enumerate(parts):
            markup = get_analysis_inline_buttons() if i == len(parts) - 1 else None
            await update.message.reply_text(part, reply_markup=markup, parse_mode="HTML")

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
    global _last_flood_cleanup
    if not update.effective_user:
        return
    user_id = str(update.effective_user.id)
    now = time.time()

    # Очистка старых записей каждые 10 минут
    if now - _last_flood_cleanup > 600:
        _last_flood_cleanup = now
        cutoff = now - 120
        stale = [uid for uid, (_, ws) in _flood_tracker.items() if ws < cutoff]
        for uid in stale:
            del _flood_tracker[uid]

    count, window_start = _flood_tracker.get(user_id, (0, now))
    if now - window_start > 60:
        count = 0
        window_start = now
    count += 1
    _flood_tracker[user_id] = (count, window_start)
    if count > MAX_MESSAGES_PER_MINUTE:
        await update.message.reply_text("⏳ Слишком много сообщений. Подождите минуту.", reply_markup=kb(update))
        return

    text = update.message.text.replace('\xa0', ' ').strip().lower()
    lang = get_lang(update)

    btn_map = {
        "старт": start, "start": start,
        "помощь": help_command, "help": help_command,
        "оплата": pay_command, "pay": pay_command, "оплатить": pay_command,
        "pdf": pdf_command, "пдф": pdf_command,
        "vip": vip_command, "вип": vip_command,
        "баланс": balance_command, "balance": balance_command,
        "мой язык": lang_command, "my lang": lang_command,
    }
    if text in btn_map:
        await btn_map[text](update, context)
        return

    update_last_activity(user_id)
    data = load_data()
    user = get_user_data(data, user_id)

    followup = check_followups(user, lang)
    if followup:
        await update.message.reply_text(followup, reply_markup=kb(update))

    pdf_state = user.get("pdf_state")
    if pdf_state == "awaiting_data" and is_pdf_state_expired(user):
        user.pop("pdf_state", None)
        user.pop("pdf_started_at", None)
        save_data(data)
        pdf_state = None
    if pdf_state == "awaiting_data":
        user.pop("pdf_state", None)
        user.pop("pdf_started_at", None)
        pdf_data = parse_pdf_data(update.message.text)
        if not pdf_data:
            await update.message.reply_text("❌ Не удалось распознать данные. Попробуйте ещё раз.", reply_markup=kb(update))
            return
        valid, error_msg = validate_pdf_data(pdf_data)
        if not valid:
            await update.message.reply_text(f"❌ {error_msg}\n\nПопробуйте ещё раз.", reply_markup=kb(update))
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
            logging.error(f"PDF generation error: {e}")
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

    # Состояние заполнения профиля
    profile_state = user.get("profile_state")
    if profile_state == "awaiting_profile":
        user.pop("profile_state", None)
        save_user(user_id, user)
        lines = [line.strip() for line in update.message.text.strip().split("\n") if line.strip()]
        fields = ["full_name", "profession", "income", "employer", "move_in_date", "occupants", "pets"]
        profile_data = {}
        for i, field in enumerate(fields):
            if i < len(lines):
                profile_data[field] = lines[i].lstrip("0123456789. ")
        if profile_data:
            save_profile(user_id, profile_data)
            await update.message.reply_text(
                "✅ Профиль сохранён!\n\n"
                "Теперь вы можете:\n"
                "• Проанализировать объявление и нажать /favorite\n"
                "• Использовать /generate_letter для письма\n"
                "• Настроить фильтры: /filters",
                reply_markup=kb(update)
            )
        else:
            await update.message.reply_text("❌ Не удалось распознать данные. Попробуйте ещё раз.", reply_markup=kb(update))
        return

    if not can_use(user):
        ref_code = user.get("ref_code", "")
        ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
        await update.message.reply_text(
            get_msg(lang, "limit_reached").format(ref_link),
            reply_markup=kb(update)
        )
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
    try:
        await process_listing(update, context, listing_text, user_id, lang)
    except Exception as e:
        logging.error(f"process_listing error for user {user_id}: {e}")
        try:
            await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=kb(update))
        except Exception:
            pass


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    user_id = str(update.effective_user.id)
    lang = get_lang(update)
    data = load_data()
    user = get_user_data(data, user_id)

    if not can_use(user):
        ref_code = user.get("ref_code", "")
        ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
        await update.message.reply_text(
            get_msg(lang, "limit_reached").format(ref_link),
            reply_markup=kb(update)
        )
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
    try:
        await process_listing(update, context, listing_text, user_id, lang)
    except Exception as e:
        logging.error(f"process_listing (photo) error for user {user_id}: {e}")
        try:
            await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=kb(update))
        except Exception:
            pass


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.effective_user:
            return
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

        # Кнопка "Проанализировать" из группы — открываем бота в личке
        elif data_prefix in ("analyze_ad", "analyze_rss"):
            await query.edit_message_reply_markup(reply_markup=None)

            token_or_short_id = query.data.split(":", 1)[1] if ":" in query.data else ""
            bot_username = context.bot.username

            # Сначала пробуем resolve как token из UrlTokens
            rss_url = resolve_url_token(token_or_short_id)

            # Если не нашли — пробуем как short_id из PendingListings
            if not rss_url:
                try:
                    from daily_poster import get_listing
                    listing = get_listing(token_or_short_id)
                    rss_url = listing.get("url", "")
                except Exception:
                    pass

            if rss_url and is_url(rss_url):
                new_token = create_url_token(rss_url)
                analyze_url = f"https://t.me/{bot_username}?start=an_{new_token}"
            else:
                analyze_url = f"https://t.me/{bot_username}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Открыть бота для анализа", url=analyze_url)]
            ])

            data = load_data()
            user = get_user_data(data, user_id)

            if not can_use(user):
                await query.message.reply_text(
                    "❌ У вас закончились проверки.\n\n"
                    "Пакеты:\n"
                    "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
                    "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
                    "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19",
                    reply_markup=keyboard,
                )
            else:
                await query.message.reply_text(
                    "🔍 Нажмите кнопку ниже, чтобы получить полный разбор объявления в личке!",
                    reply_markup=keyboard,
                )

        # Кнопка "Пропустить"
        elif data_prefix == "skip_ad":
            await query.answer("Ок", show_alert=False)

        # Кнопка "Скопировать"
        elif data_prefix == "copy":
            await query.answer("Скопируйте текст выше", show_alert=True)

        # Кнопка "Язык"
        elif data_prefix.startswith("lang_"):
            new_lang = data_prefix.split("_", 1)[1]
            user_id = str(query.from_user.id)
            data_dict = load_data()
            user = get_user_data(data_dict, user_id)
            user["lang"] = new_lang
            save_data(data_dict)
            lang_names = {"ru": "Русский", "uk": "Українська", "en": "English", "de": "Deutsch", "pl": "Polski"}
            await query.answer(f"Язык изменён: {lang_names.get(new_lang, new_lang)}", show_alert=True)

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

        # Фильтры: переключение
        elif data_prefix == "filter":
            filter_type = query.data.split(":")[1] if ":" in query.data else ""
            if filter_type in ("furnished", "pets", "parking"):
                filters = get_user_filters(user_id)
                field = f"filter_{filter_type}"
                new_val = not filters.get(field, False)
                filters[field] = new_val
                save_user_filters(
                    user_id,
                    furnished=filters.get("filter_furnished", False),
                    pets=filters.get("filter_pets", False),
                    parking=filters.get("filter_parking", False),
                )
                icon = "✅" if new_val else "❌"
                label = {"furnished": "Мебель", "pets": "Питомцы", "parking": "Парковка"}[filter_type]
                await query.answer(f"{label}: {icon}", show_alert=False)
                # Обновляем клавиатуру
                filters = get_user_filters(user_id)
                furnished = "✅" if filters.get("filter_furnished") else "❌"
                pets_f = "✅" if filters.get("filter_pets") else "❌"
                parking = "✅" if filters.get("filter_parking") else "❌"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🪑 Мебель: {furnished}", callback_data="filter:furnished")],
                    [InlineKeyboardButton(f"🐾 Питомцы: {pets_f}", callback_data="filter:pets")],
                    [InlineKeyboardButton(f"🅿️ Парковка: {parking}", callback_data="filter:parking")],
                ])
                await query.edit_message_reply_markup(reply_markup=keyboard)

        # Удаление из избранного
        elif data_prefix == "fav_del":
            fav_id = int(query.data.split(":")[1]) if ":" in query.data else 0
            if fav_id and remove_favorite(user_id, fav_id):
                await query.answer("Удалено из избранного", show_alert=False)
                await query.edit_message_reply_markup(reply_markup=None)
            else:
                await query.answer("Ошибка удаления", show_alert=True)

        # Смена статуса в трекере
        elif data_prefix == "track":
            parts = query.data.split(":")
            if len(parts) == 3:
                entry_id = int(parts[1])
                new_status = parts[2]
                if update_tracker_status(user_id, entry_id, new_status):
                    await query.answer(f"Статус: {STATUSES.get(new_status, new_status)}", show_alert=False)
                else:
                    await query.answer("Ошибка", show_alert=True)

    except Exception as e:
        logger.error(f"handle_callback error: {e}", exc_info=True)
        try:
            await query.answer("Произошла ошибка", show_alert=True)
        except Exception:
            pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    lang = get_lang(update)

    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {
            "free_used": 0,
            "balance": 0,
            "ref_code": f"ref_{hashlib.sha256(f'{user_id}eurorent2024'.encode()).hexdigest()[:8]}",
            "lang": lang,
            "created_at": datetime.now().isoformat(),
            "total_checks": 0,
            "email": "",
        }
        save_data(data)
    elif not data[user_id].get("ref_code"):
        data[user_id]["ref_code"] = f"ref_{hashlib.sha256(f'{user_id}eurorent2024'.encode()).hexdigest()[:8]}"
        save_data(data)

    if context.args and len(context.args) > 0:
        payload = context.args[0][:512]  # Ограничение длины payload
        if payload.startswith("an_"):
            # Новый формат: короткий токен
            token = payload[len("an_"):]
            url = resolve_url_token(token)
            if url and is_url(url):
                await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=kb(update))
                listing_text = fetch_url_text(url)
                if listing_text.startswith("ERROR"):
                    await update.message.reply_text(
                        "❌ Не удалось загрузить страницу (сайт блокирует парсер).\n\n"
                        "Скопируйте текст объявления и отправьте его сюда.",
                        reply_markup=kb(update)
                    )
                    return
                try:
                    await process_listing(update, context, listing_text, user_id=user_id, lang=lang)
                except Exception as e:
                    logging.error(f"process_listing (start token) error for user {user_id}: {e}")
                    try:
                        await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=kb(update))
                    except Exception:
                        pass
                return
            else:
                await update.message.reply_text("❌ Ссылка устарела. Отправьте объявление напрямую.", reply_markup=kb(update))
                return
        elif payload.startswith("analyze_"):
            # Старый формат: полный URL (для обратной совместимости)
            try:
                url = unquote(payload[len("analyze_"):])
            except Exception:
                url = ""
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
                try:
                    await process_listing(update, context, listing_text, user_id=user_id, lang=lang)
                except Exception as e:
                    logging.error(f"process_listing (start) error for user {user_id}: {e}")
                    try:
                        await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=kb(update))
                    except Exception:
                        pass
                return
        elif payload.startswith("ref_"):
            ref_code = payload
            referrer_id = None
            for uid, u in data.items():
                if u.get("ref_code") == ref_code:
                    referrer_id = uid
                    break
            if referrer_id and referrer_id != user_id:
                user = get_user_data(data, user_id)
                user["referred_by"] = referrer_id
                save_data(data)
                log_referral_event("ref_link_clicked", user_id, {"referrer": referrer_id})

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


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)
    lang = get_lang(update)

    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    is_admin = update.effective_user.id == ADMIN_ID

    if not is_admin and not user.get("vip") and not user.get("pdf_paid") and user.get("balance", 0) <= 0:
        await update.message.reply_text(
            "У вас пока нет активных услуг.\n\n"
            "Начните с бесплатных проверок: просто отправьте ссылку на объявление!",
            reply_markup=kb(update)
        )
        return

    if user.get("balance") == -1:
        remaining = "∞ (безлимит)"
    else:
        remaining = calc_remaining(user)

    vip_status = "✅ Активен" if user.get("vip") else "❌ Не активен"
    pdf_status = "✅ Оплачен" if user.get("pdf_paid") else "❌ Не оплачен"
    referrals = len(user.get("referrals", []))

    text = (
        f"📊 <b>Ваш баланс</b>\n\n"
        f"🔍 Проверок: <b>{remaining}</b>\n"
        f"💎 VIP: {vip_status}\n"
        f"📄 PDF: {pdf_status}\n"
        f"👥 Приглашено: {referrals} чел.\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def ref_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    user = get_user_data(data, user_id)

    ref_code = user.get("ref_code")
    if not ref_code:
        ref_code = f"ref_{hashlib.sha256(f'{user_id}eurorent2024'.encode()).hexdigest()[:8]}"
        user["ref_code"] = ref_code
        save_data(data)

    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start={ref_code}"
    referrals = len(user.get("referrals", []))

    text = (
        f"👥 <b>Реферальная программа</b>\n\n"
        f"Ваша ссылка:\n<code>{ref_link}</code>\n\n"
        f"Приглашено: {referrals} чел.\n\n"
        f"🎁 Награды:\n"
        f"  1 друг → 1 проверка\n"
        f"  3 друга → 3 проверки\n"
        f"  5 друзей → 5 проверок\n"
        f"  10 друзей → безлимит на месяц\n\n"
        f"Отправьте ссылку друзьям — они тоже получат бота!"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk"),
        ],
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
        ],
        [
            InlineKeyboardButton("🇵🇱 Polski", callback_data="lang_pl"),
        ],
    ])
    await update.message.reply_text("Выберите язык / Choose language:", reply_markup=keyboard)


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
        prices=[LabeledPrice(label="PDF заявление", amount=PDF_PRICE * 100)],
        need_name=False,
        need_phone_number=False,
        need_email=False,
    )


async def pay_done_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = str(update.effective_user.id)
    async with _payment_lock:
        data = load_data()
        user = get_user_data(data, user_id)
        lang = get_lang(update)

        user["pdf_paid"] = True
        user["pdf_state"] = "awaiting_data"
        user["pdf_started_at"] = time.time()
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


async def pay_stars_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_invoice(
            title="VIP-подписка",
            description="Безлимитные проверки + приоритетная обработка на 1 месяц.",
            payload="pay_stars_vip",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="VIP/мес", amount=VIP_PRICE * 100)],
            need_name=False,
        )
    except Exception:
        await update.message.reply_text("Не удалось создать счёт. Проверьте баланс Stars.", reply_markup=kb(update))


async def pay_done_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = str(update.effective_user.id)
    async with _payment_lock:
        data = load_data()
        user = get_user_data(data, user_id)
        lang = get_lang(update)

        user["vip"] = True
        user["vip_state"] = "awaiting_criteria"
        save_data(data)
    await update.message.reply_text(get_msg(lang, "vip_ask_criteria"), reply_markup=kb(update))


async def pay_done_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = str(update.effective_user.id)
    async with _payment_lock:
        data = load_data()
        user = get_user_data(data, user_id)
        lang = get_lang(update)
        user["balance"] = user.get("balance", 0) + 3
        user["last_paid_at"] = time.time()
        save_data(data)
        remaining = user["balance"] + max(0, FREE_LIMIT - user.get("free_used", 0))
    await update.message.reply_text(get_msg(lang, "pay_done_3").format(remaining), reply_markup=kb(update))


async def pay_done_9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = str(update.effective_user.id)
    async with _payment_lock:
        data = load_data()
        user = get_user_data(data, user_id)
        lang = get_lang(update)
        user["balance"] = user.get("balance", 0) + 10
        user["last_paid_at"] = time.time()
        save_data(data)
        remaining = user["balance"] + max(0, FREE_LIMIT - user.get("free_used", 0))
    await update.message.reply_text(get_msg(lang, "pay_done_9").format(remaining), reply_markup=kb(update))


async def pay_done_19(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = str(update.effective_user.id)
    async with _payment_lock:
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
    payload = update.message.successful_payment.invoice_payload

    # Атомарное обновление пользователя
    user = get_user(user_id)

    if payload == "pay_stars_3":
        user["balance"] = user.get("balance", 0) + 3
        user["last_paid_at"] = time.time()
        save_user(user_id, user)
        remaining = user["balance"] + max(0, FREE_LIMIT - user.get("free_used", 0))
        await update.message.reply_text(
            f"Оплата подтверждена! Добавлены 3 проверки. Осталось: {remaining}",
            reply_markup=kb(update)
        )
    elif payload == "pay_stars_9":
        user["balance"] = user.get("balance", 0) + 10
        user["last_paid_at"] = time.time()
        save_user(user_id, user)
        remaining = user["balance"] + max(0, FREE_LIMIT - user.get("free_used", 0))
        await update.message.reply_text(
            f"Оплата подтверждена! Добавлено 10 проверок. Осталось: {remaining}",
            reply_markup=kb(update)
        )
    elif payload == "pay_stars_19":
        user["balance"] = -1
        user["last_paid_at"] = time.time()
        save_user(user_id, user)
        await update.message.reply_text(
            "Оплата подтверждена! Безлимит на месяц активирован!",
            reply_markup=kb(update)
        )
    elif payload == "pay_stars_pdf":
        user["pdf_paid"] = True
        user["pdf_state"] = "awaiting_data"
        user["pdf_started_at"] = time.time()
        save_user(user_id, user)
        await update.message.reply_text(
            "Оплата PDF подтверждена! Отправьте данные для заявления.",
            reply_markup=kb(update)
        )
    elif payload == "pay_stars_vip":
        user["vip"] = True
        user["vip_state"] = "awaiting_criteria"
        user["last_paid_at"] = time.time()
        save_user(user_id, user)
        await update.message.reply_text(
            "Оплата VIP подтверждена! Отправьте критерии поиска (город, бюджет, район).",
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
        if new_member.user.id == context.bot.id:
            return
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
        except Exception as e:
            logger.debug(f"Failed to pin welcome message: {e}")


async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.pin()
            await update.message.reply_text("Сообщение закреплено!")
        except Exception:
            await update.message.reply_text("Не удалось закрепить. Проверьте права бота в чате.")
    else:
        await update.message.reply_text("Чтобы закрепить пост, ответьте на него и напишите /pin")


async def group_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_username = context.bot.username
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Открыть бота в личке", url=f"https://t.me/{bot_username}")]
    ])
    await update.message.reply_text(
        "👋 Нажмите кнопку ниже, чтобы начать работу со мной в личке!",
        reply_markup=keyboard,
    )


async def group_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_username = context.bot.username
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Открыть помощь в личке", url=f"https://t.me/{bot_username}?start=help")]
    ])
    await update.message.reply_text(
        "📖 Нажмите кнопку ниже, чтобы получить справку в личке!",
        reply_markup=keyboard,
    )


async def group_greeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type in ["group", "supergroup"]:
        user_id = str(update.effective_user.id) if update.effective_user else None
        now = time.time()

        # Cooldown: не чаще 1 раза в час на пользователя
        if user_id and _greeting_cooldown.get(user_id, 0) > now - GREETING_COOLDOWN:
            return
        if user_id:
            _greeting_cooldown[user_id] = now

        first_name = update.effective_user.first_name if update.effective_user else "друг"
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

    # Проверка: только админ/создатель группы может использовать анализ
    is_group_admin = False
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, update.effective_user.id
        )
        if member.status in ["administrator", "creator"]:
            is_group_admin = True
    except Exception:
        pass

    if not is_group_admin:
        return

    bot_username = context.bot.username

    is_url = text.strip().startswith(("http://", "https://", "t.me/"))
    is_long_text = len(text.strip()) > 30

    if not is_url and not is_long_text:
        return

    lang = get_lang(update)

    if is_url:
        listing_url = text.strip().split()[0]
        token = create_url_token(listing_url)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Проверить скрытые платежи", callback_data=f"analyze_ad:{token}")]
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Открыть бота в личке", url=f"https://t.me/{bot_username}")]
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


async def metrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        from rent_scanner.storage import Storage
        from rent_scanner.config import RuntimeConfig
        config = RuntimeConfig.from_env()
        storage = Storage(config.database_path)
        stats = storage.full_stats()

        top = list(stats["by_source"].items())[:5]
        top_text = "\n".join(f"  {src}: {cnt}" for src, cnt in top) if top else "  нет данных"
        days = "\n".join(f"  {d}: {c}" for d, c in stats["by_day"].items()) if stats["by_day"] else "  нет данных"
        today = stats["today"]

        text = (
            f"📊 <b>Метрики сканера</b>\n\n"
            f"👥 Подписчиков: {stats['subscribers']}\n"
            f"📋 Всего: {stats['total_leads']}\n"
            f"📤 Доставлено: {stats['total_notified']}\n\n"
            f"📅 <b>Сегодня:</b>\n"
            f"  Найдено: {today['found']}\n"
            f"  Доставлено: {today['delivered']}\n"
            f"  Ошибок: {today['errors']}\n"
            f"  Пропущено: {today['skipped']}\n\n"
            f"🏆 <b>Топ каналов:</b>\n{top_text}\n\n"
            f"📈 <b>7 дней:</b>\n{days}"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def ref_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        import time as _time
        from collections import Counter
        events = []
        if os.path.exists(REFERRAL_LOG):
            with open(REFERRAL_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))

        now = _time.time()
        day_ago = now - 86400
        week_ago = now - 604800

        total = len(events)
        today = sum(1 for e in events if e["ts"] > day_ago)
        week = sum(1 for e in events if e["ts"] > week_ago)

        types = Counter(e["type"] for e in events)
        types_today = Counter(e["type"] for e in events if e["ts"] > day_ago)

        confirmed = types.get("referral_confirmed", 0)
        clicked = types.get("ref_link_clicked", 0)
        limit_shown = types.get("limit_ref_shown", 0)
        aha_shown = types.get("aha_moment_shown", 0)
        trigger5 = types.get("5check_trigger_shown", 0)

        conv = f"{confirmed}/{clicked}" if clicked else "0/0"
        rate = f"{confirmed/clicked*100:.0f}%" if clicked else "0%"

        text = (
            f"📊 <b>Статистика рефералов</b>\n\n"
            f"📅 <b>Сегодня:</b> {today} событий\n"
            f"📈 <b>7 дней:</b> {week} событий\n"
            f"📋 <b>Всего:</b> {total} событий\n\n"
            f"🔗 Ссылка показана (limit): {limit_shown}\n"
            f"🎉 Aha-moment показан: {aha_shown}\n"
            f"📊 Триггер 5 проверок: {trigger5}\n"
            f"👆 Ссылка кликнута: {clicked}\n"
            f"✅ Реферал подтверждён: {confirmed}\n\n"
            f"💰 <b>Конверсия:</b> {conv} ({rate})"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🔄 Запускаю отправку дайджеста в группу...")
    try:
        from scheduler import send_group_digest
        await send_group_digest()
        await update.message.reply_text("✅ Дайджест отправлен!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


# ═══════════════════════════════════════════════════════════════
# НОВЫЕ ФИЧИ: Избранное, Трекер, Профиль, Фильтры, Письмо
# ═══════════════════════════════════════════════════════════════

# Временное хранилище последнего проанализированного URL для текущего пользователя
_last_analyzed_url = {}


async def favorite_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохраняет последнее проанализированное объявление в избранное."""
    user_id = str(update.effective_user.id)
    last_url = _last_analyzed_url.get(user_id, "")

    if not last_url:
        await update.message.reply_text(
            "⭐ Сначала проанализируйте объявление, а потом нажмите /favorite.",
            reply_markup=kb(update)
        )
        return

    ok = add_favorite(user_id, last_url, title="Из анализа")
    if ok:
        await update.message.reply_text(
            f"⭐ Объявление добавлено в избранное!\n\nПосмотреть: /favorites",
            reply_markup=kb(update)
        )
    else:
        await update.message.reply_text("❌ Ошибка сохранения. Попробуйте позже.", reply_markup=kb(update))


async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список избранных объявлений."""
    user_id = str(update.effective_user.id)
    favs = get_favorites(user_id)

    if not favs:
        await update.message.reply_text(
            "⭐ У вас пока нет избранных объявлений.\n\n"
            "Проанализируйте объявление и нажмите /favorite, чтобы сохранить.",
            reply_markup=kb(update)
        )
        return

    text = f"⭐ <b>Избранное</b> ({len(favs)}):\n\n"
    buttons = []
    for f in favs[:10]:
        title = f.get("listing_title", "") or f.get("listing_url", "")[:50]
        price = f.get("price", "")
        price_str = f" — {price}" if price else ""
        text += f"• {title}{price_str}\n"
        if f.get("listing_url"):
            text += f"  🔗 {f['listing_url'][:60]}\n"
        buttons.append([InlineKeyboardButton(
            f"❌ {title[:30]}", callback_data=f"fav_del:{f['id']}"
        )])

    kb_fav = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(text, reply_markup=kb_fav, parse_mode="HTML")


# ── Трекер заявок ──────────────────────────────────────────────

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавляет объявление в трекер заявок."""
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            "📋 Использование: /track ссылка\n\n"
            "Пример: /track https://www.immobilienscout24.de/expose/12345",
            reply_markup=kb(update)
        )
        return

    url = context.args[0]
    if not is_url(url):
        await update.message.reply_text("❌ Это не ссылка. Отправьте URL объявления.", reply_markup=kb(update))
        return

    entry_id = add_tracker_entry(user_id, url, title=url[:80])
    if entry_id:
        await update.message.reply_text(
            f"📋 Заявка #{entry_id} добавлена в трекер!\n\n"
            f"Статус: 💾 Сохранено\n"
            f"Ссылка: {url[:80]}\n\n"
            f"Изменить статус: /track_status {entry_id} applied",
            reply_markup=kb(update)
        )
    else:
        await update.message.reply_text("❌ Ошибка сохранения.", reply_markup=kb(update))


async def mytracks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает все заявки в трекере."""
    user_id = str(update.effective_user.id)
    entries = get_tracker_entries(user_id)

    if not entries:
        await update.message.reply_text(
            "📋 У вас пока нет заявок.\n\n"
            "Добавьте: /track ссылка",
            reply_markup=kb(update)
        )
        return

    text = f"📋 <b>Мои заявки</b> ({len(entries)}):\n\n"
    buttons = []
    for e in entries[:10]:
        status = STATUSES.get(e.get("status", "saved"), "💾 Сохранено")
        title = e.get("listing_title", "")[:40]
        entry_id = e.get("id", 0)
        text += f"#{entry_id} {status} — {title}\n"

        row = []
        for s in ["applied", "viewed", "interview", "accepted", "rejected"]:
            row.append(InlineKeyboardButton(
                STATUSES[s][:3], callback_data=f"track:{entry_id}:{s}"
            ))
        buttons.append(row)

    kb_track = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(text, reply_markup=kb_track, parse_mode="HTML")


async def track_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /track_status id status."""
    user_id = str(update.effective_user.id)

    if len(context.args) < 2:
        await update.message.reply_text(
            "📋 Использование: /track_status ID статус\n\n"
            f"Статусы: {', '.join(STATUSES.keys())}",
            reply_markup=kb(update)
        )
        return

    try:
        entry_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом.", reply_markup=kb(update))
        return

    status = context.args[1]
    if update_tracker_status(user_id, entry_id, status):
        await update.message.reply_text(
            f"✅ Заявка #{entry_id} обновлена: {STATUSES.get(status, status)}",
            reply_markup=kb(update)
        )
    else:
        await update.message.reply_text("❌ Ошибка. Проверьте ID и статус.", reply_markup=kb(update))


# ── Профиль (для писем) ────────────────────────────────────────

async def set_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Устанавливает профиль пользователя для генерации писем."""
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)

    current = "\n".join(f"  {field}: {profile.get(field, '')}" for field in PROFILE_FIELDS if profile.get(field))
    current_str = f"\n\nТекущий профиль:\n{current}" if current else ""

    await update.message.reply_text(
        f"📝 <b>Ваш профиль</b>{current_str}\n\n"
        f"Отправьте данные построчно (каждое поле с новой строки):\n"
        f"1. Имя Фамилия\n"
        f"2. Профессия\n"
        f"3. Доход\n"
        f"4. Работодатель\n"
        f"5. Дата переезда\n"
        f"6. Количество жильцов\n"
        f"7. Питомцы\n\n"
        f"Или нажмите /skip_profile",
        reply_markup=kb(update),
        parse_mode="HTML"
    )
    user = get_user(user_id)
    user["profile_state"] = "awaiting_profile"
    save_user(user_id, user)


async def skip_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмена заполнения профиля."""
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    user.pop("profile_state", None)
    save_user(user_id, user)
    await update.message.reply_text("❌ Заполнение профиля отменено.", reply_markup=kb(update))


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущий профиль."""
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)

    fields_ru = {
        "full_name": "Имя",
        "profession": "Профессия",
        "income": "Доход",
        "employer": "Работодатель",
        "move_in_date": "Дата переезда",
        "occupants": "Жильцы",
        "pets": "Питомцы",
    }

    text = "📝 <b>Ваш профиль</b>:\n\n"
    for field, label in fields_ru.items():
        value = profile.get(field, "")
        text += f"  {label}: {value or '—'}\n"

    text += "\nИзменить: /set_profile"
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb(update))


# ── Фильтры ────────────────────────────────────────────────────

async def filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает и переключает фильтры."""
    user_id = str(update.effective_user.id)
    filters = get_user_filters(user_id)

    furnished = "✅" if filters.get("filter_furnished") else "❌"
    pets = "✅" if filters.get("filter_pets") else "❌"
    parking = "✅" if filters.get("filter_parking") else "❌"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🪑 Мебель: {furnished}", callback_data="filter:furnished")],
        [InlineKeyboardButton(f"🐾 Питомцы: {pets}", callback_data="filter:pets")],
        [InlineKeyboardButton(f"🅿️ Парковка: {parking}", callback_data="filter:parking")],
    ])

    await update.message.reply_text(
        "🔧 <b>Фильтры объявлений</b>\n\n"
        "Нажмите для переключения. При анализе бот будет отмечать, "
        "соответствует ли объявление вашим фильтрам.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ── Рабочий адрес (для travel time) ────────────────────────────

async def set_work_address_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Устанавливает адрес работы/университета."""
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            "📍 Использование: /set_work_address адрес\n\n"
            "Пример: /set_work_address Friedrichstraße 100, Berlin\n\n"
            "Удалить: /set_work_address clear",
            reply_markup=kb(update)
        )
        return

    address = " ".join(context.args)
    if address.lower() == "clear":
        user = get_user(user_id)
        user["work_address"] = ""
        save_user(user_id, user)
        await update.message.reply_text("📍 Адрес работы удалён.", reply_markup=kb(update))
        return

    user = get_user(user_id)
    user["work_address"] = address
    save_user(user_id, user)
    await update.message.reply_text(
        f"📍 Адрес работы сохранён: {address}\n\n"
        f"При анализе объявлений бот покажет время в пути.",
        reply_markup=kb(update)
    )


# ── Генерация письма ───────────────────────────────────────────

async def generate_letter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерирует мотивационное письмо арендодателю."""
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)

    # Проверяем заполненность профиля
    filled = sum(1 for f in ["full_name", "profession", "income", "employer"] if profile.get(f))
    if filled < 2:
        await update.message.reply_text(
            "📝 Для генерации письма заполните профиль.\n\n"
            "Используйте: /set_profile",
            reply_markup=kb(update)
        )
        return

    last_url = _last_analyzed_url.get(user_id, "")
    if not last_url:
        await update.message.reply_text(
            "📝 Сначала проанализируйте объявление, а потом нажмите /generate_letter.",
            reply_markup=kb(update)
        )
        return

    await update.message.reply_text("📝 Генерирую письмо...", reply_markup=kb(update))

    lang = get_lang(update)
    letter_lang = "de" if lang in ("ru", "de") else "en"
    letter = generate_letter(profile, last_url, lang=letter_lang)

    if letter:
        await update.message.reply_text(
            f"📝 <b>Мотивационное письмо:</b>\n\n{letter}",
            reply_markup=kb(update),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось сгенерировать письмо. Попробуйте позже.",
            reply_markup=kb(update)
        )


# ── Подписки на алерты ─────────────────────────────────────────

async def subscribe_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подписка на алерты: /subscribe_alert [город] [макс.цена]"""
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            "🔔 <b>Подписка на алерты</b>\n\n"
            "Использование:\n"
            "/subscribe_alert berlin 1500\n"
            "/subscribe_alert amsterdam\n\n"
            "Без цены — все объявления в городе.\n"
            "С ценой — только до указанной суммы.\n\n"
            "Отписка: /unsubscribe_alert",
            reply_markup=kb(update),
            parse_mode="HTML"
        )
        return

    city = context.args[0].lower()
    max_price = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 0

    sb = _get_sb()
    if sb:
        try:
            sb.table("AlertSubscriptions").insert({
                "user_id": user_id,
                "city": city,
                "max_price": max_price,
                "active": True,
            }).execute()
            price_str = f" до {max_price} EUR" if max_price else ""
            await update.message.reply_text(
                f"✅ Подписка на алерты создана!\n\n"
                f"🏙 Город: {city}\n"
                f"💰 Макс. цена: {price_str or 'любая'}\n\n"
                f"Вы будете получать уведомления о новых объявлениях.",
                reply_markup=kb(update)
            )
        except Exception as e:
            logger.error("subscribe_alert error: %s", e)
            await update.message.reply_text("❌ Ошибка подписки.", reply_markup=kb(update))
    else:
        await update.message.reply_text("❌ Сервис алертов недоступен.", reply_markup=kb(update))


async def unsubscribe_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отписка от алертов."""
    user_id = str(update.effective_user.id)

    sb = _get_sb()
    if sb:
        try:
            sb.table("AlertSubscriptions").update({"active": False}).eq("user_id", user_id).execute()
            await update.message.reply_text("✅ Вы отписаны от алертов.", reply_markup=kb(update))
        except Exception as e:
            logger.error("unsubscribe_alert error: %s", e)
            await update.message.reply_text("❌ Ошибка.", reply_markup=kb(update))


async def my_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает активные подписки на алерты."""
    user_id = str(update.effective_user.id)

    sb = _get_sb()
    if sb:
        try:
            result = sb.table("AlertSubscriptions").select("*").eq("user_id", user_id).eq("active", True).execute()
            subs = result.data or []

            if not subs:
                await update.message.reply_text(
                    "🔔 У вас нет активных подписок.\n\n"
                    "Создайте: /subscribe_alert город",
                    reply_markup=kb(update)
                )
                return

            text = "🔔 <b>Ваши подписки:</b>\n\n"
            for s in subs:
                city = s.get("city", "?")
                price = s.get("max_price", 0)
                price_str = f"до {price:.0f} EUR" if price else "все"
                text += f"• {city} — {price_str}\n"

            await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb(update))
        except Exception as e:
            logger.error("my_alerts error: %s", e)
            await update.message.reply_text("❌ Ошибка.", reply_markup=kb(update))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        return

    data = load_data()
    total_users = len(data)
    total_free = sum(u.get("free_used", 0) for u in data.values())
    total_balance = sum(max(0, u.get("balance", 0)) for u in data.values())
    total_paid = sum(1 for u in data.values() if u.get("last_paid_at", 0) > 0)
    total_vip = sum(1 for u in data.values() if u.get("vip"))
    total_pdf = sum(1 for u in data.values() if u.get("pdf_paid"))
    total_checks = sum(u.get("total_checks", 0) for u in data.values())
    unlimited = sum(1 for u in data.values() if u.get("balance") == -1)

    top_users = sorted(
        [(uid, u.get("total_checks", 0), u.get("free_used", 0), u.get("balance", 0))
         for uid, u in data.items()],
        key=lambda x: x[1], reverse=True
    )[:10]

    top_text = ""
    for uid, checks, free, bal in top_users:
        if checks > 0:
            status = "∞" if bal == -1 else f"{bal}"
            top_text += f"  {uid}: {checks} проверок (баланс: {status})\n"

    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"🔍 Всего проверок: <b>{total_checks}</b>\n"
        f"🆓 Потрачено бесплатных: <b>{total_free}</b>\n"
        f"💰 Остаток балансов: <b>{total_balance}</b>\n"
        f"♾️ Безлимитных: <b>{unlimited}</b>\n\n"
        f"💳 Оплачивали: <b>{total_paid}</b>\n"
        f"💎 VIP: <b>{total_vip}</b>\n"
        f"📄 PDF: <b>{total_pdf}</b>\n\n"
        f"🏆 <b>Топ пользователей:</b>\n{top_text if top_text else '  Нет данных'}"
    )
    await update.message.reply_text(text, parse_mode="HTML")


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
    # 1. Создаём приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 2. Регистрируем все команды
    priv = filters.ChatType.PRIVATE

    application.add_handler(CommandHandler("start", start, priv))
    application.add_handler(CommandHandler("help", help_command, priv))
    application.add_handler(CommandHandler("revolut", revolut_command, priv))
    application.add_handler(CommandHandler("balance", balance_command, priv))
    application.add_handler(CommandHandler("ref", ref_command, priv))
    application.add_handler(CommandHandler("lang", lang_command, priv))
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
    application.add_handler(CommandHandler("pay_stars_vip", pay_stars_vip, priv))
    application.add_handler(CommandHandler("pay_3", pay_3, priv))
    application.add_handler(CommandHandler("pay_9", pay_9, priv))
    application.add_handler(CommandHandler("pay_19", pay_19, priv))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(CommandHandler("pin", pin_message, priv))
    application.add_handler(CommandHandler("subscribe_email", subscribe_email, priv))
    application.add_handler(CommandHandler("unsubscribe_email", unsubscribe_email, priv))
    application.add_handler(CommandHandler("subscribers", subscribers_count, priv))
    application.add_handler(CommandHandler("metrics", metrics_command, priv))
    application.add_handler(CommandHandler("ref_stats", ref_stats_command, priv))
    application.add_handler(CommandHandler("post_now", post_now, priv))
    application.add_handler(CommandHandler("stats", stats_command, priv))

    # Phase 1: Новые фичи
    application.add_handler(CommandHandler("favorite", favorite_command, priv))
    application.add_handler(CommandHandler("favorites", favorites_command, priv))
    application.add_handler(CommandHandler("track", track_command, priv))
    application.add_handler(CommandHandler("mytracks", mytracks_command, priv))
    application.add_handler(CommandHandler("track_status", track_status_command, priv))
    application.add_handler(CommandHandler("set_profile", set_profile_command, priv))
    application.add_handler(CommandHandler("skip_profile", skip_profile_command, priv))
    application.add_handler(CommandHandler("profile", profile_command, priv))
    application.add_handler(CommandHandler("filters", filters_command, priv))
    application.add_handler(CommandHandler("set_work_address", set_work_address_command, priv))
    application.add_handler(CommandHandler("generate_letter", generate_letter_command, priv))
    application.add_handler(CommandHandler("subscribe_alert", subscribe_alert_command, priv))
    application.add_handler(CommandHandler("unsubscribe_alert", unsubscribe_alert_command, priv))
    application.add_handler(CommandHandler("my_alerts", my_alerts_command, priv))
    application.add_handler(CommandHandler("timezone", set_timezone, priv))
    application.add_handler(CommandHandler("set_city", cmd_set_city, priv))
    application.add_handler(CommandHandler("remove_city", cmd_remove_city, priv))
    application.add_handler(CommandHandler("my_city", cmd_my_city, priv))
    application.add_handler(CommandHandler("trend", cmd_trend, priv))
    application.add_handler(CommandHandler("holygrail", cmd_holygrail, priv))
    application.add_handler(CommandHandler("cities", cmd_cities, priv))
    groups = filters.ChatType.GROUPS
    application.add_handler(CommandHandler("start", group_start, groups))
    application.add_handler(CommandHandler("help", group_help, groups))
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

    # 3. Запускаем Flask и планировщик в фоновых потоках (до polling)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask started in background")

    # Передаём bot в scheduler ДО запуска polling
    from scheduler import set_bot
    set_bot(application.bot)

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logging.info("Scheduler started in background")

    # 4. Запускаем бота (в основном потоке)
    logging.info("Starting bot polling...")
    application.run_polling(drop_pending_updates=True)
