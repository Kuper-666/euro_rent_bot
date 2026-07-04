from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Optional

from .sources import Source
from .storage import LeadRecord

CONTACT_RE = re.compile(
    r"(?P<username>@[A-Za-z0-9_]{5,32})|(?P<email>[\w.+-]+@[\w-]+\.[\w.-]+)|(?P<url>https?://\S+)"
)

PRICE_RE = re.compile(
    r"(\d[\d.,]*)\s*(?:€|EUR|eur|/mo|/month|/мес|/міс|pcm|pw)|"
    r"(?:€|EUR)\s*(\d[\d.,]*)|"
    r"\b(?:аренда|оренда|rent|loyer|huur|affitto|miete|alquiler|aluguer|количество|цена|стоимость)[\s:]*(\d[\d.,]*)",
    re.IGNORECASE,
)

AREA_RE = re.compile(
    r"(\d[\d\s.,]*)\s*(?:m²|м²|м2|m2|sq\.?\s*m|кв\.?\s*м|mq|ft²)",
    re.IGNORECASE,
)

ROOMS_RE = re.compile(
    r"(\d)\s*[-\s]?\s*(?:Zimmer|комн|кімн|rooms?|bedrooms?|chambres?|pièces?|camer|Stanze|habitaciones)|"
    r"(?:T[1-6])\b|"
    r"\b(?:Studio|студия|студія)\b",
    re.IGNORECASE,
)

BEDROOMS_RE = re.compile(
    r"(\d)\s*[-\s]?\s*(?:bedrooms?|beds|spáln[ěí]|schlafzimmer|chambres?|dormitorios)|"
    r"\b(?:Double|Triple|Single)\s+(?:Room|Bed|En)",
    re.IGNORECASE,
)


def truncate(text: str, limit: int = 1600) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."


def extract_contacts(text: str) -> tuple[str, ...]:
    contacts: list[str] = []
    for match in CONTACT_RE.finditer(text):
        value = match.group(0).rstrip(".,;)")
        if value not in contacts:
            contacts.append(value)
    return tuple(contacts[:8])


def extract_price(text: str) -> Optional[str]:
    area_ranges = [(m.start(), m.end()) for m in AREA_RE.finditer(text)]
    for m in PRICE_RE.finditer(text):
        overlaps_area = any(s <= m.start() < e or s < m.end() <= e for s, e in area_ranges)
        if overlaps_area:
            continue
        for g in m.groups():
            if g:
                raw = re.sub(r"\s+", "", g)
                if not raw:
                    continue
                price = raw.replace(",", ".")
                if "." in price and price.count(".") == 1 and len(price.split(".")[1]) == 3:
                    price = price.replace(".", "")
                try:
                    val = float(price)
                    if 50 <= val <= 50000:
                        return f"{val:.0f}"
                except ValueError:
                    continue
    return None


def extract_area(text: str) -> Optional[str]:
    m = AREA_RE.search(text)
    if m:
        area = re.sub(r"\s+", "", m.group(1)).replace(",", ".")
        try:
            return f"{float(area):.0f}"
        except ValueError:
            pass
    return None


def extract_rooms(text: str) -> Optional[str]:
    m = ROOMS_RE.search(text)
    if m:
        if m.group(0).upper().startswith("T") and m.group(0)[1:2].isdigit():
            return m.group(0)
        if m.group(1):
            return m.group(1)
    if "studio" in text.lower() or "студия" in text.lower() or "студія" in text.lower():
        return "студия"
    return None


def extract_bedrooms(text: str) -> Optional[str]:
    m = BEDROOMS_RE.search(text)
    if m and m.group(1):
        return m.group(1)
    m = re.search(r"(\d)\s*(?:спальн|спален|спальня)", text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def extract_details(text: str) -> dict[str, Optional[str]]:
    return {
        "price": extract_price(text),
        "area": extract_area(text),
        "rooms": extract_rooms(text),
        "bedrooms": extract_bedrooms(text),
    }


def format_lead(source: Source, lead: LeadRecord) -> str:
    contacts = extract_contacts(lead.text)
    contact_line = ", ".join(html.escape(item) for item in contacts) if contacts else "не найдены"
    keywords = ", ".join(html.escape(item) for item in lead.keywords[:5])
    date_text = lead.message_date
    try:
        date_text = datetime.fromisoformat(lead.message_date).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        pass

    details = extract_details(lead.text)
    detail_parts = []
    if details["price"]:
        detail_parts.append(f"💰 {details['price']} EUR")
    if details["area"]:
        detail_parts.append(f"📐 {details['area']} м2")
    if details["rooms"]:
        detail_parts.append(f"🚪 {details['rooms']}")
    if details["bedrooms"]:
        detail_parts.append(f"🛏 {details['bedrooms']} спален")
    detail_line = " · ".join(detail_parts) if detail_parts else ""

    link_line = f'\n<a href="{html.escape(lead.link)}">🔗 Перейти к объявлению</a>' if lead.link else ""
    excerpt = html.escape(truncate(lead.text, 500))

    lines = [
        f"🏠 <b>Новое объявление</b> · score {lead.score}",
        f"📌 <b>{html.escape(source.title)}</b> · {html.escape(date_text)}",
    ]
    if detail_line:
        lines.append(detail_line)
    lines.append(f"🔑 <b>Совпало:</b> {keywords}")
    lines.append(f"📞 <b>Контакты:</b> {contact_line}")
    lines.append(link_line)
    lines.append(f"\n{excerpt}")
    lines.append(f"\n🤖 <i>Проверить скрытые платежи → </i>@expat_rent_bot")

    return "\n".join(lines)
