"""Callback handler: language switch."""
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from storage import get_user, save_user
from messages import get_msg
from services.keyboards import kb

logger = logging.getLogger(__name__)


async def handle_lang_switch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data_prefix = query.data.split(":")[0] if ":" in query.data else query.data
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
