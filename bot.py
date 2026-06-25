import os
import json
import logging
import re
import threading
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request
import requests
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
from io import BytesIO
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and GROQ_API_KEY environment variables")

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running 24/7!", 200

MESSAGES = {
    "ru": {
        "start": (
            "👋 *Привет! Я бот для разбора объявлений об аренде в Европе.*\n\n"
            "🔑 Просто отправь мне текст или ссылку с объявлением — я сделаю полный разбор\\.\n\n"
            "💡 *Чтобы узнать подробности о работе, ценах и бесплатном лимите — нажми* /help\\."
        ),
        "help": (
            "🤖 *ExpatRentBot — твой умный помощник по аренде в Европе*\n\n"
            "🏠 *Что я умею?*\n"
            "Я анализирую объявления о съёме жилья\\. Перевожу текст, нахожу скрытые платежи \\(Nebenkosten, Service Charge\\), проверяю, какие документы нужны, и выявляю мошеннические риски\\.\n\n"
            "📝 *Как работать со мной?*\n"
            "Просто *скопируй ссылку* на объявление \\(например, с ImmoScout24, Rightmove, Idealista\\) или *вставь текст* объявления прямо сюда\\. Я сам всё проанализирую\\.\n\n"
            "🎁 *Бесплатный тест\\-драйв*\n"
            "Ты можешь протестировать меня на **3 объявлениях абсолютно бесплатно**, чтобы убедиться в моей полезности\\.\n\n"
            "💳 *Цены и оплата*\n"
            "После бесплатного лимита:\n"
            "• Разовый анализ — *3€*\n"
            "• Безлимитный доступ на месяц — *9€*\n\n"
            "💸 *Как оплатить*\n"
            "Оплата принимается через Revolut \\(ссылка будет отправлена после исчерпания бесплатного лимита\\)\\.\n"
            "*После оплаты обязательно напиши команду* /pay_done, чтобы я разблокировал тебе доступ\\.\n\n"
            "✅ *Готов начать?*\n"
            "Просто пришли мне любое объявление прямо в этот чат\\!"
        ),
        "analyzing": "⏳ Анализирую объявление...",
        "fetching_url": "🌐 Открываю ссылку...",
        "ocr_processing": "🔍 Распознаю текст со скриншота...",
        "limit_reached": (
            "⚠️ *Лимит бесплатных проверок*\n\n"
            "Вы использовали 3 бесплатные проверки.\n\n"
            "💳 *Варианты оплаты:*\n\n"
            "🔹 *3€* — разовая проверка\n"
            "🔹 *9€* — безлимит навсегда \\(\\*\\)\\*\n\n"
            "👉 Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=300\n"
            "👉 Безлимит: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "После оплаты напишите */pay_done*\\."
        ),
        "pay_done": "✅ *Оплата подтверждена!*\n\nТеперь у вас безлимитный доступ\\. Пользуйтесь на здоровье 🎉",
        "pay_not_used": "Вы ещё не использовали бота\\. Сначала отправьте объявление, потом оплачивайте\\.",
        "error": "❌ Ошибка: {}",
        "send_listing": "Отправь текст объявления или ссылку\\.",
        "share_text": "📋 *Поделиться с другом:*",
        "analysis_done": "✅ *Анализ готов!*",
        "system_prompt": (
            "Ты — профессиональный помощник для экспатов по аренде жилья в Европе. "
            "Отвечай на русском языке.\n\n"
            "Формат ответа ОБЯЗАТЕЛЬНО в Telegram Markdown:\n"
            "- Используй *жирный* для заголовков\n"
            "- Добавляй эмодзи: 🏠 💰 ⚠️ ✅ 📋 🔍 💡\n"
            "- Разбивай текст на логические блоки\n"
            "- В конце ставь оценку от 1 до 10 и давай совет\n\n"
            "Структура ответа:\n"
            "🏠 *Чистый перевод*\n"
            "💰 *Что включено в цену*\n"
            "📋 *Требуемые документы*\n"
            "⚠️ *Скрытые риски*\n"
            "💡 *Оценка и совет*"
        ),
    },
    "uk": {
        "start": (
            "👋 *Привіт! Я бот для розбору оголошень про оренду в Європі.*\n\n"
            "🔑 Просто надішліть мені текст або посилання на оголошення — я зроблю повний розбір\\.\n\n"
            "💡 *Щоб дізнатися подробиці про роботу, ціни та безкоштовний ліміт — натисніть* /help\\."
        ),
        "help": (
            "🤖 *ExpatRentBot — твій розумний помічник по оренді в Європі*\n\n"
            "🏠 *Що я вмію?*\n"
            "Я аналізую оголошення про оренду житла\\. Перекладаю текст, знаходжу приховані платежі \\(Nebenkosten, Service Charge\\), перевіряю, які документи потрібні, і виявляю шахрайські ризики\\.\n\n"
            "📝 *Як працювати зі мною?*\n"
            "Просто *скопіюйте посилання* на оголошення \\(наприклад, з ImmoScout24, Rightmove, Idealista\\) або *вставте текст* оголошення прямо сюди\\. Я сам все проаналізую\\.\n\n"
            "🎁 *Безкоштовний тест\\-драйв*\n"
            "Ви можете протестувати мене на **3 оголошеннях абсолютно безкоштовно**, щоб переконатися в моїй корисності\\.\n\n"
            "💳 *Ціни та оплата*\n"
            "Після безкоштовного ліміту:\n"
            "• Разовий аналіз — *3€*\n"
            "• Безлімітний доступ на місяць — *9€*\n\n"
            "💸 *Як оплатити*\n"
            "Оплата приймається через Revolut \\(посилання буде відправлено після вичерпання безкоштовного ліміту\\)\\.\n"
            "*Після оплати обов'язково напишіть команду* /pay_done, щоб я розблокував вам доступ\\.\n\n"
            "✅ *Готові почати?*\n"
            "Просто пришліть мені будь\\-яке оголошення прямо в цей чат\\!"
        ),
        "analyzing": "⏳ Аналізую оголошення...",
        "fetching_url": "🌐 Відкриваю посилання...",
        "ocr_processing": "🔍 Розпізнаю текст зі скріншота...",
        "limit_reached": (
            "⚠️ *Ліміт безкоштовних перевірок*\n\n"
            "Ви використали 3 безкоштовні перевірки\\.\n\n"
            "💳 *Варіанти оплати:*\n\n"
            "🔹 *3€* — разова перевірка\n"
            "🔹 *9€* — безліміт назавжди\\(\\*\\)\\*\n\n"
            "👉 Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=300\n"
            "👉 Безліміт: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "Після оплати напишіть */pay_done*\\."
        ),
        "pay_done": "✅ *Оплата підтверджена!*\n\nТепер у вас безлімітний доступ\\. Користуйтесь на здоров'я 🎉",
        "pay_not_used": "Ви ще не користувались ботом\\. Спочатку надішліть оголошення, потім оплачуйте\\.",
        "error": "❌ Помилка: {}",
        "send_listing": "Надішліть текст оголошення або посилання\\.",
        "share_text": "📋 *Поділитися з другом:*",
        "analysis_done": "✅ *Аналіз готовий!*",
        "system_prompt": (
            "Ти — професійний помічник для експатів по оренді житла в Європі. "
            "Відповідай українською мовою.\n\n"
            "Формат відповіДі ОБОВ'ЯЗКОВО в Telegram Markdown:\n"
            "- Використовуй *жирний* для заголовків\n"
            "- Додавай емодзи: 🏠 💰 ⚠️ ✅ 📋 🔍 💡\n"
            "- Розбивай текст на логічні блоки\n"
            "- В кінці став оцінку від 1 до 10 і давай пораду\n\n"
            "Структура відповіді:\n"
            "🏠 *Чистий переклад*\n"
            "💰 *Що включено в ціну*\n"
            "📋 *Необхідні документи*\n"
            "⚠️ *Приховані ризики*\n"
            "💡 *Оцінка і порада*"
        ),
    },
    "en": {
        "start": (
            "👋 *Hi! I'm your smart rental listing assistant for Europe.*\n\n"
            "🔑 Just send me a text or link with a listing — I'll do a full breakdown\\.\n\n"
            "💡 *To learn how I work, my pricing, and the free tier — tap* /help\\."
        ),
        "help": (
            "🤖 *ExpatRentBot — your smart rental assistant in Europe*\n\n"
            "🏠 *What do I do?*\n"
            "I analyze rental listings\\. I translate text, find hidden fees \\(Nebenkosten, Service Charge\\), check required documents, and flag scam risks\\.\n\n"
            "📝 *How to use me?*\n"
            "Simply *copy a link* to a listing \\(e.g\\. from ImmoScout24, Rightmove, Idealista\\) or *paste the listing text* right here\\. I'll analyze everything for you\\.\n\n"
            "🎁 *Free test drive*\n"
            "You can test me on **3 listings completely free** to see how useful I am\\.\n\n"
            "💳 *Pricing & Payment*\n"
            "After the free limit:\n"
            "• One\\-time analysis — *€3*\n"
            "• Unlimited access for a month — *€9*\n\n"
            "💸 *How to pay*\n"
            "Payment is accepted via Revolut \\(link will be sent after the free limit is reached\\)\\.\n"
            "*After payment, make sure to send the command* /pay_done so I can unlock your access\\.\n\n"
            "✅ *Ready to start?*\n"
            "Just send me any listing right in this chat\\!"
        ),
        "analyzing": "⏳ Analyzing listing...",
        "fetching_url": "🌐 Opening link...",
        "ocr_processing": "🔍 Reading text from screenshot...",
        "limit_reached": (
            "⚠️ *Free Check Limit Reached*\n\n"
            "You've used all 3 free checks\\.\n\n"
            "💳 *Payment options:*\n\n"
            "🔹 *€3* — one\\-time check\n"
            "🔹 *€9* — unlimited forever\\*\\*\n\n"
            "👉 Pay here: https://revolut.me/radik5f35?currency=EUR&amount=300\n"
            "👉 Unlimited: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "After payment, send */pay_done*\\."
        ),
        "pay_done": "✅ *Payment confirmed!*\n\nYou now have unlimited access\\. Enjoy 🎉",
        "pay_not_used": "You haven't used the bot yet\\. Send a listing first, then pay\\.",
        "error": "❌ Error: {}",
        "send_listing": "Send a listing text or link\\.",
        "share_text": "📋 *Share with a friend:*",
        "analysis_done": "✅ *Analysis complete!*",
        "system_prompt": (
            "You are a professional rental assistant for expats across Europe. "
            "Respond in English.\n\n"
            "Format your response in Telegram Markdown:\n"
            "- Use *bold* for headers\n"
            "- Add emojis: 🏠 💰 ⚠️ ✅ 📋 🔍 💡\n"
            "- Break text into logical blocks\n"
            "- End with a score from 1 to 10 and give advice\n\n"
            "Response structure:\n"
            "🏠 *Clean Translation*\n"
            "💰 *What's Included in Price*\n"
            "📋 *Required Documents*\n"
            "⚠️ *Hidden Risks*\n"
            "💡 *Score and Advice*"
        ),
    },
    "de": {
        "start": (
            "👋 *Hallo! Ich bin dein smarter Miet\\-Assistent für Europa.*\n\n"
            "🔑 Schick mir einfach einen Text oder Link mit einem Angebot — ich mache eine vollständige Analyse\\.\n\n"
            "💡 *Um Details zu meinem Ablauf, Preisen und dem kostenlosen Limit zu erfahren, drücke* /help\\."
        ),
        "help": (
            "🤖 *ExpatRentBot — dein smarter Miet\\-Assistent in Europa*\n\n"
            "🏠 *Was kann ich?*\n"
            "Ich analysiere Mietangebote\\. Ich übersetze Texte, finde versteckte Kosten \\(Nebenkosten, Service Charge\\), prüfe erforderliche Dokumente und entdecke Betrugsrisiken\\.\n\n"
            "📝 *So funktioniert's:*\n"
            "Kopiere einfach einen *Link* zu einem Angebot \\(z\\.B\\. von ImmoScout24, Rightmove, Idealista\\) oder *füge den Angebotstext* direkt hier ein\\. Ich analysiere alles für dich\\.\n\n"
            "🎁 *Kostenloser Testlauf*\n"
            "Du kannst mich an **3 Angeboten komplett kostenlos testen**, um meine Nützlichkeit zu prüfen\\.\n\n"
            "💳 *Preise & Zahlung*\n"
            "Nach dem kostenlosen Limit:\n"
            "• Einmalige Analyse — *3€*\n"
            "• Unbegrenzter Zugang für einen Monat — *9€*\n\n"
            "💸 *Wie bezahlen?*\n"
            "Zahlung erfolgt über Revolut \\(Link wird nach Erreichen des kostenlosen Limits gesendet\\)\\.\n"
            "*Nach der Zahlung sende unbedingt den Befehl* /pay_done, damit ich dir den Zugang freischalte\\.\n\n"
            "✅ *Bereit loszulegen?*\n"
            "Schick mir einfach ein Angebot direkt in diesen Chat\\!"
        ),
        "analyzing": "⏳ Analysiere Angebot...",
        "fetching_url": "🌐 Öffne Link...",
        "ocr_processing": "🔍 Erkenne Text vom Screenshot...",
        "limit_reached": (
            "⚠️ *Kostenlose Prüfungen aufgebraucht*\n\n"
            "Du hast alle 3 kostenlosen Prüfungen genutzt\\.\n\n"
            "💳 *Zahlungsmöglichkeiten:*\n\n"
            "🔹 *3€* — einmalige Prüfung\n"
            "🔹 *9€* — unbegrenzt für immer\\*\\*\n\n"
            "👉 Hier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=300\n"
            "👉 Unbegrenzt: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "Nach der Zahlung */pay_done* senden\\."
        ),
        "pay_done": "✅ *Zahlung bestätigt!*\n\nDu hast jetzt unbegrenzten Zugang\\. Viel Spaß 🎉",
        "pay_not_used": "Du hast den Bot noch nicht benutzt\\. Schick zuerst ein Angebot\\.",
        "error": "❌ Fehler: {}",
        "send_listing": "Schick einen Angebotstext oder Link\\.",
        "share_text": "📋 *Mit einem Freund teilen:*",
        "analysis_done": "✅ *Analyse abgeschlossen!*",
        "system_prompt": (
            "Du bist ein professioneller Miet\\-Assistent für Expats in ganz Europa. "
            "Antworte auf Deutsch.\n\n"
            "Formatiere deine Antwort in Telegram Markdown:\n"
            "- Nutze *fett* für Überschriften\n"
            "- Füge Emojis hinzu: 🏠 💰 ⚠️ ✅ 📋 🔍 💡\n"
            "- Teile den Text in logische Blöcke\n"
            "- Beende mit einer Bewertung von 1 bis 10\n\n"
            "Antwortstruktur:\n"
            "🏠 *Saubere Übersetzung*\n"
            "💰 *Was im Preis enthalten ist*\n"
            "📋 *Erforderliche Dokumente*\n"
            "⚠️ *Versteckte Risiken*\n"
            "💡 *Bewertung und Empfehlung*"
        ),
    },
    "pl": {
        "start": (
            "👋 *Cześć! Jestem twoim inteligentnym asystentem ofert wynajmu w Europie.*\n\n"
            "🔑 Wyślij mi po prostu tekst lub link z ofertą — zrobię pełną analizę\\.\n\n"
            "💡 *Aby dowiedzieć się więcej o mojej pracy, cenach i darmowym limicie — naciśnij* /help\\."
        ),
        "help": (
            "🤖 *ExpatRentBot — twój inteligentny asystent najmu w Europie*\n\n"
            "🏠 *Co umiem?*\n"
            "Analizuję oferty wynajmu\\. Tłumaczę tekst, znajduję ukryte opłaty \\(Nebenkosten, Service Charge\\), sprawdzam wymagane dokumenty i wykrywam ryzyko oszustwa\\.\n\n"
            "📝 *Jak ze mną współpracować?*\n"
            "Po prostu *skopiuj link* do oferty \\(np\\. z ImmoScout24, Rightmove, Idealista\\) lub *wklej tekst oferty* tutaj\\. Ja wszystko przeanalizuję\\.\n\n"
            "🎁 *Bezpłatny test\\-jazda*\n"
            "Możesz przetestować mnie na **3 ofertach całkowicie za darmo**, żeby przekonać się o mojej przydatności\\.\n\n"
            "💳 *Ceny i płatność*\n"
            "Po wykorzystaniu darmowego limitu:\n"
            "• Pojedyncza analiza — *3€*\n"
            "• Nieograniczony dostęp na miesiąc — *9€*\n\n"
            "💸 *Jak zapłacić?*\n"
            "Płatność odbywa się przez Revolut \\(link zostanie wysłany po osiągnięciu darmowego limitu\\)\\.\n"
            "*Po opłaceniu koniecznie wyślij komendę* /pay_done, żebym odblokował Ci dostęp\\.\n\n"
            "✅ *Gotowy, żeby zacząć?*\n"
            "Po prostu wyślij mi jakąkolwiek ofertęprosto na ten czat\\!"
        ),
        "analyzing": "⏳ Analizuję ofertę...",
        "fetching_url": "🌐 Otwieram link...",
        "ocr_processing": "🔍 Rozpoznaję tekst ze zrzutu...",
        "limit_reached": (
            "⚠️ *Wyczerpane darmowe sprawdzenia*\n\n"
            "Wykorzystałeś wszystkie 3 darmowe sprawdzenia\\.\n\n"
            "💳 *Opcje płatności:*\n\n"
            "🔹 *3€* — jednorazowe sprawdzenie\n"
            "🔹 *9€* — bez limitu na zawsze\\*\\*\n\n"
            "👉 Zapłać tutaj: https://revolut.me/radik5f35?currency=EUR&amount=300\n"
            "👉 Bez limitu: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "Po opłaceniu wyślij */pay_done*\\."
        ),
        "pay_done": "✅ *Płatność potwierdzona!*\n\nMasz teraz nieograniczony dostęp\\. Miłego korzystania 🎉",
        "pay_not_used": "Nie korzystałeś jeszcze z bota\\. Najpierw wyślij ofertę\\.",
        "error": "❌ Błąd: {}",
        "send_listing": "Wyślij tekst oferty lub link\\.",
        "share_text": "📋 *Podziel się z kolegą:*",
        "analysis_done": "✅ *Analiza gotowa!*",
        "system_prompt": (
            "Jesteś profesjonalnym asystentem najmu dla ekspatów w Europie. "
            "Odpowiadaj po polsku.\n\n"
            "Formatuj odpowiedź w Telegram Markdown:\n"
            "- Używaj *pogrubienia* dla nagłówków\n"
            "- Dodawaj emoji: 🏠 💰 ⚠️ ✅ 📋 🔍 💡\n"
            "- Dziel tekst na logiczne bloki\n"
            "- Zakończ oceną od 1 do 10\n\n"
            "Struktura odpowiedzi:\n"
            "🏠 *Czyste tłumaczenie*\n"
            "💰 *Co jest wliczone w cenę*\n"
            "📋 *Wymagane dokumenty*\n"
            "⚠️ *Ukryte ryzyka*\n"
            "💡 *Ocena i rada*"
        ),
    },
}

