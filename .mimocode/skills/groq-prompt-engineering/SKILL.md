---
name: groq-prompt-engineering
description: Use when optimizing Groq LLM prompts for rental listing analysis, translation, or scam detection
---

# Groq Prompt Engineering Skill

## Overview
Оптимизация промптов для Groq LLaMA 3.3 для анализа объявлений об аренде.

## When to Use
- AI-анализ возвращает неполные данные
- Нужно добавить новый блок в анализ
- Промпт слишком длинный или короткий
- Нужно улучшить качество перевода

## Core Pattern

### Структура промпта (7 блоков)
```
1. ПЕРЕВОД И СУТЬ — перевод + термины
2. РЕАЛЬНАЯ ЦЕНА — breakdown всех платежей
3. СРАВНЕНИЕ С РЫНКОМ — дорого/нормально/дёшево
4. ПРОВЕРКА НА МОШЕННИКОВ — 🟢🟡🔴
5. ДОКУМЕНТЫ — что нужно для подачи
6. ЮРИДИЧЕСКИЕ ТОНКОСТИ — тип договора
7. ЭКСПЕРТНАЯ ОЦЕНКА — 1-10
```

### Пример промпта
```python
system_prompt = (
    "Ты — профессиональный помощник по аренде. "
    "Раздели ответ на 7 блоков:\n\n"
    "1. ПЕРЕВОД И СУТЬ\n"
    "2. РЕАЛЬНАЯ ЦЕНА\n"
    "..."
)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Объявление:\n{listing}"}
    ],
    max_tokens=1500,
)
```

## Quick Reference

| Параметр | Значение | Описание |
|----------|----------|----------|
| model | llama-3.3-70b-versatile | Лучший для анализа |
| max_tokens | 1500 | Достаточно для 7 блоков |
| temperature | 0.7 | Баланс креативности |

## Common Mistakes
- Нет структуры → хаотичный ответ
- Слишком длинный промпт → обрезка
- Нет примеров → непредсказуемый формат
- Игнорирование языка → ответ не на нужном языке
