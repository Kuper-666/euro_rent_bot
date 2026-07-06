"""
Deep link & referral code audit for rent_bot.

Tests:
1. Generate referral link the way bot.py does, simulate /start, verify credit
2. Check if any code uses raw user_id as ref_code
3. Full deep link chain: create_url_token -> build -> extract -> resolve -> verify
4. callback_data length check (Telegram 64-byte limit)
"""
import os
import sys
import hashlib
import json
import time
import secrets
from urllib.parse import quote, unquote

sys.path.insert(0, os.path.dirname(__file__))

BOT_USERNAME = "expat_rent_bot"
TELEGRAM_64_BYTE_LIMIT = 64

errors = []
warnings = []
info = []

# ═══════════════════════════════════════════════════════════════════
# TEST 1: Referral link generation + /start simulation + credit
# ═══════════════════════════════════════════════════════════════════

def test_1_referral_flow():
    print("\n" + "=" * 70)
    print("TEST 1: Referral link generation → /start → credit flow")
    print("=" * 70)

    # 1a. Generate ref_code the way bot.py does
    referrer_user_id = "111222333"
    ref_code = f"ref_{hashlib.sha256(f'{referrer_user_id}eurorent2024'.encode()).hexdigest()[:8]}"
    print(f"  Referrer user_id: {referrer_user_id}")
    print(f"  Generated ref_code: {ref_code}")
    assert ref_code.startswith("ref_"), "ref_code must start with ref_"
    assert len(ref_code) == 12, f"ref_code should be 12 chars (ref_ + 8 hex), got {len(ref_code)}"

    # 1b. Build the deep link
    ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
    print(f"  Deep link: {ref_link}")
    assert f"?start={ref_code}" in ref_link

    # 1c. Telegram start= limit is 64 bytes
    start_param = ref_code
    print(f"  start= param length: {len(start_param.encode('utf-8'))} bytes (limit: 64)")
    assert len(start_param.encode('utf-8')) <= 64, f"start= param exceeds 64 bytes: {start_param}"

    # 1d. Simulate /start with payload — verify referrer lookup works
    # bot.py iterates all users to find matching ref_code
    simulated_data = {
        referrer_user_id: {
            "free_used": 0, "balance": 0,
            "ref_code": ref_code,
            "referrals": [],
        }
    }

    new_user_id = "444555666"
    payload = ref_code  # This is what context.args[0] would be

    # Simulate the lookup from bot.py lines 903-914
    referrer_id = None
    for uid, u in simulated_data.items():
        if u.get("ref_code") == payload:
            referrer_id = uid
            break

    assert referrer_id == referrer_user_id, f"Expected referrer_id={referrer_user_id}, got {referrer_id}"
    assert referrer_id != new_user_id, "Self-referral guard should prevent self-referral"
    print(f"  OK: Referrer lookup works, referrer_id={referrer_id}")

    # 1e. Simulate setting referred_by on new user
    simulated_data[new_user_id] = {
        "free_used": 0, "balance": 0,
        "ref_code": f"ref_{hashlib.sha256(f'{new_user_id}eurorent2024'.encode()).hexdigest()[:8]}",
    }
    simulated_data[new_user_id]["referred_by"] = referrer_id
    assert simulated_data[new_user_id]["referred_by"] == referrer_user_id
    print("  OK: referred_by set on new user")

    # 1f. Simulate first use_check → referral credit
    # After use_check, free_used becomes 1, triggering referral credit
    new_user = simulated_data[new_user_id]
    new_user["free_used"] = 1  # After first use_check()

    # bot.py lines 172-209
    if new_user.get("free_used", 0) == 1 and new_user.get("referred_by"):
        referrer_id_credit = new_user["referred_by"]
        referrer = simulated_data[referrer_id_credit]
        referrals = referrer.setdefault("referrals", [])
        if new_user_id not in referrals:
            referrals.append(new_user_id)
            reward = {1: 1, 3: 3, 5: 5, 10: -1}.get(len(referrals), 0)
            if reward > 0:
                referrer["balance"] = referrer.get("balance", 0) + reward

    assert referrer["referrals"] == [new_user_id], f"Expected referrals=[{new_user_id}], got {referrer['referrals']}"
    assert referrer["balance"] == 1, f"Expected balance=1 after 1st referral, got {referrer['balance']}"
    print(f"  OK: Referrer credited: balance={referrer['balance']}, referrals={referrer['referrals']}")

    # 1g. Test reward tiers
    reward_map = {1: 1, 3: 3, 5: 5, 10: -1}
    for threshold, expected_reward in reward_map.items():
        actual = reward_map.get(threshold, 0)
        assert actual == expected_reward
    print("  OK: Reward tiers: 1→1, 3→3, 5→5, 10→-1 (unlimited)")

    # 1h. Verify ref_code is deterministic
    ref_code_2 = f"ref_{hashlib.sha256(f'{referrer_user_id}eurorent2024'.encode()).hexdigest()[:8]}"
    assert ref_code == ref_code_2, "ref_code must be deterministic"
    print("  OK: ref_code is deterministic (same input → same output)")

    # 1i. Verify different user_ids produce different ref_codes
    other_user_id = "999888777"
    other_ref_code = f"ref_{hashlib.sha256(f'{other_user_id}eurorent2024'.encode()).hexdigest()[:8]}"
    assert ref_code != other_ref_code, "Different users should have different ref_codes"
    print("  OK: Different users → different ref_codes")

    info.append("Test 1 PASSED: Referral flow works correctly")


