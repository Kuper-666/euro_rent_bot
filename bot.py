import dns_fix  # noqa: F401 — патч DNS для Windows
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
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, PreCheckoutQueryHandler, filters, ContextTypes
)
from groq import Groq

from config import TELEGRAM_TOKEN, GROQ_API_KEY, AFFILIATE_REVOLUT, AFFILIATE_WISE, FREE_LIMIT, PDF_PRICE, VIP_PRICE
from messages import get_msg
from storage import save_user, get_user
from user_features import save_profile, get_profile
from user_features import (
    get_user_filters, save_user_filters,
    remove_favorite, update_tracker_status, STATUSES,
)
from utils import (
    load_data, save_data, get_lang, get_user_data,
    can_use, use_check, is_url, fetch_url_text, fetch_url_text_async, ocr_from_photo,
    calc_remaining, check_rate_limit, sanitize_pdf_input,
    is_pdf_state_expired, validate_pdf_data, expire_unlimited_if_needed
)
from pdf_generator import generate_mieterprofil_pdf
from letter_generator import generate_letter
from email_newsletter import add_email_subscriber, remove_email_subscriber, get_active_subscribers
from services.keyboards import kb, get_keyboard, get_analysis_inline_buttons, split_message
from handlers.user_features import (
    favorite_command, favorites_command,
    track_command, mytracks_command, track_status_command,
    set_profile_command, skip_profile_command, profile_command,
    filters_command, set_work_address_command, generate_letter_command, reply_command,
    subscribe_alert_command, unsubscribe_alert_command, my_alerts_command,
    handle_profile_state, track_last_url, get_last_url,
)
from handlers.payments import (
    pay_stars_3, pay_stars_9, pay_stars_19, pay_stars_pdf, pay_stars_vip,
    precheckout_callback, successful_payment,
    pay_3, pay_9, pay_19, pay_done_3, pay_done_9, pay_done_19,
    pay_done_pdf, pay_done_vip, pay_command, pdf_command, vip_command,
)
from handlers.admin import (
    stats_command, ref_stats_command, metrics_command,
    subscribers_count, post_now, set_timezone,
)
from handlers.groups import (
    welcome_new_member, pin_message,
    group_start, group_help, group_greeting, group_rules,
    handle_group_listing, _greeting_cooldown,
)
from handlers.cities import get_cities_keyboard, cmd_cities, handle_city_selection
from handlers.email import subscribe_email, unsubscribe_email
from listing_features import (
    cmd_set_city, cmd_remove_city, cmd_my_city, cmd_trend, cmd_holygrail,
    get_user_city, filter_by_city, detect_city, record_listing, is_holy_grail,
    format_holy_grail_alert, extract_price, record_price, extract_score,
    POPULAR_CITIES, list_cities, set_user_city
)
from scheduler import update_last_activity, run_scheduler, set_bot, set_application, store_event_loop
from web import app

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

_flood_tracker = {}  # user_id -> (count, window_start)
MAX_MESSAGES_PER_MINUTE = 10
_last_flood_cleanup = 0
GREETING_COOLDOWN = 3600  # 1 час

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

REFERRAL_LOG = "referral_events.jsonl"
REFERRAL_TABLE = "ReferralEvents"


