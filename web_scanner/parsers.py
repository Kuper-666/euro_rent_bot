"""
Парсеры для европейских порталов недвижимости.
Поддержка: ImmoScout24, Immowelt, Idealista, Rightmove, Pararius, Funda, Seloger.
"""
import os
import re
import json
import time
import random
import logging
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
]

REQUEST_TIMEOUT = 15


def _headers() -> dict:
    return {"User-Agent": random.choice(USER_AGENTS)}


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


def _safe_get(url: str) -> Optional[requests.Response]:
    """GET с обработкой ошибок и ретраями."""
    for attempt in range(3):
        try:
            r = requests.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT)
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


# ── Immowelt (DE) ──────────────────────────────────────────────

def parse_immowelt(city: str = "berlin", max_price: int = 0) -> list[Listing]:
    """Парсинг Immowelt через RSS."""
    city_slug = city.lower().replace(" ", "-")
    rss_url = f"https://www.immowelt.de/rss/{city_slug}-wohnungen-mieten"
    r = _safe_get(rss_url)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    listings = []

    for item in items[:20]:
        title = item.find("title").text if item.find("title") else ""
        link = item.find("link").text if item.find("link") else ""
        desc = item.find("description").text if item.find("description") else ""

        price_match = re.search(r"(\d[\d.,]*)\s*€", desc + " " + title)
        price = float(price_match.group(1).replace(".", "").replace(",", ".")) if price_match else 0

        if max_price and price > max_price and price > 0:
            continue

        text = BeautifulSoup(desc, "html.parser").get_text()[:500]
        listings.append(Listing(
            portal="immowelt", url=link, title=title,
            price=price, area=None, rooms=None, city=city, text=text
        ))

    return listings


# ── Idealista (ES/IT/PT) ──────────────────────────────────────

def parse_idealista(country: str = "es", city: str = "barcelona", max_price: int = 0) -> list[Listing]:
    """Парсинг Idealista через RSS."""
    country_map = {"es": "es", "it": "it", "pt": "pt"}
    c = country_map.get(country, "es")
    city_slug = city.lower().replace(" ", "-")
    rss_url = f"https://www.idealista.{c}/rss/{c}/{city_slug}/"
    r = _safe_get(rss_url)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    listings = []

    for item in items[:20]:
        title = item.find("title").text if item.find("title") else ""
        link = item.find("link").text if item.find("link") else ""
        desc = item.find("description").text if item.find("description") else ""

        price_match = re.search(r"(\d[\d.,]*)\s*€", desc + " " + title)
        price = float(price_match.group(1).replace(".", "").replace(",", ".")) if price_match else 0

        if max_price and price > max_price and price > 0:
            continue

        text = BeautifulSoup(desc, "html.parser").get_text()[:500]
        listings.append(Listing(
            portal="idealista", url=link, title=title,
            price=price, area=None, rooms=None, city=city, text=text
        ))

    return listings


# ── Rightmove (UK) ────────────────────────────────────────────

def parse_rightmove(city: str = "london", max_price: int = 0) -> list[Listing]:
    """Парсинг Rightmove через RSS."""
    city_slug = city.lower().replace(" ", "-")
    rss_url = f"https://www.rightmove.co.uk/property-to-rent/{city_slug}.html?sortType=6"
    r = _safe_get(rss_url)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    listings = []

    cards = soup.select(".propertyCard")[:20]
    for card in cards:
        title_el = card.select_one(".propertyCard-title")
        price_el = card.select_one(".propertyCard-priceValue")
        link_el = card.select_one("a.propertyCard-link")

        title = title_el.text.strip() if title_el else ""
        price_text = price_el.text.strip() if price_el else "0"
        link = "https://www.rightmove.co.uk" + link_el["href"] if link_el and link_el.get("href") else ""

        price_match = re.search(r"(\d[\d,]*)", price_text.replace("£", ""))
        price = float(price_match.group(1).replace(",", "")) if price_match else 0

        if max_price and price > max_price and price > 0:
            continue

        listings.append(Listing(
            portal="rightmove", url=link, title=title,
            price=price, area=None, rooms=None, city=city, text=title
        ))

    return listings