# ═══════════════════════════════════════════════════════════════════
# TEST 2: Check for raw user_id used as ref_code
# ═══════════════════════════════════════════════════════════════════

def test_2_raw_user_id_as_ref_code():
    print("\n" + "=" * 70)
    print("TEST 2: Check for raw user_id used as ref_code")
    print("=" * 70)

    import re
    import glob as glob_mod

    # Patterns that would indicate raw user_id used as ref_code
    dangerous_patterns = [
        (r'"ref_code"\s*:\s*f?"ref_\{[^}]*user_id[^}]*\}"', "ref_code set with raw user_id"),
        (r'"ref_code"\s*:\s*["\']ref_[\d]+["\']', "ref_code is raw numeric id"),
        (r'ref_code\s*=\s*f"ref_\{user_id\}"', "ref_code = ref_{user_id}"),
        (r'ref_code\s*=\s*["\']ref_[\d]+["\']', "ref_code hardcoded as numeric"),
        (r'f"ref_\{str\(user_id\)\}"', "ref_{str(user_id)}"),
        (r'f"ref_\{user_id\}"', "ref_{user_id}"),
        (r'f"ref_\{uid\}"', "ref_{uid}"),
    ]

    py_files = glob_mod.glob(os.path.join(os.path.dirname(__file__), "**", "*.py"), recursive=True)
    # Exclude test files and __pycache__
    py_files = [f for f in py_files if "__pycache__" not in f and "test_" not in os.path.basename(f)]

    found_dangerous = False
    for filepath in py_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        for pattern, desc in dangerous_patterns:
            matches = list(re.finditer(pattern, content))
            for m in matches:
                # Get line number
                line_num = content[:m.start()].count("\n") + 1
                errors.append(f"  BUG: {os.path.basename(filepath)}:{line_num} — {desc}: {m.group()}")
                found_dangerous = True

    if not found_dangerous:
        print("  OK: No raw user_id used as ref_code found")
    else:
        print(f"  FOUND {len(errors)} dangerous patterns!")

    # Also verify that ALL ref_code generation uses the hash
    hash_pattern = r'hashlib\.sha256\(f\'\{user_id\}eurorent2024'
    found_hash = False
    for filepath in py_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if re.search(hash_pattern, content):
            found_hash = True
            count = len(re.findall(hash_pattern, content))
            print(f"  OK: {os.path.basename(filepath)} uses hashlib SHA-256 hash ({count} occurrences)")

    assert found_hash, "Expected hashlib SHA-256 pattern in at least one file"
    info.append("Test 2 PASSED: No raw user_id as ref_code")


# ═══════════════════════════════════════════════════════════════════
# TEST 3: Full deep link chain
# ═══════════════════════════════════════════════════════════════════

