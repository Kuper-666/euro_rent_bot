"""
Генератор ответов арендодателю через Groq.
Ответ на конкретное сообщение или запрос от арендодателя.
"""
import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

REPLY_PROMPTS = {
    "de": """Du bist ein professioneller Vermieter-Assistent in Europa. Schreibe eine höfliche, professionelle Antwort an den Vermieter auf DEUTSCH.

Profil des Mieters:
{profile}

Nachricht des Vermieters / Inserat:
{landlord_message}

Anweisungen:
1. Beginne mit einer höflichen Begrüßung.
2. Bestätige das Interesse an der Wohnung.
3. Erwähne relevante Qualifikationen (Beruf, Einkommen, Zuverlässigkeit).
4. Biete einen Besichtigungstermin an.
5. Sei kurz und bündig (100-150 Wörter).
6. Verwende keine Schablonen-Phrasen.

Sende nur den Antworttext, ohne Kommentare.""",
    "en": """You are a professional rental assistant in Europe. Write a polite, professional reply to the landlord in ENGLISH.

Tenant profile:
{profile}

Landlord message / listing:
{landlord_message}

Instructions:
1. Start with a polite greeting.
2. Confirm interest in the apartment.
3. Mention relevant qualifications (profession, income, reliability).
4. Offer to schedule a viewing.
5. Keep it concise (100-150 words).
6. Do not use template phrases.

Send only the reply text, no comments or introductions.""",
}


def generate_reply(profile: dict, landlord_message: str, lang: str = "de") -> str | None:
    """Генерирует ответ арендодателю через Groq."""
    if not client:
        return None

    prompt_template = REPLY_PROMPTS.get(lang, REPLY_PROMPTS["de"])

    field_labels = {
        "full_name": "Имя / Name",
        "profession": "Профессия / Occupation",
        "income": "Доход (нетто/мес) / Monthly net income",
        "employer": "Работодатель / Employer",
        "move_in_date": "Дата переезда / Move-in date",
        "occupants": "Жильцы / Occupants",
        "pets": "Питомцы / Pets",
        "rental_duration": "Срок аренды / Rental duration",
    }
    profile_lines = []
    for k, v in profile.items():
        if v and k in field_labels:
            profile_lines.append(f"- {field_labels[k]}: {v}")
    profile_text = "\n".join(profile_lines) if profile_lines else "Данные не указаны"

    prompt = prompt_template.format(
        profile=profile_text,
        landlord_message=landlord_message[:2000],
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Reply generation error: %s", e)
        return None
