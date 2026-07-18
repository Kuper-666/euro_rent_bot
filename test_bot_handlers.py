import os
import sys
import time
import json
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock, ANY

sys.path.insert(0, os.path.dirname(__file__))

from utils import can_use, use_check, get_user_data, calc_remaining, validate_pdf_data, is_pdf_state_expired

# Redirect metrics logging to a temp file for the whole test run. Several
# tests exercise real bot code paths (start(), process_listing(),
# successful_payment()) that now call metrics.log_event() internally --
# without this redirect, every test run would append to the project's
# actual metrics_events.jsonl as an unintended side effect.
import metrics as _metrics_module
_metrics_module.METRICS_FILE = "/tmp/test_suite_metrics_events.jsonl"


# ── Helpers ───────────────────────────────────────────────────────

def make_user(**overrides):
    base = {"free_used": 0, "balance": 0}
    base.update(overrides)
    return base


def make_update(text="test", user_id=123, chat_type="private", lang="ru"):
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.reply_photo = AsyncMock()
    update.message.reply_document = AsyncMock()
    update.effective_user.id = user_id
    update.effective_user.full_name = "Test User"
    update.effective_chat.type = chat_type
    update.effective_chat.id = user_id
    update.effective_chat.send_message = AsyncMock()
    update.callback_query = MagicMock()
    update.callback_query.data = ""
    update.callback_query.answer = AsyncMock()
    update.callback_query.from_user = MagicMock()
    update.callback_query.from_user.id = user_id
    update.callback_query.message = MagicMock()
    update.callback_query.message.reply_text = AsyncMock()
    update.language_code = lang
    return update


def make_context(bot_username="TestBot"):
    ctx = MagicMock()
    ctx.bot.username = bot_username
    ctx.bot.id = 999
    ctx.bot.get_chat_member = AsyncMock(return_value=MagicMock(status="member"))
    ctx.bot.send_message = AsyncMock()
    ctx.bot.send_document = AsyncMock()
    ctx.args = []
    return ctx


# ── can_use / use_check ───────────────────────────────────────────

class TestCanUse(unittest.TestCase):
    def test_free_user_has_checks(self):
        user = make_user(free_used=0, balance=0)
        self.assertTrue(can_use(user))

    def test_free_user_exhausted(self):
        user = make_user(free_used=3, balance=0)
        self.assertFalse(can_use(user))

    def test_paid_balance_positive(self):
        user = make_user(balance=5, free_used=3)
        self.assertTrue(can_use(user))

    def test_unlimited_active(self):
        user = make_user(balance=-1, last_paid_at=time.time())
        self.assertTrue(can_use(user))

    def test_unlimited_expired(self):
        user = make_user(balance=-1, last_paid_at=time.time() - 40 * 86400)
        self.assertFalse(can_use(user))


class TestUseCheck(unittest.TestCase):
    def test_decrements_balance(self):
        user = make_user(balance=5)
        use_check(user)
        self.assertEqual(user["balance"], 4)

    def test_increments_free_used(self):
        user = make_user(balance=0, free_used=0)
        use_check(user)
        self.assertEqual(user["free_used"], 1)

    def test_unlimited_no_change(self):
        user = make_user(balance=-1)
        use_check(user)
        self.assertEqual(user["balance"], -1)

    def test_empty_user_dict_does_not_crash(self):
        """
        Regression: use_check used to read user["balance"]/user["free_used"]
        directly (no .get), which raised KeyError for a brand-new user with
        no DB record yet -- e.g. someone messaging the bot directly without
        ever pressing /start, or get_user() returning {} because Supabase
        has no row for them yet. process_listing surfaced this as
        "Ошибка: 'balance'" in the chat.
        """
        user = {}
        use_check(user)
        self.assertEqual(user["free_used"], 1)
        self.assertEqual(user["total_checks"], 1)


class TestCalcRemaining(unittest.TestCase):
    def test_unlimited(self):
        user = make_user(balance=-1)
        self.assertEqual(calc_remaining(user), "∞")

    def test_paid(self):
        user = make_user(balance=5, free_used=3)
        self.assertEqual(calc_remaining(user), "5")

    def test_free(self):
        user = make_user(balance=0, free_used=1)
        self.assertEqual(calc_remaining(user), "2")


# ── PDF validation ────────────────────────────────────────────────

class TestValidatePdfData(unittest.TestCase):
    def test_valid_data(self):
        data = {
            "name": "Max Mustermann",
            "dob": "01.01.1990",
            "phone": "+49123456789",
            "email": "max@example.com",
            "address": "Berliner Str. 1",
            "employer": "Tech GmbH",
            "income": "3500",
            "occupants": "1",
        }
        ok, err = validate_pdf_data(data)
        self.assertTrue(ok)
        self.assertEqual(err, "")

    def test_missing_fields(self):
        data = {"name": "Max"}
        ok, err = validate_pdf_data(data)
        self.assertFalse(ok)
        self.assertIn("Отсутствуют", err)

    def test_short_name(self):
        data = {
            "name": "Al",
            "dob": "01.01.1990",
            "phone": "+49123456789",
            "email": "max@example.com",
            "address": "Berliner Str. 1",
            "employer": "Tech GmbH",
            "income": "3500",
            "occupants": "1",
        }
        ok, err = validate_pdf_data(data)
        self.assertFalse(ok)
        self.assertIn("Имя", err)

    def test_invalid_email(self):
        data = {
            "name": "Max Mustermann",
            "dob": "01.01.1990",
            "phone": "+49123456789",
            "email": "invalid",
            "address": "Berliner Str. 1",
            "employer": "Tech GmbH",
            "income": "3500",
            "occupants": "1",
        }
        ok, err = validate_pdf_data(data)
        self.assertFalse(ok)
        self.assertIn("email", err)


class TestPdfStateExpired(unittest.TestCase):
    def test_not_expired(self):
        user = make_user(pdf_state="awaiting_data", pdf_started_at=time.time())
        self.assertFalse(is_pdf_state_expired(user))

    def test_expired(self):
        user = make_user(pdf_state="awaiting_data", pdf_started_at=time.time() - 3600)
        self.assertTrue(is_pdf_state_expired(user))

    def test_no_started_at(self):
        user = make_user(pdf_state="awaiting_data")
        self.assertTrue(is_pdf_state_expired(user))

    def test_different_state(self):
        user = make_user(pdf_state="other")
        self.assertFalse(is_pdf_state_expired(user))


# ── handle_message ────────────────────────────────────────────────

class TestHandleMessage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module
        self.bot_module._flood_tracker.clear()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_button_start_routes(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="старт")
        ctx = make_context()
        with patch("bot.start", new_callable=AsyncMock) as mock_start:
            await self.bot_module.handle_message(update, ctx)
            mock_start.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_button_help_routes(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="помощь")
        ctx = make_context()
        with patch("bot.help_command", new_callable=AsyncMock) as mock_help:
            await self.bot_module.handle_message(update, ctx)
            mock_help.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_flood_control(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="hello")
        ctx = make_context()
        uid = str(update.effective_user.id)
        now = time.time()
        self.bot_module._flood_tracker[uid] = (11, now)
        await self.bot_module.handle_message(update, ctx)
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Слишком много", call_text)

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.get_user", return_value={"free_used": 3, "balance": 0, "lang": "ru"})
    @patch("bot.update_last_activity")
    async def test_limit_reached(self, mock_activity, mock_get_user, mock_load, mock_save):
        user = make_user(free_used=3, balance=0)
        mock_load.return_value = {"123": user}
        update = make_update(text="some listing text here")
        ctx = make_context()
        uid = str(update.effective_user.id)
        self.bot_module._flood_tracker[uid] = (0, time.time())
        with patch("bot.get_lang", return_value="ru"):
            await self.bot_module.handle_message(update, ctx)
        self.assertTrue(update.message.reply_text.called)
        call_text = update.message.reply_text.call_args[0][0]
        self.assertTrue(
            "лимит" in call_text.lower() or "закончились" in call_text.lower() or "limit" in call_text.lower(),
            f"Expected limit message, got: {call_text[:100]}"
        )