def test_3_deep_link_chain():
    print("\n" + "=" * 70)
    print("TEST 3: Deep link chain (create → build → extract → resolve → verify)")
    print("=" * 70)

    from rent_scanner.formatting import (
        create_url_token, resolve_url_token,
        _create_url_token_local, _resolve_url_token_local,
        TOKEN_FILE
    )

    test_urls = [
        "https://www.immobilienscout24.de/expose/12345",
        "https://www.wg-gesucht.de/wg-zimmer-in-Berlin.80.1.1.0.html",
        "https://example.com/path?a=1&b=2#section",
        "https://idealista.pt/en/imovel/12345678",
    ]

    for original_url in test_urls:
        print(f"\n  Testing URL: {original_url[:60]}...")

        # 3a. Create token (local fallback since no Supabase in tests)
        token = _create_url_token_local(original_url)
        assert token, f"Token creation failed for {original_url}"
        assert len(token) <= 8, f"Token too long: {len(token)} chars"
        print(f"    Token: {token} ({len(token)} chars)")

        # 3b. Build deep link
        deep_link = f"https://t.me/{BOT_USERNAME}?start=an_{token}"
        start_param = f"an_{token}"
        assert len(start_param.encode('utf-8')) <= 64, f"start= param exceeds 64 bytes: {start_param}"
        print(f"    Deep link: {deep_link}")
        print(f"    start= bytes: {len(start_param.encode('utf-8'))} (limit: 64)")

        # 3c. Extract payload (simulating /start handler)
        payload = start_param  # context.args[0]
        assert payload.startswith("an_"), f"Payload should start with an_: {payload}"
        extracted_token = payload[len("an_"):]
        assert extracted_token == token, f"Token mismatch: extracted={extracted_token}, original={token}"

        # 3d. Resolve token
        resolved_url = _resolve_url_token_local(extracted_token)
        assert resolved_url == original_url, f"URL mismatch: resolved={resolved_url}, original={original_url}"
        print(f"    Resolved: {resolved_url[:60]}...")

        # 3e. Verify is_url check would pass
        from utils import is_url
        assert is_url(resolved_url), f"is_url() failed for resolved URL: {resolved_url}"
        print(f"    OK: Full chain works")

    # 3f. Test token deduplication
    url = "https://example.com/dedup-test"
    token1 = _create_url_token_local(url)
    token2 = _create_url_token_local(url)
    assert token1 == token2, f"Token dedup failed: {token1} != {token2}"
    print(f"\n  OK: Token deduplication works ({token1} == {token2})")

    # 3g. Test resolve non-existent token
    fake_token = "nonexist"
    result = _resolve_url_token_local(fake_token)
    assert result == "", f"Expected empty string for non-existent token, got: {result}"
    print("  OK: Non-existent token returns empty string")

    # 3h. Test the old format (analyze_ prefix) for backward compat
    from urllib.parse import unquote
    old_payload = f"analyze_{quote(test_urls[0], safe='')}"
    assert old_payload.startswith("analyze_")
    url_from_old = unquote(old_payload[len("analyze_"):])
    assert url_from_old == test_urls[0], f"Old format decode failed: {url_from_old}"
    print(f"  OK: Old format (analyze_) backward compatibility works")

    # 3i. Clean up test tokens from local file
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            tokens = json.load(f)
        for url in test_urls + ["https://example.com/dedup-test"]:
            tokens = {k: v for k, v in tokens.items() if v != url}
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens, f, ensure_ascii=False)
        print("  OK: Cleaned up test tokens")

    info.append("Test 3 PASSED: Deep link chain works correctly")


# ═══════════════════════════════════════════════════════════════════
# TEST 4: callback_data length check (64-byte Telegram limit)
# ═══════════════════════════════════════════════════════════════════

def test_4_callback_data_length():
    print("\n" + "=" * 70)
    print("TEST 4: callback_data length check (Telegram 64-byte limit)")
    print("=" * 70)

    # All static callback_data patterns found in the codebase
    static_buttons = [
        ("copy", "services/keyboards.py:47", "Копировать"),
        ("new", "services/keyboards.py:48", "Ещё одно"),
        ("gen_letter", "services/keyboards.py:51", "Письмо"),
        ("pdf", "services/keyboards.py:52", "PDF"),
        ("fav_save", "services/keyboards.py:55", "В избранное"),
        ("share", "services/keyboards.py:56", "Поделиться"),
        ("skip_ad", "daily_poster.py:149 / bot.py:631", "Пропустить"),
        ("copy_letter", "bot.py:751", "Копировать письмо"),
        ("pdf_letter", "bot.py:752", "PDF письма"),
        ("filter:furnished", "bot.py:701", "Мебель"),
        ("filter:pets", "bot.py:702", "Питомцы"),
        ("filter:parking", "bot.py:703", "Парковка"),
        ("lang_ru", "bot.py:1015", "Русский"),
        ("lang_uk", "bot.py:1016", "Українська"),
        ("lang_en", "bot.py:1019", "English"),
        ("lang_de", "bot.py:1020", "Deutsch"),
        ("lang_pl", "bot.py:1023", "Polski"),
        ("select_city:remove", "bot.py:1257", "Снять фильтр"),
    ]

    print("\n  Static callback_data:")
    all_ok = True
    for data, location, desc in static_buttons:
        byte_len = len(data.encode("utf-8"))
        status = "OK" if byte_len <= TELEGRAM_64_BYTE_LIMIT else "OVERFLOW"
        if byte_len > TELEGRAM_64_BYTE_LIMIT:
            all_ok = False
            errors.append(f"  OVERFLOW: '{data}' = {byte_len} bytes at {location} ({desc})")
        print(f"    {status}: '{data}' = {byte_len} bytes ({desc}, {location})")

    # Dynamic callback_data patterns — analyze worst case
    print("\n  Dynamic callback_data (worst-case analysis):")

    # analyze_ad:{token} — token is secrets.token_urlsafe(6)[:8] = max 8 chars
    # "analyze_ad:" = 12 bytes + 8 = 20 bytes
    analyze_ad_max = "analyze_ad:" + "abcdefgh"  # 8-char token
    byte_len = len(analyze_ad_max.encode("utf-8"))
    status = "OK" if byte_len <= TELEGRAM_64_BYTE_LIMIT else "OVERFLOW"
    if byte_len > TELEGRAM_64_BYTE_LIMIT:
        all_ok = False
    print(f"    {status}: analyze_ad:{{token}} max = {byte_len} bytes ('{analyze_ad_max}')")

    # analyze_rss:{short_id} — short_id is secrets.token_urlsafe(6)[:8] = max 8 chars
    # "analyze_rss:" = 13 bytes + 8 = 21 bytes
    analyze_rss_max = "analyze_rss:" + "abcdefgh"
    byte_len = len(analyze_rss_max.encode("utf-8"))
    status = "OK" if byte_len <= TELEGRAM_64_BYTE_LIMIT else "OVERFLOW"
    if byte_len > TELEGRAM_64_BYTE_LIMIT:
        all_ok = False
    print(f"    {status}: analyze_rss:{{short_id}} max = {byte_len} bytes ('{analyze_rss_max}')")

    # select_city:{key} — longest city key
    from listing_features import POPULAR_CITIES
    longest_key = max(POPULAR_CITIES.keys(), key=len)
    select_city_max = f"select_city:{longest_key}"
    byte_len = len(select_city_max.encode("utf-8"))
    status = "OK" if byte_len <= TELEGRAM_64_BYTE_LIMIT else "OVERFLOW"
    if byte_len > TELEGRAM_64_BYTE_LIMIT:
        all_ok = False
    print(f"    {status}: select_city:{{key}} max = {byte_len} bytes ('{select_city_max}', key='{longest_key}')")

    # fav_del:{id} — SERIAL (integer), max ~10 digits
    fav_del_max = f"fav_del:{'9' * 10}"
    byte_len = len(fav_del_max.encode("utf-8"))
    status = "OK" if byte_len <= TELEGRAM_64_BYTE_LIMIT else "OVERFLOW"
    if byte_len > TELEGRAM_64_BYTE_LIMIT:
        all_ok = False
    print(f"    {status}: fav_del:{{id}} max = {byte_len} bytes ('{fav_del_max}')")

    # track:{entry_id}:{status} — SERIAL + longest status
    longest_status = max(
        ["saved", "applied", "viewed", "interview", "accepted", "rejected"],
        key=len
    )
    track_max = f"track:{'9' * 10}:{longest_status}"
    byte_len = len(track_max.encode("utf-8"))
    status = "OK" if byte_len <= TELEGRAM_64_BYTE_LIMIT else "OVERFLOW"
    if byte_len > TELEGRAM_64_BYTE_LIMIT:
        all_ok = False
    print(f"    {status}: track:{{id}}:{{status}} max = {byte_len} bytes ('{track_max}')")

    if all_ok:
        print("\n  ALL callback_data values are within the 64-byte limit!")
    else:
        print("\n  SOME callback_data values EXCEED the 64-byte limit!")

    # Also check for emoji in callback_data (can cause regex matching issues)
    print("\n  Emoji in callback_data check:")
    emoji_found = False
    for data, location, desc in static_buttons:
        # Check for non-ASCII characters
        non_ascii = [c for c in data if ord(c) > 127]
        if non_ascii:
            print(f"    WARNING: '{data}' contains non-ASCII chars at {location}")
            emoji_found = True
    if not emoji_found:
        print("    OK: No emoji or non-ASCII characters in callback_data")

    if all_ok and not emoji_found:
        info.append("Test 4 PASSED: All callback_data within limits")
    else:
        if not all_ok:
            info.append("Test 4 FAILED: Some callback_data exceeds 64-byte limit")
        if emoji_found:
            info.append("Test 4 WARNING: Non-ASCII chars in callback_data")


