import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GOOGLE_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and GEMINI_API_KEY environment variables")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)

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

    await update.message.reply_text("🕐 Анализирую объявление через Gemini...")

    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nВот текст объявления: {user_text}"
        response = model.generate_content(full_prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 Привет! Я бот для разбора объявлений по аренде в Европе.\nПросто пришли мне текст объявления.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Скопируй текст объявления и отправь его мне.")

application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        json_data = request.get_json()
        update = Update.de_json(json_data, application.bot)
        asyncio.run(application.process_update(update))
        return "OK", 200
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running 24/7!", 200

if __name__ == "__main__":
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://euro-rent-bot.onrender.com")

    async def set_webhook():
        await application.bot.set_webhook(url=f"{render_url}/webhook")
        logging.info(f"Webhook set to {render_url}/webhook")

    asyncio.run(set_webhook())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))