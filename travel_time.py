"""
Travel Time Calculator через OSRM (OpenStreetMap).
Бесплатный API для расчета времени в пути.
"""
import os
import logging
import re
import requests

logger = logging.getLogger(__name__)

OSRM_BASE = "http://router.project-osrm.org"


def geocode(address: str) -> tuple[float, float] | None:
    """Геокодинг адреса через Nominatim (OpenStreetMap)."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}
    headers = {"User-Agent": "EuroRentBot/1.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        logger.warning("Geocode error for '%s': %s", address, e)
    return None


def calc_travel_time(origin: str, destination: str) -> dict | None:
    """Рассчитывает время в пути между двумя адресами.

    Возвращает dict с ключами:
    - duration_min: время в минутах
    - distance_km: расстояние в км
    - text: человекочитаемая строка
    """
    origin_coords = geocode(origin)
    dest_coords = geocode(destination)

    if not origin_coords or not dest_coords:
        return None

    url = f"{OSRM_BASE}/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}"
    params = {"overview": "false"}

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return None

        route = data["routes"][0]
        duration_sec = route["duration"]
        distance_m = route["distance"]

        duration_min = round(duration_sec / 60)
        distance_km = round(distance_m / 1000, 1)

        if duration_min < 60:
            text = f"🚗 {duration_min} мин ({distance_km} км)"
        else:
            hours = duration_min // 60
            mins = duration_min % 60
            text = f"🚗 {hours} ч {mins} мин ({distance_km} км)"

        return {
            "duration_min": duration_min,
            "distance_km": distance_km,
            "text": text,
        }

    except Exception as e:
        logger.warning("Travel time error: %s", e)
        return None
