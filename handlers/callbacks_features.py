"""Callback handlers: features (filters, favorites, tracker, letters, PDF)."""
import logging
import asyncio
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import get_user, save_user
from utils import get_lang
from user_features import (
    get_user_filters, save_user_filters, remove_favorite,
    get_profile, update_tracker_status, add_favorite,
)
from handlers.user_features import (
    get_last_listing_text, get_last_url, STATUSES,
)
from letter_generator import generate_letter
from pdf_generator import generate_mieterprofil_pdf

logger = logging.getLogger(__name__)


async def handle_filter_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    filter_type = query.data.split(":")[1] if ":" in query.data else ""
    if filter_type not in ("furnished", "pets", "parking"):
        await query.answer()
        return

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


async def handle_fav_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    fav_id = int(query.data.split(":")[1]) if ":" in query.data else 0
    if fav_id and await asyncio.to_thread(remove_favorite, user_id, fav_id):
        await query.answer("Удалено из избранного", show_alert=False)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
    else:
        await query.answer("Ошибка удаления", show_alert=True)


async def handle_track_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id)
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


async def handle_gen_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    lang = await asyncio.to_thread(get_lang, update)
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


async def handle_fav_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    last_url = await asyncio.to_thread(get_last_url, user_id)
    fallback_text = await asyncio.to_thread(get_last_listing_text, user_id)
    if last_url or fallback_text:
        ok = await asyncio.to_thread(add_favorite, user_id, last_url or fallback_text[:200], "Из анализа")
        if ok:
            await query.answer("⭐ Добавлено в избранное!", show_alert=False)
        else:
            await query.answer("Ошибка", show_alert=True)
    else:
        await query.answer("Нет объявления для сохранения", show_alert=True)


async def handle_copy_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer("Скопируйте текст выше", show_alert=True)


async def handle_pdf_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
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
        pdf_bytes = await asyncio.to_thread(generate_mieterprofil_pdf, pdf_data, last_letter)
        await context.bot.send_document(
            chat_id=int(user_id),
            document=BytesIO(pdf_bytes),
            filename="Cover_Letter_Mieterprofil.pdf",
            caption="📄 Письмо + Mieterprofil PDF",
        )
    else:
        await query.answer("Сначала сгенерируйте письмо", show_alert=True)
