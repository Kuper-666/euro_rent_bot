"""Callback handlers: listing actions (new, analyze, skip, copy, share, pdf, pay)."""
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import get_user
from messages import get_msg
from utils import get_lang, get_user_data, can_use, calc_remaining, is_url
from services.keyboards import kb
from rent_scanner.formatting import resolve_url_token, create_url_token

logger = logging.getLogger(__name__)


async def handle_new_listing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    user_id = str(update.effective_user.id)
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


async def handle_analyze_ad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    token_or_short_id = query.data.split(":", 1)[1] if ":" in query.data else ""
    bot_username = context.bot.username
    user_id = str(update.effective_user.id)

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


async def handle_skip_ad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass


async def handle_copy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer("Скопируйте текст выше", show_alert=True)


async def handle_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    lang = await asyncio.to_thread(get_lang, update)
    bot_username = context.bot.username
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=🏠+EuroRent+AI+-+AI-бот+для+разбора+объявлений+по+аренде+в+Европе!"
    await context.bot.send_message(
        chat_id=int(user_id),
        text=f"📤 {get_msg(lang, 'share_text')}\n\n{share_url}",
        reply_markup=kb(update, chat_type="private"),
    )


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    lang = await asyncio.to_thread(get_lang, update)
    await context.bot.send_message(
        chat_id=int(user_id),
        text=get_msg(lang, "pay_pdf"),
        reply_markup=kb(update, chat_type="private"),
    )


async def handle_show_pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    lang = await asyncio.to_thread(get_lang, update)
    data_prefix = query.data.split(":")[0] if ":" in query.data else query.data
    plan = data_prefix.replace("show_pay_", "")
    msg_key = f"pay_{plan}" if plan != "pdf" else "pay_pdf"
    if plan == "vip":
        msg_key = "vip_intro"
    await context.bot.send_message(
        chat_id=int(user_id),
        text=get_msg(lang, msg_key),
        reply_markup=kb(update, chat_type="private"),
    )
