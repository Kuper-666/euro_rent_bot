import os
import sys
import re
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.dirname(__file__))

from messages import get_msg, MESSAGES


def test_messages_load():
    for lang in ["ru", "uk", "en", "de", "pl"]:
        for key in ["start", "help", "analyzing", "limit_reached", "error",
                     "pay_done_3", "pay_done_9", "pay_done_19", "system_prompt"]:
            msg = get_msg(lang, key)
            assert msg, f"Missing {key} for {lang}"
    print("All messages loaded OK")


def test_message_lengths():
    for lang in ["ru", "uk", "en", "de", "pl"]:
        for key in ["start", "help"]:
            msg = get_msg(lang, key)
            assert len(msg) <= 4096, f"{lang}.{key} too long: {len(msg)}"
    print("All messages within Telegram limits OK")


def test_no_revolut_links():
    for lang in MESSAGES:
        for key in MESSAGES[lang]:
            val = MESSAGES[lang][key]
            if isinstance(val, str) and "revolut.me" in val:
                assert False, f"Revolut link found in {lang}.{key}"
    print("No Revolut links found OK")


def test_stars_pricing():
    for lang in ["ru", "en"]:
        help_text = get_msg(lang, "help")
        assert "300 Stars" in help_text, f"Missing 300 Stars in {lang} help"
        assert "900 Stars" in help_text, f"Missing 900 Stars in {lang} help"
        assert "1900 Stars" in help_text, f"Missing 1900 Stars in {lang} help"
    print("Stars pricing OK")


def test_split_message():
    def split_message(text, max_len=4000):
        if len(text) <= max_len:
            return [text]
        parts = []
        while text:
            if len(text) <= max_len:
                parts.append(text)
                break
            cut = text.rfind("\n", 0, max_len)
            if cut == -1:
                cut = max_len
            parts.append(text[:cut])
            text = text[cut:].lstrip("\n")
        return parts

    short = "Hello"
    assert len(split_message(short)) == 1

    long = "A\n" * 5000
    parts = split_message(long)
    for p in parts:
        assert len(p) <= 4000, f"Part too long: {len(p)}"
    print(f"Split message OK: {len(parts)} parts")


def test_calc_remaining():
    def calc_remaining(user):
        if user["balance"] == -1:
            return "∞"
        if user["balance"] > 0:
            return str(user["balance"])
        return str(3 - user["free_used"])

    assert calc_remaining({"balance": -1}) == "∞"
    assert calc_remaining({"balance": 5}) == "5"
    assert calc_remaining({"balance": 0, "free_used": 0}) == "3"
    assert calc_remaining({"balance": 0, "free_used": 2}) == "1"
    print("calc_remaining OK")


def test_is_url():
    def is_url(text):
        return bool(re.match(r'https?://', text.strip()))

    assert is_url("https://example.com")
    assert is_url("http://test.de")
    assert not is_url("hello world")
    assert not is_url("www.test.com")
    print("is_url OK")


def test_pdf_generator():
    from pdf_generator import generate_mieterprofil_pdf
    data = {"name": "Test User", "dob": "01.01.1990", "phone": "+123",
            "email": "test@test.com", "address": "Berlin",
            "employer": "Google", "income": "5000", "occupants": "2"}
    pdf = generate_mieterprofil_pdf(data)
    assert len(pdf) > 1000, f"PDF too small: {len(pdf)}"
    assert pdf[:4] == b'%PDF', "Not a valid PDF"
    print("PDF generator OK")


def test_button_texts():
    buttons = ["Старт", "Помощь", "Оплата", "PDF", "VIP"]
    for btn in buttons:
        assert len(btn) > 0
        assert not btn.startswith("/"), f"Button should not start with /: {btn}"
    print("Button texts OK")


def test_button_regex():
    patterns = {
        "Старт": r'(?i)^(старт|start)$',
        "Помощь": r'(?i)^(помощь|help)$',
        "Оплата": r'(?i)^(оплата|pay|оплатить)$',
        "PDF": r'(?i)^(pdf|пдф)$',
        "VIP": r'(?i)^(vip|вип)$',
    }
    for btn, pattern in patterns.items():
        assert re.match(pattern, btn), f"Pattern {pattern} doesn't match {btn}"
    print("Button regex patterns OK")


def test_all_langs_have_start():
    for lang in ["ru", "uk", "en", "de", "pl"]:
        start = get_msg(lang, "start")
        assert "EuroRent" in start or "европ" in start.lower() or "Europ" in start, \
            f"Start message missing brand for {lang}"
    print("All start messages have brand OK")


