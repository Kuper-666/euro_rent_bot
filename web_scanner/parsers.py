"""
Парсеры для европейских порталов недвижимости.
Поддержка: Immowelt (DE), WG-Gesucht (DE/EU), Rightmove (UK),
           ImmoScout24 (DE), HousingAnywhere (EU).

Все парсеры используют HTML scraping с rotation User-Agent.
"""
import os
import re
import json
import time
import random
import logging
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

REQUEST_TIMEOUT = 15


def _headers(referer: str = "") -> dict:
    h = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    }
    if referer:
        h["Referer"] = referer
    return h


@dataclass
class Listing:
    portal: str
    url: str
    title: str
    price: float
    area: Optional[str]
    rooms: Optional[str]
    city: str
    text: str


def _safe_get(url: str, headers: dict = None, timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
    """GET с обработкой ошибок и ретраями."""
    if headers is None:
        headers = _headers()
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 30))
                logger.warning("Rate limited on %s, waiting %ds", url, wait)
                time.sleep(wait)
                continue
            if r.status_code == 403:
                logger.warning("Blocked on %s (403)", url)
                return None
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            logger.warning("Request error on %s (attempt %d): %s", url, attempt + 1, e)
            time.sleep(2 ** attempt)
    return None


def _parse_price(text: str) -> float:
    """Извлекает цену из текста (EUR)."""
    patterns = [
        r'(\d[\d.,]*)\s*(?:€|EUR|евро)',
        r'(\d[\d.,]*)\s*(?:Kaltmiete|Warmmiete)',
        r'(?:price|preis)[:\s]*(\d[\d.,]*)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            price_str = m.group(1).replace(".", "").replace(",", ".")
            try:
                return float(price_str)
            except ValueError:
                continue
    return 0.0


# ── Immowelt (DE) ──────────────────────────────────────────────

def parse_immowelt(city: str = "berlin", max_price: int = 0) -> list[Listing]:
    """Парсинг Immowelt через HTML scraping."""
    city_slug = city.lower().replace(" ", "-")
    url = f"https://www.immowelt.de/liste/{city_slug}/wohnungen/mieten"
    r = _safe_get(url, _headers("https://www.immowelt.de/"))
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.select('a[href*="/expose/"]')
    listings = []
    seen = set()

    for link in links:
        href = link.get("href", "")
        if not href or href in seen:
            continue
        seen.add(href)

        # Полный URL
        if href.startswith("/"):
            href = "https://www.immowelt.de" + href

        # Извлекаем данные из родительского контейнера
        parent = link.find_parent("div")
        text = parent.get_text(strip=True) if parent else link.get_text(strip=True)

        # Цена
        price = 0.0
        price_match = re.search(r'(\d[\d.,]*)\s*€', text)
        if price_match:
            price = _parse_price(price_match.group(0))

        if max_price and price > max_price and price > 0:
            continue

        # Площадь и комнаты
        area_match = re.search(r'([\d.,]+)\s*m²', text)
        area = area_match.group(1) if area_match else None
        rooms_match = re.search(r'(\d+)\s*Zimmer', text)
        rooms = rooms_match.group(1) if rooms_match else None

        # Заголовок
        title_match = re.search(r'(?:Wohnung|Studio|Haus)\s+[^€\d]*', text)
        title = title_match.group(0).strip()[:80] if title_match else text[:80]

        listings.append(Listing(
            portal="immowelt", url=href, title=title,
            price=price, area=area, rooms=rooms,
            city=city, text=text[:500],
        ))

    logger.info("Immowelt: %d listings from %s", len(listings), city)
    return listings


# ── WG-Gesucht (DE/EU) ────────────────────────────────────────

def parse_wg_gesucht(city: str = "berlin", max_price: int = 0) -> list[Listing]:
    """Парсинг WG-Gesucht (квартиры)."""
    city_map = {
        "berlin": 8, "muenchen": 90, "munich": 90, "hamburg": 55,
        "koeln": 73, "cologne": 73, "frankfurt": 41, "stuttgart": 121,
        "wien": 136, "vienna": 136, "amsterdam": 167,
    }
    city_id = city_map.get(city.lower(), 8)
    url = f"https://www.wg-gesucht.de/wohnungen-in-{city.title()}.{city_id}.2.1.0.html"
    r = _safe_get(url, _headers("https://www.wg-gesucht.de/"))
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("[data-id]")
    listings = []

    for item in items:
        data_id = item.get("data-id", "")
        if not data_id:
            continue

        link = item.select_one("a[href*='angebot'], a[href*='expose']")
        if not link:
            link = item.select_one("a")
        if not link:
            continue

        href = link.get("href", "")
        if href.startswith("/"):
            href = "https://www.wg-gesucht.de" + href

        text = item.get_text(strip=True)

        # Цена — ищем отдельный элемент с ценой
        price = 0.0
        price_el = item.select_one("[class*=price]")
        if price_el:
            price = _parse_price(price_el.get_text(strip=True))
        if not price:
            price = _parse_price(text)

        if max_price and price > max_price and price > 0:
            continue

        # Площадь — ищем m² отдельно, исключая даты
        area = None
        area_els = item.select("span, div")
        for el in area_els:
            t = el.get_text(strip=True)
            m = re.match(r'^(\d[\d.,]*)\s*m²$', t)
            if m:
                area = m.group(1)
                break

        # Комнаты
        rooms = None
        rooms_match = re.search(r'(\d+)\s*(?:Zimmer|Zi\.)', text)
        if rooms_match:
            rooms = rooms_match.group(1)

        title_el = item.select_one("[class*=headline], h3, .truncate")
        title = title_el.get_text(strip=True)[:80] if title_el else text[:80]

        listings.append(Listing(
            portal="wg-gesucht", url=href, title=title,
            price=price, area=area, rooms=rooms,
            city=city, text=text[:500],
        ))

    logger.info("WG-Gesucht: %d listings from %s", len(listings), city)
    return listings


# ── Rightmove (UK) ────────────────────────────────────────────

def parse_rightmove(city: str = "london", max_price: int = 0) -> list[Listing]:
    """Парсинг Rightmove (HTML scraping)."""
    city_slug = city.lower().replace(" ", "-")
    url = f"https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E904&searchLocation={city_slug}"
    r = _safe_get(url, _headers("https://www.rightmove.co.uk/"))
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select(".propertyCard, [class*=propertyCard]")
    listings = []

    for card in cards[:20]:
        title_el = card.select_one(".propertyCard-title, [class*=title]")
        price_el = card.select_one(".propertyCard-priceValue, [class*=price]")
        link_el = card.select_one("a.propertyCard-link, a[href*='/property-to-rent/']")

        if not link_el:
            continue

        href = link_el.get("href", "")
        if href.startswith("/"):
            href = "https://www.rightmove.co.uk" + href

        title = title_el.text.strip() if title_el else ""
        price_text = price_el.text.strip() if price_el else "0"
        price = _parse_price(price_text.replace("£", ""))

        if max_price and price > max_price and price > 0:
            continue

        area_match = re.search(r'(\d[\d.,]*)\s*(?:sq\.?\s*ft|m²)', price_text + title)
        area = area_match.group(1) if area_match else None

        listings.append(Listing(
            portal="rightmove", url=href, title=title,
            price=price, area=area, rooms=None,
            city=city, text=title[:500],
        ))

    logger.info("Rightmove: %d listings from %s", len(listings), city)
    return listings


# ── ImmoScout24 (DE) ──────────────────────────────────────────

def parse_immoscout24(city: str = "berlin", max_price: int = 0) -> list[Listing]:
    """Парсинг ImmoScout24 (HTML scraping)."""
    city_map = {
        "berlin": "berlin", "muenchen": "muenchen", "munich": "muenchen",
        "hamburg": "hamburg", "koeln": "koeln", "cologne": "koeln",
        "frankfurt": "frankfurt", "stuttgart": "stuttgart",
    }
    city_slug = city_map.get(city.lower(), city.lower())
    url = f"https://www.immobilienscout24.de/Suche/de/{city_slug}/wohnung-mieten"
    r = _safe_get(url, _headers("https://www.immobilienscout24.de/"))
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    # ImmoScout24 uses data attributes for listings
    cards = soup.select("[data-testid*=result-list-entry], .result-list-entry, [class*=listings-card]")
    if not cards:
        # Fallback: find all expose links
        cards = soup.select("a[href*='/expose/']")

    listings = []
    seen = set()

    for card in cards[:20]:
        if card.name == "a":
            href = card.get("href", "")
        else:
            link = card.select_one("a[href*='/expose/']")
            href = link.get("href", "") if link else ""

        if not href or href in seen:
            continue
        seen.add(href)

        if href.startswith("/"):
            href = "https://www.immobilienscout24.de" + href

        text = card.get_text(strip=True)
        price = _parse_price(text)

        if max_price and price > max_price and price > 0:
            continue

        area_match = re.search(r'(\d[\d.,]*)\s*m²', text)
        area = area_match.group(1) if area_match else None
        rooms_match = re.search(r'(\d+)\s*Zi\.?', text)
        rooms = rooms_match.group(1) if rooms_match else None

        title = text[:80] if text else "ImmoScout24 listing"

        listings.append(Listing(
            portal="immoscout24", url=href, title=title,
            price=price, area=area, rooms=rooms,
            city=city, text=text[:500],
        ))

    logger.info("ImmoScout24: %d listings from %s", len(listings), city)
    return listings


# ── HousingAnywhere (EU) ──────────────────────────────────────

def parse_housinganywhere(city: str = "berlin", max_price: int = 0) -> list[Listing]:
    """Парсинг HousingAnywhere (HTML scraping)."""
    city_slug = city.lower().replace(" ", "-")
    url = f"https://housinganywhere.com/s/{city_slug}--Germany/apartment"
    r = _safe_get(url, _headers("https://housinganywhere.com/"))
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("[class*=listing], [class*=card], article, [data-testid*=listing]")
    listings = []

    for card in cards[:20]:
        link = card.select_one("a[href*='/apartment/'], a[href*='/room/']")
        if not link:
            link = card.select_one("a")
        if not link:
            continue

        href = link.get("href", "")
        if href.startswith("/"):
            href = "https://housinganywhere.com" + href

        text = card.get_text(strip=True)
        price = _parse_price(text)

        if max_price and price > max_price and price > 0:
            continue

        title = text[:80] if text else "HousingAnywhere listing"

        listings.append(Listing(
            portal="housinganywhere", url=href, title=title,
            price=price, area=None, rooms=None,
            city=city, text=text[:500],
        ))

    logger.info("HousingAnywhere: %d listings from %s", len(listings), city)
    return listings


# ── Aggregator ────────────────────────────────────────────────

PORTAL_PARSERS = {
    "immowelt": lambda city, max_price: parse_immowelt(city, max_price),
    "wg-gesucht": lambda city, max_price: parse_wg_gesucht(city, max_price),
    "rightmove": lambda city, max_price: parse_rightmove(city, max_price),
}


def scan_all_portals(city: str = "berlin", max_price: int = 0) -> list[Listing]:
    """Сканирует все порталы и возвращает объединённый список."""
    all_listings = []
    for name, parser in PORTAL_PARSERS.items():
        try:
            listings = parser(city, max_price)
            all_listings.extend(listings)
            logger.info("Scanned %s: %d listings", name, len(listings))
        except Exception as e:
            logger.error("Error scanning %s: %s", name, e)
        time.sleep(1)  # Пауза между порталами
    return all_listings
