"""
Генератор мотивационных писем арендодателю через Groq.
"""
import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

LETTER_PROMPTS = {
    "de": """Ты — профессиональный помощник по аренде жилья в Европе. Твоя задача — написать убедительное, тёплое и структурированное мотивационное письмо арендодателю на НЕМЕЦКОМ языке.

Учитывай культурные особенности Германии: формальность и аккуратность.

Используй следующие данные арендатора:
{profile}

Также используй информацию о самом объявлении:
{listing}

Инструкции к написанию:
1. Начни с вежливого приветствия арендодателя (Sehr geehrte Damen und Herren).
2. Кратко представься (имя и профессия).
3. Объясни, почему тебя заинтересовала именно эта квартира.
4. Укажи стабильный доход и ответственность.
5. Упомяни долгосрочный срок аренды и готовность сразу заехать.
6. Заверши предложением связаться для просмотра.

Длина: 150–200 слов. Язык: строго немецкий.
Не используй шаблонных фраз. Пиши персонализированно.
Отправь только текст письма, без комментариев.""",
    "en": """You are a professional rental assistant in Europe. Write a convincing, warm and structured cover letter to a landlord in ENGLISH.

Use the following tenant data:
{profile}

And the apartment listing information:
{listing}

Instructions:
1. Start with a polite greeting to the landlord.
2. Briefly introduce yourself (name and profession).
3. Explain why this apartment interests you.
4. Mention stable income and responsibility.
5. Mention long-term rental intent and readiness to move in immediately.
6. Close with an offer to arrange a viewing.

Length: 150-200 words. Language: strictly English.
Do not use template phrases. Write personalized content.
Send only the letter text, no comments or introductions.""",
}


def generate_letter(profile: dict, listing_text: str, lang: str = "de") -> str | None:
    """Генерирует мотивационное письмо через Groq."""
    if not client:
        return None

    prompt_template = LETTER_PROMPTS.get(lang, LETTER_PROMPTS["de"])

    field_labels = {
        "full_name": "Имя / Name",
        "profession": "Профессия / Occupation",
        "income": "Доход (нетто/мес) / Monthly net income",
        "employer": "Работодатель / Employer",
        "move_in_date": "Дата переезда / Move-in date",
        "occupants": "Жильцы / Occupants",
        "pets": "Питомцы / Pets",
        "rental_duration": "Срок аренды / Rental duration",
        "preferred_letter_lang": "Язык письма / Language",
    }
    profile_lines = []
    for k, v in profile.items():
        if v and k in field_labels:
            profile_lines.append(f"- {field_labels[k]}: {v}")
    profile_text = "\n".join(profile_lines) if profile_lines else "Данные не указаны"

    prompt = prompt_template.format(
        profile=profile_text,
        listing=listing_text[:1500],
        preferred_language=lang,
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Letter generation error: {e}")
        return None
