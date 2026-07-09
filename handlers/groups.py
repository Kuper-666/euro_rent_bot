"""Групповые хендлеры: приветствие, /start, /help, /faq, /rules, анализ в группе."""

import re
import time
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils import get_lang
from messages import get_msg
from rent_scanner.formatting import create_url_token
from listing_features import POPULAR_CITIES

logger = logging.getLogger(__name__)

GREETING_COOLDOWN = 3600
_greeting_cooldown = {}


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


async def group_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    await update.message.reply_text(
        "📜 <b>Правила группы ExpatRent Community:</b>\n\n"
        "1️⃣ Без спама и рекламы\n"
        "2️⃣ Только вопросы по аренде жилья в Европе\n"
        "3️⃣ Уважайте друг друга\n"
        "4️⃣ Используйте /faq для вопросов боту\n"
        "5️⃣ Не отправляйте личные данные в общий чат\n\n"
        "🔍 Для анализа объявления — отправьте ссылку, "
        "я перенаправлю вас в личку с ботом!",
        parse_mode="HTML"
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

    has_url = text.strip().startswith(("http://", "https://", "t.me/"))
    is_long_text = len(text.strip()) > 30

    if not has_url and not is_long_text:
        return

    lang = await asyncio.to_thread(get_lang, update)

    if has_url:
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
