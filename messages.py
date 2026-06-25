from config import AFFILIATE_REVOLUT, AFFILIATE_WISE

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
            "💳 *Пакеты и цены*\n\n"
            "🔹 *Разовый* — 3€ за 1 проверку\n"
            "▸ Оплатить: /pay_3\n\n"
            "💎 *Эконом* — 9€ за 5 проверок \\(экономия 40%\\)\n"
            "▸ Оплатить: /pay_9\n\n"
            "👑 *Профи* — 19€ за безлимит на месяц\n"
            "▸ Оплатить: /pay_19\n\n"
            "💸 *Как оплатить*\n"
            "Нажми команду выше — получишь ссылку на оплату через Revolut\\. После оплаты напиши соответствующую команду /pay_done_\\*\\, чтобы разблокировать доступ\\.\n\n"
            "🏦 *Нужен европейский счёт для оплаты депозита?*\n"
            "Откройте [Revolut]({}) или [Wise]({}) по моей ссылке и получите бонус\\!\n\n"
            "✅ *Готов начать?*\n"
            "Просто пришли мне любое объявление прямо в этот чат\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "analyzing": "⏳ Анализирую объявление...",
        "fetching_url": "🌐 Открываю ссылку...",
        "ocr_processing": "🔍 Распознаю текст со скриншота...",
        "limit_reached": (
            "⚠️ *Лимит бесплатных проверок*\n\n"
            "Вы использовали все 3 бесплатные проверки\\.\n\n"
            "💳 *Выберите пакет:*\n\n"
            "🔹 *Разовый* — 3€ за 1 проверку → /pay_3\n"
            "💎 *Эконом* — 9€ за 5 проверок \\(\\-40%\\) → /pay_9\n"
            "👑 *Профи* — 19€ за безлимит на месяц → /pay_19\n\n"
            "После оплаты напишите команду */pay_done_\\**\\."
        ),
        "pay_3": (
            "💳 *Пакет «Разовый» — 3€*\n\n"
            "1 проверка объявления\n\n"
            "👉 Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=300\n\n"
            "После оплаты напишите */pay_done_3*\\."
        ),
        "pay_9": (
            "💎 *Пакет «Эконом» — 9€*\n\n"
            "5 проверок объявлений \\(экономия 40%\\)\n\n"
            "👉 Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "После оплаты напишите */pay_done_9*\\."
        ),
        "pay_19": (
            "👑 *Пакет «Профи» — 19€*\n\n"
            "Безлимитные проверки на 1 месяц\n\n"
            "👉 Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\n"
            "После оплаты напишите */pay_done_19*\\."
        ),
        "pay_done_3": "✅ *Оплата подтверждена!*\n\nВам добавлена 1 проверка\\. Осталось: *{}*\\.",
        "pay_done_9": "✅ *Оплата подтверждена!*\n\nВам добавлено 5 проверок\\. Осталось: *{}*\\.",
        "pay_done_19": "✅ *Оплата подтверждена!*\n\nБезлимитный доступ на месяц активирован 🎉",
        "pay_not_used": "Вы ещё не использовали бота\\. Сначала отправьте объявление, потом оплачивайте\\.",
        "no_balance": "❌ У вас нет доступных проверок\\. Купите пакет: /help",
        "error": "❌ Ошибка: {}",
        "send_listing": "Отправь текст объявления или ссылку\\.",
        "share_text": "📋 *Поделиться с другом:*",
        "analysis_done": "✅ *Анализ готов!*",
        "affiliate_footer": (
            "\n\n🏦 *Нужен европейский счёт?*\n"
            "Откройте [Revolut]({}) или [Wise]({}) — получите бонус\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
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
            "💳 *Пакети та ціни*\n\n"
            "🔹 *Разовий* — 3€ за 1 перевірку\n"
            "▸ Оплатити: /pay_3\n\n"
            "💎 *Економ* — 9€ за 5 перевірок \\(економія 40%\\)\n"
            "▸ Оплатити: /pay_9\n\n"
            "👑 *Профі* — 19€ за безліміт на місяць\n"
            "▸ Оплатити: /pay_19\n\n"
            "💸 *Як оплатити*\n"
            "Натисніть команду вище — отримаєте посилання на оплату через Revolut\\. Після оплати напишіть відповідну команду /pay_done_\\*\\, щоб розблокувати доступ\\.\n\n"
            "🏦 *Потрібен європейський рахунок для оплати депозиту?*\n"
            "Відкрийте [Revolut]({}) або [Wise]({}) за моїм посиланням і отримайте бонус\\!\n\n"
            "✅ *Готові почати?*\n"
            "Просто пришліть мені будь\\-яке оголошення прямо в цей чат\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "analyzing": "⏳ Аналізую оголошення...",
        "fetching_url": "🌐 Відкриваю посилання...",
        "ocr_processing": "🔍 Розпізнаю текст зі скріншота...",
        "limit_reached": (
            "⚠️ *Ліміт безкоштовних перевірок*\n\n"
            "Ви використали всі 3 безкоштовні перевірки\\.\n\n"
            "💳 *Оберіть пакет:*\n\n"
            "🔹 *Разовий* — 3€ за 1 перевірку → /pay_3\n"
            "💎 *Економ* — 9€ за 5 перевірок \\(\\-40%\\) → /pay_9\n"
            "👑 *Профі* — 19€ за безліміт на місяць → /pay_19\n\n"
            "Після оплати напишіть команду */pay_done_\\**\\."
        ),
        "pay_3": (
            "💳 *Пакет «Разовий» — 3€*\n\n"
            "1 перевірка оголошення\n\n"
            "👉 Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=300\n\n"
            "Після оплати напишіть */pay_done_3*\\."
        ),
        "pay_9": (
            "💎 *Пакет «Економ» — 9€*\n\n"
            "5 перевірок оголошень \\(економія 40%\\)\n\n"
            "👉 Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "Після оплати напишіть */pay_done_9*\\."
        ),
        "pay_19": (
            "👑 *Пакет «Профі» — 19€*\n\n"
            "Безлімітні перевірки на 1 місяць\n\n"
            "👉 Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\n"
            "Після оплати напишіть */pay_done_19*\\."
        ),
        "pay_done_3": "✅ *Оплата підтверджена!*\n\nВам додано 1 перевірку\\. Залишилось: *{}*\\.",
        "pay_done_9": "✅ *Оплата підтверджена!*\n\nВам додано 5 перевірок\\. Залишилось: *{}*\\.",
        "pay_done_19": "✅ *Оплата підтверджена!*\n\nБезлімітний доступ на місяць активовано 🎉",
        "pay_not_used": "Ви ще не користувались ботом\\. Спочатку надішліть оголошення, потім оплачуйте\\.",
        "no_balance": "❌ У вас немає доступних перевірок\\. Купіть пакет: /help",
        "error": "❌ Помилка: {}",
        "send_listing": "Надішліть текст оголошення або посилання\\.",
        "share_text": "📋 *Поділитися з другом:*",
        "analysis_done": "✅ *Аналіз готовий!*",
        "affiliate_footer": (
            "\n\n🏦 *Потрібен європейський рахунок?*\n"
            "Відкрийте [Revolut]({}) або [Wise]({}) — отримайте бонус\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "system_prompt": (
            "Ти — професійний помічник для експатів по оренді житла в Європі. "
            "Відповідай українською мовою.\n\n"
            "Формат відповіді ОБОВ'ЯЗКОВО в Telegram Markdown:\n"
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
            "💳 *Packages & Pricing*\n\n"
            "🔹 *One\\-time* — €3 for 1 check\n"
            "▸ Pay: /pay_3\n\n"
            "💎 *Economy* — €9 for 5 checks \\(save 40%\\)\n"
            "▸ Pay: /pay_9\n\n"
            "👑 *Pro* — €19 for unlimited access per month\n"
            "▸ Pay: /pay_19\n\n"
            "💸 *How to pay*\n"
            "Tap the command above — you'll get a Revolut payment link\\. After paying, send the matching /pay_done_\\* command to unlock\\.\n\n"
            "🏦 *Need a European bank account for the deposit?*\n"
            "Open [Revolut]({}) or [Wise]({}) via my link and get a bonus\\!\n\n"
            "✅ *Ready to start?*\n"
            "Just send me any listing right in this chat\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "analyzing": "⏳ Analyzing listing...",
        "fetching_url": "🌐 Opening link...",
        "ocr_processing": "🔍 Reading text from screenshot...",
        "limit_reached": (
            "⚠️ *Free Check Limit Reached*\n\n"
            "You've used all 3 free checks\\.\n\n"
            "💳 *Choose a package:*\n\n"
            "🔹 *One\\-time* — €3 for 1 check → /pay_3\n"
            "💎 *Economy* — €9 for 5 checks \\(\\-40%\\) → /pay_9\n"
            "👑 *Pro* — €19 for unlimited/month → /pay_19\n\n"
            "After payment, send the matching */pay_done_\\**command\\."
        ),
        "pay_3": (
            "💳 *Package «One\\-time» — €3*\n\n"
            "1 listing check\n\n"
            "👉 Pay here: https://revolut.me/radik5f35?currency=EUR&amount=300\n\n"
            "After payment, send */pay_done_3*\\."
        ),
        "pay_9": (
            "💎 *Package «Economy» — €9*\n\n"
            "5 listing checks \\(save 40%\\)\n\n"
            "👉 Pay here: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "After payment, send */pay_done_9*\\."
        ),
        "pay_19": (
            "👑 *Package «Pro» — €19*\n\n"
            "Unlimited checks for 1 month\n\n"
            "👉 Pay here: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\n"
            "After payment, send */pay_done_19*\\."
        ),
        "pay_done_3": "✅ *Payment confirmed!*\n\n1 check added\\. Remaining: *{}*\\.",
        "pay_done_9": "✅ *Payment confirmed!*\n\n5 checks added\\. Remaining: *{}*\\.",
        "pay_done_19": "✅ *Payment confirmed!*\n\nUnlimited access for 1 month activated 🎉",
        "pay_not_used": "You haven't used the bot yet\\. Send a listing first, then pay\\.",
        "no_balance": "❌ No checks remaining\\. Buy a package: /help",
        "error": "❌ Error: {}",
        "send_listing": "Send a listing text or link\\.",
        "share_text": "📋 *Share with a friend:*",
        "analysis_done": "✅ *Analysis complete!*",
        "affiliate_footer": (
            "\n\n🏦 *Need a European bank account?*\n"
            "Open [Revolut]({}) or [Wise]({}) — get a bonus\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
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
            "💳 *Pakete & Preise*\n\n"
            "🔹 *Einmalig* — 3€ für 1 Prüfung\n"
            "▸ Bezahlen: /pay_3\n\n"
            "💎 *Economy* — 9€ für 5 Prüfungen \\(\\-40%\\)\n"
            "▸ Bezahlen: /pay_9\n\n"
            "👑 *Pro* — 19€ für unbegrenzten Zugang pro Monat\n"
            "▸ Bezahlen: /pay_19\n\n"
            "💸 *Wie bezahlen?*\n"
            "Drücke den Befehl oben — du erhältst einen Revolut\\-Zahlungslink\\. Nach der Zahlung sende den passenden /pay_done_\\* Befehl, um den Zugang freizuschalten\\.\n\n"
            "🏦 *Benötigst du ein europäisches Bankkonto für die Kaution?*\n"
            "Eröffne [Revolut]({}) oder [Wise]({}) über meinen Link und erhalte ein Bonus\\!\n\n"
            "✅ *Bereit loszulegen?*\n"
            "Schick mir einfach ein Angebot direkt in diesen Chat\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "analyzing": "⏳ Analysiere Angebot...",
        "fetching_url": "🌐 Öffne Link...",
        "ocr_processing": "🔍 Erkenne Text vom Screenshot...",
        "limit_reached": (
            "⚠️ *Kostenlose Prüfungen aufgebraucht*\n\n"
            "Du hast alle 3 kostenlosen Prüfungen genutzt\\.\n\n"
            "💳 *Wähle ein Paket:*\n\n"
            "🔹 *Einmalig* — 3€ für 1 Prüfung → /pay_3\n"
            "💎 *Economy* — 9€ für 5 Prüfungen \\(\\-40%\\) → /pay_9\n"
            "👑 *Pro* — 19€ für unbegrenzt/Monat → /pay_19\n\n"
            "Nach der Zahlung sende den passenden */pay_done_\\**Befehl\\."
        ),
        "pay_3": (
            "💳 *Paket «Einmalig» — 3€*\n\n"
            "1 Angebotsprüfung\n\n"
            "👉 Hier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=300\n\n"
            "Nach der Zahlung */pay_done_3* senden\\."
        ),
        "pay_9": (
            "💎 *Paket «Economy» — 9€*\n\n"
            "5 Angebotsprüfungen \\(\\-40%\\)\n\n"
            "👉 Hier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "Nach der Zahlung */pay_done_9* senden\\."
        ),
        "pay_19": (
            "👑 *Paket «Pro» — 19€*\n\n"
            "Unbegrenzte Prüfungen für 1 Monat\n\n"
            "👉 Hier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\n"
            "Nach der Zahlung */pay_done_19* senden\\."
        ),
        "pay_done_3": "✅ *Zahlung bestätigt!*\n\n1 Prüfung hinzugefügt\\. Verbleibend: *{}*\\.",
        "pay_done_9": "✅ *Zahlung bestätigt!*\n\n5 Prüfungen hinzugefügt\\. Verbleibend: *{}*\\.",
        "pay_done_19": "✅ *Zahlung bestätigt!*\n\nUnbegrenzter Zugang für 1 Monat aktiviert 🎉",
        "pay_not_used": "Du hast den Bot noch nicht benutzt\\. Schick zuerst ein Angebot\\.",
        "no_balance": "❌ Keine Prüfungen übrig\\. Kaufe ein Paket: /help",
        "error": "❌ Fehler: {}",
        "send_listing": "Schick einen Angebotstext oder Link\\.",
        "share_text": "📋 *Mit einem Freund teilen:*",
        "analysis_done": "✅ *Analyse abgeschlossen!*",
        "affiliate_footer": (
            "\n\n🏦 *Benötigst du ein europäisches Bankkonto?*\n"
            "Eröffne [Revolut]({}) oder [Wise]({}) — erhalte ein Bonus\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
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
            "💳 *Pakiety i ceny*\n\n"
            "🔹 *Jednorazowy* — 3€ za 1 sprawdzenie\n"
            "▸ Zapłać: /pay_3\n\n"
            "💎 *Economy* — 9€ za 5 sprawdzeń \\(\\-40%\\)\n"
            "▸ Zapłać: /pay_9\n\n"
            "👑 *Pro* — 19€ za nieograniczony dostęp na miesiąc\n"
            "▸ Zapłać: /pay_19\n\n"
            "💸 *Jak zapłacić?*\n"
            "Naciśnij komendę powyżej — otrzymasz link do płatności przez Revolut\\. Po opłaceniu wyślij odpowiednią komendę /pay_done_\\*, żeby odblokować dostęp\\.\n\n"
            "🏦 *Potrzebujesz europejskiego konta bankowego do wpłaty kaucji?*\n"
            "Otwórz [Revolut]({}) lub [Wise]({}) przez mój link i otrzymaj bonus\\!\n\n"
            "✅ *Gotowy, żeby zacząć?*\n"
            "Po prostu wyślij mi jakąkolwiek ofertęprosto na ten czat\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "analyzing": "⏳ Analizuję ofertę...",
        "fetching_url": "🌐 Otwieram link...",
        "ocr_processing": "🔍 Rozpoznaję tekst ze zrzutu...",
        "limit_reached": (
            "⚠️ *Wyczerpane darmowe sprawdzenia*\n\n"
            "Wykorzystałeś wszystkie 3 darmowe sprawdzenia\\.\n\n"
            "💳 *Wybierz pakiet:*\n\n"
            "🔹 *Jednorazowy* — 3€ za 1 sprawdzenie → /pay_3\n"
            "💎 *Economy* — 9€ za 5 sprawdzeń \\(\\-40%\\) → /pay_9\n"
            "👑 *Pro* — 19€ za nieograniczony/miesiąc → /pay_19\n\n"
            "Po opłaceniu wyślij passującą komendę */pay_done_\\**\\."
        ),
        "pay_3": (
            "💳 *Pakiet «Jednorazowy» — 3€*\n\n"
            "1 sprawdzenie oferty\n\n"
            "👉 Zapłać tutaj: https://revolut.me/radik5f35?currency=EUR&amount=300\n\n"
            "Po opłaceniu wyślij */pay_done_3*\\."
        ),
        "pay_9": (
            "💎 *Pakiet «Economy» — 9€*\n\n"
            "5 sprawdzeń ofert \\(\\-40%\\)\n\n"
            "👉 Zapłać tutaj: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "Po opłaceniu wyślij */pay_done_9*\\."
        ),
        "pay_19": (
            "👑 *Pakiet «Pro» — 19€*\n\n"
            "Nieograniczone sprawdzenia na 1 miesiąc\n\n"
            "👉 Zapłać tutaj: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\n"
            "Po opłaceniu wyślij */pay_done_19*\\."
        ),
        "pay_done_3": "✅ *Płatność potwierdzona!*\n\nDodano 1 sprawdzenie\\. Pozostało: *{}*\\.",
        "pay_done_9": "✅ *Płatność potwierdzona!*\n\nDodano 5 sprawdzeń\\. Pozostało: *{}*\\.",
        "pay_done_19": "✅ *Płatność potwierdzona!*\n\nNieograniczony dostęp na miesiąc aktywowany 🎉",
        "pay_not_used": "Nie korzystałeś jeszcze z bota\\. Najpierw wyślij ofertę\\.",
        "no_balance": "❌ Brak dostępnych sprawdzeń\\. Kup pakiet: /help",
        "error": "❌ Błąd: {}",
        "send_listing": "Wyślij tekst oferty lub link\\.",
        "share_text": "📋 *Podziel się z kolegą:*",
        "analysis_done": "✅ *Analiza gotowa!*",
        "affiliate_footer": (
            "\n\n🏦 *Potrzebujesz europejskiego konta bankowego?*\n"
            "Otwórz [Revolut]({}) lub [Wise]({}) — otrzymaj bonus\\!"
        ).format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
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


def get_msg(lang: str, key: str) -> str:
    return MESSAGES.get(lang, MESSAGES[DEFAULT_LANG]).get(key, MESSAGES[DEFAULT_LANG].get(key, ""))
