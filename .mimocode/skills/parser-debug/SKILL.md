---
name: parser-debug
description: Use when debugging HTML parsers for rental portals, fixing 403/429 errors, or adding new portal support
---

# Parser Debug Skill

## Overview
Отладка и исправление HTML-парсеров для порталов недвижимости (Immowelt, WG-Gesucht, Rightmove, Pararius, Funda, ImmoScout24).

## When to Use
- Парсер возвращает 0 объявлений
- Портал блокирует запросы (403, 429)
- Неправильно парсятся цены или данные
- Нужно добавить новый портал

## Core Pattern

### 1. Проверка доступности портала
```python
import requests
headers = {"User-Agent": "Mozilla/5.0 ..."}
r = requests.get(url, headers=headers, timeout=10)
print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('content-type')}")
print(f"First 500 chars: {r.text[:500]}")
```

### 2. Поиск структуры HTML
```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, "html.parser")
# Ищем карточки
cards = soup.select("[data-testid*=listing], .listing-search-item, article")
# Ищем ссылки на expose
links = soup.select("a[href*='/expose/'], a[href*='/detail/']")
```

### 3. Обход блокировок
- Ротация User-Agent
- Добавление Referer
- Использование RSS вместо HTML
- Selenium для JavaScript-рендеринга
- Undetected-chromedriver для Cloudflare

## Quick Reference

| Портал | Статус | Метод | Проблема |
|--------|--------|-------|----------|
| Immowelt | ✅ | HTML scraping | Немецкие URL |
| WG-Gesucht | ✅ | HTML scraping | Cookie consent |
| Rightmove | ✅ | HTML scraping | Нет цен |
| Pararius | ❌ | Selenium | Cloudflare |
| Funda | ❌ | RSS | 404 |
| ImmoScout24 | ❌ | API | 401 |

## Common Mistakes
- Нет `time.sleep()` между запросами → бан
- Нет fallback при ошибке → крэш
- Неправильный CSS-селектор → 0 результатов
- Игнорирование JavaScript-рендеринга → пустые данные
