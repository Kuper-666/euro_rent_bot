import dns_fix  # noqa: F401 — патч DNS для Windows
import os
import re
import logging
import threading
import time
import hashlib
import asyncio
import secrets
from datetime import datetime
from urllib.parse import unquote
from io import BytesIO
from flask import request, jsonify
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, PreCheckoutQueryHandler, filters, ContextTypes
)
from groq import Groq

from config import TELEGRAM_TOKEN, GROQ_API_KEY, PDF_PRICE, VIP_PRICE
from messages import get_msg
from storage import save_user, get_user
from user_features import save_profile, get_profile
from user_features import (
    get_user_filters, save_user_filters,
    remove_favorite, update_tracker_status, STATUSES,
)
from utils import (
    load_data, save_data, get_lang, get_user_data,
    can_use, is_url, fetch_url_text, fetch_url_text_async, ocr_from_photo,
    calc_remaining, check_rate_limit,
    is_pdf_state_expired, validate_pdf_data, expire_unlimited_if_needed
)
from pdf_generator import generate_mieterprofil_pdf
from letter_generator import generate_letter
from email_newsletter import add_email_subscriber, remove_email_subscriber, get_active_subscribers
from services.keyboards import kb, get_analysis_inline_buttons, split_message
from handlers.commands import (
    help_command, revolut_command, balance_command, ref_command,
    lang_command, pay_vip, parse_pdf_data, group_faq,
    log_referral_event,
)
from handlers.listing_analyzer import process_listing, check_followups
from handlers.user_features import (
    favorite_command, favorites_command,
    track_command, mytracks_command, track_status_command,
    set_profile_command, skip_profile_command, profile_command,
    filters_command, set_work_address_command, generate_letter_command, reply_command,
    subscribe_alert_command, unsubscribe_alert_command, my_alerts_command,
    handle_profile_state, track_last_url, get_last_url, get_last_listing_text,
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
from scheduler import update_last_activity, register_jobs
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


# Токены для коротких deep links — используют общий модуль из rent_scanner
from rent_scanner.formatting import create_url_token, resolve_url_token


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
    lang = await asyncio.to_thread(get_lang, update)

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

    await asyncio.to_thread(update_last_activity, user_id)
    data = await asyncio.to_thread(load_data)
    user = get_user_data(data, user_id)

    followup = check_followups(user, lang)
    if followup:
        await update.message.reply_text(followup, reply_markup=kb(update))

    pdf_state = user.get("pdf_state")
    if pdf_state == "awaiting_data" and is_pdf_state_expired(user):
        user.pop("pdf_state", None)
        user.pop("pdf_started_at", None)
        await asyncio.to_thread(save_data, data)
        pdf_state = None
    if pdf_state == "awaiting_data":
        user.pop("pdf_state", None)
        user.pop("pdf_started_at", None)
        await asyncio.to_thread(save_data, data)
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
        await asyncio.to_thread(save_data, data)
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
        await asyncio.to_thread(save_user, user_id, user)
        lines = [line.strip() for line in update.message.text.strip().split("\n") if line.strip()]
        fields = ["full_name", "profession", "income", "employer", "move_in_date", "occupants", "pets", "rental_duration", "preferred_letter_lang"]
        profile_data = {}
        for i, field in enumerate(fields):
            if i < len(lines):
                profile_data[field] = lines[i].lstrip("0123456789. ")
        if profile_data:
            await asyncio.to_thread(save_profile, user_id, profile_data)
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
    source_url = ""

    if user_text and is_url(user_text):
        source_url = user_text
        await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=kb(update))
        listing_text = await fetch_url_text_async(user_text)
        if listing_text.startswith("ERROR"):
            # Логируем реальную причину (таймаут / коннекшн / антибот-блок /
            # другое) — иначе на сервере нет никакой зацепки, почему именно
            # этот сайт не спарсился, и диагностика следующего похожего
            # случая начинается с нуля.
            logging.warning("fetch_url_text failed for %s: %s", user_text, listing_text)
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

    user_city = await asyncio.to_thread(get_user_city, user_id)
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
        await process_listing(update, context, listing_text, user_id, lang, source_url=source_url)
    except Exception as e:
        logging.error(f"process_listing error for user {user_id}: {e}")
        try:
            await update.message.reply_text(get_msg(lang, "error").format(str(e)[:200]), reply_markup=kb(update))
        except Exception:
            pass


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    user_id = str(update.effective_user.id)
    lang = await asyncio.to_thread(get_lang, update)
    # Точечный доступ к одному пользователю вместо полного load_data() —
    # data целиком нигде дальше не использовался, только user из неё.
    user = await asyncio.to_thread(get_user, user_id)

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
    user_city = await asyncio.to_thread(get_user_city, user_id)
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
        # Фото не имеет исходного URL по определению (это OCR-путь) —
        # раньше здесь передавался source_url, который в handle_photo вообще
        # никогда не присваивался (скопировано из handle_message без учёта
        # разницы), что гарантированно ломало КАЖДЫЙ анализ по фото с
        # NameError: name 'source_url' is not defined.
        await process_listing(update, context, listing_text, user_id, lang, source_url="")
    except Exception as e:
        logging.error(f"process_listing (photo) error for user {user_id}: {e}")
        try:
            await update.message.reply_text(get_msg(lang, "error").format(str(e)[:200]), reply_markup=kb(update))
        except Exception:
            pass


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        logger.info("Callback received: data=%s user=%s", query.data, query.from_user.id if query.from_user else "?")
        if not update.effective_user or not query.data:
            return
        
        data_prefix = query.data.split(":")[0] if ":" in query.data else query.data

        # Кнопка "Язык". answer() ПЕРВЫМ — до БД (Telegram invalidates callback ~10s)
        if data_prefix.startswith("lang_"):
            new_lang = data_prefix.split("_", 1)[1]
            lang_names = {"ru": "Русский", "uk": "Українська", "en": "English", "de": "Deutsch", "pl": "Polski"}
            try:
                await query.answer(f"✅ Язык изменён: {lang_names.get(new_lang, new_lang)}", show_alert=True)
            except Exception as e:
                logger.warning("answerCallbackQuery failed for lang_%s: %s", new_lang, e)

            uid = str(query.from_user.id)
            try:
                user = await asyncio.to_thread(get_user, uid)
                user["lang"] = new_lang
                await asyncio.to_thread(save_user, uid, user)
            except Exception as e:
                logger.error("Failed to persist lang=%s for user=%s: %s", new_lang, uid, e)
                try:
                    await context.bot.send_message(chat_id=int(uid), text="Не удалось сохранить язык, попробуйте ещё раз.")
                except Exception:
                    pass
                return

            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=get_msg(new_lang, "start"),
                    reply_markup=kb(update, chat_type="private", lang=new_lang),
                )
            except Exception as e:
                logger.warning("Failed to send post-language-switch message: %s", e)
            return

        lang = await asyncio.to_thread(get_lang, update)
        user_id = str(update.effective_user.id)

        # Кнопка "Ещё одно объявление" — в личку
        if data_prefix == "new":
            await query.answer()
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            user = await asyncio.to_thread(get_user, user_id)
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

            rss_url = await asyncio.to_thread(resolve_url_token, token_or_short_id)

            if not rss_url:
                try:
                    from daily_poster import get_listing
                    listing = await asyncio.to_thread(get_listing, token_or_short_id)
                    rss_url = listing.get("url", "")
                except Exception:
                    pass

            if rss_url and is_url(rss_url):
                new_token = await asyncio.to_thread(create_url_token, rss_url)
                analyze_url = f"https://t.me/{bot_username}?start=an_{new_token}"
            else:
                analyze_url = f"https://t.me/{bot_username}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Открыть бота для анализа", url=analyze_url)]
            ])

            user = await asyncio.to_thread(get_user, user_id)

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
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

        # Кнопка "Скопировать"
        elif data_prefix == "copy":
            await query.answer("Скопируйте текст выше", show_alert=True)

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
                user_filters = await asyncio.to_thread(get_user_filters, user_id)
                field = f"filter_{filter_type}"
                new_val = not user_filters.get(field, False)
                user_filters[field] = new_val
                await asyncio.to_thread(
                    save_user_filters,
                    user_id,
                    furnished=user_filters.get("filter_furnished", False),
                    pets=user_filters.get("filter_pets", False),
                    parking=user_filters.get("filter_parking", False),
                )
                icon = "✅" if new_val else "❌"
                label = {"furnished": "Мебель", "pets": "Питомцы", "parking": "Парковка"}[filter_type]
                await query.answer(f"{label}: {icon}", show_alert=False)
                furnished = "✅" if user_filters.get("filter_furnished") else "❌"
                pets_f = "✅" if user_filters.get("filter_pets") else "❌"
                parking = "✅" if user_filters.get("filter_parking") else "❌"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🪑 Мебель: {furnished}", callback_data="filter:furnished")],
                    [InlineKeyboardButton(f"🐾 Питомцы: {pets_f}", callback_data="filter:pets")],
                    [InlineKeyboardButton(f"🅿️ Парковка: {parking}", callback_data="filter:parking")],
                ])
                try:
                    await query.edit_message_reply_markup(reply_markup=keyboard)
                except Exception:
                    pass

        # Удаление из избранного
        elif data_prefix == "fav_del":
            fav_id = int(query.data.split(":")[1]) if ":" in query.data else 0
            if fav_id and await asyncio.to_thread(remove_favorite, user_id, fav_id):
                await query.answer("Удалено из избранного", show_alert=False)
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
            else:
                await query.answer("Ошибка удаления", show_alert=True)

        # Смена статуса в трекере
        elif data_prefix == "track":
            parts = query.data.split(":")
            if len(parts) == 3:
                entry_id = int(parts[1])
                new_status = parts[2]
                if await asyncio.to_thread(update_tracker_status, user_id, entry_id, new_status):
                    await query.answer(f"Статус: {STATUSES.get(new_status, new_status)}", show_alert=False)
                else:
                    await query.answer("Ошибка", show_alert=True)
            else:
                await query.answer()

        # Кнопка "Письмо" после анализа
        elif data_prefix == "gen_letter":
            await query.answer()
            profile = await asyncio.to_thread(get_profile, user_id)
            filled = sum(1 for f in ["full_name", "profession", "income", "employer"] if profile.get(f))
            if filled < 2:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text="📝 Для генерации письма заполните профиль.\n\nИспользуйте: /set_profile",
                )
            else:
                last_listing_text = await asyncio.to_thread(get_last_listing_text, user_id)
                if not last_listing_text:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="📝 Сначала проанализируйте объявление, потом /generate_letter.",
                    )
                else:
                    await context.bot.send_message(chat_id=int(user_id), text="📝 Генерирую письмо...")
                    letter_lang = profile.get("preferred_letter_lang", "")
                    if letter_lang not in ("de", "en"):
                        letter_lang = "de" if lang in ("ru", "de") else "en"
                    # generate_letter — синхронный вызов Groq API
                    letter = await asyncio.to_thread(generate_letter, profile, last_listing_text, letter_lang)
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
                        user = await asyncio.to_thread(get_user, user_id)
                        user["last_letter"] = letter
                        await asyncio.to_thread(save_user, user_id, user)
                    else:
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text="❌ Не удалось сгенерировать письмо. Попробуйте позже.",
                        )

        # Кнопка "В избранное"
        elif data_prefix == "fav_save":
            last_url = await asyncio.to_thread(get_last_url, user_id)
            fallback_text = await asyncio.to_thread(get_last_listing_text, user_id)
            if last_url or fallback_text:
                from user_features import add_favorite
                ok = await asyncio.to_thread(add_favorite, user_id, last_url or fallback_text[:200], "Из анализа")
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
            profile = await asyncio.to_thread(get_profile, user_id)
            user_for_letter = await asyncio.to_thread(get_user, user_id)
            last_letter = user_for_letter.get("last_letter", "")
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
    lang = await asyncio.to_thread(get_lang, update)

    user_id = str(update.effective_user.id)
    # load_data — синхронный full-table scan; используется дальше в этой же
    # функции для линейного поиска по ref_code (см. ref_ deep-link ветку),
    # поэтому не заменяем на point-lookup, а просто не блокируем event loop.
    data = await asyncio.to_thread(load_data)

    if user_id not in data:
        data[user_id] = {
            "free_used": 0,
            "balance": 0,
            "ref_code": f"ref_{secrets.token_hex(8)}",
            "lang": lang,
            "created_at": datetime.now().isoformat(),
            "total_checks": 0,
            "email": "",
        }
        await asyncio.to_thread(save_data, data)
    elif not data[user_id].get("ref_code"):
        data[user_id]["ref_code"] = f"ref_{hashlib.sha256(f'{user_id}eurorent2024'.encode()).hexdigest()[:8]}"
        await asyncio.to_thread(save_data, data)

    if context.args and len(context.args) > 0:
        payload = context.args[0][:512]  # Ограничение длины payload
        if payload.startswith("an_"):
            # Новый формат: короткий токен
            token = payload[len("an_"):]
            url = await asyncio.to_thread(resolve_url_token, token)
            if url and is_url(url):
                await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=kb(update))
                listing_text = await fetch_url_text_async(url)
                if listing_text.startswith("ERROR"):
                    # Парсер не смог загрузить — предлагаем скопировать текст
                    logging.warning("fetch_url_text failed for %s: %s", url, listing_text)
                    await update.message.reply_text(
                        f"❌ Не удалось загрузить страницу автоматически.\n\n"
                        f"📋 Ссылка: {url}\n\n"
                        f"Скопируйте текст объявления с сайта и отправьте его сюда — я проанализирую!",
                        reply_markup=kb(update)
                    )
                    return
                try:
                    await process_listing(update, context, listing_text, user_id=user_id, lang=lang, source_url=url)
                except Exception as e:
                    logging.error("process_listing (start token) error for user %s: %s", user_id, e)
                    try:
                        await update.message.reply_text(get_msg(lang, "error").format(str(e)[:200]), reply_markup=kb(update))
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
                    logging.warning("fetch_url_text failed for %s: %s", url, listing_text)
                    await update.message.reply_text(
                        f"❌ Не удалось загрузить страницу автоматически.\n\n"
                        f"📋 Ссылка: {url}\n\n"
                        f"Скопируйте текст объявления с сайта и отправьте его сюда — я проанализирую!",
                        reply_markup=kb(update)
                    )
                    return
                try:
                    await process_listing(update, context, listing_text, user_id=user_id, lang=lang, source_url=url)
                except Exception as e:
                    logging.error(f"process_listing (start) error for user {user_id}: {e}")
                    try:
                        await update.message.reply_text(get_msg(lang, "error").format(str(e)[:200]), reply_markup=kb(update))
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
                await asyncio.to_thread(save_data, data)
                log_referral_event("ref_link_clicked", user_id, {"referrer": referrer_id})

    logo_path = os.path.join(os.path.dirname(__file__), "icons", "start.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)
    await update.message.reply_text(get_msg(lang, "start"), reply_markup=kb(update))


def run_flask():
    import os
    port = int(os.environ.get("PORT", 10000))
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=port, threads=4)
    except ImportError:
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


