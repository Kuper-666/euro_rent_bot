"""
Реальная проверка состояния бота — Supabase, webhook, планировщик.

Отдельный модуль (не внутри bot.py), потому что и bot.py (для /health
HTTP-эндпоинта), и scheduler.py (для периодической проактивной проверки
с алертом) должны иметь возможность его импортировать. Если бы функция
жила в bot.py, а scheduler.py импортировал её оттуда — это создало бы
циклический импорт, так как bot.py уже импортирует scheduler.py на
верхнем уровне (from scheduler import update_last_activity, register_jobs).
"""

import time
import asyncio


async def run_health_checks(application, webhook_url: str, telegram_token: str) -> tuple[bool, dict]:
    """
    Реальная проверка состояния бота — Supabase, webhook, планировщик.

    Возвращает (overall_ok, checks_dict).
    """
    checks = {}

    try:
        from storage import get_user, _get_mode
        t0 = time.time()
        await asyncio.to_thread(get_user, "__healthcheck__")
        checks["storage"] = {
            "ok": True,
            "mode": _get_mode(),
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }
    except Exception as e:
        checks["storage"] = {"ok": False, "error": str(e)[:200]}

    try:
        info = await application.bot.get_webhook_info()
        expected_url = f"{webhook_url}/{telegram_token}"
        checks["webhook"] = {
            "ok": not info.last_error_message and info.url == expected_url,
            "url_matches_expected": info.url == expected_url,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
            "last_error_date": info.last_error_date.isoformat() if info.last_error_date else None,
        }
    except Exception as e:
        checks["webhook"] = {"ok": False, "error": str(e)[:200]}

    try:
        jobs = application.job_queue.jobs() if application.job_queue else []
        checks["scheduler"] = {"ok": len(jobs) > 0, "job_count": len(jobs)}
    except Exception as e:
        checks["scheduler"] = {"ok": False, "error": str(e)[:200]}

    overall_ok = all(c.get("ok") for c in checks.values())
    return overall_ok, checks
