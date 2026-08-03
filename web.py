import os
import json
import time
import logging
from flask import Flask, request, jsonify

from config import MOBILE_API_KEY, GROQ_API_KEY

app = Flask(__name__)
logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _load(name):
    path = os.path.join(TEMPLATES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/")
def home():
    return _load("home.html"), 200


@app.route("/b2b")
def b2b():
    return _load("b2b.html"), 200


# ── Mobile app API (EuroRent Lens) ──────────────────────────────────

def _check_api_key():
    """Verify X-Api-Key header matches MOBILE_API_KEY."""
    if not MOBILE_API_KEY:
        return False
    api_key = request.headers.get("X-Api-Key", "")
    return api_key == MOBILE_API_KEY


@app.post("/api/analyze")
def api_analyze():
    """Analyze a rental listing via Groq API."""
    if not _check_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 401

    data = request.get_json(force=True)
    text = data.get("text", "")
    user_id = data.get("user_id", "")
    lang = data.get("lang", "ru")

    if not text or not user_id:
        return jsonify({"error": "text and user_id are required"}), 400

    if not GROQ_API_KEY:
        return jsonify({"error": "GROQ_API_KEY not configured"}), 500

    try:
        import requests as req
        system_prompt = _get_system_prompt(lang)
        full_prompt = f"{system_prompt}\n\nListing text:\n{text}"

        groq_res = req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": full_prompt}],
            },
            timeout=30,
        )

        if groq_res.status_code != 200:
            logger.warning("Groq API failed: %s", groq_res.text[:200])
            return jsonify({"error": "Analysis service unavailable"}), 502

        groq_data = groq_res.json()
        analysis = groq_data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Save to mobile analysis history
        from storage import save_mobile_analysis
        save_mobile_analysis(user_id, text, analysis)

        return jsonify({
            "id": f"analysis_{int(time.time() * 1000)}",
            "text": text,
            "analysis": analysis,
            "city": _extract_city(analysis),
            "price": _extract_price(analysis),
            "score": _extract_score(analysis),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    except Exception as e:
        logger.error("api_analyze error: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@app.post("/api/link-account")
def api_link_account():
    """Link Google account to Telegram user ID."""
    if not _check_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 401

    data = request.get_json(force=True)
    google_user_id = data.get("google_user_id", "")
    email = data.get("email", "")
    telegram_user_id = data.get("telegram_user_id", "")

    if not google_user_id or not telegram_user_id:
        return jsonify({"error": "google_user_id and telegram_user_id required"}), 400

    from storage import link_mobile_account
    ok = link_mobile_account(google_user_id, telegram_user_id, email)
    return jsonify({"ok": ok})


@app.get("/api/history")
def api_history():
    """Get analysis history for a user."""
    if not _check_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 401

    telegram_user_id = request.args.get("user_id", "")
    if not telegram_user_id:
        return jsonify({"error": "user_id is required"}), 400

    from storage import get_mobile_analysis_history
    history = get_mobile_analysis_history(telegram_user_id)
    return jsonify(history)


# ── Telegram account verification ───────────────────────────────────
#
# Раньше /api/link-account принимал telegram_user_id от клиента без какой
# бы то ни было проверки владения — любой пользователь приложения мог
# ввести произвольный (в том числе чужой) Telegram ID и "привязать" его к
# своему Google-аккаунту, получив видимость привязки без реального
# доступа к этому Telegram-аккаунту. Эти три эндпоинта закрывают этот
# пробел: сервер генерирует одноразовый код, отправляет его в Telegram DM
# по указанному ID (только владелец аккаунта увидит код), и требует его
# обратно перед тем, как приложение вызывает /api/link-account.
#
# Коды хранятся в памяти процесса (не в Supabase) — они живут всего
# несколько минут, персистентность не нужна и добавила бы лишнюю
# сложность. Как и все остальные in-memory структуры в этом проекте,
# это не переживает рестарт процесса — приемлемо, потому что просто
# означает "запроси код заново", а не потерю данных.

import random
import threading

_verification_codes = {}
_verification_lock = threading.Lock()
VERIFICATION_CODE_TTL_SECONDS = 300  # 5 минут


def _cleanup_expired_codes():
    now = time.time()
    expired = [k for k, v in _verification_codes.items() if v["expires_at"] < now]
    for k in expired:
        del _verification_codes[k]


@app.post("/api/request-verification")
def api_request_verification():
    """Генерирует код и отправляет его в Telegram DM указанного telegram_user_id.
    Не подтверждает, что telegram_user_id реально существует как пользователь
    бота — если ID невалиден/бот никогда не общался с этим chat_id, Telegram
    вернёт ошибку отправки, и она пробрасывается как code_sent=False."""
    if not _check_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 401

    data = request.get_json(force=True)
    telegram_user_id = data.get("telegram_user_id", "")
    if not telegram_user_id or not telegram_user_id.isdigit():
        return jsonify({"error": "valid numeric telegram_user_id required"}), 400

    code = f"{random.randint(0, 999999):06d}"

    with _verification_lock:
        _cleanup_expired_codes()
        _verification_codes[telegram_user_id] = {
            "code": code,
            "expires_at": time.time() + VERIFICATION_CODE_TTL_SECONDS,
            "attempts": 0,
        }

    try:
        import bot as bot_module
        import asyncio as _asyncio

        async def _send():
            await bot_module.application.bot.send_message(
                chat_id=int(telegram_user_id),
                text=(
                    f"🔐 Код подтверждения для привязки к приложению EuroRent Lens: "
                    f"<b>{code}</b>\n\nНикому не сообщайте этот код. "
                    f"Он действителен {VERIFICATION_CODE_TTL_SECONDS // 60} минут."
                ),
                parse_mode="HTML",
            )

        future = _asyncio.run_coroutine_threadsafe(_send(), bot_module.loop)
        future.result(timeout=10)
        return jsonify({"ok": True})
    except Exception as e:
        logger.warning("Failed to send verification code to %s: %s", telegram_user_id, e)
        with _verification_lock:
            _verification_codes.pop(telegram_user_id, None)
        return jsonify({"error": "Failed to send code — check the Telegram ID is correct "
                                  "and has started a chat with the bot"}), 502


@app.post("/api/verify-telegram")
def api_verify_telegram():
    """Проверяет код и, если верен, линкует аккаунт (тот же эффект, что
    ручной вызов /api/link-account, но только после подтверждённого
    владения)."""
    if not _check_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 401

    data = request.get_json(force=True)
    google_user_id = data.get("google_user_id", "")
    email = data.get("email", "")
    telegram_user_id = data.get("telegram_user_id", "")
    code = data.get("code", "")

    if not google_user_id or not telegram_user_id or not code:
        return jsonify({"error": "google_user_id, telegram_user_id and code required"}), 400

    with _verification_lock:
        _cleanup_expired_codes()
        entry = _verification_codes.get(telegram_user_id)

        if not entry:
            return jsonify({"ok": False, "error": "no pending verification, request a new code"}), 400

        entry["attempts"] += 1
        if entry["attempts"] > 5:
            del _verification_codes[telegram_user_id]
            return jsonify({"ok": False, "error": "too many attempts, request a new code"}), 429

        if entry["code"] != code:
            return jsonify({"ok": False, "error": "incorrect code"}), 400

        # Код верный и одноразовый — удаляем сразу, чтобы его нельзя было
        # использовать повторно даже в пределах TTL.
        del _verification_codes[telegram_user_id]

    from storage import link_mobile_account
    ok = link_mobile_account(google_user_id, telegram_user_id, email)
    return jsonify({"ok": ok})


@app.get("/api/link-status")
def api_link_status():
    """Возвращает telegram_user_id, привязанный к google_user_id (или
    пусто, если привязки ещё нет) — используется для восстановления
    привязки на новом устройстве после переустановки приложения, раз
    локальный SharedPreferences не переживает переустановку."""
    if not _check_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 401

    google_user_id = request.args.get("google_user_id", "")
    if not google_user_id:
        return jsonify({"error": "google_user_id is required"}), 400

    from storage import resolve_mobile_account
    telegram_user_id = resolve_mobile_account(google_user_id)
    return jsonify({"telegram_user_id": telegram_user_id or ""})


def _get_system_prompt(lang):
    prompts = {
        "ru": (
            "Ты — эксперт по аренде жилья в Европе. Проанализируй объявление об аренде и дай:\n"
            "1. Оценка риска (1-10, где 10 — идеально)\n"
            "2. Реальную цену со всеми комиссиями\n"
            "3. Скрытые платежи и риски\n"
            "4. Рекомендации по документам\n"
            "5. Краткий итог (3-5 предложений)\n"
            "Отвечай на русском языке. Будь конкретным и практичен."
        ),
        "en": (
            "You are a European rental housing expert. Analyze this rental listing and provide:\n"
            "1. Risk score (1-10, where 10 is perfect)\n"
            "2. Real price with all fees\n"
            "3. Hidden payments and risks\n"
            "4. Document recommendations\n"
            "5. Brief summary (3-5 sentences)\n"
            "Answer in English. Be specific and practical."
        ),
        "de": (
            "Du bist ein Experte für Mietwohnungen in Europa. Analysiere diese Anzeige und gib:\n"
            "1. Risikobewertung (1-10, wobei 10 perfekt ist)\n"
            "2. Realen Preis mit allen Gebühren\n"
            "3. Versteckte Zahlungen und Risiken\n"
            "4. Dokumentenempfehlungen\n"
            "5. Kurze Zusammenfassung (3-5 Sätze)\n"
            "Antworte auf Deutsch. Sei konkret und praktisch."
        ),
    }
    return prompts.get(lang, prompts["ru"])


def _extract_city(text):
    import re
    match = re.search(r'🏙.*?([A-ZА-Яа-яёЁ][a-zа-яёЁ]+)', text)
    return match.group(1) if match else None


def _extract_price(text):
    import re
    # [ \t]* вместо [\d\s]* — \s включает \n, из-за чего число из
    # предыдущей строки (например "Risk Score: 8") могло случайно
    # склеиться с реальной ценой на следующей строке перед "EUR"
    # (напр. "Score: 8\n1200 EUR" матчилось как "8\n1200" -> ValueError
    # при int()). Ограничиваем совпадение одной строкой и настоящими
    # разделителями тысяч (обычный пробел), а не любым пробельным символом.
    match = re.search(r'(\d[\d ]*)\s*EUR', text)
    if match:
        digits = match.group(1).replace(' ', '')
        if digits.isdigit():
            return int(digits)
    return None


def _extract_score(text):
    import re
    match = re.search(r'(?:Риск|Score|Оценка|Risk)[^\d]*(\d+)', text)
    return int(match.group(1)) if match else None
