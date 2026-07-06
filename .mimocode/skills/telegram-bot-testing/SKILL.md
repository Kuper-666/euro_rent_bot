---
name: telegram-bot-testing
description: Use when testing Telegram bot handlers, mock objects, or debugging callback_data issues
---

# Telegram Bot Testing Skill

## Overview
Тестирование Telegram-ботов с использованием mock-объектов и изолированных тестов.

## When to Use
- Нужно протестировать хендлер без реального Telegram
- Callback_data вызывает крэш
- Нужно проверить все ветки elif-цепочки
- Нужно протестировать deep links

## Core Pattern

### Mock Update/Context
```python
from unittest.mock import MagicMock, AsyncMock

def make_update(text="/start", user_id=123, chat_type="private"):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.first_name = "Test"
    update.effective_chat.type = chat_type
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.reply_photo = AsyncMock()
    return update

def make_context(args=None):
    context = MagicMock()
    context.args = args or []
    context.bot.username = "test_bot"
    context.bot.send_message = AsyncMock()
    return context
```

### Тест хендлера
```python
import pytest
from bot import start

@pytest.mark.asyncio
async def test_start_without_args():
    update = make_update("/start")
    context = make_context()
    await start(update, context)
    update.message.reply_text.assert_called_once()
```

### Тест callback_data
```python
@pytest.mark.asyncio
async def test_filter_callback():
    update = make_update()
    update.callback_query = MagicMock()
    update.callback_query.data = "filter:furnished"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    context = make_context()
    await handle_callback(update, context)
    update.callback_query.answer.assert_called_once()
```

## Quick Reference

| Компонент | Mock |
|-----------|------|
| Update | `MagicMock()` с атрибутами |
| Context | `MagicMock()` с args, bot |
| Message | `MagicMock()` с text, reply_text |
| CallbackQuery | `MagicMock()` с data, answer |

## Common Mistakes
- Забыли `await` → тест проходит но хендлер не вызывается
- Нет `AsyncMock` для async функций → крэш
- Не проверяют все ветки elif → пропущенные баги
- Hardcode callback_data → ломается при изменении
