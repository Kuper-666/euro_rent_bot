"""
Хендлеры Phase 1-3: Избранное, Трекер, Профиль, Фильтры, Письма, Алерты.
"""
import html
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils import get_lang, is_url
from storage import save_user, get_user
from user_features import (
    add_favorite, get_favorites, remove_favorite,
    add_tracker_entry, get_tracker_entries, update_tracker_status, STATUSES,
    get_profile, save_profile, PROFILE_FIELDS,
    get_user_filters, save_user_filters,
)
from letter_generator import generate_letter
from services.keyboards import kb

logger = logging.getLogger(__name__)

# Быстрый in-process кэш — экономит round-trip к БД.
# НЕ единственный источник истины: при рестарте он обнуляется,
# поэтому данные всегда читаются/пишутся через storage.
_last_analyzed_cache = {}


def track_last_url(user_id: str, url: str, listing_text: str = ""):
    """Сохраняет последнее проанализированное объявление для /favorite и /generate_letter."""
    _last_analyzed_cache[user_id] = {"url": url or "", "text": listing_text or ""}
    try:
        user = get_user(user_id)
        user["last_listing_url"] = url or ""
        user["last_listing_text"] = listing_text or ""
        save_user(user_id, user)
    except Exception as e:
        logger.warning("Failed to persist last listing for user=%s: %s", user_id, e)


def get_last_url(user_id: str) -> str:
    """Возвращает оригинальную ссылку последнего анализа (для /favorite)."""
    cached = _last_analyzed_cache.get(user_id)
    if cached is not None:
        return cached["url"]
    try:
        user = get_user(user_id)
        return user.get("last_listing_url", "")
    except Exception as e:
        logger.warning("Failed to read last listing url for user=%s: %s", user_id, e)
    return ""


def get_last_listing_text(user_id: str) -> str:
    """Возвращает текст последнего проанализированного объявления (для писем)."""
    cached = _last_analyzed_cache.get(user_id)
    if cached is not None and cached["text"]:
        return cached["text"]
    try:
        user = get_user(user_id)
        return user.get("last_listing_text", "")
    except Exception as e:
        logger.warning("Failed to read last listing text for user=%s: %s", user_id, e)
        return ""


# ── Избранное ──────────────────────────────────────────────────

async def favorite_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    last_url = get_last_url(user_id)
    fallback_text = get_last_listing_text(user_id)

    if not last_url and not fallback_text:
        await update.message.reply_text(
            "⭐ Сначала проанализируйте объявление, потом /favorite.",
            reply_markup=kb(update)
        )
        return

    ok = add_favorite(user_id, last_url or fallback_text[:200], title="Из анализа")
    if ok:
        await update.message.reply_text(
            "⭐ Добавлено в избранное!\n\nПосмотреть: /favorites",
            reply_markup=kb(update)
        )
    else:
        await update.message.reply_text("❌ Ошибка сохранения.", reply_markup=kb(update))


async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    favs = get_favorites(user_id)

    if not favs:
        await update.message.reply_text(
            "⭐ Пока пусто.\n\nПроанализируйте объявление → /favorite",
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
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            "📋 /track ссылка\n\nПример: /track https://immobilienscout24.de/expose/123",
            reply_markup=kb(update)
        )
        return

    url = context.args[0]
    if not is_url(url):
        await update.message.reply_text("❌ Отправьте URL.", reply_markup=kb(update))
        return

    entry_id = add_tracker_entry(user_id, url, title=url[:80])
    if entry_id:
        await update.message.reply_text(
            f"📋 Заявка #{entry_id} добавлена!\n\n"
            f"Статус: 💾 Сохранено\n"
            f"Изменить: /track_status {entry_id} applied",
            reply_markup=kb(update)
        )
    else:
        await update.message.reply_text("❌ Ошибка.", reply_markup=kb(update))


async def mytracks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    entries = get_tracker_entries(user_id)

    if not entries:
        await update.message.reply_text("📋 Пока пусто.\n\nДобавьте: /track ссылка", reply_markup=kb(update))
        return

    text = f"📋 <b>Мои заявки</b> ({len(entries)}):\n\n"
    buttons = []
    for e in entries[:10]:
        status = STATUSES.get(e.get("status", "saved"), "💾 Сохранено")
        title = e.get("listing_title", "")[:40]
        entry_id = e.get("id", 0)
        text += f"#{entry_id} {status} — {title}\n"
        row = [InlineKeyboardButton(STATUSES[s][:3], callback_data=f"track:{entry_id}:{s}")
               for s in ["applied", "viewed", "interview", "accepted", "rejected"]]
        buttons.append(row)

    kb_track = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(text, reply_markup=kb_track, parse_mode="HTML")


async def track_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)

    if len(context.args) < 2:
        await update.message.reply_text(
            f"📋 /track_status ID статус\n\nСтатусы: {', '.join(STATUSES.keys())}",
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
            f"✅ #{entry_id} → {STATUSES.get(status, status)}",
            reply_markup=kb(update)
        )
    else:
        await update.message.reply_text("❌ Ошибка. Проверьте ID и статус.", reply_markup=kb(update))