def log_referral_event(event_type: str, user_id: str, extra: dict = None):
    """Логирует реферальное событие в Supabase или JSONL."""
    ts = time.time()
    entry = {"ts": ts, "type": event_type, "user_id": user_id}
    if extra:
        entry.update(extra)

    # Пробуем Supabase
    try:
        from services.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            sb.table(REFERRAL_TABLE).insert({
                "event_type": event_type,
                "user_id": user_id,
                "extra": json.dumps(extra or {}),
                "created_at": datetime.now().isoformat(),
            }).execute()
            return
    except Exception:
        pass

    # Fallback: локальный JSONL
    try:
        with open(REFERRAL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

# Токены для коротких deep links — используют общий модуль из rent_scanner
from rent_scanner.formatting import create_url_token, resolve_url_token


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
        track_last_url(user_id, listing_text[:200])

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
            expire_unlimited_if_needed(user)
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
        # Очистка greeting cooldown старше 2 часов
        greeting_cutoff = now - 7200
        stale_greetings = [uid for uid, ts in _greeting_cooldown.items() if ts < greeting_cutoff]
        for uid in stale_greetings:
            del _greeting_cooldown[uid]

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
        "помощь": help_command, "help": help_command, "допомога": help_command, "hilfe": help_command, "pomoc": help_command,
        "оплата": pay_command, "pay": pay_command, "оплатить": pay_command,
        "pdf": pdf_command, "пдф": pdf_command,
        "vip": vip_command, "вип": vip_command,
        "баланс": balance_command, "balance": balance_command, "guthaben": balance_command, "saldo": balance_command,
        "мой язык": lang_command, "my lang": lang_command, "my language": lang_command, "мова": lang_command, "sprache": lang_command, "język": lang_command,
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
        fields = ["full_name", "profession", "income", "employer", "move_in_date", "occupants", "pets", "rental_duration", "preferred_letter_lang"]
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
        expire_unlimited_if_needed(user)
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
        listing_text = await fetch_url_text_async(user_text)
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
        expire_unlimited_if_needed(user)
        if not can_use(user):
            ref_code = user.get("ref_code", "")
            ref_link = f"https://t.me/{context.bot.username}?start={ref_code}" if ref_code else ""
            await update.message.reply_text(
                get_msg(lang, "limit_reached").format(ref_link),
                reply_markup=kb(update)
            )
            return

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

    # Проверка фильтра города
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
        lang = get_lang(update)
        user_id = str(update.effective_user.id)

        data_prefix = query.data.split(":")[0] if ":" in query.data else query.data

        # Кнопка "Язык" — отвечаем с alert ниже, пропускаем общий answer
        if data_prefix.startswith("lang_"):
            new_lang = data_prefix.split("_", 1)[1]
            uid = str(query.from_user.id)
            data_dict = load_data()
            user = get_user_data(data_dict, uid)
            user["lang"] = new_lang
            save_data(data_dict)
            lang_names = {"ru": "Русский", "uk": "Українська", "en": "English", "de": "Deutsch", "pl": "Polski"}
            await query.answer(f"✅ Язык изменён: {lang_names.get(new_lang, new_lang)}", show_alert=True)
            return

        # Кнопка "Ещё одно объявление" — в личку
        if data_prefix == "new":
            await query.answer()
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
            await query.answer()
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

            token_or_short_id = query.data.split(":", 1)[1] if ":" in query.data else ""
            bot_username = context.bot.username

            rss_url = resolve_url_token(token_or_short_id)

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

            try:
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
                        reply_markup=keyboard,
                    )
                else:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="🔍 Нажмите кнопку ниже, чтобы получить полный разбор объявления в личке!",
                        reply_markup=keyboard,
                    )
            except Exception as e:
                logger.error("analyze_rss reply failed: %s", e)

        # Кнопка "Пропустить"
        elif data_prefix == "skip_ad":
            await query.answer()

        # Кнопка "Скопировать"
        elif data_prefix == "copy":
            await query.answer()

        # Кнопка "Поделиться"
        elif data_prefix == "share":
            await query.answer()
            bot_username = context.bot.username
            share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=🏠+EuroRent+AI+-+AI-бот+для+разбора+объявлений+по+аренде+в+Европе!"
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"📤 {get_msg(lang, 'share_text')}\n\n{share_url}",
                reply_markup=kb(update, chat_type="private"),
            )

        # Кнопка "PDF"
        elif data_prefix == "pdf":
            await query.answer()
            await context.bot.send_message(
                chat_id=int(user_id),
                text=get_msg(lang, "pay_pdf"),
                reply_markup=kb(update, chat_type="private"),
            )

        # Кнопки оплаты
        elif data_prefix.startswith("show_pay_"):
            await query.answer()
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
                user_filters = get_user_filters(user_id)
                field = f"filter_{filter_type}"
                new_val = not user_filters.get(field, False)
                user_filters[field] = new_val
                save_user_filters(
                    user_id,
                    furnished=user_filters.get("filter_furnished", False),
                    pets=user_filters.get("filter_pets", False),
                    parking=user_filters.get("filter_parking", False),
                )
                icon = "✅" if new_val else "❌"
                label = {"furnished": "Мебель", "pets": "Питомцы", "parking": "Парковка"}[filter_type]
                await query.answer(f"{label}: {icon}", show_alert=False)
                # Обновляем клавиатуру
                user_filters = get_user_filters(user_id)
                furnished = "✅" if user_filters.get("filter_furnished") else "❌"
                pets_f = "✅" if user_filters.get("filter_pets") else "❌"
                parking = "✅" if user_filters.get("filter_parking") else "❌"
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

        # Кнопка "Письмо" после анализа
        elif data_prefix == "gen_letter":
            await query.answer()
            profile = get_profile(user_id)
            filled = sum(1 for f in ["full_name", "profession", "income", "employer"] if profile.get(f))
            if filled < 2:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text="📝 Для генерации письма заполните профиль.\n\nИспользуйте: /set_profile",
                )
            else:
                last_url = get_last_url(user_id)
                if not last_url:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="📝 Сначала проанализируйте объявление, потом /generate_letter.",
                    )
                else:
                    await context.bot.send_message(chat_id=int(user_id), text="📝 Генерирую письмо...")
                    letter_lang = profile.get("preferred_letter_lang", "")
                    if letter_lang not in ("de", "en"):
                        letter_lang = "de" if lang in ("ru", "de") else "en"
                    letter = generate_letter(profile, last_url, lang=letter_lang)
                    if letter:
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("📋 Копировать", callback_data="copy_letter")],
                            [InlineKeyboardButton("📄 Скачать PDF", callback_data="pdf_letter")],
                        ])
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text=f"📝 <b>Мотивационное письмо ({letter_lang.upper()}):</b>\n\n{letter}",
                            reply_markup=keyboard, parse_mode="HTML",
                        )
                        user = get_user(user_id)
                        user["last_letter"] = letter
                        save_user(user_id, user)
                    else:
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text="❌ Не удалось сгенерировать письмо. Попробуйте позже.",
                        )

        # Кнопка "В избранное"
        elif data_prefix == "fav_save":
            last_url = get_last_url(user_id)
            if last_url:
                from user_features import add_favorite
                ok = add_favorite(user_id, last_url, title="Из анализа")
                if ok:
                    await query.answer("⭐ Добавлено в избранное!", show_alert=False)
                else:
                    await query.answer("Ошибка", show_alert=True)
            else:
                await query.answer("Нет объявления для сохранения", show_alert=True)

        # Кнопка "Копировать письмо"
        elif data_prefix == "copy_letter":
            await query.answer("Скопируйте текст выше", show_alert=True)

        # Кнопка "PDF письма"
        elif data_prefix == "pdf_letter":
            await query.answer()
            profile = get_profile(user_id)
            last_letter = get_user(user_id).get("last_letter", "")
            if last_letter:
                pdf_data = {
                    "name": profile.get("full_name", ""),
                    "dob": "",
                    "phone": "",
                    "email": "",
                    "address": "",
                    "employer": profile.get("employer", ""),
                    "income": profile.get("income", ""),
                    "occupants": profile.get("occupants", ""),
                }
                pdf_bytes = generate_mieterprofil_pdf(pdf_data, cover_letter=last_letter)
                await context.bot.send_document(
                    chat_id=int(user_id),
                    document=BytesIO(pdf_bytes),
                    filename="Cover_Letter_Mieterprofil.pdf",
                    caption="📄 Письмо + Mieterprofil PDF",
                )
            else:
                await query.answer("Сначала сгенерируйте письмо", show_alert=True)

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
                listing_text = await fetch_url_text_async(url)
                if listing_text.startswith("ERROR"):
                    # Парсер не смог загрузить — предлагаем скопировать текст
                    await update.message.reply_text(
                        f"❌ Не удалось загрузить страницу автоматически.\n\n"
                        f"📋 Ссылка: {url}\n\n"
                        f"Скопируйте текст объявления с сайта и отправьте его сюда — я проанализирую!",
                        reply_markup=kb(update)
                    )
                    return
                try:
                    await process_listing(update, context, listing_text, user_id=user_id, lang=lang)
                except Exception as e:
                    logging.error("process_listing (start token) error for user %s: %s", user_id, e)
                    try:
                        await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=kb(update))
                    except Exception:
                        pass
                return
            else:
                # Токен не найден — показываем приветствие с подсказкой
                await update.message.reply_text(
                    "👋 Добро пожаловать!\n\n"
                    "Отправьте мне ссылку на объявление или текст — я проанализирую за 5 секунд!\n\n"
                    "Примеры:\n"
                    "• https://www.immowelt.de/expose/...\n"
                    "• Текст объявления на любом языке",
                    reply_markup=kb(update)
                )
                return
        elif payload.startswith("analyze_"):
            # Старый формат: полный URL (для обратной совместимости)
            try:
                url = unquote(payload[len("analyze_"):])
            except Exception:
                url = ""
            if is_url(url):
                await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=kb(update))
                listing_text = await fetch_url_text_async(url)
                if listing_text.startswith("ERROR"):
                    await update.message.reply_text(
                        f"❌ Не удалось загрузить страницу автоматически.\n\n"
                        f"📋 Ссылка: {url}\n\n"
                        f"Скопируйте текст объявления с сайта и отправьте его сюда — я проанализирую!",
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
            else:
                # URL не валиден — показываем приветствие
                logo_path = os.path.join(os.path.dirname(__file__), "icons", "start.png")
                if os.path.exists(logo_path):
                    with open(logo_path, "rb") as photo:
                        await update.message.reply_photo(photo=photo)
                await update.message.reply_text(get_msg(lang, "start"), reply_markup=kb(update))
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


_LANG_PROMPT = {
    "ru": "Выберите язык:",
    "uk": "Оберіть мову:",
    "en": "Choose language:",
    "de": "Sprache wählen:",
    "pl": "Wybierz język:",
}


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
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
    await update.message.reply_text(_LANG_PROMPT.get(lang, _LANG_PROMPT["en"]), reply_markup=keyboard)


async def pay_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "vip_intro"), reply_markup=kb(update))


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


