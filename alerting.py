"""
Алерты админу в Telegram при критичных сбоях.

Отдельный модуль, а не переиспользование bot.py's Application/context.bot,
по двум причинам:

1. Нужно вызывать алерты из мест, которые НЕ обязательно выполняются в
   async-контексте с доступом к Application (например, storage.py's
   синхронные функции load_data/save_user, которые сами могут быть внутри
   asyncio.to_thread — там нет живого event loop под рукой без танцев с
   бубном).
2. Прямой HTTP-запрос к Telegram Bot API не зависит от того, жив ли
   Application/webhook в данный момент — если сам webhook отвалился
   (ровно тот случай, который стоил нескольких часов диагностики), алерт
   всё равно должен дойти.

Троттлинг: один и тот же alert_key не отправляется чаще раза в
ALERT_COOLDOWN_SECONDS — иначе при системном сбое (например, Supabase
полностью недоступен) можно получить сотни одинаковых сообщений за
минуты, что и само по себе неприятно, и может привести к рейт-лимиту
Telegram на исходящие сообщения админу.
"""

import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

ALERT_COOLDOWN_SECONDS = 30 * 60  # не чаще раза в 30 минут на один и тот же alert_key

_last_alert_sent = {}


def alert_admin(alert_key: str, message: str) -> None:
    """
    Отправляет короткое сообщение админу через прямой Telegram Bot API,
    с троттлингом по alert_key.

    alert_key — короткий идентификатор типа проблемы (например,
    "pgrst204", "supabase_down", "groq_down") — используется только для
    троттлинга, не отправляется пользователю.

    Никогда не бросает исключение наружу — вызывающий код не должен падать
    из-за того, что сам алертинг не сработал (например, если ADMIN_ID не
    задан, или сеть недоступна одновременно с основной проблемой).
    """
    try:
        now = time.time()
        last_sent = _last_alert_sent.get(alert_key, 0)
        if now - last_sent < ALERT_COOLDOWN_SECONDS:
            return

        admin_id = os.getenv("ADMIN_ID", "")
        token = os.getenv("TELEGRAM_TOKEN", "")
        if not admin_id or not token:
            return

        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": int(admin_id),
                "text": f"🚨 {message}",
            },
            timeout=5,
        )
        if resp.status_code == 200:
            _last_alert_sent[alert_key] = now
        else:
            logger.warning("alert_admin: Telegram API returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        # Алертинг не должен сам стать источником сбоя — тихо логируем и
        # продолжаем. Если это тоже не сработает, по крайней мере в логах
        # Render останется след.
        logger.warning("alert_admin failed for key=%s: %s", alert_key, e)