# ── Рабочий адрес ──────────────────────────────────────────────

async def set_work_address_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            "📍 /set_work_address адрес\n\nПример: /set_work_address Friedrichstraße 100, Berlin\n"
            "Удалить: /set_work_address clear",
            reply_markup=kb(update)
        )
        return

    address = " ".join(context.args)
    user = get_user(user_id)
    user["work_address"] = "" if address.lower() == "clear" else address
    save_user(user_id, user)
    msg = "📍 Адрес удалён." if address.lower() == "clear" else f"📍 Сохранено: {address}"
    await update.message.reply_text(msg, reply_markup=kb(update))


# ── Профиль (расширенный) ─────────────────────────────────────

PROFILE_FIELDS = ["full_name", "profession", "income", "employer", "move_in_date", "occupants", "pets", "rental_duration", "preferred_letter_lang"]
PROFILE_LABELS = {
    "full_name": "Имя Фамилия",
    "profession": "Профессия",
    "income": "Доход (нетто/мес)",
    "employer": "Работодатель",
    "move_in_date": "Дата переезда",
    "occupants": "Кол-во жильцов",
    "pets": "Питомцы",
    "rental_duration": "Желаемый срок аренды (мес)",
    "preferred_letter_lang": "Язык письма (de/en)",
}


async def set_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Устанавливает профиль пользователя для генерации писем."""
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)

    fields_text = "\n".join(
        f"  {i+1}. {PROFILE_LABELS.get(f, f)}: {profile.get(f, '')}"
        for i, f in enumerate(PROFILE_FIELDS)
    )

    await update.message.reply_text(
        f"📝 <b>Ваш профиль</b>:\n{fields_text}\n\n"
        f"Отправьте данные построчно (каждое поле с новой строки):\n"
        f"1. Имя Фамилия\n"
        f"2. Профессия\n"
        f"3. Доход (нетто/мес)\n"
        f"4. Работодатель\n"
        f"5. Дата переезда\n"
        f"6. Кол-во жильцов\n"
        f"7. Питомцы\n"
        f"8. Срок аренды (мес)\n"
        f"9. Язык письма (de/en)\n\n"
        f"/skip_profile — отмена",
        reply_markup=kb(update), parse_mode="HTML"
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
    await update.message.reply_text("❌ Отменено.", reply_markup=kb(update))


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущий профиль."""
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)

    text = "📝 <b>Профиль</b>:\n\n"
    for field, label in PROFILE_LABELS.items():
        text += f"  {label}: {profile.get(field, '') or '—'}\n"
    text += "\nИзменить: /set_profile"
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb(update))


# ── Фильтры ────────────────────────────────────────────────────