# ── Pararius (NL) ─────────────────────────────────────────────

def parse_pararius(city: str = "amsterdam", max_price: int = 0) -> list[Listing]:
    """Парсинг Pararius через RSS."""
    city_slug = city.lower().replace(" ", "-")
    rss_url = f"https://www.pararius.nl/rss/apartments/{city_slug}"
    r = _safe_get(rss_url)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    listings = []

    for item in items[:20]:
        title = item.find("title").text if item.find("title") else ""
        link = item.find("link").text if item.find("link") else ""
        desc = item.find("description").text if item.find("description") else ""

        price_match = re.search(r"€\s*([\d.,]+)", desc + " " + title)
        price = float(price_match.group(1).replace(".", "").replace(",", ".")) if price_match else 0

        if max_price and price > max_price and price > 0:
            continue

        text = BeautifulSoup(desc, "html.parser").get_text()[:500]
        listings.append(Listing(
            portal="pararius", url=link, title=title,
            price=price, area=None, rooms=None, city=city, text=text
        ))

    return listings


# ── Funda (NL) ────────────────────────────────────────────────

def parse_funda(city: str = "amsterdam", max_price: int = 0) -> list[Listing]:
    """Парсинг Funda через RSS."""
    city_slug = city.lower().replace(" ", "-")
    rss_url = f"https://www.funda.nl/huur/{city_slug}/rss/"
    r = _safe_get(rss_url)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    listings = []

    for item in items[:20]:
        title = item.find("title").text if item.find("title") else ""
        link = item.find("link").text if item.find("link") else ""
        desc = item.find("description").text if item.find("description") else ""

        price_match = re.search(r"€\s*([\d.,]+)", desc + " " + title)
        price = float(price_match.group(1).replace(".", "").replace(",", ".")) if price_match else 0

        if max_price and price > max_price and price > 0:
            continue

        text = BeautifulSoup(desc, "html.parser").get_text()[:500]
        listings.append(Listing(
            portal="funda", url=link, title=title,
            price=price, area=None, rooms=None, city=city, text=text
        ))

    return listings


# ── Seloger (FR) ──────────────────────────────────────────────

def parse_seloger(city: str = "paris", max_price: int = 0) -> list[Listing]:
    """Парсинг Seloger через RSS."""
    city_slug = city.lower().replace(" ", "-")
    rss_url = f"https://www.seloger.com/list.htm?projects=2&types=1&natures=1&cities=75056&enterprise=0&qsVersion=1.0"
    r = _safe_get(rss_url)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    listings = []

    for item in items[:20]:
        title = item.find("title").text if item.find("title") else ""
        link = item.find("link").text if item.find("link") else ""
        desc = item.find("description").text if item.find("description") else ""

        price_match = re.search(r"(\d[\d.,]*)\s*€", desc + " " + title)
        price = float(price_match.group(1).replace(".", "").replace(",", ".")) if price_match else 0

        if max_price and price > max_price and price > 0:
            continue

        text = BeautifulSoup(desc, "html.parser").get_text()[:500]
        listings.append(Listing(
            portal="seloger", url=link, title=title,
            price=price, area=None, rooms=None, city=city, text=text
        ))

    return listings


# ── Aggregator ────────────────────────────────────────────────

PORTAL_PARSERS = {
    "immowelt": lambda city, max_price: parse_immowelt(city, max_price),
    "idealista": lambda city, max_price: parse_idealista("es", city, max_price),
    "rightmove": lambda city, max_price: parse_rightmove(city, max_price),
    "pararius": lambda city, max_price: parse_pararius(city, max_price),
    "funda": lambda city, max_price: parse_funda(city, max_price),
    "seloger": lambda city, max_price: parse_seloger(city, max_price),
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
