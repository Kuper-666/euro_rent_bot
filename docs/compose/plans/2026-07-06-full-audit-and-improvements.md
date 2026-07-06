# Полный аудит EuroRent AI — Баги, Улучшения, Конкуренты

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent or compose:execute to implement this plan task-by-task.

**Goal:** Исправить все найденные баги, устранить недоработки и добавить функции конкурентов.

**Architecture:** Модульная структура: bot.py (хендлеры), storage.py (Supabase/JSON), handlers/ (фичи), web_scanner/ (парсеры), services/ (клавиатуры).

**Tech Stack:** Python 3.11, python-telegram-bot v20, Supabase, Groq LLaMA 3.3, APScheduler, BeautifulSoup

---

## ТАБЛИЦА 1: Найденные баги (приоритеты)

| # | Серьёзность | Файл | Проблема | Статус |
|---|-------------|------|----------|--------|
| 1 | 🔴 Критично | Docs.txt | Содержит пароль Supabase и JWT — не в .gitignore | Нужно исправить |
| 2 | 🔴 Критично | rls_policies.sql | Anon read access на Users/UrlTokens/PendingListings | Нужно исправить |
| 3 | 🔴 Критично | setup_tables.sql | Нет CREATE TABLE для Users и PendingListings | Нужно исправить |
| 4 | 🔴 Критично | 6 файлов | Нет Supabase таблиц: email_subscribers, posted_listings, referral_events | Нужно исправить |
| 5 | 🟡 Средне | listing_features.py | Supabase client создаётся заново каждый вызов | Нужно исправить |
| 6 | 🟡 Средне | bot.py | Нет html.escape() для AI-текста в parse_mode=HTML | Нужно исправить |
| 7 | 🟡 Средне | bot.py | Блокирующий fetch_url_text() в async handler | Нужно исправить |
| 8 | 🟡 Средне | storage.py | Race condition при concurrent записи | Нужно исправить |
| 9 | 🟡 Средне | 6 файлов | 6 отдельных Supabase клиентов вместо одного | Нужно исправить |
| 10 | 🟢 Низко | bot.py | Dead code: _pending_listings,冗余ные re-imports | Убрать |
| 11 | 🟢 Низко | config.py | Неиспользуемые: WEBHOOK_URL, OSRM_URL, WEB_SCANNER_INTERVAL | Убрать |
| 12 | 🟢 Низко | .env.example | 16 переменных не задокументированы | Добавить |
| 13 | 🟢 Низко | handlers/user_features.py | remove_tracker_entry() нигде не вызывается | Убрать |
| 14 | 🟢 Низко | email_newsletter.py | Использует блокирующий smtplib в async | Заменить |
| 15 | 🟢 Низко | daily_poster.py | Bot создаётся при import — падает без токена | Исправить |

---

## ТАБЛИЦА 2: Сравнение с конкурентами

| Фича | EuroRent AI | RentSlam | Stekkies | Rentbird | Uprent | RentHunter |
|-------|-------------|----------|----------|----------|--------|------------|
| **Страны** | 9 (DE,AT,CZ,PL,IT,ES,PT,NL,HU,UK) | NL | NL+DE | NL | NL | NL |
| **Источники** | 22 TG каналов + веб | 1000+ | 1000+ | 1400+ | 240+ | 1100+ |
| **AI-анализ** | ✅ 7 блоков (цена, мошенники, документы, право) | ❌ | ❌ | ❌ | ✅ AI-apply | ✅ AI-apply |
| **Оценка рисков** | ✅ 🟢🟡🔴 + 1-10 | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Языки** | RU,UK,EN,DE,PL | NL,EN | EN | NL,EN | EN,NL,RU | EN |
| **Цена входа** | ~3 EUR (3 проверки) | 20 EUR/мес | 17 EUR/мес | ~20 EUR/мес | Бесплатно | 35 EUR/мес |
| **PDF (Mieterprofil)** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Мотивационное письмо** | ✅ DE/EN | ❌ | ✅ шаблон | ❌ | ✅ AI | ✅ AI |
| **Ответ арендодателю** | ✅ DE/EN | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Travel time** | ✅ OSRM | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Каналы Telegram** | ✅ 22 | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Скан порталов** | 3 рабочих | 1000+ | 1000+ | 1400+ | 240+ | 1100+ |
| **Брокер услуг** | ❌ | ❌ | ❌ | ✅ Plus | ✅ 499 EUR | ✅ Coached |
| **Мобильное приложение** | ❌ (TG бот) | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Автоподача заявок** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Соцсети скан** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Trustpilot** | — | 4.6 | 4.7 | 4.7 | 4.8 | 4.5 |

---

## ТАБЛИЦА 3: Что можно улучшить/добавить

