"""Городские хендлеры: /cities, выбор города, снятие фильтра."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils import get_lang
from messages import get_msg
from listing_features import POPULAR_CITIES, get_user_city, set_user_city, list_cities


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
