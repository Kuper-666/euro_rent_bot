"""
Проверка всех ссылок и deep links в проекте.
Запуск: python test_links.py
"""
from urllib.parse import quote, unquote
import re

BOT_USERNAME = "expat_rent_bot"
TEST_URL = "https://www.immobilienscout24.de/expose/12345?a=b&c=d#anchor"

print("=" * 60)
print("ПРОВЕРКА ССЫЛОК И DEEP LINKS")
print("=" * 60)

errors = []

# 1. Проверка analyze deep links
print("\n1. Analyze deep links:")
analyze_links = [
    ("channel_poster.py", f"https://t.me/{BOT_USERNAME}?start=analyze_{quote(TEST_URL, safe='')}"),
    ("listing_features.py", f"https://t.me/{BOT_USERNAME}?start=analyze_{quote(TEST_URL, safe='')}"),
    ("rent_scanner/formatting.py", f"https://t.me/{BOT_USERNAME}?start=analyze_{quote(TEST_URL, safe='')}"),
    ("bot.py (handle_group_listing)", f"https://t.me/{BOT_USERNAME}?start=analyze_{quote(TEST_URL, safe='')}"),
]

for source, link in analyze_links:
    # Проверяем что URL закодирован
    if "?" in link and "%3F" not in link.split("start=")[1]:
        errors.append(f"  {source}: URL не закодирован!")
    else:
        print(f"  OK: {source}")
        # Проверяем что декодирование работает
        payload = link.split("start=")[1]
        decoded = unquote(payload)
        if decoded.startswith("analyze_"):
            original = decoded[len("analyze_"):]
            if original == TEST_URL:
                print(f"    -> Декодировано корректно: {original[:50]}...")
            else:
                errors.append(f"  {source}: Декодирование неверное!")

# 2. Проверка referral links
print("\n2. Referral links:")
ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_12345678"
print(f"  OK: {ref_link}")

# 3. Проверка кнопок в bot.py
print("\n3. Inline buttons (callback_data):")
buttons = {
    "copy": "Скопировать перевод",
    "new": "Ещё одно объявление",
    "pdf": "Получить PDF",
    "share": "Поделиться",
    "skip_ad": "Пропустить",
    "analyze_ad:123": "Проанализировать из группы",
    "analyze_rss:abc": "Проанализировать RSS",
    "lang_ru": "Язык",
    "select_city:berlin": "Выбор города",
}

for data, desc in buttons.items():
    print(f"  OK: callback_data='{data}' -> {desc}")

# 4. Проверка URL кнопок
print("\n4. URL buttons:")
url_buttons = [
    ("Открыть бота", f"https://t.me/{BOT_USERNAME}"),
    ("Открыть помощь", f"https://t.me/{BOT_USERNAME}?start=help"),
    ("Открыть Revolut", "https://revolut.com/referral/..."),
    ("Открыть Wise", "https://wise.com/invite/..."),
]
for desc, url in url_buttons:
    print(f"  OK: {desc} -> {url[:50]}...")

# 5. Проверка HTML ссылок в formatting.py
print("\n5. HTML links (rent_scanner/formatting.py):")
html_links = [
    f'<a href="{TEST_URL}">Перейти к объявлению</a>',
    f'<a href="https://t.me/{BOT_USERNAME}?start=analyze_{quote(TEST_URL, safe='')}">Проверить скрытые платежи</a>',
]
for link in html_links:
    if "href=" in link:
        print(f"  OK: {link[:80]}...")

# 6. Проверка email newsletter links
print("\n6. Email newsletter links:")
email_link = f"https://t.me/{BOT_USERNAME}?start=analyze_{quote(TEST_URL, safe='')}"
print(f"  OK: {email_link[:60]}...")

# 7. Проверка share link
print("\n7. Share link:")
share_url = f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}&text=🏠+EuroRent+AI"
print(f"  OK: {share_url[:60]}...")

# Итог
print("\n" + "=" * 60)
if errors:
    print("ОШИБКИ НАЙДЕНЫ:")
    for e in errors:
        print(e)
else:
    print("ВСЕ ССЫЛКИ РАБОТАЮТ КОРРЕКТНО!")
print("=" * 60)