DEFAULT_LANG = "en"
FREE_LIMIT = 3
PRICE_ONCE = 3
PRICE_UNLIMITED = 9

def get_lang(update: Update) -> str:
    lang_code = update.effective_user.language_code
    if lang_code:
        short = lang_code.split("-")[0].lower()
        if short in MESSAGES:
            return short
    return DEFAULT_LANG

def get_msg(lang: str, key: str) -> str:
    return MESSAGES.get(lang, MESSAGES[DEFAULT_LANG]).get(key, MESSAGES[DEFAULT_LANG].get(key, ""))

def get_keyboard():
    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/help"), KeyboardButton("/pay_done")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_analysis_inline_buttons():
    keyboard = [
        [
            InlineKeyboardButton("📋 Скопировать перевод", callback_data="copy"),
            InlineKeyboardButton("🔍 Ещё одно объявление", callback_data="new"),
        ],
        [
            InlineKeyboardButton("🌐 Поделиться с другом", callback_data="share"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def fetch_url_text(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 10]
        return "\n".join(lines[:200])
    except Exception as e:
        return f"ERROR: {e}"

def ocr_from_photo(photo_bytes: bytes) -> str:
    try:
        image = Image.open(BytesIO(photo_bytes))
        text = pytesseract.image_to_string(image, lang="eng+rus+ukr+deu+pol")
        return text.strip()
    except Exception as e:
        return f"ERROR: {e}"

def is_url(text: str) -> bool:
    return bool(re.match(r'https?://', text.strip()))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    lang = get_lang(update)
    data = load_data()

    if user_id not in data:
        data[user_id] = {"count": 0, "paid": False, "tier": "free"}

    if not data[user_id]["paid"] and data[user_id]["count"] >= FREE_LIMIT:
        await update.message.reply_text(get_msg(lang, "limit_reached"), reply_markup=get_keyboard())
        return

    user_text = update.message.text

    if user_text and is_url(user_text):
        await update.message.reply_text(get_msg(lang, "fetching_url"), reply_markup=get_keyboard())
        listing_text = fetch_url_text(user_text)
    elif user_text:
        listing_text = user_text
    else:
        await update.message.reply_text(get_msg(lang, "send_listing"), reply_markup=get_keyboard())
        return

    await update.message.reply_text(get_msg(lang, "analyzing"), reply_markup=get_keyboard())

    try:
        system_prompt = get_msg(lang, "system_prompt")
        full_prompt = f"{system_prompt}\n\nListing text:\n{listing_text}"
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}]
        )
        result = response.choices[0].message.content

        share_invite = f"\n\n💬 {get_msg(lang, 'share_text')}\nhttps://t.me/{context.bot.username}?start=ref_{user_id}"

        await update.message.reply_text(
            result + share_invite,
            reply_markup=get_analysis_inline_buttons(),
            parse_mode="Markdown"
        )

        data[user_id]["count"] += 1
        save_data(data)

    except Exception as e:
        await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=get_keyboard())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    lang = get_lang(update)
    data = load_data()

    if user_id not in data:
        data[user_id] = {"count": 0, "paid": False, "tier": "free"}

    if not data[user_id]["paid"] and data[user_id]["count"] >= FREE_LIMIT:
        await update.message.reply_text(get_msg(lang, "limit_reached"), reply_markup=get_keyboard())
        return

    await update.message.reply_text(get_msg(lang, "ocr_processing"), reply_markup=get_keyboard())

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        listing_text = ocr_from_photo(bytes(photo_bytes))

        if not listing_text or listing_text.startswith("ERROR"):
            await update.message.reply_text("❌ Не удалось распознать текст. Попробуйте отправить текст или ссылку.", reply_markup=get_keyboard())
            return

        await update.message.reply_text(get_msg(lang, "analyzing"), reply_markup=get_keyboard())

        system_prompt = get_msg(lang, "system_prompt")
        full_prompt = f"{system_prompt}\n\nListing text (from OCR):\n{listing_text}"
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}]
        )
        result = response.choices[0].message.content

        share_invite = f"\n\n💬 {get_msg(lang, 'share_text')}\nhttps://t.me/{context.bot.username}?start=ref_{user_id}"

        await update.message.reply_text(
            result + share_invite,
            reply_markup=get_analysis_inline_buttons(),
            parse_mode="Markdown"
        )

        data[user_id]["count"] += 1
        save_data(data)

    except Exception as e:
        await update.message.reply_text(get_msg(lang, "error").format(e), reply_markup=get_keyboard())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_lang(update)

    if query.data == "new":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(get_msg(lang, "send_listing"), reply_markup=get_keyboard())

    elif query.data == "share":
        bot_username = context.bot.username
        share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=🏠+Европа+Аренда+AI+-+бесплатный+бот+для+разбора+объявлений+по+аренде!"
        await query.message.reply_text(
            f"📤 {get_msg(lang, 'share_text')}\n\n{share_url}",
            reply_markup=get_keyboard()
        )

    elif query.data == "copy":
        await query.answer("Скопируйте текст выше 👆", show_alert=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "start"), reply_markup=get_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "help"), reply_markup=get_keyboard())

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    await update.message.reply_text(get_msg(lang, "limit_reached"), reply_markup=get_keyboard())

async def pay_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()
    lang = get_lang(update)

    if user_id in data:
        data[user_id]["paid"] = True
        data[user_id]["tier"] = "unlimited"
        save_data(data)
        await update.message.reply_text(get_msg(lang, "pay_done"), reply_markup=get_keyboard())
    else:
        await update.message.reply_text(get_msg(lang, "pay_not_used"), reply_markup=get_keyboard())

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
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("pay_done", pay_done))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if WEBHOOK_URL:
        logging.info(f"Starting bot with webhook: {WEBHOOK_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 10000)),
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        )
    else:
        logging.info("Starting bot polling...")
        application.run_polling()