async def filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает и переключает фильтры."""
    user_id = str(update.effective_user.id)
    filters = get_user_filters(user_id)
    f = "✅" if filters.get("filter_furnished") else "❌"
    p = "✅" if filters.get("filter_pets") else "❌"
    pk = "✅" if filters.get("filter_parking") else "❌"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🪑 Мебель: {f}", callback_data="filter:furnished")],
        [InlineKeyboardButton(f"🐾 Питомцы: {p}", callback_data="filter:pets")],
        [InlineKeyboardButton(f"🅿️ Парковка: {pk}", callback_data="filter:parking")],
    ])
    await update.message.reply_text(
        "🔧 <b>Фильтры</b>\n\nБот отмечает соответствие при анализе.",
        reply_markup=keyboard, parse_mode="HTML"
    )


# ── Письмо ─────────────────────────────────────────────────────

async def generate_letter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерирует мотивационное письмо арендодателю."""
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)

    filled = sum(1 for f in ["full_name", "profession", "income", "employer"] if profile.get(f))
    if filled < 2:
        await update.message.reply_text(
            "📝 Для генерации письма заполните профиль.\n\n"
            "Используйте: /set_profile",
            reply_markup=kb(update)
        )
        return

    last_listing_text = get_last_listing_text(user_id)
    if not last_listing_text:
        await update.message.reply_text(
            "📝 Сначала проанализируйте объявление, потом /generate_letter.",
            reply_markup=kb(update)
        )
        return

    await update.message.reply_text("📝 Генерирую письмо...", reply_markup=kb(update))

    lang = await asyncio.to_thread(get_lang, update)
    # Используем предпочтительный язык из профиля, если указан
    letter_lang = profile.get("preferred_letter_lang", "")
    if letter_lang not in ("de", "en"):
        letter_lang = "de" if lang in ("ru", "de") else "en"

    letter = generate_letter(profile, last_listing_text, lang=letter_lang)

    if letter:
        # Кнопка для копирования и PDF
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Копировать", callback_data="copy_letter")],
            [InlineKeyboardButton("📄 Скачать PDF", callback_data="pdf_letter")],
        ])
        await update.message.reply_text(
            f"📝 <b>Мотивационное письмо ({letter_lang.upper()}):</b>\n\n{html.escape(letter)}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        # Сохраняем письмо для PDF
        user = get_user(user_id)
        user["last_letter"] = letter
        save_user(user_id, user)
    else:
        await update.message.reply_text(
            "❌ Не удалось сгенерировать письмо. Попробуйте позже.",
            reply_markup=kb(update)
        )
        return


# ── Ответ арендодателю ────────────────────────────────────────

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерирует ответ на сообщение арендодателю."""
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)

    filled = sum(1 for f in ["full_name", "profession", "income", "employer"] if profile.get(f))
    if filled < 2:
        await update.message.reply_text(
            "📝 Для генерации ответа заполните профиль.\n\n"
            "Используйте: /set_profile",
            reply_markup=kb(update)
        )
        return

    if context.args:
        landlord_message = " ".join(context.args)
    else:
        last_listing_text = get_last_listing_text(user_id)
        if last_listing_text:
            landlord_message = last_listing_text
        else:
            await update.message.reply_text(
                "💬 /reply сообщение_арендодателя\n\n"
                "Ответьте на сообщение арендодателя или пришлите текст объявления.",
                reply_markup=kb(update)
            )
            return

    await update.message.reply_text("💬 Генерирую ответ...", reply_markup=kb(update))

    lang = await asyncio.to_thread(get_lang, update)
    reply_lang = profile.get("preferred_letter_lang", "")
    if reply_lang not in ("de", "en"):
        reply_lang = "de" if lang in ("ru", "de") else "en"

    from reply_generator import generate_reply
    reply_text = generate_reply(profile, landlord_message, lang=reply_lang)

    if reply_text:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Копировать", callback_data="copy_letter")],
        ])
        await update.message.reply_text(
            f"💬 <b>Ответ арендодателю ({reply_lang.upper()}):</b>\n\n{html.escape(reply_text)}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        user = get_user(user_id)
        user["last_letter"] = reply_text
        save_user(user_id, user)
    else:
        await update.message.reply_text(
            "❌ Не удалось сгенерировать ответ. Попробуйте позже.",
            reply_markup=kb(update)
        )


# ── Алерты ─────────────────────────────────────────────────────

async def subscribe_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            "🔔 /subscribe_alert город [макс.цена]\n\nПример: /subscribe_alert berlin 1500\n"
            "Отписка: /unsubscribe_alert",
            reply_markup=kb(update)
        )
        return

    city = context.args[0].lower()
    max_price = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 0

    from storage import _get_sb
    sb = _get_sb()
    if sb:
        try:
            sb.table("AlertSubscriptions").insert({
                "user_id": user_id, "city": city, "max_price": max_price, "active": True,
            }).execute()
            price_str = f" до {max_price} EUR" if max_price else ""
            await update.message.reply_text(
                f"✅ Алерты: {city}{price_str}", reply_markup=kb(update)
            )
        except Exception as e:
            logger.error("subscribe_alert error: %s", e)
            await update.message.reply_text("❌ Ошибка.", reply_markup=kb(update))


async def unsubscribe_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    from storage import _get_sb
    sb = _get_sb()
    if sb:
        try:
            sb.table("AlertSubscriptions").update({"active": False}).eq("user_id", user_id).execute()
            await update.message.reply_text("✅ Отписаны от алертов.", reply_markup=kb(update))
        except Exception as e:
            logger.error("unsubscribe_alert error: %s", e)


async def my_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    from storage import _get_sb
    sb = _get_sb()
    if sb:
        try:
            result = sb.table("AlertSubscriptions").select("*").eq("user_id", user_id).eq("active", True).execute()
            subs = result.data or []
            if not subs:
                await update.message.reply_text("🔔 Нет подписок.\n\nСоздать: /subscribe_alert город", reply_markup=kb(update))
                return
            text = "🔔 <b>Алерты:</b>\n\n"
            for s in subs:
                city = s.get("city", "?")
                price = s.get("max_price", 0)
                text += f"• {city} — {'до ' + str(int(price)) + ' EUR' if price else 'все'}\n"
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb(update))
        except Exception as e:
            logger.error("my_alerts error: %s", e)


# ── Обработка профиля в handle_message ─────────────────────────

def handle_profile_state(user_id: str, text: str) -> tuple[bool, str]:
    """Обрабатывает ввод профиля. Возвращает (handled, result_message)."""
    user = get_user(user_id)
    if user.get("profile_state") != "awaiting_profile":
        return False, ""

    user.pop("profile_state", None)
    save_user(user_id, user)

    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    fields = list(PROFILE_LABELS.keys())
    profile_data = {}
    for i, field in enumerate(fields):
        if i < len(lines):
            profile_data[field] = lines[i].lstrip("0123456789. ")

    if profile_data:
        save_profile(user_id, profile_data)
        return True, "profile_saved"
    return True, "profile_error"
