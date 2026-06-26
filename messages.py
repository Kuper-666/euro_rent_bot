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
            "Бесплатный тест: 3 проверки без оплаты.\n\n"
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
            "Официальная страница: euro-rent-bot.onrender.com\n\n"
            "Готов начать? Просто пришли мне любое объявление прямо сейчас!"
        ),
        "analyzing": "Анализирую объявление...",
        "fetching_url": "Открываю ссылку...",
        "ocr_processing": "Распознаю текст со скриншота...",
        "limit_reached": (
            "Лимит бесплатных проверок\n\n"
            "Вы использовали все 3 бесплатные проверки.\n\n"
            "Оплата через Telegram Stars:\n"
            "1 проверка — 100 Stars -> /pay_stars_3\n"
            "5 проверок — 250 Stars -> /pay_stars_9\n"
            "Безлимит/мес — 500 Stars -> /pay_stars_19"
        ),
        "pay_done_3": "Оплата подтверждена! Добавлена 1 проверка. Осталось: {}.",
        "pay_done_9": "Оплата подтверждена! Добавлено 5 проверок. Осталось: {}.",
        "pay_done_19": "Оплата подтверждена! Безлимитный доступ на месяц активирован!",
        "pay_not_used": "Вы ещё не использовали бота. Сначала отправьте объявление.",
        "no_balance": "У вас нет доступных проверок. Купите пакет: /help",
        "error": "Ошибка: {}",
        "send_listing": "Отправь текст объявления или ссылку.",
        "share_text": "Поделиться с другом:",
        "analysis_done": "Анализ готов!",
        "affiliate_footer": "",
        "pdf_intro": "PDF-заявление (Mieterprofil) — 5€\n\nОтправьте данные для заявления:\n- Имя и фамилия\n- Дата рождения\n- Телефон\n- Email\n- Текущий адрес\n- Работодатель\n- Доход (нетто)\n- Количество жильцов",
        "pdf_need_data": "Заполните данные для заявления:\n\n1. Имя и фамилия\n2. Дата рождения\n3. Телефон\n4. Email\n5. Текущий адрес\n6. Работодатель\n7. Доход (нетто/мес)\n8. Количество жильцов\n\nОтправьте все данные одним сообщением.",
        "pdf_generating": "Генерирую PDF...",
        "pdf_done": "Готово! PDF с заявлением на аренду отправлен.",
        "pdf_error": "Ошибка при генерации PDF: {}",
        "vip_intro": "VIP-подписка — 15EUR/мес\n\nЕжедневная подборка объявлений по вашим критериям.\n\nЧто входит:\n- До 10 проверенных объявлений в день\n- Фильтр по городу, цене, площади\n- Предупреждения о мошенниках\n- Безлимитные проверки",
        "pay_done_vip": "VIP активирован!\n\nОтправьте мне критерии поиска:\n- Город\n- Макс. цена\n- Мин. площадь\n- Количество комнат",
        "vip_ask_criteria": "Отправьте критерии поиска:\n\n- Город\n- Макс. цена (EUR/мес)\n- Мин. площадь (м2)\n- Количество комнат\n\nПример: Берлин, 800EUR, 40м2, 2 комнаты",
        "system_prompt": (
            "Ты — профессиональный консультант по недвижимости с 10-летним опытом в Европе. "
            "Отвечай на русском языке.\n\n"
            "Раздели ответ на 5 блоков:\n\n"
            "1. Краткий пересказ — суть объявления за 1 предложение (метраж, комнаты, цена, этаж).\n\n"
            "2. Реальная цена и сравнение с рынком — посчитай полную стоимость с учётом коммуналки, депозита и парковки. "
            "Сравни со средней рыночной ценой в районе.\n\n"
            "3. Анализ района и инфраструктуры — есть ли рядом магазины (Aldi, Lidl, Rewe), транспорт (U-Bahn, S-Bahn), "
            "шумный ли район. Если район не указан — порекомендуй проверить в Google Maps.\n\n"
            "4. Документы и риски — перечисли документы для этой страны (Schufa, Gehaltsnachweise и т.д.). "
            "Отметь красные флаги.\n\n"
            "5. Совет от эксперта — 2-3 вопроса владельцу перед подписанием. Оценка от 1 до 10.\n\n"
            "Заверши фразой: Аренда — это марафон, а не спринт. Проверяй каждый пункт перед подписанием!"
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
            "Безкоштовний тест: 3 перевірки без оплати.\n\n"
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
            "Готові почати? Просто пришліть мені будь-яке оголошення прямо зараз!"
        ),
        "analyzing": "Аналізую оголошення...",
        "fetching_url": "Відкриваю посилання...",
        "ocr_processing": "Розпізнаю текст зі скріншота...",
        "limit_reached": (
            "Ліміт безкоштовних перевірок\n\n"
            "Ви використали всі 3 безкоштовні перевірки.\n\n"
            "Оплата через Telegram Stars:\n"
            "1 перевірка — 100 Stars -> /pay_stars_3\n"
            "5 перевірок — 250 Stars -> /pay_stars_9\n"
            "Безліміт/міс — 500 Stars -> /pay_stars_19"
        ),
        "pay_done_3": "Оплата підтверджена! Додано 1 перевірку. Залишилось: {}.",
        "pay_done_9": "Оплата підтверджена! Додано 5 перевірок. Залишилось: {}.",
        "pay_done_19": "Оплата підтверджена! Безлімітний доступ на місяць активовано!",
        "pay_not_used": "Ви ще не користувались ботом. Спочатку надішліть оголошення.",
        "no_balance": "У вас немає доступних перевірок. Купіть пакет: /help",
        "error": "Помилка: {}",
        "send_listing": "Надішліть текст оголошення або посилання.",
        "share_text": "Поділитися з другом:",
        "analysis_done": "Аналіз готовий!",
        "affiliate_footer": "",
        "pdf_intro": "PDF-заява (Mieterprofil) — 5€\n\nНадішліть дані для заяви:\n- Ім'я та прізвище\n- Дата народження\n- Телефон\n- Email\n- Поточна адреса\n- Роботодавець\n- Дохід (нетто)\n- Кількість мешканців",
        "pdf_need_data": "Заповніть дані для заяви:\n\n1. Ім'я та прізвище\n2. Дата народження\n3. Телефон\n4. Email\n5. Поточна адреса\n6. Роботодавець\n7. Дохід (нетто/міс)\n8. Кількість мешканців",
        "pdf_generating": "Генерую PDF...",
        "pdf_done": "Готово! PDF із заявою на оренду надіслано.",
        "pdf_error": "Помилка при генерації PDF: {}",
        "vip_intro": "VIP-підписка — 15EUR/міс\n\nЩоденна підбірка оголошень за вашими критеріями.\n\nЩо входить:\n- До 10 перевірених оголошень на день\n- Фільтр за містом, ціною, площею\n- Попередження про шахраїв\n- Безлімітні перевірки",
        "pay_done_vip": "VIP активовано!\n\nНадішліть мені критерії пошуку:\n- Місто\n- Макс. ціна\n- Мін. площа\n- Кількість кімнат",
        "vip_ask_criteria": "Надішліть критерії пошуку:\n\n- Місто\n- Макс. ціна (EUR/міс)\n- Мін. площа (м2)\n- Кількість кімнат\n\nПриклад: Берлін, 800EUR, 40м2, 2 кімнати",
        "system_prompt": (
            "Ти — професійний консультант з нерухомості з 10-річним досвідом в Європі. "
            "Відповідай українською мовою.\n\n"
            "Розділи відповідь на 5 блоків:\n\n"
            "1. Короткий переказ — суть оголошення за 1 речення.\n\n"
            "2. Реальна ціна та порівняння з ринком — підрахуй повну вартість з комуналкою, депозитом та парковкою.\n\n"
            "3. Аналіз району та інфраструктури — магазини, транспорт, шум.\n\n"
            "4. Документи та ризики — документи для країни + червоні прапорці.\n\n"
            "5. Порада від експерта — 2-3 питання власнику + оцінка від 1 до 10.\n\n"
            "Заверши фразою: Оренда — це марафон, а не спринт!"
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
            "Free trial: 3 checks no payment.\n\n"
            "Learn more — tap /help"
        ),
        "help": (
            "EuroRent AI — smart rental assistant in Europe\n\n"
            "What do I do?\n"
            "I analyze rental listings: translate text, find hidden commissions, check documents and warn about scams.\n\n"
            "How to use me?\n"
            "Simply copy a link from any site (ImmoScout, Rightmove, Idealista) or paste the listing text right here.\n\n"
            "Free test drive\n"
            "You can check 3 listings completely free.\n\n"
            "Packages & Pricing:\n"
            "One-time — 3EUR for 1 check -> /pay_3\n"
            "Economy — 9EUR for 5 checks (save 40%) -> /pay_9\n"
            "Pro — 19EUR for unlimited/month -> /pay_19\n"
            "PDF Application (Mieterprofil) — 5EUR -> /pdf\n"
            "VIP Subscription — 15EUR/month (daily picks) -> /vip\n\n"
            "Official page: euro-rent-bot.onrender.com\n\n"
            "Ready to start? Just send me any listing right now!"
        ),
        "analyzing": "Analyzing listing...",
        "fetching_url": "Opening link...",
        "ocr_processing": "Reading text from screenshot...",
        "limit_reached": (
            "Free Check Limit Reached\n\n"
            "You've used all 3 free checks.\n\n"
            "Pay with Telegram Stars:\n"
            "1 check — 100 Stars -> /pay_stars_3\n"
            "5 checks — 250 Stars -> /pay_stars_9\n"
            "Unlimited/month — 500 Stars -> /pay_stars_19"
        ),
        "pay_done_3": "Payment confirmed! 1 check added. Remaining: {}.",
        "pay_done_9": "Payment confirmed! 5 checks added. Remaining: {}.",
        "pay_done_19": "Payment confirmed! Unlimited access for 1 month activated!",
        "pay_not_used": "You haven't used the bot yet. Send a listing first.",
        "no_balance": "No checks remaining. Buy a package: /help",
        "error": "Error: {}",
        "send_listing": "Send a listing text or link.",
        "share_text": "Share with a friend:",
        "analysis_done": "Analysis complete!",
        "affiliate_footer": "",
        "pdf_intro": "PDF Application (Mieterprofil) — 5EUR\n\nSend your data:\n- Full name\n- Date of birth\n- Phone\n- Email\n- Current address\n- Employer\n- Income (net)\n- Number of occupants",
        "pdf_need_data": "Fill in your application data:\n\n1. Full name\n2. Date of birth\n3. Phone\n4. Email\n5. Current address\n6. Employer\n7. Income (net/month)\n8. Number of occupants",
        "pdf_generating": "Generating PDF...",
        "pdf_done": "Done! PDF rental application sent.",
        "pdf_error": "PDF generation error: {}",
        "vip_intro": "VIP Subscription — 15EUR/month\n\nDaily curated list of listings matching your criteria.\n\nWhat's included:\n- Up to 10 verified listings per day\n- Filter by city, price, area\n- Scam alerts\n- Unlimited checks",
        "pay_done_vip": "VIP activated!\n\nSend me your search criteria:\n- City\n- Max. price\n- Min. area\n- Number of rooms",
        "vip_ask_criteria": "Send your search criteria:\n\n- City\n- Max. price (EUR/month)\n- Min. area (m2)\n- Number of rooms\n\nExample: Berlin, 800EUR, 40m2, 2 rooms",
        "system_prompt": (
            "You are a professional real estate consultant with 10 years of experience in Europe. "
            "Respond in English.\n\n"
            "Divide the response into 5 blocks:\n\n"
            "1. Brief summary — the essence in 1 sentence.\n\n"
            "2. Real price and market comparison — calculate total cost including utilities, deposit, parking.\n\n"
            "3. Neighborhood and infrastructure — shops, transport, noise level.\n\n"
            "4. Documents and risks — list documents needed + red flags.\n\n"
            "5. Expert advice — 2-3 questions to landlord + score from 1 to 10.\n\n"
            "End with: Renting is a marathon, not a sprint!"
        ),
    },
    "de": {
        "start": (
            "Hallo! Ich bin EuroRent AI — dein persoenlicher Miet-Detector in Europa.\n\n"
            "Schick mir einfach einen Link zu einem Angebot oder kopiere den Text — ich mache in 5 Sekunden eine Analyse.\n\n"
            "Was ich kann:\n"
            "- Uebersetze Angebote\n"
            "- Zeige versteckte Gebuehren\n"
            "- Sage dir, welche Dokumente noetig sind\n"
            "- Warne vor Betrug\n\n"
            "Kostenloser Test: 3 Pruefungen ohne Zahlung.\n\n"
            "Mehr dazu — druecke /help"
        ),
        "help": (
            "EuroRent AI — smarter Miet-Assistent in Europa\n\n"
            "Analysiere Mietangebote, finde versteckte Provisionen, pruefe Dokumente.\n\n"
            "Kostenloser Testlauf — 3 Angebote komplett kostenlos.\n\n"
            "Pakete & Preise:\n"
            "Einmalig — 3EUR fuer 1 Pruefung -> /pay_3\n"
            "Economy — 9EUR fuer 5 Pruefungen (-40%) -> /pay_9\n"
            "Pro — 19EUR fuer unbegrenzt/Monat -> /pay_19\n"
            "PDF-Antrag (Mieterprofil) — 5EUR -> /pdf\n"
            "VIP-Abo — 15EUR/Monat (taegliche Angebote) -> /vip\n\n"
            "Bereit? Schick mir ein Angebot!"
        ),
        "analyzing": "Analysiere Angebot...",
        "fetching_url": "Oeffne Link...",
        "ocr_processing": "Erkenne Text vom Screenshot...",
        "limit_reached": (
            "Kostenlose Pruefungen aufgebraucht\n\n"
            "Bezahlen mit Telegram Stars:\n"
            "1 Pruefung — 100 Stars -> /pay_stars_3\n"
            "5 Pruefungen — 250 Stars -> /pay_stars_9\n"
            "Unbegrenzt/Monat — 500 Stars -> /pay_stars_19"
        ),
        "pay_done_3": "Zahlung bestaetigt! 1 Pruefung hinzugefuegt. Verbleibend: {}.",
        "pay_done_9": "Zahlung bestaetigt! 5 Pruefungen hinzugefuegt. Verbleibend: {}.",
        "pay_done_19": "Zahlung bestaetigt! Unbegrenzter Zugang aktiviert!",
        "pay_not_used": "Du hast den Bot noch nicht benutzt.",
        "no_balance": "Keine Pruefungen uebrig: /help",
        "error": "Fehler: {}",
        "send_listing": "Schick einen Angebotstext oder Link.",
        "share_text": "Mit einem Freund teilen:",
        "analysis_done": "Analyse abgeschlossen!",
        "affiliate_footer": "",
        "pdf_intro": "PDF-Antrag (Mieterprofil) — 5EUR\n\nSchick deine Daten:\n- Name\n- Geburtsdatum\n- Telefon\n- Email\n- Adresse\n- Arbeitgeber\n- Einkommen\n- Bewohner",
        "pdf_need_data": "Fuelle deine Daten aus:\n\n1. Name\n2. Geburtsdatum\n3. Telefon\n4. Email\n5. Adresse\n6. Arbeitgeber\n7. Einkommen\n8. Bewohner",
        "pdf_generating": "Erstelle PDF...",
        "pdf_done": "Fertig! PDF-Mietantrag gesendet.",
        "pdf_error": "PDF-Fehler: {}",
        "vip_intro": "VIP-Abo — 15EUR/Monat\n\nTaegliche Auswahl heisser Angebote.\n\nEnthalten:\n- Bis zu 10 gepruefte Angebote pro Tag\n- Filter nach Stadt, Preis, Flaeche\n- Betrugswarnungen\n- Unbegrenzte Pruefungen",
        "pay_done_vip": "VIP aktiviert!\n\nSchick mir deine Suchkriterien:\n- Stadt\n- Max. Preis\n- Min. Flaeche\n- Zimmer",
        "vip_ask_criteria": "Suchkriterien:\n\n- Stadt\n- Max. Preis (EUR/Monat)\n- Min. Flaeche (m2)\n- Zimmer",
        "system_prompt": (
            "Du bist ein professioneller Immobilienberater mit 10 Jahren Erfahrung in Europa. "
            "Antworte auf Deutsch.\n\n"
            "5 Bloecke:\n\n"
            "1. Kurze Zusammenfassung.\n\n"
            "2. Realer Preis und Marktvergleich.\n\n"
            "3. Stadtteil-Analyse.\n\n"
            "4. Dokumente und Risiken.\n\n"
            "5. Expertenrat + Bewertung 1-10.\n\n"
            "Beende mit: Mieten ist ein Marathon, kein Sprint!"
        ),
    },
    "pl": {
        "start": (
            "Czesc! Jestem EuroRent AI — twoj detektor najmu w Europie.\n\n"
            "Wyslij mi link lub tekst — cale analize w 5 sekund.\n\n"
            "Co umiem:\n"
            "- Tlumacze oferty\n"
            "- Pokazuje ukryte oplaty\n"
            "- Podpowiadam dokumenty\n"
            "- Sprawdzam oszustwa\n\n"
            "Darmowy test: 3 sprawdzenia.\n\n"
            "Wiecej — /help"
        ),
        "help": (
            "EuroRent AI — inteligentny asystent najmu w Europie\n\n"
            "Analizuje oferty, znajduje ukryte prowizje, sprawdza dokumenty.\n\n"
            "Bezplatny test — 3 oferty calekowicie za darmo.\n\n"
            "Pakiety i ceny:\n"
            "Jednorazowy — 3EUR za 1 sprawdzenie -> /pay_3\n"
            "Economy — 9EUR za 5 sprawdzen (-40%) -> /pay_9\n"
            "Pro — 19EUR za nieograniczony/mies -> /pay_19\n"
            "PDF-wniosek (Mieterprofil) — 5EUR -> /pdf\n"
            "VIP — 15EUR/mies (codzienne listy) -> /vip\n\n"
            "Gotowy? Wyslij mi oferte!"
        ),
        "analyzing": "Analizuje oferte...",
        "fetching_url": "Otwieram link...",
        "ocr_processing": "Rozpoznaje tekst ze zrzutu...",
        "limit_reached": (
            "Wyczerpane darmowe sprawdzenia\n\n"
            "Platnosc przez Telegram Stars:\n"
            "1 sprawdzenie — 100 Stars -> /pay_stars_3\n"
            "5 sprawdzen — 250 Stars -> /pay_stars_9\n"
            "Nieograniczony/mies — 500 Stars -> /pay_stars_19"
        ),
        "pay_done_3": "Platnosc potwierdzona! Dodano 1 sprawdzenie. Pozostalo: {}.",
        "pay_done_9": "Platnosc potwierdzona! Dodano 5 sprawdzen. Pozostalo: {}.",
        "pay_done_19": "Platnosc potwierdzona! Nieograniczony dostep aktywowany!",
        "pay_not_used": "Nie korzystales jeszcze z bota.",
        "no_balance": "Brak sprawdzen: /help",
        "error": "Blad: {}",
        "send_listing": "Wyslij tekst oferty lub link.",
        "share_text": "Podziel sie z kolega:",
        "analysis_done": "Analiza gotowa!",
        "affiliate_footer": "",
        "pdf_intro": "PDF-wniosek (Mieterprofil) — 5EUR\n\nWyslij dane:\n- Imie i nazwisko\n- Data urodzenia\n- Telefon\n- Email\n- Adres\n- Pracodawca\n- Dochod\n- Liczba mieszkancow",
        "pdf_need_data": "Wypelnij dane:\n\n1. Imie i nazwisko\n2. Data urodzenia\n3. Telefon\n4. Email\n5. Adres\n6. Pracodawca\n7. Dochod\n8. Liczba mieszkancow",
        "pdf_generating": "Generuje PDF...",
        "pdf_done": "Gotowe! PDF wyslany.",
        "pdf_error": "Blad PDF: {}",
        "vip_intro": "VIP — 15EUR/mies\n\nCodzienne listy ofert.\n\nCo zawiera:\n- Do 10 sprawdzonych ofert dziennie\n- Filtr po miescie, cenie\n- Ostrzezenia\n- Nieograniczone sprawdzenia",
        "pay_done_vip": "VIP aktywowany!\n\nWyslij kryteria:\n- Miasto\n- Maks. cena\n- Min. powierzchnia\n- Pokoje",
        "vip_ask_criteria": "Kryteria:\n\n- Miasto\n- Maks. cena (EUR/mies)\n- Min. powierzchnia (m2)\n- Pokoje",
        "system_prompt": (
            "Jestes profesjonalnym konsultantem ds. nieruchomosci z 10-letnim doswiadczeniem w Europie. "
            "Odpowiadaj po polsku.\n\n"
            "5 blokow:\n\n"
            "1. Krotkie podsumowanie.\n\n"
            "2. Realna cena i porownanie z rynkiem.\n\n"
            "3. Analiza okolicy.\n\n"
            "4. Dokumenty i ryzyka.\n\n"
            "5. Rada eksperta + ocena 1-10.\n\n"
            "Zakoncz: Najem to maraton, a nie sprint!"
        ),
    },
}

DEFAULT_LANG = "en"


def get_msg(lang: str, key: str) -> str:
    return MESSAGES.get(lang, MESSAGES[DEFAULT_LANG]).get(key, MESSAGES[DEFAULT_LANG].get(key, ""))