# ── process_listing ───────────────────────────────────────────────

class TestProcessListing(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    @unittest.skip("Mocking load_data inside _payment_lock requires integration test")
    async def test_successful_analysis(self):
        user = {"free_used": 0, "balance": 5}
        data = {"123": user}
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Analysis result"))]

        update = make_update(text="Wohnung 3 Zimmer Berlin 1200€")
        ctx = make_context()
        with patch.object(self.bot_module, "load_data", return_value=data):
            with patch.object(self.bot_module, "save_data"):
                with patch.object(self.bot_module, "client") as mc:
                    mc.chat.completions.create.return_value = mock_response
                    with patch.object(self.bot_module, "extract_score", return_value=7):
                        await self.bot_module.process_listing(update, ctx, "Wohnung 3 Zimmer Berlin 1200€", "123", "ru")

        self.assertEqual(data["123"]["balance"], 4)
        update.message.reply_text.assert_called()

    @patch("handlers.listing_analyzer.save_data")
    @patch("handlers.listing_analyzer.load_data")
    @patch("handlers.listing_analyzer.client")
    async def test_admin_bypass(self, mock_client, mock_load, mock_save):
        """
        Regression: this test previously used the default chat_type="private",
        so `if not is_admin and update.effective_chat.type in ["group",
        "supergroup"]:` was never true, get_chat_member was never actually
        consulted, and the test silently exercised the non-admin path the
        whole time despite its name and the mocked "administrator" status.
        Using chat_type="group" here makes it genuinely test the group-
        moderator admin bypass.
        """
        user = make_user(free_used=3, balance=0)
        mock_load.return_value = {"123": user}
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Analysis"))]
        mock_client.chat.completions.create.return_value = mock_response

        update = make_update(text="Wohnung Berlin", chat_type="group")
        ctx = make_context()
        ctx.bot.get_chat_member.return_value = MagicMock(status="administrator")

        with patch("bot.extract_score", return_value=5):
            await self.bot_module.process_listing(update, ctx, "Wohnung Berlin", "123", "ru")

        self.assertEqual(user["free_used"], 3)
        update.message.reply_text.assert_called()
        # reply_text is ALSO called from the except-block on failure (with
        # get_msg(lang, "error").format(...)) -- assert_called() alone
        # would stay green even if process_listing crashed internally, as
        # it did for the ADMIN_ID path below. Check the actual text.
        sent_text = update.message.reply_text.call_args_list[-1][0][0]
        self.assertNotIn("Ошибка:", sent_text)

    @patch("handlers.listing_analyzer.save_data")
    @patch("handlers.listing_analyzer.load_data")
    @patch("handlers.listing_analyzer.get_user")
    @patch("handlers.listing_analyzer.client")
    async def test_admin_id_own_analysis_does_not_crash(self, mock_client, mock_get_user, mock_load, mock_save):
        """
        Регрессия: process_listing присваивал переменную `user` ТОЛЬКО в
        ветке else (не-админ), но использовал её дальше по коду (в т.ч.
        remaining = calc_remaining(user), user.get("ref_code") и т.д.)
        независимо от того, админ это или нет. Когда сообщение прислал сам
        ADMIN_ID (не просто модератор группы, как в test_admin_bypass выше,
        а владелец бота лично), process_listing падал с:
        UnboundLocalError: cannot access local variable 'user' where it is
        not associated with a value -- и пользователь видел это в чате как
        "Ошибка: cannot access local variable 'user'...".
        """
        os.environ["ADMIN_ID"] = "999"
        mock_load.return_value = {}
        mock_get_user.return_value = {"balance": -1, "free_used": 10, "ref_code": "ref_admin"}
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Analysis for the admin"))]
        mock_client.chat.completions.create.return_value = mock_response

        update = make_update(user_id=999, text="Wohnung Berlin")
        ctx = make_context()

        with patch("handlers.listing_analyzer.extract_score", return_value=5):
            await self.bot_module.process_listing(update, ctx, "Wohnung Berlin", "999", "ru")

        sent_text = update.message.reply_text.call_args_list[-1][0][0]
        self.assertNotIn("Ошибка:", sent_text)
        self.assertIn("Analysis for the admin", sent_text)


# ── handle_photo ────────────────────────────────────────────────

class TestHandlePhoto(unittest.IsolatedAsyncioTestCase):
    """
    Regression: handle_photo called process_listing(..., source_url=source_url),
    but `source_url` was NEVER assigned anywhere in handle_photo (it only
    makes sense for the URL-fetch path in handle_message, which handle_photo
    doesn't have -- this is an OCR path). This was a guaranteed NameError on
    every single photo sent to the bot: "name 'source_url' is not defined".
    No test previously covered handle_photo's success path end-to-end, so
    this went unnoticed.
    """

    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    async def test_photo_analysis_does_not_raise_nameerror(self):
        update = make_update(user_id=456)
        update.message.photo = [MagicMock(file_id="abc123")]
        ctx = make_context()
        ctx.bot.get_file = AsyncMock(return_value=MagicMock())
        ctx.bot.get_file.return_value.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake"))

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Photo analysis result"))]

        with patch("bot.get_user", return_value={"balance": 5}):
            with patch("bot.check_rate_limit", return_value=(True, 0)):
                with patch("bot.ocr_from_photo", return_value="Wohnung Berlin 3 Zimmer 1200 EUR"):
                    with patch("bot.get_user_city", return_value=None):
                        with patch("handlers.listing_analyzer.get_user", return_value={"balance": 5}):
                            with patch("handlers.listing_analyzer.client") as mock_client:
                                mock_client.chat.completions.create.return_value = mock_response
                                with patch("handlers.listing_analyzer.extract_score", return_value=5):
                                    await self.bot_module.handle_photo(update, ctx)

        sent_text = update.message.reply_text.call_args_list[-1][0][0]
        self.assertNotIn("source_url", sent_text)
        self.assertNotIn("Ошибка:", sent_text)
        self.assertIn("Photo analysis result", sent_text)


# ── successful_payment ────────────────────────────────────────────

class TestSuccessfulPayment(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    @patch("handlers.payments.save_user")
    @patch("handlers.payments.get_user")
    async def test_pay_3(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update()
        update.message.successful_payment = MagicMock(invoice_payload="pay_stars_3")
        ctx = make_context()
        from handlers.payments import successful_payment
        await successful_payment(update, ctx)
        self.assertEqual(user["balance"], 3)
        self.assertIn("last_paid_at", user)

    @patch("handlers.payments.save_user")
    @patch("handlers.payments.get_user")
    async def test_pay_9(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update()
        update.message.successful_payment = MagicMock(invoice_payload="pay_stars_9")
        ctx = make_context()
        from handlers.payments import successful_payment
        await successful_payment(update, ctx)
        self.assertEqual(user["balance"], 10)

    @patch("handlers.payments.save_user")
    @patch("handlers.payments.get_user")
    async def test_pay_19_unlimited(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update()
        update.message.successful_payment = MagicMock(invoice_payload="pay_stars_19")
        ctx = make_context()
        from handlers.payments import successful_payment
        await successful_payment(update, ctx)
        self.assertEqual(user["balance"], -1)

    @patch("handlers.payments.save_user")
    @patch("handlers.payments.get_user")
    async def test_pay_pdf(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update()
        update.message.successful_payment = MagicMock(invoice_payload="pay_stars_pdf")
        ctx = make_context()
        from handlers.payments import successful_payment
        await successful_payment(update, ctx)
        self.assertTrue(user["pdf_paid"])
        self.assertEqual(user["pdf_state"], "awaiting_data")
        self.assertIn("pdf_started_at", user)


# ── pay_done_* admin check ────────────────────────────────────────

class TestPayDoneAdminOnly(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    @patch("bot.save_data")
    @patch("bot.load_data")
    async def test_pay_done_3_non_admin_silently_ignored(self, mock_load, mock_save):
        user = make_user()
        mock_load.return_value = {"123": user}
        update = make_update(user_id=999)
        ctx = make_context()
        with patch.dict(os.environ, {"ADMIN_ID": "111"}):
            await self.bot_module.pay_done_3(update, ctx)
        update.message.reply_text.assert_not_called()
        self.assertEqual(user["balance"], 0)

    @patch("handlers.payments.save_user")
    @patch("handlers.payments.get_user")
    async def test_pay_done_3_admin_works(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update(user_id=111)
        ctx = make_context()
        with patch.dict(os.environ, {"ADMIN_ID": "111"}):
            from handlers.payments import pay_done_3
            await pay_done_3(update, ctx)
        self.assertEqual(user["balance"], 3)

    @patch("handlers.payments.save_user")
    @patch("handlers.payments.get_user")
    async def test_pay_done_vip_non_admin_silently_ignored(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update(user_id=999)
        ctx = make_context()
        with patch.dict(os.environ, {"ADMIN_ID": "111"}):
            await self.bot_module.pay_done_vip(update, ctx)
        update.message.reply_text.assert_not_called()
        self.assertNotIn("vip", user)

    @patch("bot.save_data")
    @patch("bot.load_data")
    async def test_pay_done_pdf_non_admin_silently_ignored(self, mock_load, mock_save):
        user = make_user()
        mock_load.return_value = {"123": user}
        update = make_update(user_id=999)
        ctx = make_context()
        with patch.dict(os.environ, {"ADMIN_ID": "111"}):
            await self.bot_module.pay_done_pdf(update, ctx)
        update.message.reply_text.assert_not_called()
        self.assertNotIn("pdf_paid", user)


# ── welcome_new_member ────────────────────────────────────────────

class TestWelcomeNewMember(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    async def test_welcome_new_user(self):
        update = MagicMock()
        update.chat_member.new_chat_member = MagicMock(
            user=MagicMock(id=456, full_name="New User"),
            status="member",
        )
        update.chat_member.old_chat_member = MagicMock(status="left")
        update.effective_chat.send_message = AsyncMock()
        ctx = make_context()
        await self.bot_module.welcome_new_member(update, ctx)
        update.effective_chat.send_message.assert_called_once()
        call_text = update.effective_chat.send_message.call_args[0][0]
        self.assertIn("Добро пожаловать", call_text)

    async def test_bot_self_join_no_crash(self):
        update = MagicMock()
        update.chat_member.new_chat_member = MagicMock(
            user=MagicMock(id=999, full_name="Bot"),
            status="member",
        )
        update.chat_member.old_chat_member = MagicMock(status="left")
        update.effective_chat.send_message = AsyncMock()
        ctx = make_context()
        await self.bot_module.welcome_new_member(update, ctx)
        update.effective_chat.send_message.assert_not_called()

    async def test_old_member_no_welcome(self):
        update = MagicMock()
        update.chat_member.new_chat_member = MagicMock(
            user=MagicMock(id=456, full_name="User"),
            status="member",
        )
        update.chat_member.old_chat_member = MagicMock(status="member")
        update.effective_chat.send_message = AsyncMock()
        ctx = make_context()
        await self.bot_module.welcome_new_member(update, ctx)
        update.effective_chat.send_message.assert_not_called()


# ── get_user_data ─────────────────────────────────────────────────

class TestGetUserData(unittest.TestCase):
    def test_existing_user(self):
        data = {"123": {"balance": 5}}
        user = get_user_data(data, "123")
        self.assertEqual(user["balance"], 5)

    def test_new_user(self):
        data = {}
        user = get_user_data(data, "456")
        self.assertEqual(user["free_used"], 0)
        self.assertEqual(user["balance"], 0)
        self.assertIn("456", data)


# ── get_msg ────────────────────────────────────────────────────────

class TestGetMsg(unittest.TestCase):
    def test_all_langs_have_required_keys(self):
        from messages import get_msg, MESSAGES
        required = [
            "start", "help", "analyzing", "fetching_url", "ocr_processing",
            "limit_reached", "error", "send_listing", "share_text",
            "analysis_done", "pay_done_3", "pay_done_9", "pay_done_19",
            "pdf_generating", "pdf_done", "pdf_error", "system_prompt",
            "group_redirect", "city_selected", "city_filter_skip",
        ]
        for lang in MESSAGES:
            for key in required:
                msg = get_msg(lang, key)
                self.assertTrue(msg, f"Missing {key} for lang={lang}")

    def test_unknown_lang_falls_back_to_english(self):
        from messages import get_msg
        result = get_msg("xx", "start")
        en_result = get_msg("en", "start")
        self.assertEqual(result, en_result)

    def test_unknown_key_falls_back_to_english(self):
        from messages import get_msg
        result = get_msg("ru", "nonexistent_key_xyz")
        en_result = get_msg("en", "nonexistent_key_xyz")
        self.assertEqual(result, en_result)


# ── get_lang ───────────────────────────────────────────────────────

class TestGetLang(unittest.TestCase):
    def test_returns_saved_lang(self):
        from utils import get_lang
        update = make_update(user_id=123)
        update.effective_user.language_code = "en"
        with patch("utils.get_user", return_value={"lang": "de"}):
            result = get_lang(update)
        self.assertEqual(result, "de")

    def test_falls_back_to_tg_language(self):
        from utils import get_lang
        update = make_update(user_id=123)
        update.effective_user.language_code = "de"
        with patch("utils.get_user", return_value={}):
            result = get_lang(update)
        self.assertEqual(result, "de")

    def test_falls_back_to_default(self):
        from utils import get_lang
        update = make_update(user_id=123)
        update.effective_user.language_code = "fr"
        with patch("utils.get_user", return_value={}):
            result = get_lang(update)
        self.assertEqual(result, "en")


# ── Keyboard localization ──────────────────────────────────────────

class TestKeyboardLocalization(unittest.TestCase):
    def test_ru_keyboard_labels(self):
        from services.keyboards import get_keyboard
        kb = get_keyboard("ru")
        buttons = [btn.text for row in kb.keyboard for btn in row]
        self.assertIn("Старт", buttons)
        self.assertIn("Помощь", buttons)
        self.assertIn("Баланс", buttons)
        self.assertIn("Мой язык", buttons)

    def test_en_keyboard_labels(self):
        from services.keyboards import get_keyboard
        kb = get_keyboard("en")
        buttons = [btn.text for row in kb.keyboard for btn in row]
        self.assertIn("Start", buttons)
        self.assertIn("Help", buttons)
        self.assertIn("Balance", buttons)
        self.assertIn("My language", buttons)

    def test_de_keyboard_labels(self):
        from services.keyboards import get_keyboard
        kb = get_keyboard("de")
        buttons = [btn.text for row in kb.keyboard for btn in row]
        self.assertIn("Start", buttons)
        self.assertIn("Hilfe", buttons)
        self.assertIn("Guthaben", buttons)
        self.assertIn("Sprache", buttons)

    def test_uk_keyboard_labels(self):
        from services.keyboards import get_keyboard
        kb = get_keyboard("uk")
        buttons = [btn.text for row in kb.keyboard for btn in row]
        self.assertIn("Старт", buttons)
        self.assertIn("Допомога", buttons)
        self.assertIn("Мова", buttons)

    def test_pl_keyboard_labels(self):
        from services.keyboards import get_keyboard
        kb = get_keyboard("pl")
        buttons = [btn.text for row in kb.keyboard for btn in row]
        self.assertIn("Start", buttons)
        self.assertIn("Pomoc", buttons)
        self.assertIn("Język", buttons)

    def test_pdf_vip_always_same(self):
        from services.keyboards import get_keyboard
        for lang in ["ru", "uk", "en", "de", "pl"]:
            kb = get_keyboard(lang)
            buttons = [btn.text for row in kb.keyboard for btn in row]
            self.assertIn("PDF", buttons)
            self.assertIn("VIP", buttons)

    def test_kb_none_for_group(self):
        from services.keyboards import kb
        update = make_update(chat_type="group")
        self.assertIsNone(kb(update))

    def test_kb_none_for_supergroup(self):
        from services.keyboards import kb
        update = make_update(chat_type="supergroup")
        self.assertIsNone(kb(update))

    def test_kb_returns_keyboard_for_private(self):
        from services.keyboards import kb
        update = make_update(chat_type="private")
        result = kb(update)
        self.assertIsNotNone(result)


# ── Language callback ──────────────────────────────────────────────

class TestLanguageCallback(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    async def _run_lang_callback(self, callback_data, user_data=None):
        if user_data is None:
            user_data = {"free_used": 0, "balance": 0}
        update = make_update(user_id=123)
        update.callback_query.data = callback_data
        ctx = make_context()
        saved = {}
        def capture_save(uid, data):
            saved.update({uid: dict(data)})
        with patch("handlers.callbacks_lang.get_user", return_value=dict(user_data)):
            with patch("handlers.callbacks_lang.save_user", side_effect=capture_save):
                from handlers.callbacks_lang import handle_lang_switch
                await handle_lang_switch(update, ctx)
        return saved

    async def test_lang_ru_saves(self):
        saved = await self._run_lang_callback("lang_ru")
        self.assertEqual(saved["123"]["lang"], "ru")

    async def test_lang_en_saves(self):
        saved = await self._run_lang_callback("lang_en", {"lang": "ru", "free_used": 0, "balance": 0})
        self.assertEqual(saved["123"]["lang"], "en")

    async def test_lang_de_saves(self):
        saved = await self._run_lang_callback("lang_de", {"lang": "en", "free_used": 0, "balance": 0})
        self.assertEqual(saved["123"]["lang"], "de")

    async def test_lang_uk_saves(self):
        saved = await self._run_lang_callback("lang_uk")
        self.assertEqual(saved["123"]["lang"], "uk")

    async def test_lang_pl_saves(self):
        saved = await self._run_lang_callback("lang_pl")
        self.assertEqual(saved["123"]["lang"], "pl")

    async def test_lang_callback_shows_alert(self):
        update = make_update(user_id=123)
        update.callback_query.data = "lang_en"
        ctx = make_context()
        with patch("handlers.callbacks_lang.get_user", return_value={"free_used": 0, "balance": 0}):
            with patch("handlers.callbacks_lang.save_user"):
                from handlers.callbacks_lang import handle_lang_switch
                await handle_lang_switch(update, ctx)
        update.callback_query.answer.assert_called_once()
        call_args = update.callback_query.answer.call_args
        self.assertIn("English", call_args[0][0])
        self.assertTrue(call_args[1]["show_alert"])

    async def test_lang_callback_sends_confirmation_message(self):
        """After language switch, bot clears keyboard and sends welcome in new language."""
        update = make_update(user_id=123)
        update.callback_query.data = "lang_ru"
        update.callback_query.edit_message_reply_markup = AsyncMock()
        ctx = make_context()
        with patch("handlers.callbacks_lang.get_user", return_value={"free_used": 0, "balance": 0}):
            with patch("handlers.callbacks_lang.save_user"):
                from handlers.callbacks_lang import handle_lang_switch
                await handle_lang_switch(update, ctx)
        update.callback_query.edit_message_reply_markup.assert_called_once_with(reply_markup=None)
        ctx.bot.send_message.assert_called_once()
        call_kwargs = ctx.bot.send_message.call_args[1]
        self.assertEqual(call_kwargs["chat_id"], 123)

    async def test_lang_callback_answers_before_db_access(self):
        """answer() must fire BEFORE database read/write (10s Telegram timeout)."""
        call_order = []
        update = make_update(user_id=123)
        update.callback_query.data = "lang_de"

        async def record_answer(*a, **k):
            call_order.append("answer")
        update.callback_query.answer = AsyncMock(side_effect=record_answer)

        def record_get_user(uid):
            call_order.append("get_user")
            return {"free_used": 0, "balance": 0}

        def record_save_user(uid, data):
            call_order.append("save_user")

        ctx = make_context()
        with patch("handlers.callbacks_lang.get_user", side_effect=record_get_user):
            with patch("handlers.callbacks_lang.save_user", side_effect=record_save_user):
                from handlers.callbacks_lang import handle_lang_switch
                await handle_lang_switch(update, ctx)

        self.assertEqual(call_order[0], "answer", f"answer() must be first, got order: {call_order}")

    async def test_lang_callback_db_failure_notifies_user(self):
        """If DB save fails, user gets explicit error message."""
        update = make_update(user_id=123)
        update.callback_query.data = "lang_en"
        ctx = make_context()
        with patch("handlers.callbacks_lang.get_user", side_effect=Exception("Supabase unavailable")):
            from handlers.callbacks_lang import handle_lang_switch
            await handle_lang_switch(update, ctx)
        ctx.bot.send_message.assert_called_once()
        call_kwargs = ctx.bot.send_message.call_args[1]
        self.assertEqual(call_kwargs["chat_id"], 123)


# ── Callback handler branches ──────────────────────────────────────

class TestCallbackHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    @patch("bot.load_data")
    async def test_skip_ad_answers_ok(self, mock_load):
        update = make_update(user_id=123)
        update.callback_query.data = "skip_ad"
        update.callback_query.edit_message_reply_markup = AsyncMock()
        ctx = make_context()
        from handlers.callbacks_listing import handle_skip_ad
        await handle_skip_ad(update, ctx)
        update.callback_query.answer.assert_called_once()

    @patch("bot.load_data")
    async def test_copy_answers_copied(self, mock_load):
        update = make_update(user_id=123)
        update.callback_query.data = "copy"
        ctx = make_context()
        from handlers.callbacks_listing import handle_copy
        await handle_copy(update, ctx)
        self.assertTrue(update.callback_query.answer.called)

    @patch("handlers.callbacks_listing.get_user", return_value={"free_used": 0, "balance": 5})
    async def test_new_callback_sends_message(self, mock_get_user):
        update = make_update(user_id=123)
        update.callback_query.data = "new"
        update.callback_query.edit_message_reply_markup = AsyncMock()
        ctx = make_context()
        from handlers.callbacks_listing import handle_new_listing
        await handle_new_listing(update, ctx)
        ctx.bot.send_message.assert_called_once()
        call_kwargs = ctx.bot.send_message.call_args[1]
        self.assertEqual(call_kwargs["chat_id"], 123)

    @patch("handlers.callbacks_features.get_profile", return_value={"full_name": "Test"})
    @patch("handlers.callbacks_features.get_user", return_value={"last_letter": "Some cover letter text"})
    async def test_pdf_letter_does_not_block_event_loop(self, mock_get_user, mock_get_profile):
        """
        Regression: generate_mieterprofil_pdf (synchronous, CPU-bound PDF
        generation) used to be called directly inside the async pdf_letter
        branch, blocking the bot's entire event loop -- and therefore every
        other user's request -- for the duration of PDF generation.
        Confirmed via a concurrent-ticker test: a parallel task fully
        stalled during the blocking call and resumed immediately once
        wrapped in asyncio.to_thread.
        """
        update = make_update(user_id=123)
        update.callback_query.data = "pdf_letter"
        ctx = make_context()

        tick_count = {"n": 0}

        def slow_pdf_gen(data, cover_letter=""):
            time.sleep(0.3)
            return b"fake pdf bytes"

        async def ticker():
            for _ in range(5):
                tick_count["n"] += 1
                await asyncio.sleep(0.05)

        with patch("handlers.callbacks_features.generate_mieterprofil_pdf", side_effect=slow_pdf_gen):
            from handlers.callbacks_features import handle_pdf_letter
            await asyncio.gather(
                handle_pdf_letter(update, ctx),
                ticker(),
            )

        self.assertEqual(tick_count["n"], 5)
        ctx.bot.send_document.assert_called_once()


# ── Last analyzed listing tracking (favorites / letters) ───────────

class TestLastListingTracking(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        import handlers.user_features as huf_module
        self.bot_module = bot_module
        self.huf_module = huf_module
        self.huf_module._last_analyzed_cache.clear()

    async def test_fav_save_uses_real_url_not_listing_text(self):
        from handlers.user_features import track_last_url
        user_id = "123"
        with patch("handlers.user_features.get_user", return_value={"free_used": 0, "balance": 0}):
            with patch("handlers.user_features.save_user"):
                track_last_url(user_id, "https://example.com/listing/42", "Some scraped ad text here")
        update = make_update(user_id=123)
        update.callback_query.data = "fav_save"
        ctx = make_context()
        with patch("handlers.callbacks_features.add_favorite") as mock_add_fav:
            mock_add_fav.return_value = True
            from handlers.callbacks_features import handle_fav_save
            await handle_fav_save(update, ctx)
        mock_add_fav.assert_called_once()
        saved_url = mock_add_fav.call_args[0][1]
        self.assertEqual(saved_url, "https://example.com/listing/42")

    async def test_gen_letter_uses_listing_text_not_url(self):
        from handlers.user_features import track_last_url
        user_id = "123"
        with patch("handlers.user_features.get_user", return_value={"free_used": 0, "balance": 0}):
            with patch("handlers.user_features.save_user"):
                track_last_url(user_id, "https://example.com/listing/42", "Some scraped ad text here")
        update = make_update(user_id=123)
        update.callback_query.data = "gen_letter"
        ctx = make_context()
        with patch("handlers.callbacks_features.get_profile", return_value={"full_name": "A", "profession": "B", "income": "C", "employer": "D"}):
            with patch("handlers.callbacks_features.generate_letter", return_value="Dear Sir/Madam...") as mock_gen:
                with patch("handlers.callbacks_features.get_user", return_value={"free_used": 0, "balance": 0}):
                    with patch("handlers.callbacks_features.save_user"):
                        from handlers.callbacks_features import handle_gen_letter
                        await handle_gen_letter(update, ctx)
        mock_gen.assert_called_once()
        listing_text_arg = mock_gen.call_args[0][1]
        self.assertEqual(listing_text_arg, "Some scraped ad text here")

    async def test_fav_save_with_no_url_falls_back_to_text(self):
        from handlers.user_features import track_last_url
        user_id = "123"
        with patch("handlers.user_features.get_user", return_value={"free_used": 0, "balance": 0}):
            with patch("handlers.user_features.save_user"):
                track_last_url(user_id, "", "Raw pasted ad text without any link")
        update = make_update(user_id=123)
        update.callback_query.data = "fav_save"
        ctx = make_context()
        with patch("handlers.callbacks_features.add_favorite") as mock_add_fav:
            mock_add_fav.return_value = True
            from handlers.callbacks_features import handle_fav_save
            await handle_fav_save(update, ctx)
        mock_add_fav.assert_called_once()
        saved_value = mock_add_fav.call_args[0][1]
        self.assertIn("Raw pasted ad text", saved_value)

    async def test_last_listing_survives_in_memory_cache_clear(self):
        from handlers.user_features import track_last_url, get_last_url, get_last_listing_text
        user_id = "123"
        stored = {}
        def fake_save_user(uid, data):
            stored[uid] = dict(data)
        def fake_get_user(uid):
            return dict(stored.get(uid, {"free_used": 0, "balance": 0}))
        with patch("handlers.user_features.get_user", side_effect=fake_get_user):
            with patch("handlers.user_features.save_user", side_effect=fake_save_user):
                track_last_url(user_id, "https://example.com/x", "listing text")
        self.huf_module._last_analyzed_cache.clear()
        with patch("handlers.user_features.get_user", side_effect=fake_get_user):
            self.assertEqual(get_last_url(user_id), "https://example.com/x")
            self.assertEqual(get_last_listing_text(user_id), "listing text")


# ── Button routing ─────────────────────────────────────────────────

class TestButtonRouting(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module
        self.bot_module._flood_tracker.clear()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_ru_start_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Старт")
        ctx = make_context()
        with patch("bot.start", new_callable=AsyncMock) as mock_start:
            await self.bot_module.handle_message(update, ctx)
            mock_start.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_en_start_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Start")
        ctx = make_context()
        with patch("bot.start", new_callable=AsyncMock) as mock_start:
            await self.bot_module.handle_message(update, ctx)
            mock_start.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_ru_help_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Помощь")
        ctx = make_context()
        with patch("bot.help_command", new_callable=AsyncMock) as mock_help:
            await self.bot_module.handle_message(update, ctx)
            mock_help.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_en_help_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Help")
        ctx = make_context()
        with patch("bot.help_command", new_callable=AsyncMock) as mock_help:
            await self.bot_module.handle_message(update, ctx)
            mock_help.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_de_help_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Hilfe")
        ctx = make_context()
        with patch("bot.help_command", new_callable=AsyncMock) as mock_help:
            await self.bot_module.handle_message(update, ctx)
            mock_help.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_uk_help_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Допомога")
        ctx = make_context()
        with patch("bot.help_command", new_callable=AsyncMock) as mock_help:
            await self.bot_module.handle_message(update, ctx)
            mock_help.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_pl_help_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Pomoc")
        ctx = make_context()
        with patch("bot.help_command", new_callable=AsyncMock) as mock_help:
            await self.bot_module.handle_message(update, ctx)
            mock_help.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_ru_lang_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Мой язык")
        ctx = make_context()
        with patch("bot.lang_command", new_callable=AsyncMock) as mock_lang:
            await self.bot_module.handle_message(update, ctx)
            mock_lang.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_en_lang_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="My language")
        ctx = make_context()
        with patch("bot.lang_command", new_callable=AsyncMock) as mock_lang:
            await self.bot_module.handle_message(update, ctx)
            mock_lang.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_de_lang_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Sprache")
        ctx = make_context()
        with patch("bot.lang_command", new_callable=AsyncMock) as mock_lang:
            await self.bot_module.handle_message(update, ctx)
            mock_lang.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_uk_lang_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Мова")
        ctx = make_context()
        with patch("bot.lang_command", new_callable=AsyncMock) as mock_lang:
            await self.bot_module.handle_message(update, ctx)
            mock_lang.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_pl_lang_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Język")
        ctx = make_context()
        with patch("bot.lang_command", new_callable=AsyncMock) as mock_lang:
            await self.bot_module.handle_message(update, ctx)
            mock_lang.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_ru_balance_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Баланс")
        ctx = make_context()
        with patch("bot.balance_command", new_callable=AsyncMock) as mock_bal:
            await self.bot_module.handle_message(update, ctx)
            mock_bal.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_en_balance_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Balance")
        ctx = make_context()
        with patch("bot.balance_command", new_callable=AsyncMock) as mock_bal:
            await self.bot_module.handle_message(update, ctx)
            mock_bal.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_de_balance_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Guthaben")
        ctx = make_context()
        with patch("bot.balance_command", new_callable=AsyncMock) as mock_bal:
            await self.bot_module.handle_message(update, ctx)
            mock_bal.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_pl_balance_button(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="Saldo")
        ctx = make_context()
        with patch("bot.balance_command", new_callable=AsyncMock) as mock_bal:
            await self.bot_module.handle_message(update, ctx)
            mock_bal.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_pdf_button_routes(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="PDF")
        ctx = make_context()
        with patch("bot.pdf_command", new_callable=AsyncMock) as mock_pdf:
            await self.bot_module.handle_message(update, ctx)
            mock_pdf.assert_called_once()

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.update_last_activity")
    async def test_vip_button_routes(self, mock_activity, mock_load, mock_save):
        mock_load.return_value = {}
        update = make_update(text="VIP")
        ctx = make_context()
        with patch("bot.vip_command", new_callable=AsyncMock) as mock_vip:
            await self.bot_module.handle_message(update, ctx)
            mock_vip.assert_called_once()


# ── lang_command text ──────────────────────────────────────────────

class TestLangCommand(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    async def test_lang_command_shows_keyboard_with_all_languages(self):
        update = make_update(user_id=123)
        ctx = make_context()
        await self.bot_module.lang_command(update, ctx)
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        keyboard = call_args[1]["reply_markup"]
        buttons = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
        self.assertIn("lang_ru", buttons)
        self.assertIn("lang_uk", buttons)
        self.assertIn("lang_en", buttons)
        self.assertIn("lang_de", buttons)
        self.assertIn("lang_pl", buttons)

    async def _check_lang_text(self, lang_code, expected_text):
        update = make_update(user_id=123)
        ctx = make_context()
        with patch("utils.get_user", return_value={"lang": lang_code}):
            await self.bot_module.lang_command(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        self.assertIn(expected_text, text)

    async def test_lang_command_ru_text(self):
        await self._check_lang_text("ru", "Выберите язык")

    async def test_lang_command_en_text(self):
        await self._check_lang_text("en", "Choose language")

    async def test_lang_command_de_text(self):
        await self._check_lang_text("de", "Sprache wählen")

    async def test_lang_command_uk_text(self):
        await self._check_lang_text("uk", "Оберіть мову")

    async def test_lang_command_pl_text(self):
        await self._check_lang_text("pl", "Wybierz język")


# ── start command ──────────────────────────────────────────────────

class TestStartCommand(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("storage.load_data")
    async def test_start_creates_new_user(self, mock_sb_load, mock_load, mock_save):
        mock_load.return_value = {}
        mock_sb_load.return_value = {}
        update = make_update(user_id=456)
        ctx = make_context()
        await self.bot_module.start(update, ctx)
        saved = mock_save.call_args[0][0]
        self.assertIn("456", saved)
        user = saved["456"]
        self.assertEqual(user["free_used"], 0)
        self.assertEqual(user["balance"], 0)
        self.assertTrue(user["ref_code"].startswith("ref_"))

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("storage.load_data")
    async def test_start_existing_user_not_overwritten(self, mock_sb_load, mock_load, mock_save):
        mock_load.return_value = {"123": {"lang": "de", "balance": 5, "ref_code": "ref_old"}}
        mock_sb_load.return_value = {"123": {"lang": "de", "balance": 5, "ref_code": "ref_old"}}
        update = make_update(user_id=123)
        ctx = make_context()
        await self.bot_module.start(update, ctx)
        # start() only saves for new users or when ref_code is missing
        # for existing user with ref_code, it still calls save_data to update activity
        if mock_save.called:
            saved = mock_save.call_args[0][0]
            self.assertEqual(saved["123"]["lang"], "de")
            self.assertEqual(saved["123"]["balance"], 5)


# ── All callback_data values match known branches ──────────────────

class TestCallbackDataCoverage(unittest.TestCase):
    def test_all_inline_button_callbacks_are_handled(self):
        """Every callback_data from keyboards should match a registered CallbackQueryHandler pattern."""
        from services.keyboards import get_analysis_inline_buttons
        inline_kb = get_analysis_inline_buttons()
        all_callbacks = set()
        for row in inline_kb.inline_keyboard:
            for btn in row:
                all_callbacks.add(btn.callback_data)

        lang_callbacks = {f"lang_{lang}" for lang in ["ru", "uk", "en", "de", "pl"]}
        all_callbacks.update(lang_callbacks)

        known_prefixes = {
            "new", "analyze_ad", "analyze_rss", "skip_ad", "copy",
            "share", "pdf", "show_pay_", "filter", "fav_save", "fav_del",
            "track", "gen_letter", "copy_letter", "pdf_letter",
        }
        known_starts = set()
        for prefix in known_prefixes:
            known_starts.add(prefix)
        known_starts.update(lang_callbacks)

        for cb in all_callbacks:
            prefix = cb.split(":")[0] if ":" in cb else cb
            found = prefix in known_starts
            self.assertTrue(
                found,
                f"callback_data '{cb}' has no registered handler"
            )


# ── storage schema round-trip ───────────────────────────────────────

class TestStorageSchemaRoundTrip(unittest.TestCase):
    """
    Регрессия: last_reminder/last_limit_reminder существовали в коде
    scheduler.py (читались и писались в user dict), но отсутствовали в
    _user_to_row/_row_to_user -- в Supabase-режиме эти поля полностью
    терялись при каждом save_data()/load_data(), из-за чего анти-спам
    защита от повторной отправки одного и того же напоминания никогда не
    переживала следующий запуск планировщика.

    Этот тест не проверяет конкретные поля по имени (чтобы не плодить
    список вручную при каждом новом поле) -- вместо этого проверяет
    инвариант: всё, что кладёт в user dict _row_to_user(_user_to_row(...)),
    должно совпадать с тем, что было передано, для полей, которые
    scheduler.py/bot.py реально читают и пишут.
    """

    def test_last_reminder_fields_survive_round_trip(self):
        from storage import _user_to_row, _row_to_user
        user = {
            "balance": 5,
            "last_paid_at": 1000.0,
            "last_activity": 2000.0,
            "last_reminder": 3000.5,
            "last_limit_reminder": 4000.5,
        }
        row = _user_to_row("123", user)
        restored = _row_to_user(row)
        self.assertEqual(restored["last_reminder"], 3000.5)
        self.assertEqual(restored["last_limit_reminder"], 4000.5)

    def test_last_reminder_fields_default_to_zero(self):
        from storage import _user_to_row, _row_to_user
        user = {"balance": 5}
        row = _user_to_row("123", user)
        restored = _row_to_user(row)
        self.assertEqual(restored.get("last_reminder", 0), 0)
        self.assertEqual(restored.get("last_limit_reminder", 0), 0)


# ── pay_stars_* invoice commands ────────────────────────────────────

class TestPayStarsInvoiceCommands(unittest.IsolatedAsyncioTestCase):
    """
    Regression: pay_stars_pdf was the only one of the five pay_stars_*
    invoice commands (3, 9, 19, pdf, vip) missing a try/except around
    reply_invoice() -- if Telegram's Payments API failed for any reason
    (network blip, transient error), this one command would raise an
    unhandled exception instead of gracefully showing "Не удалось создать
    счёт." like its four siblings.
    """

    async def test_pay_stars_pdf_handles_invoice_failure_gracefully(self):
        import handlers.payments as payments
        update = make_update()
        update.message.reply_invoice = AsyncMock(side_effect=Exception("Telegram API error"))
        ctx = make_context()
        await payments.pay_stars_pdf(update, ctx)
        update.message.reply_text.assert_called_once_with(
            "Не удалось создать счёт.", reply_markup=ANY
        )

    async def test_pay_stars_pdf_success_path_unaffected(self):
        import handlers.payments as payments
        update = make_update()
        update.message.reply_invoice = AsyncMock()
        ctx = make_context()
        await payments.pay_stars_pdf(update, ctx)
        update.message.reply_invoice.assert_called_once()
        update.message.reply_text.assert_not_called()


# ── /health endpoint ─────────────────────────────────────────────────

class TestHealthChecks(unittest.IsolatedAsyncioTestCase):
    """
    Regression coverage for run_health_checks -- the / healthCheckPath used
    by Render is a static page that always returns 200 regardless of actual
    bot health, so this is the only automated signal for "the bot can
    actually do its job" (Supabase reachable, webhook delivering, scheduler
    registered). These tests lock in the pass/fail logic for each of the
    three checks and the overall status combination.
    """

    async def test_all_healthy(self):
        import bot as bot_module
        application = MagicMock()
        fake_info = MagicMock()
        fake_info.last_error_message = None
        fake_info.url = "https://example.onrender.com/123:ABC"
        fake_info.pending_update_count = 0
        fake_info.last_error_date = None
        application.bot.get_webhook_info = AsyncMock(return_value=fake_info)
        application.job_queue.jobs.return_value = (MagicMock(),) * 9

        with patch("storage.get_user", return_value={}):
            ok, checks = await bot_module.run_health_checks(
                application, "https://example.onrender.com", "123:ABC"
            )

        self.assertTrue(ok)
        self.assertTrue(checks["storage"]["ok"])
        self.assertTrue(checks["webhook"]["ok"])
        self.assertTrue(checks["scheduler"]["ok"])
        self.assertEqual(checks["scheduler"]["job_count"], 9)

    async def test_webhook_delivery_failure_reported(self):
        """
        The exact scenario diagnosed in the 'buttons don't respond, zero
        log lines' investigation: Telegram has a last_error_message and a
        growing pending_update_count. The other two checks staying healthy
        must not mask this -- overall_ok must be False.
        """
        import bot as bot_module
        application = MagicMock()
        fake_info = MagicMock()
        fake_info.last_error_message = "Wrong response from the webhook: 502 Bad Gateway"
        fake_info.url = "https://example.onrender.com/123:ABC"
        fake_info.pending_update_count = 47
        fake_info.last_error_date = None
        application.bot.get_webhook_info = AsyncMock(return_value=fake_info)
        application.job_queue.jobs.return_value = (MagicMock(),) * 9

        with patch("storage.get_user", return_value={}):
            ok, checks = await bot_module.run_health_checks(
                application, "https://example.onrender.com", "123:ABC"
            )

        self.assertFalse(ok)
        self.assertFalse(checks["webhook"]["ok"])
        self.assertEqual(checks["webhook"]["pending_update_count"], 47)
        self.assertIn("502", checks["webhook"]["last_error_message"])
        # The other checks being fine shouldn't be hidden either -- callers
        # reading the response should see exactly which check(s) failed.
        self.assertTrue(checks["storage"]["ok"])
        self.assertTrue(checks["scheduler"]["ok"])

    async def test_webhook_url_mismatch_flagged_even_without_error(self):
        """Telegram reports no delivery error, but the registered URL doesn't
        match what this deploy expects (e.g. stale webhook from a previous
        Render service URL) -- must still fail the check."""
        import bot as bot_module
        application = MagicMock()
        fake_info = MagicMock()
        fake_info.last_error_message = None
        fake_info.url = "https://old-service-name.onrender.com/123:ABC"
        fake_info.pending_update_count = 0
        fake_info.last_error_date = None
        application.bot.get_webhook_info = AsyncMock(return_value=fake_info)
        application.job_queue.jobs.return_value = (MagicMock(),)

        with patch("storage.get_user", return_value={}):
            ok, checks = await bot_module.run_health_checks(
                application, "https://example.onrender.com", "123:ABC"
            )

        self.assertFalse(ok)
        self.assertFalse(checks["webhook"]["url_matches_expected"])

    async def test_storage_failure_reported(self):
        import bot as bot_module
        application = MagicMock()
        fake_info = MagicMock()
        fake_info.last_error_message = None
        fake_info.url = "https://example.onrender.com/123:ABC"
        fake_info.pending_update_count = 0
        fake_info.last_error_date = None
        application.bot.get_webhook_info = AsyncMock(return_value=fake_info)
        application.job_queue.jobs.return_value = (MagicMock(),)

        with patch("storage.get_user", side_effect=Exception("Connection refused")):
            ok, checks = await bot_module.run_health_checks(
                application, "https://example.onrender.com", "123:ABC"
            )

        self.assertFalse(ok)
        self.assertFalse(checks["storage"]["ok"])
        self.assertIn("Connection refused", checks["storage"]["error"])

    async def test_scheduler_not_registered_reported(self):
        """job_queue.jobs() returning empty means register_jobs() either
        never ran or raised before registering anything -- e.g. the
        UnboundLocalError-style bugs found earlier in this project could
        have silently prevented jobs from being scheduled."""
        import bot as bot_module
        application = MagicMock()
        fake_info = MagicMock()
        fake_info.last_error_message = None
        fake_info.url = "https://example.onrender.com/123:ABC"
        fake_info.pending_update_count = 0
        fake_info.last_error_date = None
        application.bot.get_webhook_info = AsyncMock(return_value=fake_info)
        application.job_queue.jobs.return_value = ()

        with patch("storage.get_user", return_value={}):
            ok, checks = await bot_module.run_health_checks(
                application, "https://example.onrender.com", "123:ABC"
            )

        self.assertFalse(ok)
        self.assertFalse(checks["scheduler"]["ok"])
        self.assertEqual(checks["scheduler"]["job_count"], 0)


# ── channel_poster: blocking calls ──────────────────────────────────

class TestChannelPosterBlocking(unittest.IsolatedAsyncioTestCase):
    """
    Regression: post_to_channel and send_holy_grail_alert called
    create_url_token (a synchronous Supabase select+insert) directly inside
    async functions that run on the bot's main event loop via the
    scheduler's hourly job_queue task -- blocking the whole bot for every
    live user for the duration of the Supabase round-trip, once per
    listing posted (up to 5 per run).
    """

    async def test_post_to_channel_does_not_block_event_loop(self):
        import channel_poster
        channel_poster.bot = MagicMock()
        channel_poster.bot.send_message = AsyncMock()

        tick_count = {"n": 0}

        def slow_create_url_token(url):
            time.sleep(0.3)
            return "tok123"

        async def ticker():
            for _ in range(5):
                tick_count["n"] += 1
                await asyncio.sleep(0.05)

        with patch("channel_poster.create_url_token", side_effect=slow_create_url_token):
            await asyncio.gather(
                channel_poster.post_to_channel(12345, "test text", "testbot", "https://example.com/x"),
                ticker(),
            )

        self.assertEqual(tick_count["n"], 5)
        channel_poster.bot.send_message.assert_called_once()

    async def test_send_holy_grail_alert_does_not_block_event_loop(self):
        import channel_poster
        channel_poster.bot = MagicMock()
        channel_poster.bot.send_message = AsyncMock()
        channel_poster.POST_TARGET = -100123456
        channel_poster.CITY_CHANNELS = {}

        tick_count = {"n": 0}

        def slow_create_url_token(url):
            time.sleep(0.3)
            return "tok123"

        async def ticker():
            for _ in range(5):
                tick_count["n"] += 1
                await asyncio.sleep(0.05)

        entry = {"url": "https://example.com/x", "city": "berlin", "price": 1000, "score": 9, "grail_reason": "great deal"}
        with patch("channel_poster.create_url_token", side_effect=slow_create_url_token):
            with patch("channel_poster.format_holy_grail_alert", return_value="alert text"):
                await asyncio.gather(
                    channel_poster.send_holy_grail_alert(entry, "testbot"),
                    ticker(),
                )

        self.assertEqual(tick_count["n"], 5)
        channel_poster.bot.send_message.assert_called_once()


# ── metrics: event logging + daily summary ──────────────────────────

class TestMetrics(unittest.TestCase):
    """
    metrics.py is a lightweight append-only JSONL event log feeding the
    daily admin report. Known limitation documented in the module itself:
    the file lives on Render's ephemeral disk, so events are lost across a
    process restart -- these tests cover the aggregation logic itself,
    not that limitation (which isn't something code can fix).
    """

    def setUp(self):
        import metrics
        self.metrics = metrics
        self._orig_file = metrics.METRICS_FILE
        self.tmp_file = "/tmp/test_metrics_events_unittest.jsonl"
        metrics.METRICS_FILE = self.tmp_file
        if os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)

    def tearDown(self):
        self.metrics.METRICS_FILE = self._orig_file
        if os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)

    def test_empty_file_returns_zeros(self):
        summary = self.metrics.get_daily_summary()
        self.assertEqual(summary["new_users"], 0)
        self.assertEqual(summary["alerts_fired"], [])

    def test_logs_and_aggregates_events(self):
        self.metrics.log_event("new_user", user_id="1")
        self.metrics.log_event("new_user", user_id="2")
        self.metrics.log_event("analysis_completed", user_id="1")
        self.metrics.log_event("analysis_failed", user_id="2", error="timeout")
        self.metrics.log_event("payment_completed", user_id="1", plan="pay_stars_3")

        summary = self.metrics.get_daily_summary()
        self.assertEqual(summary["new_users"], 2)
        self.assertEqual(summary["analyses_completed"], 1)
        self.assertEqual(summary["analyses_failed"], 1)
        self.assertEqual(summary["payments_completed"], 1)

    def test_alerts_fired_deduplicated_by_key(self):
        self.metrics.log_event("alert_fired", alert_key="pgrst204")
        self.metrics.log_event("alert_fired", alert_key="pgrst204")
        self.metrics.log_event("alert_fired", alert_key="health_check_failed")

        summary = self.metrics.get_daily_summary()
        self.assertEqual(summary["alerts_fired"], ["health_check_failed", "pgrst204"])

    def test_events_older_than_window_excluded(self):
        old_ts = time.time() - 30 * 3600
        with open(self.tmp_file, "w") as f:
            f.write(json.dumps({"ts": old_ts, "type": "new_user"}) + "\n")
        self.metrics.log_event("new_user")

        summary = self.metrics.get_daily_summary(hours=24)
        self.assertEqual(summary["new_users"], 1)

    def test_corrupted_line_does_not_crash(self):
        with open(self.tmp_file, "w") as f:
            f.write("not valid json at all\n")
        self.metrics.log_event("new_user")

        summary = self.metrics.get_daily_summary()
        self.assertEqual(summary["new_users"], 1)

    def test_log_event_failure_does_not_raise(self):
        """log_event must never crash the caller even if writing fails
        (e.g. disk full, permission error) -- same principle as
        alert_admin's own safe-failure guarantee."""
        with patch("builtins.open", side_effect=OSError("disk full")):
            self.metrics.log_event("new_user")  # should not raise


# ── scheduler: daily admin report ───────────────────────────────────

class TestDailyAdminReport(unittest.IsolatedAsyncioTestCase):

    async def test_sends_formatted_report_with_metrics_and_health(self):
        import scheduler as scheduler_module
        context = MagicMock()
        application = MagicMock()
        application.bot.send_message = AsyncMock()
        context.application = application

        fake_summary = {
            "new_users": 5, "analyses_completed": 20, "analyses_failed": 2,
            "photos_analyzed": 3, "pdfs_generated": 1, "letters_generated": 2,
            "payments_completed": 1, "alerts_fired": ["pgrst204"],
        }

        async def fake_health_check(*a, **k):
            return True, {"storage": {"ok": True}, "webhook": {"ok": True}, "scheduler": {"ok": True}}

        with patch("os.getenv", side_effect=lambda k, d=None: {
            "ADMIN_ID": "999", "WEBHOOK_URL": "https://example.onrender.com", "TELEGRAM_TOKEN": "123:ABC"
        }.get(k, d)):
            with patch("metrics.get_daily_summary", return_value=fake_summary):
                with patch("health.run_health_checks", side_effect=fake_health_check):
                    await scheduler_module.send_daily_admin_report(context)

        application.bot.send_message.assert_called_once()
        call_kwargs = application.bot.send_message.call_args[1]
        self.assertEqual(call_kwargs["chat_id"], 999)
        text = call_kwargs["text"]
        self.assertIn("5", text)
        self.assertIn("pgrst204", text)
        self.assertIn("всё в порядке", text)

    async def test_reports_unhealthy_state(self):
        import scheduler as scheduler_module
        context = MagicMock()
        application = MagicMock()
        application.bot.send_message = AsyncMock()
        context.application = application

        fake_summary = {
            "new_users": 0, "analyses_completed": 0, "analyses_failed": 0,
            "photos_analyzed": 0, "pdfs_generated": 0, "letters_generated": 0,
            "payments_completed": 0, "alerts_fired": [],
        }

        async def fake_health_check(*a, **k):
            return False, {"storage": {"ok": True}, "webhook": {"ok": False}, "scheduler": {"ok": True}}

        with patch("os.getenv", side_effect=lambda k, d=None: {
            "ADMIN_ID": "999", "WEBHOOK_URL": "https://example.onrender.com", "TELEGRAM_TOKEN": "123:ABC"
        }.get(k, d)):
            with patch("metrics.get_daily_summary", return_value=fake_summary):
                with patch("health.run_health_checks", side_effect=fake_health_check):
                    await scheduler_module.send_daily_admin_report(context)

        text = application.bot.send_message.call_args[1]["text"]
        self.assertIn("webhook", text)

    async def test_no_admin_id_does_not_send(self):
        import scheduler as scheduler_module
        context = MagicMock()
        context.application = MagicMock()
        context.application.bot.send_message = AsyncMock()

        with patch("os.getenv", side_effect=lambda k, d=None: d):
            await scheduler_module.send_daily_admin_report(context)

        context.application.bot.send_message.assert_not_called()

    async def test_no_application_does_not_crash(self):
        import scheduler as scheduler_module
        await scheduler_module.send_daily_admin_report(None)
        context = MagicMock()
        context.application = None
        await scheduler_module.send_daily_admin_report(context)  # should not raise


if __name__ == "__main__":
    unittest.main()
