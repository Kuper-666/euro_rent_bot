"""
Единая retry-логика для вызовов Telegram Bot API.

До этого модуля retry был реализован отдельно и по-разному в нескольких
местах (storage.py для Supabase, kb()-подобные функции — нигде для самих
вызовов Telegram), а прямые вызовы bot.send_message/reply_text/
send_document по всему проекту (159+ мест) вообще не ретраились —
единичный TimedOut/NetworkError от Telegram (в том числе на слабом
соединении Render, при пиковой нагрузке на Bot API, или во время
собственных краткосрочных сетевых сбоев) просто терял сообщение
пользователю без какого-либо восстановления.

Использование:
    from telegram_retry import safe_send

    await safe_send(context.bot.send_message, chat_id=123, text="...")
    await safe_send(update.message.reply_text, "...", reply_markup=kb)
    await safe_send(context.bot.send_document, chat_id=123, document=doc)

safe_send() принимает любую bound-корутину Telegram (send_message,
reply_text, reply_photo, send_document, edit_message_text, и т.д.) как
первый аргумент, плюс её обычные args/kwargs — не нужно оборачивать
каждый вызов вручную.
"""

import asyncio
import logging
from telegram.error import TimedOut, NetworkError, RetryAfter, BadRequest

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1


async def safe_send(coro_func, *args, max_retries: int = MAX_RETRIES, **kwargs):
    """
    Вызывает coro_func(*args, **kwargs) с ретраями при транзиентных ошибках.

    Ретраим только то, что имеет смысл повторить:
    - TimedOut / NetworkError — временный сбой сети/Telegram, повтор с
      exponential backoff (1с, 2с, 4с) обычно решает.
    - RetryAfter — Telegram явно говорит, сколько ждать (флуд-контроль);
      ждём ровно столько, сколько попросили, не свой backoff.

    НЕ ретраим (и правильно — повтор не поможет, только теряет время):
    - BadRequest (например, невалидный chat_id, слишком длинный текст).
      ВАЖНО: в этой версии python-telegram-bot BadRequest — подкласс
      NetworkError (issubclass(BadRequest, NetworkError) == True),
      что контринтуитивно и легко пропустить — сначала эта функция сама
      наступила на эти грабли (except (TimedOut, NetworkError) ловил и
      BadRequest тоже, ретраил невалидные запросы 3 раза без толку,
      прежде чем сдаться). Проверяем BadRequest первым и явно.
    - Forbidden (пользователь заблокировал бота — это не сбой, это факт)
    - Любое другое исключение — пробрасывается сразу, не глушится молча.

    Возвращает результат coro_func при успехе. Если все попытки
    исчерпаны, пробрасывает последнее исключение — вызывающий код решает,
    что делать дальше (залогировать, показать пользователю fallback,
    и т.д.), а не теряет сообщение молча.
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await coro_func(*args, **kwargs)
        except BadRequest:
            # Не ретраим — см. докстринг выше про наследование от
            # NetworkError. Пробрасываем сразу же, на первой попытке.
            raise
        except RetryAfter as e:
            last_exception = e
            wait = e.retry_after
            # PTB предупреждает (PTBDeprecationWarning), что в будущей
            # версии retry_after станет datetime.timedelta вместо int —
            # asyncio.sleep() не принимает timedelta напрямую, поэтому
            # конвертируем заранее, чтобы не сломаться на обновлении PTB.
            if hasattr(wait, "total_seconds"):
                wait = wait.total_seconds()
            logger.warning("safe_send: RetryAfter, ждём %ss (attempt %d/%d)", wait, attempt + 1, max_retries)
            if attempt < max_retries - 1:
                await asyncio.sleep(wait)
        except (TimedOut, NetworkError) as e:
            last_exception = e
            delay = BASE_DELAY_SECONDS * (2 ** attempt)
            logger.warning(
                "safe_send: %s, retry through %ss (attempt %d/%d)",
                type(e).__name__, delay, attempt + 1, max_retries,
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)

    logger.error("safe_send: exhausted %d retries, giving up: %s", max_retries, last_exception)
    raise last_exception
