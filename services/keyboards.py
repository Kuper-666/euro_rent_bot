"""Клавиатуры и утилиты форматирования."""
import os
import json
from telegram import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from utils import get_lang
from messages import get_msg

_pending_listings = {}
PENDING_FILE = "pending_listings.json"


def _load_pending_listings():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_pending_listings(data):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


_KB_LABELS = {
    "ru": {"start": "Старт", "help": "Помощь", "balance": "Баланс", "lang": "Мой язык"},
    "uk": {"start": "Старт", "help": "Допомога", "balance": "Баланс", "lang": "Мова"},
    "en": {"start": "Start", "help": "Help", "balance": "Balance", "lang": "My language"},
    "de": {"start": "Start", "help": "Hilfe", "balance": "Guthaben", "lang": "Sprache"},
    "pl": {"start": "Start", "help": "Pomoc", "balance": "Saldo", "lang": "Język"},
}


def get_keyboard(lang="ru"):
    labels = _KB_LABELS.get(lang, _KB_LABELS["en"])
    keyboard = [
        [KeyboardButton(labels["start"]), KeyboardButton(labels["help"]), KeyboardButton(labels["balance"])],
        [KeyboardButton("PDF"), KeyboardButton("VIP"), KeyboardButton(labels["lang"])],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def kb(update, chat_type=None, lang=None):
    """Reply-keyboard только в личке."""
    if chat_type is None:
        chat_type = update.effective_chat.type if update and update.effective_chat else None
    if chat_type == "private":
        if lang is None:
            lang = get_lang(update) if update else "en"
        return get_keyboard(lang)
    return None


def get_analysis_inline_buttons():
    keyboard = [
        [
            InlineKeyboardButton("📋 Скопировать", callback_data="copy"),
            InlineKeyboardButton("🔍 Ещё одно", callback_data="new"),
        ],
        [
            InlineKeyboardButton("📝 Письмо", callback_data="gen_letter"),
            InlineKeyboardButton("📄 PDF", callback_data="pdf"),
        ],
        [
            InlineKeyboardButton("⭐ В избранное", callback_data="fav_save"),
            InlineKeyboardButton("🌐 Поделиться", callback_data="share"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def split_message(text: str, max_len: int = 4000) -> list:
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts
