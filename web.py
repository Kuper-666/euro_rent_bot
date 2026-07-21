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
    match = re.search(r'(\d[\d\s]*)\s*EUR', text)
    if match:
        return int(match.group(1).replace(' ', ''))
    return None


def _extract_score(text):
    import re
    match = re.search(r'(?:Риск|Score|Оценка|Risk)[^\d]*(\d+)', text)
    return int(match.group(1)) if match else None