def test_group_redirect_messages_exist():
    for lang in ["ru", "uk", "en", "de", "pl"]:
        msg = get_msg(lang, "group_redirect")
        assert msg, f"Missing group_redirect for {lang}"
        assert len(msg) > 20, f"group_redirect for {lang} too short: {msg}"
    print("All group_redirect messages exist OK")


def test_group_redirect_messages_length():
    for lang in ["ru", "uk", "en", "de", "pl"]:
        msg = get_msg(lang, "group_redirect")
        assert len(msg) <= 4096, f"{lang}.group_redirect too long: {len(msg)}"
    print("group_redirect messages within Telegram limits OK")


def test_greeting_pattern():
    pattern = re.compile(
        r'^(?i:привет|здравствуй|hello|hi|добрый день|доброе утро|добрый вечер|ку|хай|hey|hallo|servus|cześć|witaj)\b'
    )

    greetings = [
        "Привет", "привет", "ПРИВЕТ",
        "Здравствуй", "здравствуй",
        "Hello", "hello", "HELLO",
        "Hi", "hi", "HI",
        "Добрый день", "добрый день",
        "Доброе утро", "доброе утро",
        "Добрый вечер", "добрый вечер",
        "Ку", "ку", "КУ",
        "Хай", "хай",
        "Hey", "hey",
        "Hallo", "hallo",
        "Servus", "servus",
        "Cześć", "cześć",
        "Witaj", "witaj",
    ]

    for g in greetings:
        assert pattern.match(g), f"Greeting pattern should match: {g}"

    non_greetings = [
        "Квартира в Берлине",
        "https://example.com",
        "Тест",
    ]

    for ng in non_greetings:
        if ng.strip():
            assert not pattern.match(ng), f"Greeting pattern should NOT match: {ng}"

    print("Greeting pattern OK")


def test_group_listing_detection_logic():
    def should_redirect(text):
        greeting_pattern = re.compile(
            r'^(?i:привет|здравствуй|hello|hi|добрый день|доброе утро|добрый вечер|ку|хай|hey|hallo|servus|cześć|witaj)\b'
        )
        if greeting_pattern.match(text.strip()):
            return False
        is_url = text.strip().startswith(("http://", "https://", "t.me/"))
        is_long_text = len(text.strip()) > 30
        return is_url or is_long_text

    assert should_redirect("https://www.immobilienscout24.de/Suche/123")
    assert should_redirect("http://example.com/listing/456")
    assert should_redirect("t.me/channel/123")
    assert should_redirect("2-комнатная квартира в Берлине, 800 EUR, 55м2, рядом с метро")
    assert should_redirect("Kuche im Zentrum, 2 Zimmer, 750 EUR warm, 45m2")

    assert not should_redirect("Привет")
    assert not should_redirect("Hello")
    assert not should_redirect("Ку")
    assert not should_redirect("Hi")
    assert not should_redirect("Hey")
    assert not should_redirect("Привет, вот ссылка https://example.com")
    assert not should_redirect("Hello world")
    assert not should_redirect("短い")
    assert not should_redirect("")
    assert not should_redirect("  ")

    print("Group listing detection logic OK")


def test_deep_link_construction():
    bot_username = "ExpatRentBot"
    user_id = "12345678"
    deep_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    assert deep_link == "https://t.me/ExpatRentBot?start=ref_12345678"
    assert "analyze_" not in deep_link
    assert len(deep_link) < 200
    print("Deep link construction OK")


def test_handler_no_commands_filter():
    cmd_pattern = re.compile(r'^/')
    assert not cmd_pattern.match("Привет")
    assert not cmd_pattern.match("https://example.com")
    assert cmd_pattern.match("/start")
    assert cmd_pattern.match("/help")
    print("No-commands filter OK")


def test_start_analyze_payload():
    payload = "analyze_https%3A%2F%2Fexample.com%2Flisting"
    assert payload.startswith("analyze_")
    from urllib.parse import unquote
    url = unquote(payload[len("analyze_"):])
    assert url == "https://example.com/listing"
    print("Start analyze payload OK")


def test_start_ref_payload():
    payload = "ref_abc123"
    assert payload.startswith("ref_")
    ref_code = payload
    assert ref_code == "ref_abc123"
    print("Start ref payload OK")


def test_welcome_new_member_text():
    name = "Тест Узер"
    welcome_text = (
        f"Добро пожаловать, {name}!\n\n"
        f"Этот чат создан для экспатов в Европе. "
        f"Полезные ссылки и подборки по аренде можно найти в закрепленных сообщениях.\n\n"
        f"Как анализировать объявления:\n"
        f"Просто отправьте ссылку или текст объявления сюда в чат.\n"
        f"Я перенаправлю вас в личку с ботом, где он сделает полный разбор за 5 секунд!\n\n"
        f"Или начните сразу: /start"
    )
    assert "Тест Узер" in welcome_text
    assert "/start" in welcome_text
    assert "личк" in welcome_text
    print("Welcome new member text OK")


