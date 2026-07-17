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
from config import TELEGRAM_TOKEN, PDF_PRICE, VIP_PRICE
from handlers.callbacks_lang import handle_lang_switch
from handlers.callbacks_listing import (
    handle_new_listing, handle_analyze_ad, handle_skip_ad,
    handle_copy, handle_share, handle_pdf, handle_show_pay,
)
from handlers.callbacks_features import (
    handle_filter_toggle, handle_fav_delete, handle_track_status,
    handle_gen_letter, handle_fav_save, handle_copy_letter,
    handle_pdf_letter,
)
from messages import get_msg
from storage import save_user, get_user
from user_features import save_profile, get_profile
from utils import (
    load_data, save_data, get_lang, get_user_data,
    can_use, is_url, fetch_url_text_async, ocr_from_photo,
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
    user = await asyncio.to_thread(get_user, user_id)

    followup = check_followups(user, lang)
    if followup:
        await update.message.reply_text(followup, reply_markup=kb(update))

    pdf_state = user.get("pdf_state")
    if pdf_state == "awaiting_data" and is_pdf_state_expired(user):
        user.pop("pdf_state", None)
        user.pop("pdf_started_at", None)
        await asyncio.to_thread(save_user, user_id, user)
        pdf_state = None
    if pdf_state == "awaiting_data":
        user.pop("pdf_state", None)
        user.pop("pdf_started_at", None)
        await asyncio.to_thread(save_user, user_id, user)
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
            # Синхронная CPU-bound генерация PDF; без to_thread блокирует
            # event loop бота для всех остальных пользователей на время
            # генерации (тот же класс проблемы, что чинился по всему
            # проекту ранее).
            pdf_bytes = await asyncio.to_thread(generate_mieterprofil_pdf, pdf_data)
            await update.message.reply_document(
                document=BytesIO(pdf_bytes),
                filename="Mieterprofil.pdf",
                caption=get_msg(lang, "pdf_done"),
                reply_markup=kb(update)
            )
        except Exception as e:
            logging.error(f"PDF generation error: {e}")
            await update.message.reply_text(get_msg(lang, "pdf_error").format(str(e)[:200]), reply_markup=kb(update))
        return

    vip_state = user.get("vip_state")
    if vip_state == "awaiting_criteria":
        user.pop("vip_state", None)
        user["vip"] = True
        user["vip_criteria"] = update.message.text
        await asyncio.to_thread(save_user, user_id, user)
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
        elif payload == "help":
            # group_help отправляет кнопку "Открыть помощь в личке" с этим
            # payload'ом, но раньше он не обрабатывался вообще — попадал в
            # обычное приветствие вместо реального раздела помощи, то есть
            # кнопка технически не падала, но не делала того, что обещала.
            await update.message.reply_text(get_msg(lang, "help"), reply_markup=kb(update))
            return

    logo_path = os.path.join(os.path.dirname(__file__), "icons", "start.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)
    await update.message.reply_text(get_msg(lang, "start"), reply_markup=kb(update))


async def run_health_checks(application, webhook_url: str, telegram_token: str) -> tuple[bool, dict]:
    """
    Реальная проверка состояния бота, а не просто "процесс жив".

    render.yaml использует "/" как healthCheckPath, но это статичная
    HTML-страница из web.py, которая всегда отвечает 200, даже если
    Supabase недоступен, webhook отключён Telegram'ом, или задачи
    планировщика не зарегистрированы — то есть Render считает сервис
    "здоровым", пока сам бот может быть полностью нефункционален. Именно
    это привело к долгому поиску причины "кнопки не отвечают": ни один
    автоматический сигнал не показывал проблему, приходилось вручную
    сверять логи в момент нажатия кнопки.

    Вынесена в отдельную функцию модульного уровня (а не определена
    инлайн внутри Flask route в main()), чтобы её можно было протестировать
    напрямую с моком application, без поднятия реального Flask/event loop.

    Возвращает (overall_ok, checks_dict).
    """
    checks = {}

    # 1. Supabase — реальный лёгкий запрос, не просто "заданы ли переменные
    # окружения". get_user на заведомо несуществующий id не создаёт записей
    # и работает в обоих режимах (Supabase/JSON).
    try:
        from storage import get_user, _get_mode
        t0 = time.time()
        await asyncio.to_thread(get_user, "__healthcheck__")
        checks["storage"] = {
            "ok": True,
            "mode": _get_mode(),
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }
    except Exception as e:
        checks["storage"] = {"ok": False, "error": str(e)[:200]}

    # 2. Webhook — сверяем с тем, что реально знает Telegram, а не просто с
    # тем, что бот думает, что установил при старте.
    try:
        info = await application.bot.get_webhook_info()
        expected_url = f"{webhook_url}/{telegram_token}"
        checks["webhook"] = {
            "ok": not info.last_error_message and info.url == expected_url,
            "url_matches_expected": info.url == expected_url,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
            "last_error_date": info.last_error_date.isoformat() if info.last_error_date else None,
        }
    except Exception as e:
        checks["webhook"] = {"ok": False, "error": str(e)[:200]}

    # 3. Планировщик — job_queue реально содержит задачи, значит
    # register_jobs() отработал при старте без исключения.
    try:
        jobs = application.job_queue.jobs() if application.job_queue else []
        checks["scheduler"] = {"ok": len(jobs) > 0, "job_count": len(jobs)}
    except Exception as e:
        checks["scheduler"] = {"ok": False, "error": str(e)[:200]}

    overall_ok = all(c.get("ok") for c in checks.values())
    return overall_ok, checks


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
    application.add_handler(CallbackQueryHandler(handle_lang_switch, pattern=r'^lang_'))
    application.add_handler(CallbackQueryHandler(handle_new_listing, pattern=r'^new$'))
    application.add_handler(CallbackQueryHandler(handle_analyze_ad, pattern=r'^(analyze_ad|analyze_rss):'))
    application.add_handler(CallbackQueryHandler(handle_skip_ad, pattern=r'^skip_ad$'))
    application.add_handler(CallbackQueryHandler(handle_copy, pattern=r'^copy$'))
    application.add_handler(CallbackQueryHandler(handle_share, pattern=r'^share$'))
    application.add_handler(CallbackQueryHandler(handle_pdf, pattern=r'^pdf$'))
    application.add_handler(CallbackQueryHandler(handle_show_pay, pattern=r'^show_pay_'))
    application.add_handler(CallbackQueryHandler(handle_filter_toggle, pattern=r'^filter:'))
    application.add_handler(CallbackQueryHandler(handle_fav_delete, pattern=r'^fav_del:'))
    application.add_handler(CallbackQueryHandler(handle_track_status, pattern=r'^track:'))
    application.add_handler(CallbackQueryHandler(handle_gen_letter, pattern=r'^gen_letter$'))
    application.add_handler(CallbackQueryHandler(handle_fav_save, pattern=r'^fav_save$'))
    application.add_handler(CallbackQueryHandler(handle_copy_letter, pattern=r'^copy_letter$'))
    application.add_handler(CallbackQueryHandler(handle_pdf_letter, pattern=r'^pdf_letter$'))
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

        @app.get("/health")
        def health():
            overall_ok, checks = asyncio.run_coroutine_threadsafe(
                run_health_checks(application, WEBHOOK_URL, TELEGRAM_TOKEN), loop
            ).result(timeout=15)
            status_code = 200 if overall_ok else 503
            return jsonify({"ok": overall_ok, "checks": checks}), status_code

        # Set webhook
        #
        # ВАЖНО: allowed_updates передаётся ЯВНО. Если не указать его,
        # Telegram сохраняет предыдущую настройку с прошлого вызова
        # setWebhook — если тот прошлый вызов был сделан без callback_query
        # в списке (например, вручную через curl/браузер при отладке),
        # кнопки могли бы молча перестать доходить до бота, при том что
        # текстовые сообщения продолжали бы работать.
        #
        # Также Telegram автоматически отключает webhook после достаточного
        # числа неудачных попыток доставки подряд (типично — если сервис на
        # Render был недоступен несколько секунд/минут во время передеплоя).
        # Код ранее вызывал set_webhook() один раз при старте и не проверял
        # результат — если Telegram уже "выключил" доставку из-за таких
        # сбоев, бот никак не узнавал об этом и не переустанавливал
        # webhook заново, что могло приводить к полной тишине без единой
        # ошибки в логах Render (апдейт не долетает до процесса вообще).
        async def set_webhook():
            full_url = WEBHOOK_URL + f"/{TELEGRAM_TOKEN}"
            await application.bot.set_webhook(
                full_url,
                allowed_updates=["message", "callback_query", "chat_member",
                                  "my_chat_member", "pre_checkout_query"],
                drop_pending_updates=False,
            )
            # Логируем реальное состояние сразу после установки — чтобы при
            # следующем деплое можно было проверить доставку прямо в логах
            # Render, без ручного похода на api.telegram.org/getWebhookInfo.
            info = await application.bot.get_webhook_info()
            logging.info(
                "Webhook info after set: url=%s pending_update_count=%s "
                "last_error_date=%s last_error_message=%s",
                info.url, info.pending_update_count,
                info.last_error_date, info.last_error_message,
            )
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