| # | Приоритет | Фича | Описание | Сложность |
|---|-----------|------|----------|-----------|
| 1 | 🔴 | Безопасность | Убрать Docs.txt из git, ротировать ключи, исправить RLS | 1 день |
| 2 | 🔴 | Supabase миграция | Добавить 3 недостающие таблицы, исправить Users | 1 день |
| 3 | 🔴 | Shared Supabase client | Один клиент вместо 6, кеширование | 2 дня |
| 4 | 🟡 | Исправить парсеры | Funda, Pararius, ImmoScout24 — обойти блокировки | 5 дней |
| 5 | 🟡 | Автоподача заявок | AI-apply как у Uprent/RentHunter | 10 дней |
| 6 | 🟡 | Мобильное приложение | Мини-приложение Telegram | 7 дней |
| 7 | 🟡 | Расширить каналы | Добавить DE/UK/ES/IT Telegram каналы | 3 дня |
| 8 | 🟡 | Соцсети скан | Как у Stekkies — Facebook groups, WhatsApp | 5 дней |
| 9 | 🟢 | Брокер услуг | Партнёрство с агентствами | 14 дней |
| 10 | 🟢 | Аналитика рынка | Графики цен, прогнозы, отчёты | 5 дней |
| 11 | 🟢 | Email-рассылка улучшить | Персонализация, сегментация | 3 дня |
| 12 | 🟢 | Язык IT | Добавить итальянский, чешский | 2 дня |
| 13 | 🟢 | Push-уведомления | Через Telegram Mini App | 5 дней |
| 14 | 🟢 | Юридическая консультация | AI-консультант по правам арендатора | 3 дня |
| 15 | 🟢 | Онлайн-чат с экспертом | Поддержка через бота | 7 дней |

---

## ТАБЛИЦА 4: Преимущества перед конкурентами

| Преимущество | EuroRent AI | Конкуренты |
|--------------|-------------|------------|
| Мультистранность | 9 стран Европы | Только NL (+ DE у Stekkies) |
| AI-глубина анализа | 7 блоков: перевод, цена, мошенники, документы, право, оценка | Фильтрация без анализа |
| Цена входа | 3 EUR за 3 проверки | 17-40 EUR/мес минимум |
| Языки Восточной Европы | RU, UK, PL | Только EN, NL |
| Telegram-интеграция | 22 канала, автопостинг | Нет Telegram-каналов |
| PDF-документы | Mieterprofil, мотивационное письмо | Нет |
| Travel time | OSRM API | Только Stekkies |
| Скан по цене | Бесплатный AI-анализ | Платная подписка |

---

## ЗАДАЧИ ДЛЯ РЕАЛИЗАЦИИ

### Задача 1: Безопасность (1 день)

**Files:**
- Modify: `.gitignore` — добавить `Docs.txt`
- Modify: `rls_policies.sql` — убрать `USING (true)` анонимный доступ
- Modify: `setup_tables.sql` — добавить `CREATE TABLE IF NOT EXISTS "Users"`
- Modify: `setup_tables.sql` — добавить `CREATE TABLE IF NOT EXISTS "PendingListings"`

**Steps:**
- [ ] Добавить `Docs.txt` в `.gitignore`
- [ ] Удалить `Docs.txt` из git tracking: `git rm --cached Docs.txt`
- [ ] Исправить RLS политики — убрать анонимный read
- [ ] Добавить CREATE TABLE для Users и PendingListings
- [ ] Ротировать все ключи (Supabase, Groq)

### Задача 2: Supabase миграция (1 день)

**Files:**
- Create: `setup_tables.sql` — добавить 3 таблицы
- Modify: `email_newsletter.py` — миграция на Supabase
- Modify: `channel_poster.py` — миграция posted_listings на Supabase
- Modify: `bot.py` — миграция referral_events на Supabase

**Steps:**
- [ ] Создать таблицу `EmailSubscribers` в Supabase
- [ ] Создать таблицу `PostedListings` в Supabase
- [ ] Создать таблицу `ReferralEvents` в Supabase
- [ ] Обновить `email_newsletter.py` для работы с Supabase
- [ ] Обновить `channel_poster.py` для хранения в Supabase
- [ ] Обновить `bot.py` для логирования рефералов в Supabase

### Задача 3: Shared Supabase client (2 дня)

**Files:**
- Create: `services/supabase_client.py` — единый клиент
- Modify: `storage.py` — импорт из services
- Modify: `user_features.py` — импорт из services
- Modify: `listing_features.py` — импорт из services
- Modify: `daily_poster.py` — импорт из services
- Modify: `channel_poster.py` — импорт из services
- Modify: `web_scanner/alerts.py` — импорт из services

**Steps:**
- [ ] Создать `services/supabase_client.py` с кешированным клиентом
- [ ] Заменить все 6 одиночных клиентов на импорт из `services/supabase_client.py`
- [ ] Добавить `dns_fix` импорт в `services/supabase_client.py`
- [ ] Протестировать все модули