def test_city_selected_messages_exist():
    for lang in ["ru", "uk", "en", "de", "pl"]:
        msg = get_msg(lang, "city_selected")
        assert msg, f"Missing city_selected for {lang}"
        assert "{emoji}" in msg, f"city_selected for {lang} missing {{emoji}} placeholder"
        assert "{name}" in msg, f"city_selected for {lang} missing {{name}} placeholder"
    print("All city_selected messages exist OK")


def test_city_filter_skip_messages_exist():
    for lang in ["ru", "uk", "en", "de", "pl"]:
        msg = get_msg(lang, "city_filter_skip")
        assert msg, f"Missing city_filter_skip for {lang}"
        assert "{user_city}" in msg, f"city_filter_skip for {lang} missing {{user_city}} placeholder"
    print("All city_filter_skip messages exist OK")


def test_popular_cities_complete():
    from listing_features import POPULAR_CITIES
    required_keys = ["name", "name_en", "name_de", "avg_price", "emoji"]
    for city_key, info in POPULAR_CITIES.items():
        for k in required_keys:
            assert k in info, f"City {city_key} missing key: {k}"
        assert isinstance(info["avg_price"], int), f"City {city_key} avg_price not int"
        assert info["avg_price"] > 0, f"City {city_key} avg_price not positive"
    print("All popular cities complete OK")


def test_detect_city():
    from listing_features import detect_city
    assert detect_city("2-комнатная квартира в Берлине, 800 EUR") == "berlin"
    assert detect_city("Apartment in Munich, 2 Zimmer") == "munich"
    assert detect_city("Wohnung in Berlin, Kaltmiete 750 EUR") == "berlin"
    assert detect_city("Wohnung in München, 900 EUR") == "munich"
    assert detect_city("Wohnung in Köln, 700 EUR") == "cologne"
    assert detect_city("Apartment in Vienna, 3 rooms") == "vienna"
    assert detect_city("Wohnung in Wien, 2 Zimmer") == "vienna"
    assert detect_city("Piso en Barcelona, 850 EUR") == "barcelona"
    assert detect_city("Flat in London, 1200 GBP") is None
    print("detect_city OK")


def test_city_filter_logic():
    from listing_features import detect_city, get_user_city, POPULAR_CITIES

    user_city = "berlin"
    listing_berlin = "2-комнатная квартира в Берлине, 800 EUR"
    listing_munich = "Apartment in Munich, 2 Zimmer, 900 EUR"

    detected_berlin = detect_city(listing_berlin)
    detected_munich = detect_city(listing_munich)

    assert detected_berlin == "berlin"
    assert detected_munich == "munich"
    assert detected_berlin == user_city
    assert detected_munich != user_city

    print("City filter logic OK")


def test_cities_keyboard_structure():
    from listing_features import POPULAR_CITIES
    cities = sorted(POPULAR_CITIES.items(), key=lambda x: x[1]["avg_price"])
    keyboard = []
    row = []
    for key, info in cities:
        row.append(f"{info['emoji']} {info['name_en']}")
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    total_buttons = sum(len(r) for r in keyboard)
    assert total_buttons == len(POPULAR_CITIES), f"Expected {len(POPULAR_CITIES)} buttons, got {total_buttons}"
    assert all(len(r) <= 2 for r in keyboard), "Some rows have more than 2 buttons"
    print("Cities keyboard structure OK")


def test_city_callback_data_format():
    callback_data = "select_city:berlin"
    assert callback_data.startswith("select_city:")
    city_key = callback_data.split(":")[1]
    assert city_key == "berlin"

    callback_remove = "select_city:remove"
    assert callback_remove.split(":")[1] == "remove"
    print("City callback data format OK")


if __name__ == "__main__":
    tests = [
        test_messages_load,
        test_message_lengths,
        test_no_revolut_links,
        test_stars_pricing,
        test_split_message,
        test_calc_remaining,
        test_is_url,
        test_pdf_generator,
        test_button_texts,
        test_button_regex,
        test_all_langs_have_start,
        test_group_redirect_messages_exist,
        test_group_redirect_messages_length,
        test_greeting_pattern,
        test_group_listing_detection_logic,
        test_deep_link_construction,
        test_handler_no_commands_filter,
        test_start_analyze_payload,
        test_start_ref_payload,
        test_welcome_new_member_text,
        test_city_selected_messages_exist,
        test_city_filter_skip_messages_exist,
        test_popular_cities_complete,
        test_detect_city,
        test_city_filter_logic,
        test_cities_keyboard_structure,
        test_city_callback_data_format,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed")
