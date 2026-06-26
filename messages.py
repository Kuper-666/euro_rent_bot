from config import AFFILIATE_REVOLUT, AFFILIATE_WISE

MESSAGES = {
    "ru": {
        "start": (
            "Привет! Я EuroRent AI — твой личный детектор по аренде в Европе.\n\n"
            "Просто отправь мне ссылку на объявление или скопируй текст — я сделаю полный разбор за 5 секунд.\n\n"
            "Что я умею:\n"
            "- Перевожу объявление на русский/английский\n"
            "- Показываю скрытые платежи (Nebenkosten, Service Charge)\n"
            "- Подсказываю, какие документы нужны\n"
            "- Проверяю на мошенников и скам\n\n"
            "Бесплатный тест: 3 проверки без оплаты.\n"
            "После лимита: 3EUR за раз или 9EUR за месяц.\n\n"
            "Подробнее — нажми /help"
        ),
        "help": (
            "EuroRent AI — умный помощник по аренде жилья в Европе\n\n"
            "Что я делаю?\n"
            "Анализирую объявления о съеме: перевожу текст, вычисляю скрытые комиссии, проверяю документы и предупреждаю о мошеннических схемах.\n\n"
            "Как пользоваться?\n"
            "Просто скопируй ссылку с любого сайта (ImmoScout, Rightmove, Idealista) или вставь текст объявления прямо сюда.\n\n"
            "Бесплатный тест-драйв\n"
            "Ты можешь проверить 3 объявления абсолютно бесплатно.\n\n"
            "Пакеты и цены:\n"
            "Разовый — 3EUR за 1 проверку -> /pay_3\n"
            "Эконом — 9EUR за 5 проверок (экономия 40%) -> /pay_9\n"
            "Профи — 19EUR за безлимит на месяц -> /pay_19\n"
            "PDF-заявление (Mieterprofil) — 5EUR -> /pdf\n"
            "VIP-подписка — 15EUR/мес (ежедневные подборки) -> /vip\n\n"
            "Как оплатить?\n"
            "Нажми команду выше — получишь ссылку на оплату через Revolut. После оплаты напиши команду /pay_done_3 (или _9, _19).\n\n"
            "Нужен европейский счет для депозита?\n"
            f"Откройте Revolut ({AFFILIATE_REVOLUT}) или Wise ({AFFILIATE_WISE}) по моей ссылке и получите бонус!\n\n"
            "Официальная страница: euro-rent-bot.onrender.com\n\n"
            "Готов начать? Просто пришли мне любое объявление прямо сейчас!"
        ),
        "analyzing": "Анализирую объявление...",
        "fetching_url": "Открываю ссылку...",
        "ocr_processing": "Распознаю текст со скриншота...",
        "limit_reached": (
            "Лимит бесплатных проверок\n\n"
            "Вы использовали все 3 бесплатные проверки.\n\n"
            "Выберите пакет:\n"
            "Разовый — 3EUR за 1 проверку -> /pay_3\n"
            "Эконом — 9EUR за 5 проверок (-40%) -> /pay_9\n"
            "Профи — 19EUR за безлимит на месяц -> /pay_19\n\n"
            "После оплаты напишите /pay_done_3 (или _9, _19)."
        ),
        "pay_3": (
            "Пакет Разовый — 3EUR\n\n"
            "1 проверка объявления\n\n"
            "Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=300\n\n"
            "После оплаты напишите /pay_done_3."
        ),
        "pay_9": (
            "Пакет Эконом — 9EUR\n\n"
            "5 проверок объявлений (экономия 40%)\n\n"
            "Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "После оплаты напишите /pay_done_9."
        ),
        "pay_19": (
            "Пакет Профи — 19EUR\n\n"
            "Безлимитные проверки на 1 месяц\n\n"
            "Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\n"
            "После оплаты напишите /pay_done_19."
        ),
        "pay_done_3": "Оплата подтверждена! Вам добавлена 1 проверка. Осталось: {}.",
        "pay_done_9": "Оплата подтверждена! Вам добавлено 5 проверок. Осталось: {}.",
        "pay_done_19": "Оплата подтверждена! Безлимитный доступ на месяц активирован!",
        "pay_not_used": "Вы ещё не использовали бота. Сначала отправьте объявление, потом оплачивайте.",
        "no_balance": "У вас нет доступных проверок. Купите пакет: /help",
        "error": "Ошибка: {}",
        "send_listing": "Отправь текст объявления или ссылку.",
        "share_text": "Поделиться с другом:",
        "analysis_done": "Анализ готов!",
        "affiliate_footer": (
            "\n\nНужен европейский счет?\n"
            f"Откройте Revolut ({AFFILIATE_REVOLUT}) или Wise ({AFFILIATE_WISE}) — получите бонус!"
        ),
        "pdf_intro": (
            "Готовое заявление на аренду (Mieterprofil)\n\n"
            "Я могу сформировать PDF с заполненным заявлением на аренду.\n\n"
            "Стоимость: 5EUR\n"
            "Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "После оплаты отправьте мне данные:\n"
            "- Имя и фамилия\n"
            "- Дата рождения\n"
            "- Телефон\n"
            "- Email\n"
            "- Текущий адрес\n"
            "- Работодатель\n"
            "- Доход (нетто)\n"
            "- Количество жильцов\n\n"
            "Отправьте все данные одним сообщением."
        ),
        "pdf_need_data": (
            "Заполните данные для заявления:\n\n"
            "1. Имя и фамилия\n"
            "2. Дата рождения\n"
            "3. Телефон\n"
            "4. Email\n"
            "5. Текущий адрес\n"
            "6. Работодатель\n"
            "7. Доход (нетто/мес)\n"
            "8. Количество жильцов\n\n"
            "Отправьте все данные одним сообщением, каждый пункт с новой строки."
        ),
        "pdf_generating": "Генерирую PDF...",
        "pdf_done": "Готово! PDF с заявлением на аренду отправлен.",
        "pdf_error": "Ошибка при генерации PDF: {}",
        "pay_pdf": (
            "Оплата PDF (Mieterprofil) — 5EUR\n\n"
            "Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=500\n\n"
            "После оплаты напишите /pay_done_pdf."
        ),
        "pay_done_pdf": "Оплата подтверждена! Отправьте данные для заявления.",
        "vip_intro": (
            "VIP-подписка — 15EUR/мес\n\n"
            "Ежедневная подборка горячих объявлений по вашим критериям.\n\n"
            "Что входит:\n"
            "- До 10 проверенных объявлений в день\n"
            "- Фильтр по городу, цене, площади\n"
            "- Предупреждения о мошенниках\n"
            "- Безлимитные проверки\n\n"
            "Оплатите: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\n"
            "После оплаты напишите /pay_done_vip."
        ),
        "pay_done_vip": (
            "VIP активирован!\n\n"
            "Теперь вы получаете ежедневную подборку.\n\n"
            "Отправьте мне критерии поиска:\n"
            "- Город\n"
            "- Макс. цена\n"
            "- Мин. площадь\n"
            "- Количество комнат\n\n"
            "Я буду присылать подходящие объявления каждый день!"
        ),
        "vip_ask_criteria": (
            "Отправьте критерии поиска:\n\n"
            "- Город\n"
            "- Макс. цена (EUR/мес)\n"
            "- Мин. площадь (м2)\n"
            "- Количество комнат\n\n"
            "Пример: Берлин, 800EUR, 40м2, 2 комнаты"
        ),
        "system_prompt": (
            "Ты — профессиональный помощник для экспатов по аренде жилья в Европе. "
            "Отвечай на русском языке.\n\n"
            "Формат ответа в Telegram Markdown:\n"
            "- Используй жирный для заголовков\n"
            "- Добавляй эмодзи\n"
            "- Разбивай текст на логические блоки\n"
            "- В конце ставь оценку от 1 до 10 и давай совет\n\n"
            "Структура ответа:\n"
            "Чистый перевод\n"
            "Что включено в цену\n"
            "Требуемые документы\n"
            "Скрытые риски\n"
            "Оценка и совет"
        ),
    },
    "uk": {
        "start": (
            "Привіт! Я EuroRent AI — твій особистий детектор оренди в Європі.\n\n"
            "Просто надішліть мені посилання на оголошення або скопіюйте текст — я зроблю повний розбір за 5 секунд.\n\n"
            "Що я вмію:\n"
            "- Перекладаю оголошення українською/англійською\n"
            "- Показую приховані платежі (Nebenkosten, Service Charge)\n"
            "- Підказую, які документи потрібні\n"
            "- Перевіряю шахраїв та скам\n\n"
            "Безкоштовний тест: 3 перевірки без оплати.\n"
            "Після ліміту: 3EUR за раз або 9EUR за місяць.\n\n"
            "Детальніше — натисніть /help"
        ),
        "help": (
            "EuroRent AI — розумний помічник по оренді житла в Європі\n\n"
            "Що я роблю?\n"
            "Аналізую оголошення про оренду: перекладаю текст, знаходжу приховані комісії, перевіряю документи і попереджаю про шахрайські схеми.\n\n"
            "Як користуватися?\n"
            "Просто скопіюйте посилання з будь-якого сайту (ImmoScout, Rightmove, Idealista) або вставте текст оголошення прямо сюди.\n\n"
            "Безкоштовний тест-драйв\n"
            "Ви можете перевірити 3 оголошення абсолютно безкоштовно.\n\n"
            "Пакети та ціни:\n"
            "Разовий — 3EUR за 1 перевірку -> /pay_3\n"
            "Економ — 9EUR за 5 перевірок (економія 40%) -> /pay_9\n"
            "Профі — 19EUR за безліміт на місяць -> /pay_19\n"
            "PDF-заява (Mieterprofil) — 5EUR -> /pdf\n"
            "VIP-підписка — 15EUR/міс (щоденні підбірки) -> /vip\n\n"
            "Як оплатити?\n"
            "Натисніть команду вище — отримаєте посилання на оплату через Revolut. Після оплати напишіть /pay_done_3.\n\n"
            f"Відкрийте Revolut ({AFFILIATE_REVOLUT}) або Wise ({AFFILIATE_WISE}) за моїм посиланням і отримайте бонус!\n\n"
            "Офіційна сторінка: euro-rent-bot.onrender.com\n\n"
            "Готові почати? Просто пришліть мені будь-яке оголошення прямо зараз!"
        ),
        "analyzing": "Аналізую оголошення...",
        "fetching_url": "Відкриваю посилання...",
        "ocr_processing": "Розпізнаю текст зі скріншота...",
        "limit_reached": (
            "Ліміт безкоштовних перевірок\n\n"
            "Ви використали всі 3 безкоштовні перевірки.\n\n"
            "Оберіть пакет:\n"
            "Разовий — 3EUR за 1 перевірку -> /pay_3\n"
            "Економ — 9EUR за 5 перевірок (-40%) -> /pay_9\n"
            "Профі — 19EUR за безліміт на місяць -> /pay_19\n\n"
            "Після оплати напишіть /pay_done_3."
        ),
        "pay_3": (
            "Пакет Разовий — 3EUR\n\n"
            "1 перевірка оголошення\n\n"
            "Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=300\n\n"
            "Після оплати напишіть /pay_done_3."
        ),
        "pay_9": (
            "Пакет Економ — 9EUR\n\n"
            "5 перевірок оголошень (економія 40%)\n\n"
            "Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=900\n\n"
            "Після оплати напишіть /pay_done_9."
        ),
        "pay_19": (
            "Пакет Профі — 19EUR\n\n"
            "Безлімітні перевірки на 1 місяць\n\n"
            "Оплатіть: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\n"
            "Після оплати напишіть /pay_done_19."
        ),
        "pay_done_3": "Оплата підтверджена! Вам додано 1 перевірку. Залишилось: {}.",
        "pay_done_9": "Оплата підтверджена! Вам додано 5 перевірок. Залишилось: {}.",
        "pay_done_19": "Оплата підтверджена! Безлімітний доступ на місяць активовано!",
        "pay_not_used": "Ви ще не користувались ботом. Спочатку надішліть оголошення, потім оплачуйте.",
        "no_balance": "У вас немає доступних перевірок. Купіть пакет: /help",
        "error": "Помилка: {}",
        "send_listing": "Надішліть текст оголошення або посилання.",
        "share_text": "Поділитися з другом:",
        "analysis_done": "Аналіз готовий!",
        "affiliate_footer": (
            "\n\nПотрібен європейський рахунок?\n"
            f"Відкрийте Revolut ({AFFILIATE_REVOLUT}) або Wise ({AFFILIATE_WISE}) — отримайте бонус!"
        ),
        "pdf_intro": "Готова заява на оренду (Mieterprofil)\n\nЯ можу сформувати PDF із заповненою заявою.\n\nВартість: 5EUR\nОплатіть: https://revolut.me/radik5f35?currency=EUR&amount=500\n\nПісля оплати надішліть дані:\n- Ім'я та прізвище\n- Дата народження\n- Телефон\n- Email\n- Поточна адреса\n- Роботодавець\n- Дохід (нетто)\n- Кількість мешканців",
        "pdf_need_data": "Заповніть дані для заяви:\n\n1. Ім'я та прізвище\n2. Дата народження\n3. Телефон\n4. Email\n5. Поточна адреса\n6. Роботодавець\n7. Дохід (нетто/міс)\n8. Кількість мешканців\n\nНадішліть всі дані одним повідомленням.",
        "pdf_generating": "Генерую PDF...",
        "pdf_done": "Готово! PDF із заявою на оренду надіслано.",
        "pdf_error": "Помилка при генерації PDF: {}",
        "pay_pdf": "Оплата PDF (Mieterprofil) — 5EUR\n\nОплатіть: https://revolut.me/radik5f35?currency=EUR&amount=500\n\nПісля оплати напишіть /pay_done_pdf.",
        "pay_done_pdf": "Оплата підтверджена! Надішліть дані для заяви.",
        "vip_intro": "VIP-підписка — 15EUR/міс\n\nЩоденна підбірка гарячих оголошень за вашими критеріями.\n\nЩо входить:\n- До 10 перевірених оголошень на день\n- Фільтр за містом, ціною, площею\n- Попередження про шахраїв\n- Безлімітні перевірки\n\nОплатіть: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\nПісля оплати напишіть /pay_done_vip.",
        "pay_done_vip": "VIP активовано!\n\nТепер ви отримуєте щоденну підбірку.\n\nНадішліть мені критерії пошуку:\n- Місто\n- Макс. ціна\n- Мін. площа\n- Кількість кімнат",
        "vip_ask_criteria": "Надішліть критерії пошуку:\n\n- Місто\n- Макс. ціна (EUR/міс)\n- Мін. площа (м2)\n- Кількість кімнат\n\nПриклад: Берлін, 800EUR, 40м2, 2 кімнати",
        "system_prompt": (
            "Ти — професійний помічник для експатів по оренді житла в Європі. "
            "Відповідай українською мовою.\n\n"
            "Формат відповіді в Telegram Markdown:\n"
            "- Використовуй жирний для заголовків\n"
            "- Додавай емодзи\n"
            "- Розбивай текст на логічні блоки\n"
            "- В кінці став оцінку від 1 до 10 і давай пораду\n\n"
            "Структура відповіді:\n"
            "Чистий переклад\n"
            "Що включено в ціну\n"
            "Необхідні документи\n"
            "Приховані ризики\n"
            "Оцінка і порада"
        ),
    },
    "en": {
        "start": (
            "Hi! I'm EuroRent AI — your personal rental detector in Europe.\n\n"
            "Just send me a link to a listing or copy the text — I'll do a full breakdown in 5 seconds.\n\n"
            "What I do:\n"
            "- Translate listings to Russian/English\n"
            "- Show hidden fees (Nebenkosten, Service Charge)\n"
            "- Tell you which documents are needed\n"
            "- Check for scams and fraud\n\n"
            "Free trial: 3 checks no payment.\n"
            "After the limit: 3EUR per check or 9EUR per month.\n\n"
            "Learn more — tap /help"
        ),
        "help": (
            "EuroRent AI — smart rental assistant in Europe\n\n"
            "What do I do?\n"
            "I analyze rental listings: translate text, find hidden commissions, check what documents landlords require, and warn you about scam schemes.\n\n"
            "How to use me?\n"
            "Simply copy a link from any site (ImmoScout, Rightmove, Idealista, etc.) or paste the listing text right here.\n\n"
            "Free test drive\n"
            "You can check 3 listings completely free to see how useful I am.\n\n"
            "Packages & Pricing:\n"
            "One-time — 3EUR for 1 check -> /pay_3\n"
            "Economy — 9EUR for 5 checks (save 40%) -> /pay_9\n"
            "Pro — 19EUR for unlimited access per month -> /pay_19\n"
            "PDF Application (Mieterprofil) — 5EUR -> /pdf\n"
            "VIP Subscription — 15EUR/mo (daily curated listings) -> /vip\n\n"
            "How to pay?\n"
            "Tap the command above — you'll get a Revolut payment link. After paying, send /pay_done_3.\n\n"
            f"Open Revolut ({AFFILIATE_REVOLUT}) or Wise ({AFFILIATE_WISE}) via my link and get a bonus!\n\n"
            "Official website: euro-rent-bot.onrender.com\n\n"
            "Ready to start? Just send me any listing right now!"
        ),
        "analyzing": "Analyzing listing...",
        "fetching_url": "Opening link...",
        "ocr_processing": "Reading text from screenshot...",
        "limit_reached": (
            "Free Check Limit Reached\n\n"
            "You've used all 3 free checks.\n\n"
            "Choose a package:\n"
            "One-time — 3EUR for 1 check -> /pay_3\n"
            "Economy — 9EUR for 5 checks (-40%) -> /pay_9\n"
            "Pro — 19EUR for unlimited/month -> /pay_19\n\n"
            "After payment, send /pay_done_3."
        ),
        "pay_3": "Package One-time — 3EUR\n\n1 listing check\n\nPay here: https://revolut.me/radik5f35?currency=EUR&amount=300\n\nAfter payment, send /pay_done_3.",
        "pay_9": "Package Economy — 9EUR\n\n5 listing checks (save 40%)\n\nPay here: https://revolut.me/radik5f35?currency=EUR&amount=900\n\nAfter payment, send /pay_done_9.",
        "pay_19": "Package Pro — 19EUR\n\nUnlimited checks for 1 month\n\nPay here: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\nAfter payment, send /pay_done_19.",
        "pay_done_3": "Payment confirmed! 1 check added. Remaining: {}.",
        "pay_done_9": "Payment confirmed! 5 checks added. Remaining: {}.",
        "pay_done_19": "Payment confirmed! Unlimited access for 1 month activated!",
        "pay_not_used": "You haven't used the bot yet. Send a listing first, then pay.",
        "no_balance": "No checks remaining. Buy a package: /help",
        "error": "Error: {}",
        "send_listing": "Send a listing text or link.",
        "share_text": "Share with a friend:",
        "analysis_done": "Analysis complete!",
        "affiliate_footer": "\n\nNeed a European bank account?\nOpen Revolut ({}) or Wise ({}) — get a bonus!".format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "pdf_intro": "Ready-made rental application (Mieterprofil)\n\nI can generate a PDF with a filled rental application.\n\nPrice: 5EUR\nPay here: https://revolut.me/radik5f35?currency=EUR&amount=500\n\nAfter payment, send me your data:\n- Full name\n- Date of birth\n- Phone\n- Email\n- Current address\n- Employer\n- Income (net)\n- Number of occupants\n\nSend all data in one message.",
        "pdf_need_data": "Fill in your application data:\n\n1. Full name\n2. Date of birth\n3. Phone\n4. Email\n5. Current address\n6. Employer\n7. Income (net/month)\n8. Number of occupants\n\nSend all data in one message, each item on a new line.",
        "pdf_generating": "Generating PDF...",
        "pdf_done": "Done! PDF rental application sent.",
        "pdf_error": "PDF generation error: {}",
        "pay_pdf": "Pay for PDF (Mieterprofil) — 5EUR\n\nPay here: https://revolut.me/radik5f35?currency=EUR&amount=500\n\nAfter payment, send /pay_done_pdf.",
        "pay_done_pdf": "Payment confirmed! Send your application data.",
        "vip_intro": "VIP Subscription — 15EUR/month\n\nDaily curated list of hot listings matching your criteria.\n\nWhat's included:\n- Up to 10 verified listings per day\n- Filter by city, price, area\n- Scam alerts\n- Unlimited checks\n\nPay here: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\nAfter payment, send /pay_done_vip.",
        "pay_done_vip": "VIP activated!\n\nYou'll now receive daily curated listings.\n\nSend me your search criteria:\n- City\n- Max. price\n- Min. area\n- Number of rooms",
        "vip_ask_criteria": "Send your search criteria:\n\n- City\n- Max. price (EUR/month)\n- Min. area (m2)\n- Number of rooms\n\nExample: Berlin, 800EUR, 40m2, 2 rooms",
        "system_prompt": (
            "You are a professional rental assistant for expats across Europe. "
            "Respond in English.\n\n"
            "Format your response in Telegram Markdown:\n"
            "- Use bold for headers\n"
            "- Add emojis\n"
            "- Break text into logical blocks\n"
            "- End with a score from 1 to 10 and give advice\n\n"
            "Response structure:\n"
            "Clean Translation\n"
            "What's Included in Price\n"
            "Required Documents\n"
            "Hidden Risks\n"
            "Score and Advice"
        ),
    },
    "de": {
        "start": (
            "Hallo! Ich bin EuroRent AI — dein persoenlicher Miet-Detector in Europa.\n\n"
            "Schick mir einfach einen Link zu einem Angebot oder kopiere den Text — ich mache in 5 Sekunden eine vollstaendige Analyse.\n\n"
            "Was ich kann:\n"
            "- Uebersetze Angebote ins Russische/Englische\n"
            "- Zeige versteckte Gebuehren (Nebenkosten, Service Charge)\n"
            "- Sage dir, welche Dokumente noetig sind\n"
            "- Warne vor Betrug und Scams\n\n"
            "Kostenloser Test: 3 Pruefungen ohne Zahlung.\n"
            "Nach dem Limit: 3EUR pro Pruefung oder 9EUR pro Monat.\n\n"
            "Mehr dazu — druecke /help"
        ),
        "help": (
            "EuroRent AI — smarter Miet-Assistent in Europa\n\n"
            "Was mache ich?\n"
            "Ich analysiere Mietangebote: uebersetze Texte, finde versteckte Provisionen, pruefe Dokumente und warne vor Betrugs-Maschen.\n\n"
            "So funktioniert's:\n"
            "Kopiere einfach einen Link von einer beliebigen Seite (ImmoScout, Rightmove, Idealista) oder fuege den Angebotstext direkt hier ein.\n\n"
            "Kostenloser Testlauf\n"
            "Du kannst 3 Angebote komplett kostenlos pruefen.\n\n"
            "Pakete & Preise:\n"
            "Einmalig — 3EUR fuer 1 Pruefung -> /pay_3\n"
            "Economy — 9EUR fuer 5 Pruefungen (-40%) -> /pay_9\n"
            "Pro — 19EUR fuer unbegrenzten Zugang pro Monat -> /pay_19\n"
            "PDF-Antrag (Mieterprofil) — 5EUR -> /pdf\n"
            "VIP-Abo — 15EUR/Monat (taegliche Angebote) -> /vip\n\n"
            "Wie bezahlen?\n"
            "Druecke den Befehl oben — du erhaeltst einen Revolut-Zahlungslink. Nach der Zahlung sende /pay_done_3.\n\n"
            f"Eroeffne Revolut ({AFFILIATE_REVOLUT}) oder Wise ({AFFILIATE_WISE}) ueber meinen Link und erhalte ein Bonus!\n\n"
            "Offizielle Webseite: euro-rent-bot.onrender.com\n\n"
            "Bereit loszulegen? Schick mir einfach ein Angebot direkt jetzt!"
        ),
        "analyzing": "Analysiere Angebot...",
        "fetching_url": "Oeffne Link...",
        "ocr_processing": "Erkenne Text vom Screenshot...",
        "limit_reached": "Kostenlose Pruefungen aufgebraucht\n\nDu hast alle 3 kostenlosen Pruefungen genutzt.\n\nWaehle ein Paket:\nEinmalig — 3EUR fuer 1 Pruefung -> /pay_3\nEconomy — 9EUR fuer 5 Pruefungen (-40%) -> /pay_9\nPro — 19EUR fuer unbegrenzt/Monat -> /pay_19\n\nNach der Zahlung sende /pay_done_3.",
        "pay_3": "Paket Einmalig — 3EUR\n\n1 Angebotspruefung\n\nHier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=300\n\nNach der Zahlung /pay_done_3 senden.",
        "pay_9": "Paket Economy — 9EUR\n\n5 Angebotspruefungen (-40%)\n\nHier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=900\n\nNach der Zahlung /pay_done_9 senden.",
        "pay_19": "Paket Pro — 19EUR\n\nUnbegrenzte Pruefungen fuer 1 Monat\n\nHier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\nNach der Zahlung /pay_done_19 senden.",
        "pay_done_3": "Zahlung bestaetigt! 1 Pruefung hinzugefuegt. Verbleibend: {}.",
        "pay_done_9": "Zahlung bestaetigt! 5 Pruefungen hinzugefuegt. Verbleibend: {}.",
        "pay_done_19": "Zahlung bestaetigt! Unbegrenzter Zugang fuer 1 Monat aktiviert!",
        "pay_not_used": "Du hast den Bot noch nicht benutzt. Schick zuerst ein Angebot.",
        "no_balance": "Keine Pruefungen uebrig. Kaufe ein Paket: /help",
        "error": "Fehler: {}",
        "send_listing": "Schick einen Angebotstext oder Link.",
        "share_text": "Mit einem Freund teilen:",
        "analysis_done": "Analyse abgeschlossen!",
        "affiliate_footer": "\n\nBenötigst du ein europaeisches Bankkonto?\nEröffne Revolut ({}) oder Wise ({}) — erhalte ein Bonus!".format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "pdf_intro": "Fertiger Mietantrag (Mieterprofil)\n\nIch kann ein PDF mit einem ausgefuellten Mietantrag erstellen.\n\nPreis: 5EUR\nHier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=500\n\nNach der Zahlung schick mir deine Daten:\n- Name\n- Geburtsdatum\n- Telefon\n- Email\n- Aktuelle Adresse\n- Arbeitgeber\n- Einkommen (netto)\n- Anzahl der Bewohner",
        "pdf_need_data": "Fuelle deine Daten aus:\n\n1. Name\n2. Geburtsdatum\n3. Telefon\n4. Email\n5. Aktuelle Adresse\n6. Arbeitgeber\n7. Einkommen (netto/Monat)\n8. Anzahl der Bewohner\n\nSchick alle Daten in einer Nachricht.",
        "pdf_generating": "Erstelle PDF...",
        "pdf_done": "Fertig! PDF-Mietantrag gesendet.",
        "pdf_error": "PDF-Fehler: {}",
        "pay_pdf": "PDF bezahlen (Mieterprofil) — 5EUR\n\nHier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=500\n\nNach der Zahlung /pay_done_pdf senden.",
        "pay_done_pdf": "Zahlung bestaetigt! Schick deine Antragsdaten.",
        "vip_intro": "VIP-Abo — 15EUR/Monat\n\nTaeglichste Auswahl heisser Angebote nach deinen Kriterien.\n\nEnthalten:\n- Bis zu 10 gepruefte Angebote pro Tag\n- Filter nach Stadt, Preis, Flaeche\n- Betrugswarnungen\n- Unbegrenzte Pruefungen\n\nHier bezahlen: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\nNach der Zahlung /pay_done_vip senden.",
        "pay_done_vip": "VIP aktiviert!\n\nDu erhaeltst jetzt taegliche Angebote.\n\nSchick mir deine Suchkriterien:\n- Stadt\n- Max. Preis\n- Min. Flaeche\n- Anzahl Zimmer",
        "vip_ask_criteria": "Schick deine Suchkriterien:\n\n- Stadt\n- Max. Preis (EUR/Monat)\n- Min. Flaeche (m2)\n- Anzahl Zimmer\n\nBeispiel: Berlin, 800EUR, 40m2, 2 Zimmer",
        "system_prompt": (
            "Du bist ein professioneller Miet-Assistent fuer Expats in ganz Europa. "
            "Antworte auf Deutsch.\n\n"
            "Formatiere deine Antwort in Telegram Markdown:\n"
            "- Nutze fett fuer Ueberschriften\n"
            "- Fuege Emojis hinzu\n"
            "- Teile den Text in logische Bloecke\n"
            "- Beende mit einer Bewertung von 1 bis 10\n\n"
            "Antwortstruktur:\n"
            "Saubere Uebersetzung\n"
            "Was im Preis enthalten ist\n"
            "Erforderliche Dokumente\n"
            "Versteckte Risiken\n"
            "Bewertung und Empfehlung"
        ),
    },
    "pl": {
        "start": (
            "Czesc! Jestem EuroRent AI — twoj osobisty detektor wynajmu w Europie.\n\n"
            "Wyslij mi po prostu link do oferty lub skopiuj tekst — cale analize w 5 sekund.\n\n"
            "Co umiem:\n"
            "- Tlumacze oferty na polski/angielski\n"
            "- Pokazuje ukryte oplaty (Nebenkosten, Service Charge)\n"
            "- Podpowiadam, jakie dokumenty sa potrzebne\n"
            "- Sprawdzam oszustwa i skamy\n\n"
            "Darmowy test: 3 sprawdzenia bez oplaty.\n"
            "Po limicie: 3EUR za sprawdzenie lub 9EUR za miesiac.\n\n"
            "Wiecej — nacisnij /help"
        ),
        "help": (
            "EuroRent AI — inteligentny asystent najmu w Europie\n\n"
            "Co robie?\n"
            "Analizuje oferty wynajmu: tlumacze tekst, znajduje ukryte prowizje, sprawdzam dokumenty i ostrzegam przed oszustwami.\n\n"
            "Jak ze mna wspolpracowac?\n"
            "Po prostu skopiuj link z dowolnej strony (ImmoScout, Rightmove, Idealista) lub wklej tekst oferty tutaj.\n\n"
            "Bezplatny test-jazda\n"
            "Mozesz sprawdzic 3 oferty calekowicie za darmo.\n\n"
            "Pakiety i ceny:\n"
            "Jednorazowy — 3EUR za 1 sprawdzenie -> /pay_3\n"
            "Economy — 9EUR za 5 sprawdzen (-40%) -> /pay_9\n"
            "Pro — 19EUR za nieograniczony dostep na miesiac -> /pay_19\n"
            "PDF-wniosek (Mieterprofil) — 5EUR -> /pdf\n"
            "Subskrypcja VIP — 15EUR/mies (codzienne listy) -> /vip\n\n"
            "Jak zaplacic?\n"
            "Nacisnij komende powyzej — otrzymasz link do platnosci przez Revolut. Po oplaceniu wyslij /pay_done_3.\n\n"
            f"Otworz Revolut ({AFFILIATE_REVOLUT}) lub Wise ({AFFILIATE_WISE}) przez moj link i otrzymaj bonus!\n\n"
            "Oficjalna strona: euro-rent-bot.onrender.com\n\n"
            "Gotowy, żeby zaczac? Wyslij mi jakakolwiek oferte prosto teraz!"
        ),
        "analyzing": "Analizuje oferte...",
        "fetching_url": "Otwieram link...",
        "ocr_processing": "Rozpoznaje tekst ze zrzutu...",
        "limit_reached": "Wyczerpane darmowe sprawdzenia\n\nWykorzystales wszystkie 3 darmowe sprawdzenia.\n\nWybierz pakiet:\nJednorazowy — 3EUR za 1 sprawdzenie -> /pay_3\nEconomy — 9EUR za 5 sprawdzen (-40%) -> /pay_9\nPro — 19EUR za nieograniczony/miesiac -> /pay_19\n\nPo oplaceniu wyslij /pay_done_3.",
        "pay_3": "Pakiet Jednorazowy — 3EUR\n\n1 sprawdzenie oferty\n\nZaplac tutaj: https://revolut.me/radik5f35?currency=EUR&amount=300\n\nPo oplaceniu wyslij /pay_done_3.",
        "pay_9": "Pakiet Economy — 9EUR\n\n5 sprawdzen ofert (-40%)\n\nZaplac tutaj: https://revolut.me/radik5f35?currency=EUR&amount=900\n\nPo oplaceniu wyslij /pay_done_9.",
        "pay_19": "Pakiet Pro — 19EUR\n\nNieograniczone sprawdzenia na 1 miesiac\n\nZaplac tutaj: https://revolut.me/radik5f35?currency=EUR&amount=1900\n\nPo oplaceniu wyslij /pay_done_19.",
        "pay_done_3": "Platnosc potwierdzona! Dodano 1 sprawdzenie. Pozostalo: {}.",
        "pay_done_9": "Platnosc potwierdzona! Dodano 5 sprawdzen. Pozostalo: {}.",
        "pay_done_19": "Platnosc potwierdzona! Nieograniczony dostep na miesiac aktywowany!",
        "pay_not_used": "Nie korzystales jeszcze z bota. Najpierw wyslij oferte.",
        "no_balance": "Brak dostepnych sprawdzen. Kup pakiet: /help",
        "error": "Blad: {}",
        "send_listing": "Wyslij tekst oferty lub link.",
        "share_text": "Podziel sie z kolega:",
        "analysis_done": "Analiza gotowa!",
        "affiliate_footer": "\n\nPotrzebujesz europejskiego konta bankowego?\nOtworz Revolut ({}) lub Wise ({}) — otrzymaj bonus!".format(AFFILIATE_REVOLUT, AFFILIATE_WISE),
        "pdf_intro": "Gotowy formularz najmu (Mieterprofil)\n\nMoge wygenerowac PDF z wypelnionym formularzem najmu.\n\nCena: 5EUR\nZaplac tutaj: https://revolut.me/radik5f35?currency=EUR&amount=500\n\nPo oplaceniu wyslij mi dane:\n- Imie i nazwisko\n- Data urodzenia\n- Telefon\n- Email\n- Aktualny adres\n- Pracodawca\n- Dochod (netto)\n- Liczba mieszkancow",
        "pdf_need_data": "Wypelnij dane do formularza:\n\n1. Imie i nazwisko\n2. Data urodzenia\n3. Telefon\n4. Email\n5. Aktualny adres\n6. Pracodawca\n7. Dochod (netto/mies)\n8. Liczba mieszkancow\n\nWyslij wszystkie dane w jednej wiadomosci.",
        "pdf_generating": "Generuje PDF...",
        "pdf_done": "Gotowe! PDF z formularzem najmu wyslany.",
        "pdf_error": "Blad generowania PDF: {}",
        "pay_pdf": "Zaplac za PDF (Mieterprofil) — 5EUR\n\nZaplac tutaj: https://revolut.me/radik5f35?currency=EUR&amount=500\n\nPo oplaceniu wyslij /pay_done_pdf.",
        "pay_done_pdf": "Platnosc potwierdzona! Wyslij dane do formularza.",
        "vip_intro": "Subskrypcja VIP — 15EUR/mies\n\nCodzienna lista goracych ofert dopasowanych do Twoich kryteriow.\n\nCo zawiera:\n- Do 10 sprawdzonych ofert dziennie\n- Filtr po miescie, cenie, powierzchni\n- Ostrzezenia przed oszustwami\n- Nieograniczone sprawdzenia\n\nZaplac tutaj: https://revolut.me/radik5f35?currency=EUR&amount=1500\n\nPo oplaceniu wyslij /pay_done_vip.",
        "pay_done_vip": "VIP aktywowany!\n\nOdtad otrzymujesz codzienne listy ofert.\n\nWyslij mi kryteria wyszukiwania:\n- Miasto\n- Maks. cena\n- Min. powierzchnia\n- Liczba pokoi",
        "vip_ask_criteria": "Wyslij kryteria wyszukiwania:\n\n- Miasto\n- Maks. cena (EUR/mies)\n- Min. powierzchnia (m2)\n- Liczba pokoi\n\nPrzyklad: Berlin, 800EUR, 40m2, 2 pokoje",
        "system_prompt": (
            "Jestes profesjonalnym asystentem najmu dla ekspatow w Europie. "
            "Odpowiadaj po polsku.\n\n"
            "Formatuj odpowiedz w Telegram Markdown:\n"
            "- Uzywaj pogrubienia dla naglowkow\n"
            "- Dodawaj emoji\n"
            "- Dziel tekst na logiczne bloki\n"
            "- Zakoncz ocena od 1 do 10\n\n"
            "Struktura odpowiedzi:\n"
            "Czyste tlumaczenie\n"
            "Co jest wliczone w cene\n"
            "Wymagane dokumenty\n"
            "Ukryte ryzyka\n"
            "Ocena i rada"
        ),
    },
}

DEFAULT_LANG = "en"


def get_msg(lang: str, key: str) -> str:
    return MESSAGES.get(lang, MESSAGES[DEFAULT_LANG]).get(key, MESSAGES[DEFAULT_LANG].get(key, ""))