### Задача 4: HTML escape для AI-текста (1 день)

**Files:**
- Modify: `bot.py:290-310` — добавить escape перед отправкой
- Modify: `handlers/user_features.py:314` — escape для письма
- Modify: `channel_poster.py:193-200` — escape для постов

**Steps:**
- [ ] Добавить `html.escape()` для `safe_result` в `process_listing`
- [ ] Добавить `html.escape()` для текста письма в `generate_letter_command`
- [ ] Добавить `html.escape()` для текста поста в `format_channel_post`
- [ ] Протестировать с кириллицей и спецсимволами

### Задача 5: Async HTTP (1 день)

**Files:**
- Modify: `bot.py` — заменить `fetch_url_text()` на async
- Modify: `utils.py` — добавить async версию `fetch_url_text`

**Steps:**
- [ ] Добавить `async def fetch_url_text_async()` в `utils.py`
- [ ] Заменить вызов в `handle_message` на async версию
- [ ] Заменить `smtplib` на `aiosmtplib` в `email_newsletter.py`

### Задача 6: Убрать dead code (1 день)

**Files:**
- Modify: `bot.py` — удалить `_pending_listings`,冗余ные re-imports
- Modify: `config.py` — удалить `WEBHOOK_URL`, `WEB_SCANNER_INTERVAL`
- Modify: `handlers/user_features.py` — удалить `remove_tracker_entry`
- Modify: `services/keyboards.py` — удалить `_pending_listings`

**Steps:**
- [ ] Удалить мёртвые переменные и функции
- [ ] Удалить冗余ные re-imports в `handle_callback`
- [ ] Добавить все переменные в `.env.example`

### Задача 7: Расширение парсеров (5 дней)

**Files:**
- Modify: `web_scanner/parsers.py` — исправить Pararius, Funda, ImmoScout24

**Steps:**
- [ ] Добавить парсинг через Selenium для Pararius (обход Cloudflare)
- [ ] Исправить RSS-парсер для Funda
- [ ] Добавить парсинг ImmoScout24 через API
- [ ] Добавить правильные URL для NL/DE/UK порталов
- [ ] Протестировать все парсеры

### Задача 8: Автоподача заявок (10 дней)

**Files:**
- Create: `handlers/auto_apply.py` — модуль автоподачи
- Modify: `bot.py` — команда `/auto_apply`
- Modify: `handlers/user_features.py` — профиль для автоподачи

**Steps:**
- [ ] Создать команду `/auto_apply` для настройки
- [ ] Сохранять профиль для автоподачи (имя, email, телефон, мотивация)
- [ ] Генерировать персонализированное письмо через Groq
- [ ] Автоматически отправлять письма арендодателям
- [ ] Логировать отправленные заявки в Supabase

### Задача 9: Telegram Mini App (7 дней)

**Files:**
- Create: `webapp/` — фронтенд для Mini App
- Modify: `bot.py` — команда `/app`

**Steps:**
- [ ] Создать HTML/CSS/JS фронтенд
- [ ] Добавить команду `/app` для открытия Mini App
- [ ] Реализовать форму поиска квартир
- [ ] Показать результаты с AI-анализом
- [ ] Добавить историю поиска

### Задача 10: Расширение каналов (3 дня)

**Files:**
- Modify: `channel_poster.py` — добавить DE/UK/ES каналы
- Modify: `render.yaml` — добавить cron для новых каналов

**Steps:**
- [ ] Найти Telegram каналы по аренде в DE/UK/ES
- [ ] Добавить их в `SCAN_CITIES`
- [ ] Настроить автопостинг для каждого языка
- [ ] Протестировать посты на разных языках

### Задача 11: Документация (2 дня)

**Files:**
- Modify: `.env.example` — все переменные
- Create: `docs/SETUP.md` — инструкция по настройке
- Create: `docs/API.md` — описание API

**Steps:**
- [ ] Добавить все переменные в `.env.example`
- [ ] Написать инструкцию по настройке на Render
- [ ] Документировать Supabase таблицы
- [ ] Описать процесс добавления нового портала

---

## Создаваемые скиллы

### Skill 1: `supabase-migration`
Для миграции данных из локальных JSON в Supabase.

### Skill 2: `parser-debug`
Для отладки и исправления HTML-парсеров порталов.

### Skill 3: `groq-prompt-engineering`
Для оптимизации промптов Groq AI.

### Skill 4: `telegram-bot-testing`
Для тестирования Telegram-ботов с mock-объектами.

---

## Верификация

- [ ] Все тесты проходят: `python -m pytest`
- [ ] Бот подключается к Telegram
- [ ] Supabase таблицы созданы
- [ ] Deep links работают
- [ ] Посты в канал отправляются
- [ ] AI-анализ работает на 5 языках
- [ ] PDF генерируется с кириллицей
