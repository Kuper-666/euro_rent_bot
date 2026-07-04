from __future__ import annotations

import re
from dataclasses import dataclass

MIN_SCORE = 3

KEYWORDS: dict[str, int] = {
    # DE Germany
    "wohnung": 5,
    "zu vermieten": 5,
    "mieten": 4,
    "Nebenkosten": 5,
    "Kaltmiete": 4,
    "Warmmiete": 4,
    "Kaution": 4,
    "Schufa": 4,
    "zimmer": 3,
    "Immoscout": 3,
    # EN English
    "apartment": 5,
    "flat": 4,
    "for rent": 4,
    "rental": 3,
    "loft": 3,
    # RU Russian
    "аренда": 4,
    "квартира": 4,
    "снять": 3,
    "м²": 3,
    "кв.м": 3,
    "комнат": 3,
    "студія": 3,
    # PL Poland
    "wynajem": 4,
    "mieszkanie": 4,
    "do wynajęcia": 4,
    "mieszkania": 3,
    # IT Italy
    "affitto": 4,
    "appartamento": 4,
    "casa in affitto": 4,
    # CZ Czech
    "pronájem": 4,
    "byt": 3,
    "k pronájmu": 3,
    # ES Spain
    "alquiler": 4,
    "piso": 4,
    "apartamento": 3,
    # FR France
    "appartement": 3,
    "à louer": 4,
    "location": 3,
    "loyer": 4,
    "meublé": 3,
    "pièces": 3,
    "chambres": 3,
    "studio": 3,
    "surface": 2,
    "disponible": 2,
    "rénové": 2,
    "charges comprises": 3,
    # AT Austria
    "Wohnung Wien": 4,
    # PT Portugal
    "arrendamento": 4,
    "apartamento": 3,
    "alugar": 4,
    "quarto": 3,
    # NL Netherlands
    "huur": 4,
    "te huur": 5,
    "appartement": 3,
    "kamer": 3,
    # HU Hungary
    "kiadó": 4,
    "lakás": 4,
    "albérlet": 4,
    # GR Greece
    "ενοικίαση": 4,
    "διαμέρισμα": 4,
    "μίσθωση": 3,
}

STOP_WORDS: list[str] = [
    "smm", "смм", "маркетинг", "маркетолог", "копирайтер",
    "продажа", "реклама", "услуги", "ремонт", "мебель", "купить", "продаю",
    "срочно", "обмен", "аренда коммерческой", "офис", "склад", "магазин", "помещение",
    "агентство", "риэлтор", "предоплата", "деньги", "перевод", "казино", "ставки",
    "gambling", "onlyfans", "работа", "вакансия", "фриланс",
    # Персидские и арабские
    "اجاره", "آپارتمان", "اتاق", "استودیو", "برلین", "در", "به", "برای", "با", "از", "یک", "دو",
    "قابلیت", "ملده", "ماهانه", "یورو", "منطقه", "طولانی", "موقت", "امکانات", "باشگاه", "ورزشی",
]


@dataclass(frozen=True)
class MatchResult:
    accepted: bool
    score: int
    matched_keywords: tuple[str, ...]
    rejected_by: tuple[str, ...]


def normalize(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    return re.sub(r"\s+", " ", lowered).strip()


def find_terms(text: str, terms: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    normalized = normalize(text)
    matches: list[str] = []
    for term in terms:
        term_normalized = normalize(term)
        if term_normalized and term_normalized in normalized:
            matches.append(term)
    return tuple(matches)


def match_text(text: str) -> MatchResult:
    rejected_by = find_terms(text, tuple(STOP_WORDS))
    if rejected_by:
        return MatchResult(False, 0, (), rejected_by)

    normalized = normalize(text)
    matched: list[str] = []
    score = 0
    for keyword, weight in KEYWORDS.items():
        if normalize(keyword) in normalized:
            matched.append(keyword)
            score += weight

    accepted = score >= MIN_SCORE
    return MatchResult(accepted, score, tuple(matched), ())
