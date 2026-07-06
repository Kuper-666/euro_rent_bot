"""
Тесты для channel_scanner.py
"""
import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from rent_scanner.channel_scanner import (
    _load_channels,
    _is_rental_listing,
    _extract_price,
    _extract_url,
    _load_subscribed,
    _save_subscribed,
    _reset_daily_counter,
    match_listing_to_subscribers,
)


class TestLoadChannels:
    def test_load_channels_file_exists(self):
        config = _load_channels()
        assert "channels" in config
        assert "scan_keywords" in config
        assert "price_patterns" in config
        assert "exclude_keywords" in config

    def test_channels_count(self):
        config = _load_channels()
        assert len(config["channels"]) >= 10

    def test_keywords_not_empty(self):
        config = _load_channels()
        assert len(config["scan_keywords"]) > 0


class TestRentalDetection:
    def test_detects_rental_ru(self):
        config = _load_channels()
        text = "Квартира 2 комнаты, 60м², 850€/мес, Берлин"
        assert _is_rental_listing(text, config["scan_keywords"], config["exclude_keywords"])

    def test_detects_rental_de(self):
        config = _load_channels()
        text = "Wohnung zu mieten, 2 Zimmer, 900€ Warmmiete"
        assert _is_rental_listing(text, config["scan_keywords"], config["exclude_keywords"])

    def test_detects_rental_en(self):
        config = _load_channels()
        text = "Apartment for rent, 3 bedrooms, £1200/month"
        assert _is_rental_listing(text, config["scan_keywords"], config["exclude_keywords"])

    def test_rejects_sale(self):
        config = _load_channels()
        text = "Продаю машину BMW 2020 года"
        assert not _is_rental_listing(text, config["scan_keywords"], config["exclude_keywords"])

    def test_rejects_buy(self):
        config = _load_channels()
        text = "Куплю диван недорого"
        assert not _is_rental_listing(text, config["scan_keywords"], config["exclude_keywords"])


class TestPriceExtraction:
    def test_extract_price_eur(self):
        config = _load_channels()
        text = "Квартира 850€/мес"
        price = _extract_price(text, config["price_patterns"])
        assert price == 850.0

    def test_extract_price_warmmiete(self):
        config = _load_channels()
        text = "Warmmiete: 1.200 EUR"
        price = _extract_price(text, config["price_patterns"])
        assert price == 1200.0

    def test_extract_price_monthly(self):
        config = _load_channels()
        text = "Rent: 1500 monthly"
        price = _extract_price(text, config["price_patterns"])
        assert price == 1500.0

    def test_no_price(self):
        config = _load_channels()
        text = "Квартира без указания цены"
        price = _extract_price(text, config["price_patterns"])
        assert price is None


class TestUrlExtraction:
    def test_extract_url(self):
        text = "Подробнее: https://t.me/channel/123"
        url = _extract_url(text)
        assert url == "https://t.me/channel/123"

    def test_no_url(self):
        text = "Просто текст без ссылок"
        url = _extract_url(text)
        assert url is None


class TestSubscribedChannels:
    def test_load_subscribed(self):
        data = _load_subscribed()
        assert "subscribed" in data

    def test_save_subscribed(self):
        test_data = {"subscribed": ["test_channel"], "subscribed_today": 1}
        _save_subscribed(test_data)
        loaded = _load_subscribed()
        assert "test_channel" in loaded["subscribed"]
        # Очистка
        _save_subscribed({"subscribed": [], "subscribed_today": 0})


class TestMatchListing:
    def test_match_by_city(self):
        listing = {"city": "berlin", "price": 800}
        subscribers = [
            {"city": "berlin", "max_price": 1000},
            {"city": "munich", "max_price": 1000},
        ]
        matches = match_listing_to_subscribers(listing, subscribers)
        assert len(matches) == 1
        assert matches[0]["city"] == "berlin"

    def test_match_by_price(self):
        listing = {"city": "berlin", "price": 500}
        subscribers = [
            {"city": "berlin", "max_price": 400},
            {"city": "berlin", "max_price": 600},
        ]
        matches = match_listing_to_subscribers(listing, subscribers)
        assert len(matches) == 1
        assert matches[0]["max_price"] == 600

    def test_no_match(self):
        listing = {"city": "berlin", "price": 1500}
        subscribers = [
            {"city": "munich", "max_price": 1000},
        ]
        matches = match_listing_to_subscribers(listing, subscribers)
        assert len(matches) == 0


def test_auto_subscribe_limit():
    """Проверяет лимит автоподписок (5 в день)."""
    from rent_scanner.channel_scanner import _load_subscribed, _save_subscribed, _reset_daily_counter

    # Устанавливаем лимит
    _save_subscribed({"subscribed": [], "subscribed_today": 5, "last_reset": ""})
    _reset_daily_counter()

    # Проверяем что лимит сброшен при новом дне
    data = _load_subscribed()
    assert data.get("subscribed_today", 0) == 0

    # Очистка
    _save_subscribed({"subscribed": [], "subscribed_today": 0})
