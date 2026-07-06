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
            "Полезные команды:\n"
            "/balance — сколько проверок осталось\n"
            "/ref — твоя реферальная ссылка\n"
            "/lang — сменить язык\n\n"
            "Фильтр по городу:\n"
            "/set_city berlin — показывать только Берлин\n"
            "/my_city — ваш город и тренд цен\n"
            "/trend berlin — тренд цен по городу\n"
            "/holygrail — идеальные квартиры\n"
            "/cities — все доступные города\n\n"
            "Полезные фичи:\n"
            "/favorite — добавить в избранное\n"
            "/favorites — список избранного\n"
            "/track ссылка — отслеживать заявку\n"
            "/mytracks — мои заявки\n"
            "/set_profile — заполнить профиль\n"
            "/generate_letter — мотивационное письмо\n"
            "/reply сообщение — ответ арендодателю\n"
            "/set_work_address адрес — для расчёта пути\n\n"
            "Дайджест по email:\n"
            "Каждую неделю — подборка лучших объявлений.\n"
            "Подписаться: /subscribe_email your@email.com\n"
            "Отписаться: /unsubscribe_email\n\n"
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
            "Безлимит/мес — 1900 Stars (~19EUR) -> /pay_19\n\n"
            "🎁 Или пригласите друга — получите +1 проверку бесплатно!\n"
            "Ваша ссылка: {}"
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
            "Неважно, на каком языке написано объявление — ты всегда выдаёшь ответ на русском.\n\n"
            "Раздели ответ на 7 блоков:\n\n"
            "1. ПЕРЕВОД И СУТЬ\n"
            "Переведи ключевые моменты объявления. Если объявление на немецком/голландском/итальянском — "
            "объясни непонятные термины (Kaltmiete/Warmmiete, Nebenkosten, Kaution, Provision, Schufa, NIE и т.д.).\n\n"
            "2. РЕАЛЬНАЯ ЦЕНА\n"
            "Покажи разницу между заявленной ценой и реальной:\n"
            "- Kaltmiete (холодная) vs Warmmiete (тёплая)\n"
            "- Nebenkosten (коммуналка) — сколько примерно добавится\n"
            "- Kaution (депозит) — обычно 2-3 месяца\n"
            "- Provision (комиссия агента) — есть ли\n"
            "- Service Charge, Courtage, Maklergebühr — другие скрытые комиссии\n"
            "Укажи итоговую реальную стоимость аренды в месяц.\n\n"
            "3. СРАВНЕНИЕ С РЫНКОМ\n"
            "Сравни цену со средней по городу/району. Укажи:\n"
            "- Это дорого, нормально или дёшево?\n"
            "- На сколько % отклонение от средней\n"
            "- Стоит ли торопиться или можно подождать\n\n"
            "4. ПРОВЕРКА НА МОШЕННИКОВ\n"
            "Проверь объявление на признаки мошенничества:\n"
            "- Слишком низкая цена для района\n"
            "- Нет фото или только stock-фото\n"
            "- Просьба о предоплате до просмотра\n"
            "- Подозрительный email/телефон\n"
            "- Скопированное объявление (дубликаты)\n"
            "- Нет реального адреса\n"
            "Оцените риск: 🟢 низкий / 🟡 средний / 🔴 высокий\n\n"
            "5. ДОКУМЕНТЫ И ТРЕБОВАНИЯ\n"
            "Перечисли какие документы нужны для подачи заявки:\n"
            "- Schufa (кредитная история в Германии)\n"
            "- NIE (налоговый номер в Испании)\n"
            "- Garant/Bürgschaft (поручитель)\n"
            "- Справка о доходах (Einkommensnachweis)\n"
            "- Трудовой договор (Arbeitsvertrag)\n"
            "- Копия паспорта\n"
            "- Рекомендательные письма от предыдущих арендодателей\n"
            "Укажи что именно требует этот конкретный арендодатель.\n\n"
            "6. ЮРИДИЧЕСКИЕ ТОНКОСТИ\n"
            "Отметь важные правовые моменты:\n"
            "- Тип договора (befristet/unbefristet — срочный/бессрочный)\n"
            "- Срокnotice (как быстро можно выехать)\n"
            "- Права арендатора по закону страны\n"
            "- Есть ли Kündigungsfrist (срок предупреждения)\n"
            "- Особенности депозита (возврат, условия)\n\n"
            "7. ЭКСПЕРТНАЯ ОЦЕНКА\n"
            "- 2-3 конкретных вопроса владельцу\n"
            "- Совет: стоит ли подавать заявку\n"
            "- Оценка от 1 до 10 (где 10 — идеальная сделка)\n"
            "- Причина оценки\n\n"
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
            "Корисні команди:\n"
            "/balance — скільки перевірок залишилось\n"
            "/ref — твоє реферальне посилання\n"
            "/lang — змінити мову\n\n"
            "Фільтр за містом:\n"
            "/set_city berlin — показувати тільки Берлін\n"
            "/my_city — ваше місто та тренд цін\n\n"
            "Корисні фічі:\n"
            "/favorite — додати в обране\n"
            "/favorites — список обраних\n"
            "/track посилання — відстежувати заявку\n"
            "/mytracks — мої заявки\n"
            "/set_profile — заповнити профіль\n"
            "/generate_letter — мотиваційний лист\n"
            "/reply повідомлення — відповідь орендодавцю\n"
            "/set_work_address адреса — для розрахунку шляху\n\n"
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
            "Безліміт/міс — 1900 Stars (~19EUR) -> /pay_19\n\n"
            "🎁 Або запросіть друга — отримайте +1 перевірку безкоштовно!\n"
            "Ваше посилання: {}"
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
            "Ти завжди даєш відповідь українською.\n\n"
            "7 блоків:\n\n"
            "1. ПЕРЕКЛАД ТА СУТЬ\n"
            "Переклади ключові моменти. Поясни незрозумілі терміни.\n\n"
            "2. РЕАЛЬНА ЦІНА\n"
            "Покажи різницю між заявленою та реальною ціною.\n\n"
            "3. ПОРІВНЯННЯ З РИНКОМ\n"
            "Це дорого, нормально чи дешево?\n\n"
            "4. ПЕРЕВІРКА НА ШАХРАЇВ\n"
            "Ознаки шахрайства: занадто низька ціна, немає фото, прохання про передоплату.\n\n"
            "5. ДОКУМЕНТИ\n"
            "Що потрібно для подачі заявки.\n\n"
            "6. ЮРИДИЧНІ НЮАНСИ\n"
            "Тип договору, строк попередження.\n\n"
            "7. ОЦІНКА ЕКСПЕРТА\n"
            "Питання власнику, оцінка 1-10.\n\n"
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
            "Useful commands:\n"
            "/balance — how many checks you have left\n"
            "/ref — your referral link\n"
            "/lang — change language\n\n"
            "City filter:\n"
            "/set_city berlin — show only Berlin listings\n"
            "/my_city — your city and price trends\n\n"
            "Useful features:\n"
            "/favorite — save to favorites\n"
            "/favorites — list favorites\n"
            "/track url — track an application\n"
            "/mytracks — my applications\n"
            "/set_profile — fill in your profile\n"
            "/generate_letter — motivation letter\n"
            "/reply message — reply to landlord\n"
            "/set_work_address address — for travel time\n\n"
            "Weekly email digest:\n"
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
            "Unlimited/month — 1900 Stars (~19EUR) -> /pay_19\n\n"
            "🎁 Or invite a friend — get +1 free check!\n"
            "Your link: {}"
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
            "No matter what language the listing is written in — you always respond in English.\n\n"
            "Structure your response in 7 blocks:\n\n"
            "1. TRANSLATION & SUMMARY\n"
            "Translate key points. Explain unfamiliar terms (Kaltmiete/Warmmiete, Nebenkosten, Kaution, "
            "Provision, Schufa, NIE, Garant, etc.).\n\n"
            "2. REAL PRICE BREAKDOWN\n"
            "Show the difference between listed price and actual cost:\n"
            "- Cold rent vs warm rent\n"
            "- Nebenkosten (utilities) — estimated add-on\n"
            "- Kaution (deposit) — usually 2-3 months\n"
            "- Provision (agent fee)\n"
            "- Other hidden fees (Service Charge, Courtage)\n"
            "State the total estimated monthly cost.\n\n"
            "3. MARKET COMPARISON\n"
            "- Is this expensive, fair, or cheap for the area?\n"
            "- Percentage deviation from average\n"
            "- Should you rush or wait?\n\n"
            "4. SCAM CHECK\n"
            "Check for red flags:\n"
            "- Price too low for the neighborhood\n"
            "- No photos or stock images only\n"
            "- Request for prepayment before viewing\n"
            "- Suspicious email/phone\n"
            "- Duplicate listing\n"
            "- No real address\n"
            "Risk level: 🟢 low / 🟡 medium / 🔴 high\n\n"
            "5. DOCUMENTS REQUIRED\n"
            "- Schufa (credit check — Germany)\n"
            "- NIE (tax number — Spain)\n"
            "- Garant/Bürgschaft (guarantor)\n"
            "- Income proof (Einkommensnachweis)\n"
            "- Employment contract\n"
            "- Passport copy\n"
            "- Landlord references\n"
            "Specify what THIS landlord requires.\n\n"
            "6. LEGAL NOTES\n"
            "- Contract type (fixed-term vs unlimited)\n"
            "- Notice period (Kündigungsfrist)\n"
            "- Tenant rights under local law\n"
            "- Deposit conditions\n\n"
            "7. EXPERT VERDICT\n"
            "- 2-3 specific questions for the landlord\n"
            "- Should you apply?\n"
            "- Score from 1 to 10 (10 = perfect deal)\n"
            "- Reason for score\n\n"
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
            "Nuetzliche Befehle:\n"
            "/balance — wie viele Pruefungen noch\n"
            "/ref — dein Empfehlungslink\n"
            "/lang — Sprache wechseln\n\n"
            "Stadtfilter:\n"
            "/set_city berlin — nur Berlin anzeigen\n"
            "/my_city — deine Stadt und Preistrends\n\n"
            "Nuetzliche Features:\n"
            "/favorite — merken\n"
            "/favorites — gemerkte Angebote\n"
            "/track link — Bewerbung verfolgen\n"
            "/mytracks — meine Bewerbungen\n"
            "/set_profile — Profil ausfuellen\n"
            "/generate_letter — Anschreiben\n"
            "/reply nachricht — Vermieter antworten\n"
            "/set_work_address adresse — fuer Wegzeit\n\n"
            "Bereit? Schick mir ein Angebot!"
        ),
        "analyzing": "Analysiere Angebot...",
        "fetching_url": "Oeffne Link...",
        "ocr_processing": "Erkenne Text...",
        "limit_reached": (
            "Kostenlose Pruefungen aufgebraucht\n\n"
            "Pakete & Preise:\n"
            "3 Pruefungen — 300 Stars (~3EUR) -> /pay_3\n"
            "10 Pruefungen — 900 Stars (~9EUR) -> /pay_9\n"
            "Unbegrenzt/Monat — 1900 Stars (~19EUR) -> /pay_19\n\n"
            "🎁 Oder laden Sie einen Freund ein — +1 kostenlose Pruefung!\n"
            "Ihr Link: {}"
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
            "Du antwortest immer auf Deutsch.\n\n"
            "7 Bloecke:\n\n"
            "1. UEBERSETZUNG UND ZUSAMMENFASSUNG\n"
            "Uebersetze die Hauptpunkte. Erklaere Fachbegriffe.\n\n"
            "2. REALER PREIS\n"
            "Zeige den Unterschied zwischen Mietpreis und tatsaechlichen Kosten.\n\n"
            "3. MARKTVERGLEICH\n"
            "Ist es teuer, fair oder gunstig?\n\n"
            "4. BETRUGSPRUEFUNG\n"
            "Pruefe auf Betrug: zu gunstiger Preis, keine Fotos, Vorauszahlung.\n\n"
            "5. BENOTIGTE DOKUMENTE\n"
            "Schufa, Einkommensnachweis, Mietvertrag usw.\n\n"
            "6. RECHTLICHE HINWEISE\n"
            "Vertragstyp, Kuendigungsfrist.\n\n"
            "7. EXPERTENURTEIL\n"
            "Fragen an Vermieter, Bewertung 1-10.\n\n"
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
            "Uzyteczne komendy:\n"
            "/balance — ile sprawdzen zostalo\n"
            "/ref — twoj link referencyjny\n"
            "/lang — zmien jezyk\n\n"
            "Filtr po miescie:\n"
            "/set_city berlin — pokazuj tylko Berlin\n"
            "/my_city — twoje miasto i trendy cenowe\n\n"
            "Uzyteczne funkcje:\n"
            "/favorite — dodaj do ulubionych\n"
            "/favorites — lista ulubionych\n"
            "/track link — sledz zgloszenie\n"
            "/mytracks — moje zgloszenia\n"
            "/set_profile — wypelnij profil\n"
            "/generate_letter — list motywacyjny\n"
            "/reply wiadomosc — odpowiedz wynajmujacemu\n"
            "/set_work_address adres — do obliczenia czasu podróży\n\n"
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
            "Nieograniczony/mies — 1900 Stars (~19EUR) -> /pay_19\n\n"
            "🎁 Zaproś znajomego — otrzymaj +1 darmowe sprawdzenie!\n"
            "Twój link: {}"
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
            "Zawsze odpowiadasz po polsku.\n\n"
            "7 blokow:\n\n"
            "1. TLUMACZENIE I STRESZCZENIE\n"
            "Przetlumacz kluczowe punkty. Wyjasnij nieznane terminy.\n\n"
            "2. REALNA CENA\n"
            "Pokaz roznice miedzy cena wynajmu a rzeczywistym kosztem.\n\n"
            "3. POROWNANIE Z RYNKIEM\n"
            "Czy to drogo, tanio czy w normie?\n\n"
            "4. SPRAWDZENIE OSZUSTW\n"
            "Sprawdz oznaki oszustwa: zbyt niska cena, brak zdjec, wplata zaliczki.\n\n"
            "5. WYMAGANE DOKUMENTY\n"
            "Schufa, NIE, umowa o prace itp.\n\n"
            "6. UWAGI PRAWNE\n"
            "Typ umowy, okres wypowiedzenia.\n\n"
            "7. OCENA EKSPERTA\n"
            "Pytania do wlasciciela, ocena 1-10.\n\n"
            "Zakoncz: Najem to maraton!"
        ),
    },
}

DEFAULT_LANG = "en"


def get_msg(lang: str, key: str) -> str:
    return MESSAGES.get(lang, MESSAGES[DEFAULT_LANG]).get(key, MESSAGES[DEFAULT_LANG].get(key, ""))
