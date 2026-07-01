MESSAGES = {
    "ru": {
        "start": (
            "👋 *Привет! Я EuroRent AI — твой личный детектор по аренде во всей Европе.*\n\n"
            "Переезд — это стресс. А поиск квартиры в Европе — это двойной стресс. "
            "Неважно, на каком языке написано объявление — немецкий, французский, испанский, "
            "голландский, английский или даже латышский. Я понимаю всё.\n\n"
            "Я создан, чтобы сделать твой переезд проще. Вот что я умею за 5 секунд:\n\n"
            "🔥 Мгновенно перевожу объявления с ImmoScout, Rightmove, Airbnb или любого другого европейского портала.\n"
            "💸 Нахожу скрытые платежи (Nebenkosten, Service Charge, Charges) и считаю реальную цену.\n"
            "📋 Подсказываю, какие документы требуют хозяева (Schufa, Gehaltsnachweise, Garant, NIE).\n"
            "🚨 Проверяю объявления на мошенников и фейки по всей Европе.\n\n"
            "💰 *Как начать?*\n"
            "Просто кинь мне ссылку на любое объявление — я сделаю разбор за 5 секунд.\n\n"
            "🎁 *Бесплатный тест-драйв:*\n"
            "Первые 3 проверки — абсолютно бесплатно. Это мой подарок тебе.\n\n"
            "👥 *Для друзей:*\n"
            "Если я сэкономлю тебе время, нервы и деньги — просто перешли мой контакт друзьям-экспатам! \n"
            "Чем больше нас, тем круче."
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
            "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
            "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
            "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19\n"
            "PDF-заявление — 500 Stars (~5EUR) -> /pdf\n"
            "VIP-подписка — 1500 Stars (~15EUR/мес) -> /vip\n\n"
            "Дайджест по email:\n"
            "Каждую неделю — подборка лучших объявлений.\n"
            "Подписаться: /subscribe_email your@email.com\n"
            "Отписаться: /unsubscribe_email\n\n"
            "Фильтр по городу:\n"
            "/set_city berlin — показывать только Берлин\n"
            "/my_city — ваш город и тренд цен\n"
            "/trend berlin — тренд цен по городу\n"
            "/holygrail — идеальные квартиры\n\n"
            "Официальная страница: euro-rent-bot.onrender.com\n\n"
            "Готов начать? Просто пришли мне любое объявление прямо сейчас!"
        ),
        "analyzing": "Анализирую объявление...",
        "fetching_url": "Открываю ссылку...",
        "ocr_processing": "Распознаю текст со скриншота...",
        "limit_reached": (
            "Лимит бесплатных проверок\n\n"
            "Вы использовали все 3 бесплатные проверки.\n\n"
            "Пакеты и цены:\n"
            "3 проверки — 300 Stars (~3EUR) -> /pay_3\n"
            "10 проверок — 900 Stars (~9EUR) -> /pay_9\n"
            "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19"
        ),
        "pay_done_3": "Оплата подтверждена! Добавлены 3 проверки. Осталось: {}.",
        "pay_done_9": "Оплата подтверждена! Добавлено 10 проверок. Осталось: {}.",
        "pay_done_19": "Оплата подтверждена! Безлимитный доступ на месяц активирован!",
        "pay_not_used": "Вы ещё не использовали бота. Сначала отправьте объявление.",
        "no_balance": "У вас нет доступных проверок. Купите пакет: /help",
        "error": "Ошибка: {}",
        "send_listing": "Отправь текст объявления или ссылку.",
        "share_text": "Поделиться с другом:",
        "analysis_done": "Анализ готов!",
        "affiliate_footer": "",
        "pdf_intro": "PDF-заявление (Mieterprofil) — 500 Stars (~5EUR)\n\nОплатите: /pdf\n\nПосле оплаты отправьте данные.",
        "pdf_need_data": "Заполните данные для заявления:\n\n1. Имя и фамилия\n2. Дата рождения\n3. Телефон\n4. Email\n5. Текущий адрес\n6. Работодатель\n7. Доход (нетто/мес)\n8. Количество жильцов\n\nОтправьте все данные одним сообщением.",
        "pdf_generating": "Генерирую PDF...",
        "pdf_done": "Готово! PDF с заявлением на аренду отправлен.",
        "pdf_error": "Ошибка при генерации PDF: {}",
        "vip_intro": "VIP-подписка — 1500 Stars (~15EUR/мес)\n\nЕжедневная подборка объявлений по вашим критериям.\n\nЧто входит:\n- До 10 проверенных объявлений в день\n- Фильтр по городу, цене, площади\n- Предупреждения о мошенниках\n- Безлимитные проверки",
        "pay_done_vip": "VIP активирован!\n\nОтправьте мне критерии поиска:\n- Город\n- Макс. цена\n- Мин. площадь\n- Количество комнат",
        "vip_ask_criteria": "Отправьте критерии поиска:\n\n- Город\n- Макс. цена (EUR/мес)\n- Мин. площадь (м2)\n- Количество комнат\n\nПример: Берлин, 800EUR, 40м2, 2 комнаты",
        "pay_pdf": "PDF-заявление (Mieterprofil) — 500 Stars (~5EUR)\n\nОплатите: /pay_stars_pdf\n\nПосле оплаты отправьте данные.",
        "pay_vip": "VIP-подписка — 1500 Stars (~15EUR/мес)\n\nОплатите: /pay_stars_vip\n\nПосле оплаты отправьте критерии.",
        "pay_stars_pdf": "PDF-заявление (Mieterprofil) — 500 Stars (~5EUR)\n\nНажмите /pay_stars_pdf для оплаты.",
        "pay_stars_vip": "VIP-подписка — 1500 Stars (~15EUR/мес)\n\nНажмите /pay_stars_vip для оплаты.",
        "group_redirect": (
            "🔍 Вижу объявление!\n\n"
            "Нажмите кнопку ниже, чтобы перейти в бота.\n"
            "Скопируйте ссылку на объявление и отправьте её мне в личку — я разберу за 5 секунд!"
        ),
        "city_selected": "✅ Город установлен: {emoji} {name}\n\nТеперь я буду анализировать только объявления из {name}.\nСнять фильтр: /remove_city",
        "city_filter_skip": "⏭ Объявление не из вашего города ({user_city}). Анализ пропущен.\n\nЧтобы снять фильтр: /remove_city",
        "system_prompt": (
            "Ты — профессиональный помощник по аренде жилья во всей Европе с 10-летним опытом. "
            "Неважно, на каком языке написано объявление (немецкий, французский, испанский, португальский, "
            "голландский, итальянский, польский, чешский, словацкий, венгерский, румынский, болгарский, "
            "хорватский, сербский, греческий, латышский, литовский, эстонский или английский) — "
            "ты всегда выдаёшь ответ на русском языке, структурированно, с разбором цены, документов и рисков.\n\n"
            "Раздели ответ на 5 блоков:\n\n"
            "1. Краткий пересказ — суть объявления за 1 предложение.\n\n"
            "2. Реальная цена и сравнение с рынком.\n\n"
            "3. Анализ района и инфраструктуры.\n\n"
            "4. Документы и риски.\n\n"
            "5. Совет от эксперта — 2-3 вопроса владельцу + оценка от 1 до 10.\n\n"
            "Заверши фразой: Аренда — это марафон, а не спринт!"
        ),
    },
    "uk": {
        "start": (
            "Привіт! Я EuroRent AI — твій особистий детектор оренди в Європі.\n\n"
            "Просто надішліть мені посилання або скопіюйте текст — я зроблю повний розбір за 5 секунд.\n\n"
            "Що я вмію:\n"
            "- Перекладаю оголошення\n"
            "- Показую приховані платежі\n"
            "- Підказую документи\n"
            "- Перевіряю шахраїв\n\n"
            "Безкоштовний тест: 3 перевірки.\n\n"
            "Детальніше — /help"
        ),
        "help": (
            "EuroRent AI — розумний помічник по оренді\n\n"
            "Аналізую оголошення, знаходжу приховані комісії, перевіряю документи.\n\n"
            "Безкоштовний тест — 3 оголошення безкоштовно.\n\n"
            "Пакети та ціни:\n"
            "3 перевірки — 300 Stars (~3EUR) -> /pay_3\n"
            "10 перевірок — 900 Stars (~9EUR) -> /pay_9\n"
            "Безліміт/міс — 1900 Stars (~19EUR) -> /pay_19\n"
            "PDF-заява — 500 Stars (~5EUR) -> /pdf\n"
            "VIP-підписка — 1500 Stars (~15EUR/міс) -> /vip\n\n"
            "Готові? Пришліть оголошення!"
        ),
        "analyzing": "Аналізую оголошення...",
        "fetching_url": "Відкриваю посилання...",
        "ocr_processing": "Розпізнаю текст зі скріншота...",
        "limit_reached": (
            "Ліміт безкоштовних перевірок\n\n"
            "Пакети та ціни:\n"
            "3 перевірки — 300 Stars (~3EUR) -> /pay_3\n"
            "10 перевірок — 900 Stars (~9EUR) -> /pay_9\n"
            "Безліміт/міс — 1900 Stars (~19EUR) -> /pay_19"
        ),
        "pay_done_3": "Оплата підтверджена! Додано 3 перевірки. Залишилось: {}.",
        "pay_done_9": "Оплата підтверджена! Додано 10 перевірок. Залишилось: {}.",
        "pay_done_19": "Оплата підтверджена! Безліміт на місяць активовано!",
        "pay_not_used": "Ви ще не користувались ботом.",
        "no_balance": "Немає перевірок: /help",
        "error": "Помилка: {}",
        "send_listing": "Надішліть текст оголошення або посилання.",
        "share_text": "Поділитися з другом:",
        "analysis_done": "Аналіз готовий!",
        "affiliate_footer": "",
        "pdf_intro": "PDF-заява — 500 Stars (~5EUR)\n\nОплатіть: /pdf",
        "pdf_need_data": "Заповніть дані:\n\n1. Ім'я\n2. Дата народження\n3. Телефон\n4. Email\n5. Адреса\n6. Роботодавець\n7. Дохід\n8. Мешканці",
        "pdf_generating": "Генерую PDF...",
        "pdf_done": "Готово! PDF надіслано.",
        "pdf_error": "Помилка PDF: {}",
        "vip_intro": "VIP — 1500 Stars (~15EUR/міс)\n\nЩоденна підбірка оголошень.\n\nЩо входить:\n- До 10 перевірених оголошень на день\n- Фільтр за містом, ціною\n- Попередження про шахраїв\n- Безлімітні перевірки",
        "pay_done_vip": "VIP активовано!\n\nНадішліть критерії:\n- Місто\n- Макс. ціна\n- Мін. площа\n- Кімнати",
        "vip_ask_criteria": "Критерії:\n\n- Місто\n- Макс. ціна (EUR/міс)\n- Мін. площа (м2)\n- Кімнати",
        "pay_pdf": "PDF-заява (Mieterprofil) — 500 Stars (~5EUR)\n\nОплатіть: /pay_stars_pdf\n\nПісля оплати надішліть дані.",
        "pay_vip": "VIP-підписка — 1500 Stars (~15EUR/міс)\n\nОплатіть: /pay_stars_vip\n\nПісля оплати надішліть критерії.",
        "pay_stars_pdf": "PDF-заява (Mieterprofil) — 500 Stars (~5EUR)\n\nНатисніть /pay_stars_pdf для оплати.",
        "pay_stars_vip": "VIP-підписка — 1500 Stars (~15EUR/міс)\n\nНатисніть /pay_stars_vip для оплати.",
        "group_redirect": (
            "🔍 Бачу оголошення!\n\n"
            "Натисніть кнопку нижче, щоб перейти в бота.\n"
            "Скопіюйте посилання на оголошення та надішліть мені в особисті повідомлення — я розберу за 5 секунд!"
        ),
        "city_selected": "✅ Місто встановлено: {emoji} {name}\n\nТепер я аналізуватиму лише оголошення з {name}.\nЗняти фільтр: /remove_city",
        "city_filter_skip": "⏭ Оголошення не з вашого міста ({user_city}). Аналіз пропущено.\n\nЩоб зняти фільтр: /remove_city",
        "system_prompt": (
            "Ти — професійний помічник по оренди житла в усій Європі з 10-річним досвідом. "
            "Неважливо якою мовою написане оголошення (німецька, французька, іспанська, португальська, "
            "голландська, італійська, польська, чеська, словацька, угорська, румунська, болгарська, "
            "хорватська, сербська, грецька, латвійська, литовська, естонська або англійська) — "
            "ти завжди даєш відповідь українською, структуровано, з розбором ціни, документів та ризиків.\n\n"
            "5 блоків:\n\n"
            "1. Короткий переказ.\n\n"
            "2. Реальна ціна та порівняння з ринком.\n\n"
            "3. Аналіз району.\n\n"
            "4. Документи та ризики.\n\n"
            "5. Порада від експерта + оцінка 1-10.\n\n"
            "Заверши: Оренда — це марафон!"
        ),
    },
    "en": {
        "start": (
            "Hi! I'm EuroRent AI — your personal rental detector in Europe.\n\n"
            "Just send me a link or copy the text — I'll do a full breakdown in 5 seconds.\n\n"
            "What I do:\n"
            "- Translate listings\n"
            "- Show hidden fees\n"
            "- Tell you which documents are needed\n"
            "- Check for scams\n\n"
            "Free trial: 3 checks.\n\n"
            "Learn more — /help"
        ),
        "help": (
            "EuroRent AI — smart rental assistant\n\n"
            "I analyze rental listings: translate text, find hidden commissions, check documents.\n\n"
            "Free test drive — 3 listings completely free.\n\n"
            "Packages & Pricing:\n"
            "3 checks — 300 Stars (~3EUR) -> /pay_3\n"
            "10 checks — 900 Stars (~9EUR) -> /pay_9\n"
            "Unlimited/month — 1900 Stars (~19EUR) -> /pay_19\n"
            "PDF Application — 500 Stars (~5EUR) -> /pdf\n"
            "VIP Subscription — 1500 Stars (~15EUR/month) -> /vip\n\n"
            "Weekly email digest:\n"
            "Best listings every week.\n"
            "Subscribe: /subscribe_email your@email.com\n"
            "Unsubscribe: /unsubscribe_email\n\n"
            "Ready? Send me a listing!"
        ),
        "analyzing": "Analyzing listing...",
        "fetching_url": "Opening link...",
        "ocr_processing": "Reading text from screenshot...",
        "limit_reached": (
            "Free Check Limit Reached\n\n"
            "Packages & Pricing:\n"
            "3 checks — 300 Stars (~3EUR) -> /pay_3\n"
            "10 checks — 900 Stars (~9EUR) -> /pay_9\n"
            "Unlimited/month — 1900 Stars (~19EUR) -> /pay_19"
        ),
        "pay_done_3": "Payment confirmed! 3 checks added. Remaining: {}.",
        "pay_done_9": "Payment confirmed! 10 checks added. Remaining: {}.",
        "pay_done_19": "Payment confirmed! Unlimited access activated!",
        "pay_not_used": "You haven't used the bot yet.",
        "no_balance": "No checks: /help",
        "error": "Error: {}",
        "send_listing": "Send a listing text or link.",
        "share_text": "Share with a friend:",
        "analysis_done": "Analysis complete!",
        "affiliate_footer": "",
        "pdf_intro": "PDF Application — 500 Stars (~5EUR)\n\nPay: /pdf",
        "pdf_need_data": "Fill in your data:\n\n1. Name\n2. DOB\n3. Phone\n4. Email\n5. Address\n6. Employer\n7. Income\n8. Occupants",
        "pdf_generating": "Generating PDF...",
        "pdf_done": "Done! PDF sent.",
        "pdf_error": "PDF error: {}",
        "vip_intro": "VIP — 1500 Stars (~15EUR/month)\n\nDaily curated listings.\n\nWhat's included:\n- Up to 10 verified listings per day\n- Filter by city, price\n- Scam alerts\n- Unlimited checks",
        "pay_done_vip": "VIP activated!\n\nSend criteria:\n- City\n- Max price\n- Min area\n- Rooms",
        "vip_ask_criteria": "Criteria:\n\n- City\n- Max price (EUR/month)\n- Min area (m2)\n- Rooms",
        "pay_pdf": "PDF Application (Mieterprofil) — 500 Stars (~5EUR)\n\nPay: /pay_stars_pdf\n\nAfter payment send your data.",
        "pay_vip": "VIP Subscription — 1500 Stars (~15EUR/month)\n\nPay: /pay_stars_vip\n\nAfter payment send your criteria.",
        "pay_stars_pdf": "PDF Application (Mieterprofil) — 500 Stars (~5EUR)\n\nTap /pay_stars_pdf to pay.",
        "pay_stars_vip": "VIP Subscription — 1500 Stars (~15EUR/month)\n\nTap /pay_stars_vip to pay.",
        "group_redirect": (
            "🔍 I see a listing!\n\n"
            "Tap the button below to go to the bot.\n"
            "Copy the listing link and send it to me in a private chat — I'll analyze it in 5 seconds!"
        ),
        "city_selected": "✅ City set: {emoji} {name}\n\nNow I'll only analyze listings from {name}.\nRemove filter: /remove_city",
        "city_filter_skip": "⏭ Listing is not from your city ({user_city}). Analysis skipped.\n\nTo remove filter: /remove_city",
        "system_prompt": (
            "You are a professional rental assistant for all of Europe with 10 years of experience. "
            "No matter what language the listing is written in (German, French, Spanish, Portuguese, "
            "Dutch, Italian, Polish, Czech, Slovak, Hungarian, Romanian, Bulgarian, "
            "Croatian, Serbian, Greek, Latvian, Lithuanian, Estonian or English) — "
            "you always respond in the user's language, structured, with price breakdown, documents and risks.\n\n"
            "5 blocks:\n\n"
            "1. Brief summary.\n\n"
            "2. Real price and market comparison.\n\n"
            "3. Neighborhood analysis.\n\n"
            "4. Documents and risks.\n\n"
            "5. Expert advice + score 1-10.\n\n"
            "End with: Renting is a marathon!"
        ),
    },
    "de": {
        "start": (
            "Hallo! Ich bin EuroRent AI — dein Miet-Detector in Europa.\n\n"
            "Schick mir einen Link oder Text — Analyse in 5 Sekunden.\n\n"
            "Was ich kann:\n"
            "- Uebersetze Angebote\n"
            "- Zeige versteckte Gebuehren\n"
            "- Sage Dokumente\n"
            "- Warne vor Betrug\n\n"
            "Kostenloser Test: 3 Pruefungen.\n\n"
            "Mehr — /help"
        ),
        "help": (
            "EuroRent AI — smarter Miet-Assistent\n\n"
            "Analysiere Mietangebote, finde versteckte Provisionen.\n\n"
            "Kostenloser Test — 3 Angebote kostenlos.\n\n"
            "Pakete & Preise:\n"
            "3 Pruefungen — 300 Stars (~3EUR) -> /pay_3\n"
            "10 Pruefungen — 900 Stars (~9EUR) -> /pay_9\n"
            "Unbegrenzt/Monat — 1900 Stars (~19EUR) -> /pay_19\n"
            "PDF-Antrag — 500 Stars (~5EUR) -> /pdf\n"
            "VIP-Abo — 1500 Stars (~15EUR/Monat) -> /vip\n\n"
            "Bereit? Schick ein Angebot!"
        ),
        "analyzing": "Analysiere Angebot...",
        "fetching_url": "Oeffne Link...",
        "ocr_processing": "Erkenne Text...",
        "limit_reached": (
            "Kostenlose Pruefungen aufgebraucht\n\n"
            "Pakete & Preise:\n"
            "3 Pruefungen — 300 Stars (~3EUR) -> /pay_3\n"
            "10 Pruefungen — 900 Stars (~9EUR) -> /pay_9\n"
            "Unbegrenzt/Monat — 1900 Stars (~19EUR) -> /pay_19"
        ),
        "pay_done_3": "Zahlung bestaetigt! 3 Pruefungen. Verbleibend: {}.",
        "pay_done_9": "Zahlung bestaetigt! 10 Pruefungen. Verbleibend: {}.",
        "pay_done_19": "Zahlung bestaetigt! Unbegrenzt aktiviert!",
        "pay_not_used": "Du hast den Bot noch nicht benutzt.",
        "no_balance": "Keine Pruefungen: /help",
        "error": "Fehler: {}",
        "send_listing": "Schick einen Angebotstext oder Link.",
        "share_text": "Mit Freund teilen:",
        "analysis_done": "Analyse fertig!",
        "affiliate_footer": "",
        "pdf_intro": "PDF-Antrag — 500 Stars (~5EUR)\n\nBezahlen: /pdf",
        "pdf_need_data": "Daten ausfuellen:\n\n1. Name\n2. Geburtsdatum\n3. Telefon\n4. Email\n5. Adresse\n6. Arbeitgeber\n7. Einkommen\n8. Bewohner",
        "pdf_generating": "Erstelle PDF...",
        "pdf_done": "Fertig! PDF gesendet.",
        "pdf_error": "PDF-Fehler: {}",
        "vip_intro": "VIP — 1500 Stars (~15EUR/Monat)\n\nTaegliche Angebote.\n\nEnthalten:\n- Bis zu 10 gepruefte Angebote\n- Filter Stadt, Preis\n- Betrugswarnungen\n- Unbegrenzt",
        "pay_done_vip": "VIP aktiviert!\n\nSuchkriterien:\n- Stadt\n- Max. Preis\n- Flaeche\n- Zimmer",
        "vip_ask_criteria": "Kriterien:\n\n- Stadt\n- Max. Preis (EUR/Monat)\n- Flaeche (m2)\n- Zimmer",
        "pay_pdf": "PDF-Antrag (Mieterprofil) — 500 Stars (~5EUR)\n\nBezahlen: /pay_stars_pdf\n\nNach Zahlung Daten senden.",
        "pay_vip": "VIP-Abo — 1500 Stars (~15EUR/Monat)\n\nBezahlen: /pay_stars_vip\n\nNach Zahlung Kriterien senden.",
        "pay_stars_pdf": "PDF-Antrag (Mieterprofil) — 500 Stars (~5EUR)\n\nTippe /pay_stars_pdf zum Bezahlen.",
        "pay_stars_vip": "VIP-Abo — 1500 Stars (~15EUR/Monat)\n\nTippe /pay_stars_vip zum Bezahlen.",
        "group_redirect": (
            "🔍 Ich sehe ein Angebot!\n\n"
            "Klicke auf die Schaltflaeche unten, um zum Bot zu gehen.\n"
            "Kopiere den Link und sende ihn mir per PN — Analyse in 5 Sekunden!"
        ),
        "city_selected": "✅ Stadt eingestellt: {emoji} {name}\n\nJetzt analysiere ich nur Angebote aus {name}.\nFilter entfernen: /remove_city",
        "city_filter_skip": "⏭ Angebot nicht aus Ihrer Stadt ({user_city}). Analyse uebersprungen.\n\nFilter entfernen: /remove_city",
        "system_prompt": (
            "Du bist ein professioneller Miet-Assistent fuer ganz Europa mit 10 Jahren Erfahrung. "
            "Egal in welcher Sprache das Angebot geschrieben ist (Deutsch, Franzoesisch, Spanisch, Portugiesisch, "
            "Italienisch, Niederlaendisch, Polnisch, Tschechisch, Slowakisch, Ungarisch, Roemaenisch, Bulgarisch, "
            "Kroatisch, Serbisch, Griechisch, Lettisch, Litauisch, Estnisch oder Englisch) — "
            "du antwortest immer in der Sprache des Nutzers, strukturiert, mit Preisanalyse, Dokumenten und Risiken.\n\n"
            "5 Bloecke:\n\n"
            "1. Zusammenfassung.\n\n"
            "2. Preis und Marktvergleich.\n\n"
            "3. Stadtteil-Analyse.\n\n"
            "4. Dokumente und Risiken.\n\n"
            "5. Expertenrat + Bewertung 1-10.\n\n"
            "Beende: Mieten ist ein Marathon!"
        ),
    },
    "pl": {
        "start": (
            "Czesc! Jestem EuroRent AI — twoj detektor najmu.\n\n"
            "Wyslij link lub tekst — analiza w 5 sekund.\n\n"
            "Co umiem:\n"
            "- Tlumacze oferty\n"
            "- Pokazuje ukryte oplaty\n"
            "- Podpowiadam dokumenty\n"
            "- Sprawdzam oszustwa\n\n"
            "Darmowy test: 3 sprawdzenia.\n\n"
            "Wiecej — /help"
        ),
        "help": (
            "EuroRent AI — inteligentny asystent najmu\n\n"
            "Analizuje oferty, znajduje ukryte prowizje.\n\n"
            "Bezplatny test — 3 oferty za darmo.\n\n"
            "Pakiety i ceny:\n"
            "3 sprawdzenia — 300 Stars (~3EUR) -> /pay_3\n"
            "10 sprawdzen — 900 Stars (~9EUR) -> /pay_9\n"
            "Nieograniczony/mies — 1900 Stars (~19EUR) -> /pay_19\n"
            "PDF-wniosek — 500 Stars (~5EUR) -> /pdf\n"
            "VIP — 1500 Stars (~15EUR/mies) -> /vip\n\n"
            "Gotowy? Wyslij oferte!"
        ),
        "analyzing": "Analizuje oferte...",
        "fetching_url": "Otwieram link...",
        "ocr_processing": "Rozpoznaje tekst...",
        "limit_reached": (
            "Wyczerpane darmowe sprawdzenia\n\n"
            "Pakiety i ceny:\n"
            "3 sprawdzenia — 300 Stars (~3EUR) -> /pay_3\n"
            "10 sprawdzen — 900 Stars (~9EUR) -> /pay_9\n"
            "Nieograniczony/mies — 1900 Stars (~19EUR) -> /pay_19"
        ),
        "pay_done_3": "Platnosc potwierdzona! 3 sprawdzenia. Pozostalo: {}.",
        "pay_done_9": "Platnosc potwierdzona! 10 sprawdzen. Pozostalo: {}.",
        "pay_done_19": "Platnosc potwierdzona! Nieograniczony dostep!",
        "pay_not_used": "Nie korzystales jeszcze z bota.",
        "no_balance": "Brak sprawdzen: /help",
        "error": "Blad: {}",
        "send_listing": "Wyslij tekst oferty lub link.",
        "share_text": "Podziel sie z kolega:",
        "analysis_done": "Analiza gotowa!",
        "affiliate_footer": "",
        "pdf_intro": "PDF-wniosek — 500 Stars (~5EUR)\n\nZaplac: /pdf",
        "pdf_need_data": "Wypelnij dane:\n\n1. Imie\n2. Data urodzenia\n3. Telefon\n4. Email\n5. Adres\n6. Pracodawca\n7. Dochod\n8. Mieszkancy",
        "pdf_generating": "Generuje PDF...",
        "pdf_done": "Gotowe! PDF wyslany.",
        "pdf_error": "Blad PDF: {}",
        "vip_intro": "VIP — 1500 Stars (~15EUR/mies)\n\nCodzienne listy.\n\nCo zawiera:\n- Do 10 sprawdzonych ofert\n- Filtr miasto, cena\n- Ostrzezenia\n- Nieograniczone sprawdzenia",
        "pay_done_vip": "VIP aktywowany!\n\nKryteria:\n- Miasto\n- Maks. cena\n- Powierzchnia\n- Pokoje",
        "vip_ask_criteria": "Kryteria:\n\n- Miasto\n- Maks. cena (EUR/mies)\n- Powierzchnia (m2)\n- Pokoje",
        "pay_pdf": "PDF-wniosek (Mieterprofil) — 500 Stars (~5EUR)\n\nZaplac: /pay_stars_pdf\n\nPo opacie wyslij dane.",
        "pay_vip": "VIP — 1500 Stars (~15EUR/mies)\n\nZaplac: /pay_stars_vip\n\nPo opacie wyslij kryteria.",
        "pay_stars_pdf": "PDF-wniosek (Mieterprofil) — 500 Stars (~5EUR)\n\nKliknij /pay_stars_pdf aby zaplacic.",
        "pay_stars_vip": "VIP — 1500 Stars (~15EUR/mies)\n\nKliknij /pay_stars_vip aby zaplacic.",
        "group_redirect": (
            "🔍 Widze oferte!\n\n"
            "Kliknij przycisk ponizej, zeby przejsc do bota.\n"
            "Skopiuj link i wyslij mi w wiadomosci prywatnej — przeanalizuje w 5 sekund!"
        ),
        "city_selected": "✅ Miasto ustawione: {emoji} {name}\n\nTeraz bede analizowal tylko oferty z {name}.\nUsun filtr: /remove_city",
        "city_filter_skip": "⏭ Oferta nie z Twojego miasta ({user_city}). Analiza pominieta.\n\nAby usunac filtr: /remove_city",
        "system_prompt": (
            "Jestes profesjonalnym asystentem najmu w calnej Europie z 10-letnim doswiadczeniem. "
            "Bez wzgledu na jezyk oferty (niemiecki, francuski, hiszpanski, portugalski, "
            "wloski, holenderski, polski, czeski, slowacki, wegierski, rumunski, bułgarski, "
            "chorwacki, serbski, grecki, lawski, litewski, estoński lub angielski) — "
            "zawsze odpowiadasz w jezyku uzytkownika, strukturalnie, z analiza ceny, dokumentow i ryzyk.\n\n"
            "5 blokow:\n\n"
            "1. Podsumowanie.\n\n"
            "2. Cena i porownanie z rynkiem.\n\n"
            "3. Analiza okolicy.\n\n"
            "4. Dokumenty i ryzyka.\n\n"
            "5. Rada eksperta + ocena 1-10.\n\n"
            "Zakoncz: Najem to maraton!"
        ),
    },
}

DEFAULT_LANG = "en"


def get_msg(lang: str, key: str) -> str:
    return MESSAGES.get(lang, MESSAGES[DEFAULT_LANG]).get(key, MESSAGES[DEFAULT_LANG].get(key, ""))
