"""
Лёгкое логирование событий для ежедневного отчёта админу.

Append-only JSONL файл (тот же паттерн, что уже использовался для
referral_events.jsonl) — каждое событие это одна строка JSON. Не требует
новой инфраструктуры (БД, внешний сервис), простой и предсказуемый формат.

ВАЖНО — известное ограничение: metrics_events.jsonl живёт на локальном
диске Render, который эфемерный (не переживает деплой/рестарт процесса,
и не расшарен между несколькими сервисами, если их несколько). Если бот
перезапустится в середине дня, накопленные за этот день события будут
потеряны, и следующий отчёт покажет заниженные цифры. Это приемлемо для
чисто наблюдательных метрик (не критично, если "проверок сегодня" будет
неточным после рестарта), но НЕ подходит для чего-либо, что требует
гарантированной сохранности (платежи, балансы — те уже идут через
Supabase, не через этот файл).
"""

import os
import json
import time
import logging

logger = logging.getLogger(__name__)

METRICS_FILE = "metrics_events.jsonl"

# Максимальный размер файла, после которого начинаем ротацию (оставляем
# только последние N строк) — без этого файл рос бы бесконечно на
# долгоживущем процессе.
MAX_LINES = 20000
TRIM_TO_LINES = 10000


def log_event(event_type: str, **fields) -> None:
    """
    Записывает одну строку события. Никогда не бросает исключение —
    сбой метрик не должен ронять основную логику бота (тот же принцип,
    что и у alert_admin).
    """
    try:
        entry = {"ts": time.time(), "type": event_type, **fields}
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("log_event failed for %s: %s", event_type, e)


def _maybe_trim_file() -> None:
    """Обрезает файл до последних TRIM_TO_LINES строк, если он вырос
    больше MAX_LINES. Вызывается лениво из get_daily_summary, не на
    каждую запись — дешевле."""
    try:
        if not os.path.exists(METRICS_FILE):
            return
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > MAX_LINES:
            with open(METRICS_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines[-TRIM_TO_LINES:])
    except Exception as e:
        logger.warning("metrics file trim failed: %s", e)


def get_daily_summary(hours: int = 24) -> dict:
    """
    Читает METRICS_FILE и агрегирует события за последние `hours` часов.

    Возвращает словарь с посчитанными метриками. Работает даже если файла
    ещё нет (например, только что после деплоя) — возвращает нули, а не
    падает.
    """
    _maybe_trim_file()

    cutoff = time.time() - hours * 3600
    counts = {
        "new_users": 0,
        "analyses_completed": 0,
        "analyses_failed": 0,
        "photos_analyzed": 0,
        "pdfs_generated": 0,
        "letters_generated": 0,
        "payments_completed": 0,
        "alerts_fired": set(),
    }

    if not os.path.exists(METRICS_FILE):
        counts["alerts_fired"] = []
        return counts

    try:
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("ts", 0) < cutoff:
                    continue

                etype = entry.get("type")
                if etype == "new_user":
                    counts["new_users"] += 1
                elif etype == "analysis_completed":
                    counts["analyses_completed"] += 1
                elif etype == "analysis_failed":
                    counts["analyses_failed"] += 1
                elif etype == "photo_analyzed":
                    counts["photos_analyzed"] += 1
                elif etype == "pdf_generated":
                    counts["pdfs_generated"] += 1
                elif etype == "letter_generated":
                    counts["letters_generated"] += 1
                elif etype == "payment_completed":
                    counts["payments_completed"] += 1
                elif etype == "alert_fired":
                    counts["alerts_fired"].add(entry.get("alert_key", "unknown"))
    except Exception as e:
        logger.warning("get_daily_summary failed to read metrics: %s", e)

    counts["alerts_fired"] = sorted(counts["alerts_fired"])
    return counts