# Global application for webhook access
application = None

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
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT & priv, successful_payment))
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

    # Регистрируем задачи в job_queue (вместо отдельного потока)
    register_jobs(application)
    logging.info("Scheduler jobs registered in job_queue")

    # 3. Check if WEBHOOK_URL is set
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if WEBHOOK_URL:
        logging.info("Starting bot with webhook...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Initialize and start application
        async def init_and_start():
            await application.initialize()
            await application.start()
        loop.run_until_complete(init_and_start())
        # Run Flask in main thread
        from web import app
        # Add webhook route to Flask app
        @app.post(f"/{TELEGRAM_TOKEN}")
        def webhook():
            if application:
                update = Update.de_json(data=request.get_json(force=True), bot=application.bot)
                if update:
                    asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
            return jsonify({"ok": True})
        # Set webhook
        async def set_webhook():
            await application.bot.set_webhook(WEBHOOK_URL + f"/{TELEGRAM_TOKEN}")
        loop.run_until_complete(set_webhook())
        logging.info(f"Webhook set to {WEBHOOK_URL}/{TELEGRAM_TOKEN}")
        # Run Flask in a thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        # Keep the main thread alive
        loop.run_forever()
    else:
        # Run Flask in background thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logging.info("Flask started in background")
        # 4. Запускаем бота в polling mode
        logging.info("Starting bot polling...")
        application.run_polling(drop_pending_updates=True)
