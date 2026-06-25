import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8603905857:AAFENhR1ChJ-inEO7u4umx35tKAaQTLjTAs")
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBAceN2YiNCO5yqJX-bqu14H9-BVFM3jSU")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

SYSTEM_PROMPT = """
Ты — профессиональный помощник для экспатов по аренде жилья во всей Европе. 
Твоя задача — получить текст объявления и выдать структурированную справку на русском языке.
Шаг 1. Определи страну.
Шаг 2. Выдай 4 раздела: «Чистый перевод», «Что включено в цену», «Требуемые документы», «Скрытые риски».
В конце поставь оценку от 1 до 10 и дай совет.
"""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    if not user_text:
        await update.message.reply_text("Отправьте текст объявления.")
        return

    await update.message.reply_text("Анализирую объявление через Gemini...")

    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nВот текст объявления: {user_text}"
        response = model.generate_content(full_prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот для разбора объявлений по аренде в Европе.\n"
        "Пришли мне текст объявления."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Скопируй текст объявления и отправь его мне.")

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == "__main__":
    main()