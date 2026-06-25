import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GOOGLE_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and GEMINI_API_KEY environment variables")

client = genai.Client(api_key=GOOGLE_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running 24/7!", 200

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
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=full_prompt
        )
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

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask started in background")

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Starting bot polling in main thread...")
    application.run_polling()