def run_flask():
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


async def group_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /faq [вопрос] — ответ через Groq в группе."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    if not context.args:
        await update.message.reply_text(
            "📖 Использование: /faq ваш вопрос\n\n"
            "Пример: /faq какие документы нужны для аренды в Германии?"
        )
        return

    question = " ".join(context.args)
    await update.message.reply_text("🤔 Думаю...")

    try:
        system_prompt = (
            "Ты — эксперт по аренде жилья в Европе. Отвечай на вопросы экспатов "
            "кратко и по делу на русском языке. Максимум 200 слов. "
            "Если вопрос не про аренду — вежливо перенаправляй на тему."
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            max_tokens=400,
        )
        answer = response.choices[0].message.content.strip()
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"FAQ error: {e}")
        await update.message.reply_text("❌ Не удалось ответить. Попробуйте позже.")


# ═══════════════════════════════════════════════════════════════
# НОВЫЕ ФИЧИ: Избранное, Трекер, Профиль, Фильтры, Письмо
# ═══════════════════════════════════════════════════════════════

# ── Трекер заявок ──────────────────────────────────────────────

# ── Профиль (для писем) ────────────────────────────────────────

# ── Фильтры ────────────────────────────────────────────────────

# ── Рабочий адрес (для travel time) ────────────────────────────

# ── Генерация письма ───────────────────────────────────────────

# ── Подписки на алерты ─────────────────────────────────────────

if __name__ == "__main__":
    # 1. Создаём приложение
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(store_event_loop).build()

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
    application.add_handler(CommandHandler("reply", reply_command, priv))
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
    application.add_handler(CommandHandler("faq", group_faq, groups))
    application.add_handler(CommandHandler("rules", group_rules, groups))
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
    set_bot(application.bot)
    set_application(application)

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logging.info("Scheduler started in background")

    # 4. Запускаем бота (в основном потоке)
    logging.info("Starting bot polling...")
    application.run_polling(drop_pending_updates=True)
