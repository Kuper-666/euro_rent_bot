import os
import json
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

DATA_FILE = "users_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and GROQ_API_KEY environment variables")

client = Groq(api_key=GROQ_API_KEY)

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
    user_id = str(update.effective_user.id)
    user_text = update.message.text

    if not user_text:
        await update.message.reply_text("Отправь текст объявления.")
        return

    data = load_data()
    if user_id not in data:
        data[user_id] = {"count": 0, "paid": False}

    if not data[user_id]["paid"] and data[user_id]["count"] >= 3:
        await update.message.reply_text(
            "⚠️ Вы использовали все 3 бесплатных проверки.\n\n"
            "Чтобы продолжить пользоваться ботом, оплатите разовый доступ:\n"
            "💳 **3€**  (или Revolut).\n\n"
            "👉 После оплаты напишите мне команду **/pay_done** в этом чате, и я разблокирую вас навсегда / на месяц."
        )
        return

    await update.message.reply_text("🕐 Анализирую через Groq...")

    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nВот текст объявления: {user_text}"
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}]
        )
        await update.message.reply_text(response.choices[0].message.content)

        data[user_id]["count"] += 1
        save_data(data)

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

async def pay_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id in data:
        data[user_id]["paid"] = True
        save_data(data)
        await update.message.reply_text("✅ Оплата подтверждена! Теперь у вас неограниченный доступ.")
    else:
        await update.message.reply_text("Вы еще не использовали бота. Сначала отправьте одно объявление, потом оплачивайте.")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask started in background")

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("pay_done", pay_done))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Starting bot polling in main thread...")
    application.run_polling()