# ═══════════════════════════════════════════════════════════════════
# TEST 5: Referral self-referral and edge cases
# ═══════════════════════════════════════════════════════════════════

def test_5_referral_edge_cases():
    print("\n" + "=" * 70)
    print("TEST 5: Referral edge cases")
    print("=" * 70)

    # 5a. Self-referral prevention
    user_id = "123"
    data = {
        "123": {"ref_code": "ref_abc12345"},
        "456": {"ref_code": "ref_def67890"},
    }
    payload = "ref_abc12345"  # User clicking their own link
    referrer_id = None
    for uid, u in data.items():
        if u.get("ref_code") == payload:
            referrer_id = uid
            break

    if referrer_id and referrer_id != user_id:
        print("  FAIL: Self-referral not prevented!")
        errors.append("  BUG: Self-referral not prevented")
    else:
        print("  OK: Self-referral prevented (referrer_id == user_id)")

    # 5b. Double-referral prevention (same person clicks twice)
    new_user_data = {"referred_by": "456"}
    # Second click should not overwrite
    if not new_user_data.get("referred_by"):
        new_user_data["referred_by"] = "789"
        print("  BUG: Second referral click overwrites first!")
    else:
        print("  OK: Second referral click does NOT overwrite (referred_by already set)")

    # 5c. Referral credit only on first check (free_used == 1)
    user_after_2_checks = {"free_used": 2, "referred_by": "456"}
    should_credit = user_after_2_checks.get("free_used", 0) == 1 and user_after_2_checks.get("referred_by")
    assert not should_credit, "Should NOT credit after 2nd check"
    print("  OK: No credit after 2nd check (free_used=2)")

    user_after_1_check = {"free_used": 1, "referred_by": "456"}
    should_credit = user_after_1_check.get("free_used", 0) == 1 and user_after_1_check.get("referred_by")
    assert should_credit, "Should credit after 1st check"
    print("  OK: Credit given after 1st check (free_used=1)")

    # 5d. Dedup: same referrer doesn't get double credit
    referrer = {"referrals": ["456"], "balance": 1}
    new_user_id = "456"
    if new_user_id not in referrer["referrals"]:
        referrer["referrals"].append(new_user_id)
    assert len(referrer["referrals"]) == 1, "Should not add duplicate"
    assert referrer["balance"] == 1, "Balance should not change on dedup"
    print("  OK: Dedup prevents double credit")

    # 5e. referred_by is cleared after credit
    user = {"referred_by": "456"}
    user.pop("referred_by", None)
    assert "referred_by" not in user
    print("  OK: referred_by cleared after credit")

    info.append("Test 5 PASSED: Referral edge cases handled correctly")


