"""Email хендлеры: /subscribe_email, /unsubscribe_email."""

import re
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from email_newsletter import add_email_subscriber, remove_email_subscriber


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

    if await asyncio.to_thread(add_email_subscriber, email, user_id):
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
    if await asyncio.to_thread(remove_email_subscriber, email):
        await update.message.reply_text(f"✅ Вы отписались от дайджеста ({email}).")
    else:
        await update.message.reply_text("ℹ️ Этот email не найден в подписчиках.")
