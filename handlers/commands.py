"""
Простые команды: /help, /revolut, /balance, /ref, /lang, /pay_vip, /faq.
Вынесены из bot.py для разгрузки.
"""
import os
import re
import time
import json
import hashlib
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import AFFILIATE_REVOLUT, AFFILIATE_WISE, FREE_LIMIT, GROQ_API_KEY
from messages import get_msg
from storage import save_user, get_user
from utils import get_lang, calc_remaining, sanitize_pdf_input
from services.keyboards import kb

logger = logging.getLogger(__name__)

client = None
if GROQ_API_KEY:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)


# ── Реферальное логирование ───────────────────────────────────

REFERRAL_LOG = "referral_events.jsonl"
REFERRAL_TABLE = "ReferralEvents"


def log_referral_event(event_type: str, user_id: str, extra: dict = None):
    """Логирует реферальное событие в Supabase или JSONL."""
    ts = time.time()
    entry = {"ts": ts, "type": event_type, "user_id": user_id}
    if extra:
        entry.update(extra)

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

    try:
        with open(REFERRAL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── Простые команды ───────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await asyncio.to_thread(get_lang, update)
    icon_path = os.path.join(os.path.dirname(__file__), "..", "icons", "help.png")
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
    user = await asyncio.to_thread(get_user, user_id)
    lang = await asyncio.to_thread(get_lang, update)

    ADMIN_ID = int(os.getenv("ADMIN_ID", "-1"))
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
    user = await asyncio.to_thread(get_user, user_id)

    ref_code = user.get("ref_code")
    if not ref_code:
        ref_code = f"ref_{hashlib.sha256(f'{user_id}eurorent2024'.encode()).hexdigest()[:8]}"
        user["ref_code"] = ref_code
        await asyncio.to_thread(save_user, user_id, user)

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
    lang = await asyncio.to_thread(get_lang, update)
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
    lang = await asyncio.to_thread(get_lang, update)
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
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            max_tokens=400,
        )
        answer = response.choices[0].message.content
        if not answer:
            answer = "Не удалось сформировать ответ."
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"FAQ error: {e}")
        await update.message.reply_text("❌ Не удалось ответить. Попробуйте позже.")
