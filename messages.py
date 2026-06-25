from config import AFFILIATE_REVOLUT, AFFILIATE_WISE

MESSAGES = {
    "ru": {
        "start": (
            "👋 *Привет! Я EuroRent AI — твой личный детектор по аренде в Европе.*\n\n"
            "🔑 Просто отправь мне ссылку на объявление или скопируй текст — я сделаю полный разбор за 5 секунд\\.\n\n"
            "📌 *Что я умею:*\n"
            "• Перевожу объявление на русский/английский\n"
            "• Показываю скрытые платежи \\(Nebenkosten, Service Charge\\)\n"
            "• Подсказываю, какие документы нужны\n"
            "• Проверяю на мошенников и скам\n\n"
            "🎁 *Бесплатный тест:* 3 проверки без оплаты\\.\n"
            "💸 *После лимита:* 3€ за раз или 9€ за месяц\\.\n\n"
            "💡 *Подробнее — нажми* /help"
        ),
        "help": (
            "🤖 *EuroRent AI — умный помощник по аренде жилья в Европе*\n\n"
            "🏠 *Что я делаю?*\n"
            "Я анализирую объявления о съёме: перевожу текст, вычисляю скрытые комиссии, проверяю, какие документы просят хозяева, и предупреждаю о мошеннических схемах\\.\n\n"
            "📝 *Как мной пользоваться?*\n"
            "Просто *скопируй ссылку* с любого сайта \\(ImmoScout, Rightmove, Idealista, и т\\.д\\.\\) или вставь *текст объявления* прямо сюда\\. Я сам определю страну и выдам полный разбор\\.\n\n"
            "🎁 *Бесплатный тест\\-драйв*\n"
            "Ты можешь проверить **3 объявления абсолютно бесплатно**, чтобы убедиться в моей полезности\\.\n\n"
            "💳 *Пакеты и цены*\n\n"
            "🔹 *Разовый* — 3€ за 1 проверку\n"
            "▸ Оплатить: /pay_3\n\n"
            "💎 *Эконом* — 9€ за 5 проверок \\(экономия 40%\\)\n"
            "▸ Оплатить: /pay_9\n\n"
            "👑 *Профи* — 19€ за безлимит на месяц\n"
            "▸ Оплатить: /pay_19\n\n"
            "📄 *PDF\\-заявление \\(Mieterprofil\\)* — 5€\n"
            "▸ Оплатить: /pdf\n\n"
            "⭐ *VIP\\-подписка* — 15€/мес \\(ежедневные подборки\\)\n"
            "▸ Оплатить: /vip\n\n"
            "💸 *Как оплатить*\n"
            "Нажми команду выше — получишь ссылку на оплату через Revolut\\. После оплаты напиши соответствующую команду /pay_done_\\*\\, чтобы разблокировать доступ\\.\n\n"
            "🏦 *Нужен европейский счёт для оплаты депозита?*\n"
            "Откройте [Revolut]({}) или [Wise]({}) по моей ссылке и получите бонус\\!\n\n"
            "🌐 *Официальная страница:* euro\\-rent\\-bot\\.onrender\\.com\n\n"
            "✅ *Готов начать?*\n"
            "Просто пришли мне любое объявление прямо сейчас\\!"
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
        "pdf_intro": (
            "📄 *Готовое заявление на аренду \\(Mieterprofil\\)*\n\n"
            "Я могу сформировать вам PDF с заполненным заявлением на аренду на немецком/английском языке\\.\n\n"
            "💰 Стоимость: *5€*\n"
            "👉 Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "После оплаты отправьте мне данные:\\.\n"
            "Я попрошу вас заполнить:\n"
            "• Имя и фамилия\n"
            "• Дата рождения\n"
            "• Телефон\n"
            "• Email\n"
            "• Текущий адрес\n"
            "• Работодатель / ИП\n"
            "• Доход (нетто)\n"
            "• Количество жильцов\n\n"
            "После заполнения я сгенерирую PDF и отправлю вам\\."
        ),
        "pdf_need_data": (
            "📝 *Заполните данные для заявления:*\n\n"
            "1\\. Имя и фамилия\n"
            "2\\. Дата рождения\n"
            "3\\. Телефон\n"
            "4\\. Email\n"
            "5\\. Текущий адрес\n"
            "6\\. Работодатель / ИП\n"
            "7\\. Доход \\(нетто/мес\\)\n"
            "8\\. Количество жильцов\n\n"
            "Отправьте все данные одним сообщением, каждый пункт с новой строки\\."
        ),
        "pdf_generating": "📄 Генерирую PDF\\.\\.\\.",
        "pdf_done": "✅ *Готово!* PDF с заявлением на аренду отправлен 👇",
        "pdf_error": "❌ Ошибка при генерации PDF: {}",
        "pay_pdf": (
            "📄 *Оплата PDF \\(Mieterprofil\\) — 5€*\n\n"
            "👉 Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "После оплаты напишите */pay_done_pdf*\\."
        ),
        "pay_done_pdf": "✅ *Оплата подтверждена!*\n\nОтправьте данные для заявления:\\.",
        "vip_intro": (
            "⭐ *VIP-подписка — 15€/мес*\n\n"
            "Ежедневная подборка «горячих» объявлений по вашим критериям\\.\n\n"
            "Что входит:\n"
            "• До 10 проверенных объявлений в день\n"
            "• Фильтр по городу, цене, площади\n"
            "• Предупреждения о мошенниках\n"
            "• Безлимитные проверки\n\n"
            "👉 Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\n"
            "После оплаты напишите */pay_done_vip*\\."
        ),
        "pay_done_vip": (
            "✅ *VIP активирован!*\n\n"
            "⭐ Теперь вы получаете ежедневную подборку\\.\n\n"
            "Отправьте мне критерии поиска:\n"
            "• Город\n"
            "• Макс\\. цена\n"
            "• Мин\\. площадь\n"
            "• Кол\\-во комнат\n\n"
            "Я буду присылать подходящие объявления каждый день!"
        ),
        "vip_ask_criteria": (
            "📝 *Отправьте критерии поиска:*\n\n"
            "• Город\n"
            "• Макс\\. цена \\(€/мес\\)\n"
            "• Мин\\. площадь \\(м²\\)\n"
            "• Кол\\-во комнат\n\n"
            "Пример: Берлин, 800€, 40м², 2 комнаты"
        ),
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
            "👋 *Привіт! Я EuroRent AI — твій особистий детектор оренди в Європі.*\n\n"
            "🔑 Просто надішліть мені посилання на оголошення або скопіюйте текст — я зроблю повний розбір за 5 секунд\\.\n\n"
            "📌 *Що я вмію:*\n"
            "• Перекладаю оголошення українською/англійською\n"
            "• Показую приховані платежі \\(Nebenkosten, Service Charge\\)\n"
            "• Підказую, які документи потрібні\n"
            "• Перевіряю шахраїв та скам\n\n"
            "🎁 *Безкоштовний тест:* 3 перевірки без оплати\\.\n"
            "💸 *Після ліміту:* 3€ за раз або 9€ за місяць\\.\n\n"
            "💡 *Детальніше — натисніть* /help"
        ),
        "help": (
            "🤖 *EuroRent AI — розумний помічник по оренді житла в Європі*\n\n"
            "🏠 *Що я роблю?*\n"
            "Я аналізую оголошення про оренду: перекладаю текст, знаходжу приховані комісії, перевіряю, які документи просять власники, і попереджаю про шахрайські схеми\\.\n\n"
            "📝 *Як мною користуватися?*\n"
            "Просто *скопіюйте посилання* з будь\\-якого сайту \\(ImmoScout, Rightmove, Idealista тощо\\) або вставте *текст оголошення* прямо сюди\\. Я сам визначу країну і видам повний розбір\\.\n\n"
            "🎁 *Безкоштовний тест\\-драйв*\n"
            "Ви можете перевірити **3 оголошення абсолютно безкоштовно**, щоб переконатися в моїй корисності\\.\n\n"
            "💳 *Пакети та ціни*\n\n"
            "🔹 *Разовий* — 3€ за 1 перевірку\n"
            "▸ Оплатити: /pay_3\n\n"
            "💎 *Економ* — 9€ за 5 перевірок \\(економія 40%\\)\n"
            "▸ Оплатити: /pay_9\n\n"
            "👑 *Профі* — 19€ за безліміт на місяць\n"
            "▸ Оплатити: /pay_19\n\n"
            "📄 *PDF\\-заява \\(Mieterprofil\\)* — 5€\n"
            "▸ Оплатити: /pdf\n\n"
            "⭐ *VIP\\-підписка* — 15€/міс \\(щоденні підбірки\\)\n"
            "▸ Оплатити: /vip\n\n"
            "💸 *Як оплатити*\n"
            "Натисніть команду вище — отримаєте посилання на оплату через Revolut\\. Після оплати напишіть відповідну команду /pay_done_\\*\\, щоб розблокувати доступ\\.\n\n"
            "🏦 *Потрібен європейський рахунок для оплати депозиту?*\n"
            "Відкрийте [Revolut]({}) або [Wise]({}) за моїм посиланням і отримайте бонус\\!\n\n"
            "🌐 *Офіційна сторінка:* euro\\-rent\\-bot\\.onrender\\.com\n\n"
            "✅ *Готові почати?*\n"
            "Просто пришліть мені будь\\-яке оголошення прямо зараз\\!"
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
        "pdf_intro": (
            "📄 *Готова заява на оренду \\(Mieterprofil\\)*\n\n"
            "Я можу сформувати вам PDF із заповненою заявою на оренду німецькою/англійською мовою\\.\n\n"
            "💰 Вартість: *5€*\n"
            "👉 Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "Після оплати надішліть мені дані\\.\n"
            "Я попрошу вас заповнити:\n"
            "• Ім'я та прізвище\n"
            "• Дата народження\n"
            "• Телефон\n"
            "• Email\n"
            "• Поточна адреса\n"
            "• Роботодавець / ФОП\n"
            "• Дохід \\(нетто\\)\n"
            "• Кількість мешканців\n\n"
            "Після заповнення я згенерую PDF і надішлю вам\\."
        ),
        "pdf_need_data": (
            "📝 *Заповніть дані для заяви:*\n\n"
            "1\\. Ім'я та прізвище\n"
            "2\\. Дата народження\n"
            "3\\. Телефон\n"
            "4\\. Email\n"
            "5\\. Поточна адреса\n"
            "6\\. Роботодавець / ФОП\n"
            "7\\. Дохід \\(нетто/міс\\)\n"
            "8\\. Кількість мешканців\n\n"
            "Надішліть всі дані одним повідомленням, кожен пункт з нового рядка\\."
        ),
        "pdf_generating": "📄 Генерую PDF\\.\\.\\.",
        "pdf_done": "✅ *Готово!* PDF із заявою на оренду надіслано 👇",
        "pdf_error": "❌ Помилка при генерації PDF: {}",
        "pay_pdf": (
            "📄 *Оплата PDF \\(Mieterprofil\\) — 5€*\n\n"
            "👉 Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "Після оплати напишіть */pay_done_pdf*\\."
        ),
        "pay_done_pdf": "✅ *Оплата підтверджена!*\n\nНадішліть дані для заяви\\.",
        "vip_intro": (
            "⭐ *VIP-підписка — 15€/міс*\n\n"
            "Щоденна підбірка «гарячих» оголошень за вашими критеріями\\.\n\n"
            "Що входить:\n"
            "• До 10 перевірених оголошень на день\n"
            "• Фільтр за містом, ціною, площею\n"
            "• Попередження про шахраїв\n"
            "• Безлімітні перевірки\n\n"
            "👉 Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\n"
            "Після оплати напишіть */pay_done_vip*\\."
        ),
        "pay_done_vip": (
            "✅ *VIP активовано!*\n\n"
            "⭐ Тепер ви отримуєте щоденну підбірку\\.\n\n"
            "Надішліть мені критерії пошуку:\n"
            "• Місто\n"
            "• Макс\\. ціна\n"
            "• Мін\\. площа\n"
            "• Кількість кімнат\n\n"
            "Я буду надсилати відповідні оголошення щодня!"
        ),
        "vip_ask_criteria": (
            "📝 *Надішліть критерії пошуку:*\n\n"
            "• Місто\n"
            "• Макс\\. ціна \\(€/міс\\)\n"
            "• Мін\\. площа \\(м²\\)\n"
            "• Кількість кімнат\n\n"
            "Приклад: Берлін, 800€, 40м², 2 кімнати"
        ),
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
            "👋 *Hi! I'm EuroRent AI — your personal rental detector in Europe.*\n\n"
            "🔑 Just send me a link to a listing or copy the text — I'll do a full breakdown in 5 seconds\\.\n\n"
            "📌 *What I do:*\n"
            "• Translate listings to Russian/English\n"
            "• Show hidden fees \\(Nebenkosten, Service Charge\\)\n"
            "• Tell you which documents are needed\n"
            "• Check for scams and fraud\n\n"
            "🎁 *Free trial:* 3 checks no payment\\.\n"
            "💸 *After the limit:* €3 per check or €9 per month\\.\n\n"
            "💡 *Learn more — tap* /help"
        ),
        "help": (
            "🤖 *EuroRent AI — smart rental assistant in Europe*\n\n"
            "🏠 *What do I do?*\n"
            "I analyze rental listings: translate text, find hidden commissions, check what documents landlords require, and warn you about scam schemes\\.\n\n"
            "📝 *How to use me?*\n"
            "Simply *copy a link* from any site \\(ImmoScout, Rightmove, Idealista, etc\\.\\) or paste the *listing text* right here\\. I'll detect the country and give you a full breakdown\\.\n\n"
            "🎁 *Free test drive*\n"
            "You can check **3 listings completely free** to see how useful I am\\.\n\n"
            "💳 *Packages & Pricing*\n\n"
            "🔹 *One\\-time* — €3 for 1 check\n"
            "▸ Pay: /pay_3\n\n"
            "💎 *Economy* — €9 for 5 checks \\(save 40%\\)\n"
            "▸ Pay: /pay_9\n\n"
            "👑 *Pro* — €19 for unlimited access per month\n"
            "▸ Pay: /pay_19\n\n"
            "📄 *PDF Application \\(Mieterprofil\\)* — €5\n"
            "▸ Pay: /pdf\n\n"
            "⭐ *VIP Subscription* — €15/mo \\(daily curated listings\\)\n"
            "▸ Pay: /vip\n\n"
            "💸 *How to pay*\n"
            "Tap the command above — you'll get a Revolut payment link\\. After paying, send the matching /pay_done_\\* command to unlock\\.\n\n"
            "🏦 *Need a European bank account for the deposit?*\n"
            "Open [Revolut]({}) or [Wise]({}) via my link and get a bonus\\!\n\n"
            "🌐 *Official website:* euro\\-rent\\-bot\\.onrender\\.com\n\n"
            "✅ *Ready to start?*\n"
            "Just send me any listing right now\\!"
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
        "pdf_intro": (
            "📄 *Ready\\-made rental application \\(Mieterprofil\\)*\n\n"
            "I can generate a PDF with a filled rental application in German/English\\.\n\n"
            "💰 Price: *€5*\n"
            "👉 Pay here: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "After payment, send me your data\\.\n"
            "I'll ask you to fill in:\n"
            "• Full name\n"
            "• Date of birth\n"
            "• Phone\n"
            "• Email\n"
            "• Current address\n"
            "• Employer / Self\\-employed\n"
            "• Income \\(net\\)\n"
            "• Number of occupants\n\n"
            "After filling in, I'll generate and send you the PDF\\."
        ),
        "pdf_need_data": (
            "📝 *Fill in your application data:*\n\n"
            "1\\. Full name\n"
            "2\\. Date of birth\n"
            "3\\. Phone\n"
            "4\\. Email\n"
            "5\\. Current address\n"
            "6\\. Employer / Self\\-employed\n"
            "7\\. Income \\(net/month\\)\n"
            "8\\. Number of occupants\n\n"
            "Send all data in one message, each item on a new line\\."
        ),
        "pdf_generating": "📄 Generating PDF\\.\\.\\.",
        "pdf_done": "✅ *Done!* PDF rental application sent 👇",
        "pdf_error": "❌ PDF generation error: {}",
        "pay_pdf": (
            "📄 *Pay for PDF \\(Mieterprofil\\) — €5*\n\n"
            "👉 Pay here: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "After payment, send */pay_done_pdf*\\."
        ),
        "pay_done_pdf": "✅ *Payment confirmed!*\n\nSend your application data\\.",
        "vip_intro": (
            "⭐ *VIP Subscription — €15/month*\n\n"
            "Daily curated list of hot listings matching your criteria\\.\n\n"
            "What's included:\n"
            "• Up to 10 verified listings per day\n"
            "• Filter by city, price, area\n"
            "• Scam alerts\n"
            "• Unlimited checks\n\n"
            "👉 Pay here: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\n"
            "After payment, send */pay_done_vip*\\."
        ),
        "pay_done_vip": (
            "✅ *VIP activated!*\n\n"
            "⭐ You'll now receive daily curated listings\\.\n\n"
            "Send me your search criteria:\n"
            "• City\n"
            "• Max\\. price\n"
            "• Min\\. area\n"
            "• Number of rooms\n\n"
            "I'll send matching listings every day!"
        ),
        "vip_ask_criteria": (
            "📝 *Send your search criteria:*\n\n"
            "• City\n"
            "• Max\\. price \\(€/month\\)\n"
            "• Min\\. area \\(m²\\)\n"
            "• Number of rooms\n\n"
            "Example: Berlin, €800, 40m², 2 rooms"
        ),
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
            "👋 *Hallo! Ich bin EuroRent AI — dein persönlicher Miet\\-Detector in Europa.*\n\n"
            "🔑 Schick mir einfach einen Link zu einem Angebot oder kopiere den Text — ich mache in 5 Sekunden eine vollständige Analyse\\.\n\n"
            "📌 *Was ich kann:*\n"
            "• Übersetze Angebote ins Russische/Englische\n"
            "• Zeige versteckte Gebühren \\(Nebenkosten, Service Charge\\)\n"
            "• Sage dir, welche Dokumente nötig sind\n"
            "• Warne vor Betrug und Scams\n\n"
            "🎁 *Kostenloser Test:* 3 Prüfungen ohne Zahlung\\.\n"
            "💸 *Nach dem Limit:* 3€ pro Prüfung oder 9€ pro Monat\\.\n\n"
            "💡 *Mehr dazu — drücke* /help"
        ),
        "help": (
            "🤖 *EuroRent AI — smarter Miet\\-Assistent in Europa*\n\n"
            "🏠 *Was mache ich?*\n"
            "Ich analysiere Mietangebote: übersetze Texte, finde versteckte Provisionen, prüfe, welche Dokumente Vermieter verlangen, und warne vor Betrugs\\-Maschen\\.\n\n"
            "📝 *So funktioniert's:*\n"
            "Kopiere einfach einen *Link* von einer beliebigen Seite \\(ImmoScout, Rightmove, Idealista usw\\.\\) oder füge den *Angebotstext* direkt hier ein\\. Ich erkenne das Land und gebe dir eine vollständige Analyse\\.\n\n"
            "🎁 *Kostenloser Testlauf*\n"
            "Du kannst **3 Angebote komplett kostenlos** prüfen, um meine Nützlichkeit zu testen\\.\n\n"
            "💳 *Pakete & Preise*\n\n"
            "🔹 *Einmalig* — 3€ für 1 Prüfung\n"
            "▸ Bezahlen: /pay_3\n\n"
            "💎 *Economy* — 9€ für 5 Prüfungen \\(\\-40%\\)\n"
            "▸ Bezahlen: /pay_9\n\n"
            "👑 *Pro* — 19€ für unbegrenzten Zugang pro Monat\n"
            "▸ Bezahlen: /pay_19\n\n"
            "📄 *PDF\\-Antrag \\(Mieterprofil\\)* — 5€\n"
            "▸ Bezahlen: /pdf\n\n"
            "⭐ *VIP\\-Abo* — 15€/Monat \\(tägliche Angebote\\)\n"
            "▸ Bezahlen: /vip\n\n"
            "💸 *Wie bezahlen?*\n"
            "Drücke den Befehl oben — du erhältst einen Revolut\\-Zahlungslink\\. Nach der Zahlung sende den passenden /pay_done_\\* Befehl\\.\n\n"
            "🏦 *Benötigst du ein europäisches Bankkonto für die Kaution?*\n"
            "Eröffne [Revolut]({}) oder [Wise]({}) über meinen Link und erhalte ein Bonus\\!\n\n"
            "🌐 *Offizielle Webseite:* euro\\-rent\\-bot\\.onrender\\.com\n\n"
            "✅ *Bereit loszulegen?*\n"
            "Schick mir einfach ein Angebot direkt jetzt\\!"
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
        "pdf_intro": (
            "📄 *Fertiger Mietantrag \\(Mieterprofil\\)*\n\n"
            "Ich kann ein PDF mit einem ausgefüllten Mietantrag auf Deutsch/Englisch erstellen\\.\n\n"
            "💰 Preis: *3€*\n"
            "👉 Hier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "Nach der Zahlung schick mir deine Daten\\.\n"
            "Ich bitte dich um:\n"
            "• Name\n"
            "• Geburtsdatum\n"
            "• Telefon\n"
            "• Email\n"
            "• Aktuelle Adresse\n"
            "• Arbeitgeber / Selbstständig\n"
            "• Einkommen \\(netto\\)\n"
            "• Anzahl der Bewohner\n\n"
            "Nach dem Ausfüllen erstelle ich dir das PDF\\."
        ),
        "pdf_need_data": (
            "📝 *Fülle deine Daten aus:*\n\n"
            "1\\. Name\n"
            "2\\. Geburtsdatum\n"
            "3\\. Telefon\n"
            "4\\. Email\n"
            "5\\. Aktuelle Adresse\n"
            "6\\. Arbeitgeber / Selbstständig\n"
            "7\\. Einkommen \\(netto/Monat\\)\n"
            "8\\. Anzahl der Bewohner\n\n"
            "Schick alle Daten in einer Nachricht, jeder Punkt in einer neuen Zeile\\."
        ),
        "pdf_generating": "📄 Erstelle PDF\\.\\.\\.",
        "pdf_done": "✅ *Fertig!* PDF\\-Mietantrag gesendet 👇",
        "pdf_error": "❌ PDF\\-Fehler: {}",
        "pay_pdf": (
            "📄 *PDF bezahlen \\(Mieterprofil\\) — 3€*\n\n"
            "👉 Hier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "Nach der Zahlung */pay_done_pdf* senden\\."
        ),
        "pay_done_pdf": "✅ *Zahlung bestätigt!*\n\nSchick deine Antragsdaten\\.",
        "vip_intro": (
            "⭐ *VIP\\-Abo — 15€/Monat*\n\n"
            "Tägliche Auswahl heißer Angebote nach deinen Kriterien\\.\n\n"
            "Enthalten:\n"
            "• Bis zu 10 geprüfte Angebote pro Tag\n"
            "• Filter nach Stadt, Preis, Fläche\n"
            "• Betrugswarnungen\n"
            "• Unbegrenzte Prüfungen\n\n"
            "👉 Hier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\n"
            "Nach der Zahlung */pay_done_vip* senden\\."
        ),
        "pay_done_vip": (
            "✅ *VIP aktiviert!*\n\n"
            "⭐ Du erhältst jetzt tägliche Angebote\\.\n\n"
            "Schick mir deine Suchkriterien:\n"
            "• Stadt\n"
            "• Max\\. Preis\n"
            "• Min\\. Fläche\n"
            "• Anzahl Zimmer\n\n"
            "Ich schicke dir täglich passende Angebote!"
        ),
        "vip_ask_criteria": (
            "📝 *Schick deine Suchkriterien:*\n\n"
            "• Stadt\n"
            "• Max\\. Preis \\(€/Monat\\)\n"
            "• Min\\. Fläche \\(m²\\)\n"
            "• Anzahl Zimmer\n\n"
            "Beispiel: Berlin, 800€, 40m², 2 Zimmer"
        ),
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
            "👋 *Cześć! Jestem EuroRent AI — twój osobisty detektor wynajmu w Europie.*\n\n"
            "🔑 Wyślij mi po prostu link do oferty lub skopiuj tekst — zrobię pełną analizę w 5 sekund\\.\n\n"
            "📌 *Co umiem:*\n"
            "• Tłumaczę oferty na polski/angielski\n"
            "• Pokazuję ukryte opłaty \\(Nebenkosten, Service Charge\\)\n"
            "• Podpowiadam, jakie dokumenty są potrzebne\n"
            "• Sprawdzam oszustwa i skamy\n\n"
            "🎁 *Darmowy test:* 3 sprawdzenia bez opłaty\\.\n"
            "💸 *Po limicie:* 3€ za sprawdzenie lub 9€ za miesiąc\\.\n\n"
            "💡 *Więcej — naciśnij* /help"
        ),
        "help": (
            "🤖 *EuroRent AI — inteligentny asystent najmu w Europie*\n\n"
            "🏠 *Co robię?*\n"
            "Analizuję oferty wynajmu: tłumaczę tekst, znajduję ukryte prowizje, sprawdzam, jakie dokumenty wymagają właściciele, i ostrzegam przed oszustwami\\.\n\n"
            "📝 *Jak ze mną współpracować?*\n"
            "Po prostu *skopiuj link* z dowolnej strony \\(ImmoScout, Rightmove, Idealista itp\\.\\) lub wklej *tekst oferty* tutaj\\. Sam określę kraj i dam pełną analizę\\.\n\n"
            "🎁 *Bezpłatny test\\-jazda*\n"
            "Możesz sprawdzić **3 oferty całkowicie za darmo**, żeby przekonać się o mojej przydatności\\.\n\n"
            "💳 *Pakiety i ceny*\n\n"
            "🔹 *Jednorazowy* — 3€ za 1 sprawdzenie\n"
            "▸ Zapłać: /pay_3\n\n"
            "💎 *Economy* — 9€ za 5 sprawdzeń \\(\\-40%\\)\n"
            "▸ Zapłać: /pay_9\n\n"
            "👑 *Pro* — 19€ za nieograniczony dostęp na miesiąc\n"
            "▸ Zapłać: /pay_19\n\n"
            "📄 *PDF\\-wniosek \\(Mieterprofil\\)* — 5€\n"
            "▸ Zapłać: /pdf\n\n"
            "⭐ *Subskrypcja VIP* — 15€/mies \\(codzienne listy\\)\n"
            "▸ Zapłać: /vip\n\n"
            "💸 *Jak zapłacić?*\n"
            "Naciśnij komendę powyżej — otrzymasz link do płatności przez Revolut\\. Po opłaceniu wyślij odpowiednią komendę /pay_done_\\*\\.\n\n"
            "🏦 *Potrzebujesz europejskiego konta bankowego do wpłaty kaucji?*\n"
            "Otwórz [Revolut]({}) lub [Wise]({}) przez mój link i otrzymaj bonus\\!\n\n"
            "🌐 *Oficjalna strona:* euro\\-rent\\-bot\\.onrender\\.com\n\n"
            "✅ *Gotowy, żeby zacząć?*\n"
            "Po prostu wyślij mi jakąkolwiek ofertęprosto teraz\\!"
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
        "pdf_intro": (
            "📄 *Gotowy formularz najmu \\(Mieterprofil\\)*\n\n"
            "Mogę wygenerować PDF z wypełnionym formularzem najmu po niemiecku/angielsku\\.\n\n"
            "💰 Cena: *5€*\n"
            "👉 Zapłać tutaj: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "Po opłaceniu wyślij mi dane\\.\n"
            "Poproszę o wypełnienie:\n"
            "• Imię i nazwisko\n"
            "• Data urodzenia\n"
            "• Telefon\n"
            "• Email\n"
            "• Aktualny adres\n"
            "• Pracodawca / Samozatrudniony\n"
            "• Dochód \\(netto\\)\n"
            "• Liczba mieszkańców\n\n"
            "Po wypełnieniu wygeneruję i prześlę PDF\\."
        ),
        "pdf_need_data": (
            "📝 *Wypełnij dane do formularza:*\n\n"
            "1\\. Imię i nazwisko\n"
            "2\\. Data urodzenia\n"
            "3\\. Telefon\n"
            "4\\. Email\n"
            "5\\. Aktualny adres\n"
            "6\\. Pracodawca / Samozatrudniony\n"
            "7\\. Dochód \\(netto/mies\\)\n"
            "8\\. Liczba mieszkańców\n\n"
            "Wyślij wszystkie dane w jednej wiadomości, każdy punkt w nowej linii\\."
        ),
        "pdf_generating": "📄 Generuję PDF\\.\\.\\.",
        "pdf_done": "✅ *Gotowe!* PDF z formularzem najmu wysłany 👇",
        "pdf_error": "❌ Błąd generowania PDF: {}",
        "pay_pdf": (
            "📄 *Zapłać za PDF \\(Mieterprofil\\) — 5€*\n\n"
            "👉 Zapłać tutaj: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "Po opłaceniu wyślij */pay_done_pdf*\\."
        ),
        "pay_done_pdf": "✅ *Płatność potwierdzona!*\n\nWyślij dane do formularza\\.",
        "vip_intro": (
            "⭐ *Subskrypcja VIP — 15€/mies*\n\n"
            "Codzienna lista gorących ofert dopasowanych do Twoich kryteriów\\.\n\n"
            "Co zawiera:\n"
            "• Do 10 sprawdzonych ofert dziennie\n"
            "• Filtr po mieście, cenie, powierzchni\n"
            "• Ostrzeżenia przed oszustwami\n"
            "• Nieograniczone sprawdzenia\n\n"
            "👉 Zapłać tutaj: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\n"
            "Po opłaceniu wyślij */pay_done_vip*\\."
        ),
        "pay_done_vip": (
            "✅ *VIP aktywowany!*\n\n"
            "⭐ Odtąd otrzymujesz codzienne listy ofert\\.\n\n"
            "Wyślij mi kryteria wyszukiwania:\n"
            "• Miasto\n"
            "• Maks\\. cena\n"
            "• Min\\. powierzchnia\n"
            "• Liczba pokoi\n\n"
            "Będę wysyłać pasujące oferty każdego dnia!"
        ),
        "vip_ask_criteria": (
            "📝 *Wyślij kryteria wyszukiwania:*\n\n"
            "• Miasto\n"
            "• Maks\\. cena \\(€/mies\\)\n"
            "• Min\\. powierzchnia \\(m²\\)\n"
            "• Liczba pokoi\n\n"
            "Przykład: Berlin, 800€, 40m², 2 pokoje"
        ),
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
