import os
import sys
import re

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
