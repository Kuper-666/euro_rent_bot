from __future__ import annotations

import re
from dataclasses import dataclass

MIN_SCORE = 3

KEYWORDS: dict[str, int] = {
    "wohnung": 5,
    "apartment": 5,
    "flat": 4,
    "zu vermieten": 5,
    "for rent": 4,
    "à louer": 4,
    "alquilar": 3,
    "аренда": 4,
    "квартира": 4,
    "снять": 3,
    "mieten": 4,
    "rental": 3,
    "piso": 3,
    "appartement": 3,
    "Immoscout": 3,
    "Nebenkosten": 5,
    "Kaltmiete": 4,
    "Warmmiete": 4,
    "Kaution": 4,
    "Schufa": 4,
    "provision": 3,
    "м²": 3,
    "кв.м": 3,
    "комнат": 3,
    "zimmer": 3,
    "студія": 3,
    "loft": 3,
}

STOP_WORDS: list[str] = [
    "smm", "смм", "маркетинг", "маркетолог", "копирайтер",
    "продажа", "реклама", "услуги", "ремонт", "мебель", "купить", "продаю",
    "срочно", "обмен", "аренда коммерческой", "офис", "склад", "магазин", "помещение",
    "агентство", "риэлтор", "предоплата", "деньги", "перевод", "казино", "ставки",
    "gambling", "onlyfans", "работа", "вакансия", "фриланс",
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