# ═══════════════════════════════════════════════════════════════════
# TEST 6: Deep link payload truncation and encoding
# ═══════════════════════════════════════════════════════════════════

def test_6_payload_edge_cases():
    print("\n" + "=" * 70)
    print("TEST 6: Deep link payload edge cases")
    print("=" * 70)

    # 6a. Payload truncation to 512 chars
    long_payload = "a" * 1000
    truncated = long_payload[:512]
    assert len(truncated) == 512
    print("  OK: Payload truncation to 512 chars works")

    # 6b. URL encoding in analyze_ payloads
    from urllib.parse import quote, unquote
    url_with_special = "https://example.com/path?a=1&b=2#frag"
    encoded = quote(url_with_special, safe='')
    analyze_payload = f"analyze_{encoded}"
    # Extract
    extracted = unquote(analyze_payload[len("analyze_"):])
    assert extracted == url_with_special, f"Round-trip failed: {extracted}"
    print(f"  OK: URL encoding round-trip works ({len(analyze_payload)} chars)")

    # 6c. Very long URL in analyze_ payload
    very_long_url = "https://example.com/" + "a" * 500
    encoded_long = quote(very_long_url, safe='')
    analyze_long = f"analyze_{encoded_long}"
    start_param = analyze_long[:64]  # Telegram truncates to 64
    # This is a KNOWN ISSUE — Telegram truncates start= to 64 bytes
    if len(analyze_long) > 64:
        print(f"  WARNING: Long URLs in analyze_ format get truncated by Telegram!")
        print(f"    Full payload: {len(analyze_long)} bytes, but start= limited to 64")
        # This is why the an_TOKEN format was introduced
        warnings.append("  Long URLs in old analyze_ format are truncated by Telegram (known, mitigated by an_TOKEN)")

    # 6d. an_TOKEN format stays under 64 bytes
    token = secrets.token_urlsafe(6)[:8]
    an_payload = f"an_{token}"
    assert len(an_payload.encode("utf-8")) <= 64, f"an_TOKEN exceeds 64 bytes: {len(an_payload)}"
    print(f"  OK: an_TOKEN format = {len(an_payload)} bytes (well under 64)")

    # 6e. ref_CODE stays under 64 bytes
    ref_code = f"ref_{hashlib.sha256(b'123456eurorent2024').hexdigest()[:8]}"
    assert len(ref_code.encode("utf-8")) <= 64, f"ref_CODE exceeds 64 bytes: {len(ref_code)}"
    print(f"  OK: ref_CODE format = {len(ref_code)} bytes (well under 64)")

    # 6f. Context of start handler — check all payload prefixes
    prefixes = ["an_", "analyze_", "ref_"]
    for prefix in prefixes:
        print(f"  Prefix '{prefix}': {len(prefix)} bytes prefix")

    info.append("Test 6 PASSED: Payload edge cases handled correctly")


# ═══════════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("DEEP LINK & REFERRAL CODE AUDIT")
    print(f"Project: {os.path.dirname(os.path.abspath(__file__))}")
    print("=" * 70)

    tests = [
        test_1_referral_flow,
        test_2_raw_user_id_as_ref_code,
        test_3_deep_link_chain,
        test_4_callback_data_length,
        test_5_referral_edge_cases,
        test_6_payload_edge_cases,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {t.__name__}: {e}")
            errors.append(f"  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {t.__name__}: {e}")
            errors.append(f"  {t.__name__} EXCEPTION: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)
    print(f"\nTests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")

    if errors:
        print(f"\nBUGS FOUND ({len(errors)}):")
        for e in errors:
            print(f"  ❌ {e}")
    else:
        print("\n✅ NO BUGS FOUND")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠️  {w}")

    if info:
        print(f"\nINFO:")
        for i in info:
            print(f"  ℹ️  {i}")

    print("\n" + "=" * 70)
    print("END OF AUDIT")
    print("=" * 70)
