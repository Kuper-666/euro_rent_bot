import os
import logging
import threading
from flask import Flask
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and GEMINI_API_KEY environment variables")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

SYSTEM_PROMPT = """
Ты — профессиональный помощник для экспатов по аренде жилья во всей Европе. 
Твоя задача — получить текст объявления и выдать структурированную справку на русском языке (или английском по умолчанию).

Шаг 1. Определи страну по языку и терминам.
Шаг 2. Выдай 4 раздела:
1. «Чистый перевод» — переведи текст, расшифруй местные термины.
2. «Что включено в цену» — детализированный перечень (Kalt/Nebenkosten и т.д.).
3. «Требуемые документы» — что просят в этой стране (Schufa, Garant и т.д.).
4. «Скрытые риски и нюансы» — фейки, высота потолков, депозит, ограничения.
В конце поставь оценку от 1 до 10 и дай совет: связываться или нет.
Используй жирный шрифт и маркированные списки.
"""

app = Flask(__name__)

@app.route("/")
def health():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    if not user_text:
        await update.message.reply_text("Пожалуйста, отправьте текст объявления или ссылку.")
        return

    await update.message.reply_text("🕐 Анализирую объявление... Это займет 5-10 секунд.")

    try:
        response = model.generate_content(
            SYSTEM_PROMPT + "\n\nВот текст объявления: " + user_text
        )
        answer = response.text
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Я бот для разбора объявлений по аренде в Европе.\n\n"
        "Просто пришли мне текст объявления или ссылку, и я сделаю детальный разбор."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Как использовать:\n"
        "1. Скопируй текст объявления с ImmoScout, Rightmove, Idealista и т.д.\n"
        "2. Отправь его мне.\n"
        "3. Я сам определю страну и выдам полный анализ с терминами и рисками."
    )

def main() -> None:
    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()