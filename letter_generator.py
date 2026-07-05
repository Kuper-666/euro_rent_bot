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
    "de": """Du bist ein Experte für die Erstellung von Mietanträgen (Bewerbungsschreiben) in Deutschland.
Erstelle ein professionelles, höfliches Anschreiben auf Deutsch für eine Mietwohnung.

Adressat: Vermieter / Hausverwaltung
Thema: Bewerbung um die Wohnung

Struktur:
1. Anrede
2. Vorstellung (Name, Beruf, Einkommen)
3. Warum diese Wohnung (Lage, Größe passen)
4. Mietsicherheit (Stabilität, Kaution)
5. Verfügbarkeit / Einzugstermin
6. Grußformel

Stil: Professionell, aber herzlich. Keine Floskeln. Maximal 200 Wörter.

Daten des Bewerbers:
{profile}

Details der Wohnung:
{listing}""",
    "en": """You are an expert at writing rental application cover letters in English.
Write a professional, friendly cover letter for a rental apartment.

Addressee: Landlord / Property Manager
Subject: Rental Application

Structure:
1. Greeting
2. Introduction (name, profession, income)
3. Why this apartment (location, size suit me)
4. Rental security (stability, deposit)
5. Availability / move-in date
6. Closing

Style: Professional but warm. No clichés. Max 200 words.

Applicant details:
{profile}

Apartment details:
{listing}""",
}


def generate_letter(profile: dict, listing_text: str, lang: str = "de") -> str | None:
    """Генерирует мотивационное письмо через Groq."""
    if not client:
        return None

    prompt_template = LETTER_PROMPTS.get(lang, LETTER_PROMPTS["de"])

    profile_text = "\n".join(f"- {k}: {v}" for k, v in profile.items() if v and k not in ("user_id", "created_at", "cover_letter"))
    prompt = prompt_template.format(profile=profile_text, listing=listing_text[:1000])

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Letter generation error: {e}")
        return None
