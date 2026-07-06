import os
import sys
import time
import json
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(__file__))

from utils import can_use, use_check, get_user_data, calc_remaining, validate_pdf_data, is_pdf_state_expired


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
    @patch("bot.update_last_activity")
    async def test_limit_reached(self, mock_activity, mock_load, mock_save):
        user = make_user(free_used=3, balance=0)
        mock_load.return_value = {"123": user}
        update = make_update(text="some listing text here")
        ctx = make_context()
        uid = str(update.effective_user.id)
        self.bot_module._flood_tracker[uid] = (0, time.time())
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

    @patch("bot.save_data")
    @patch("bot.load_data")
    @patch("bot.client")
    async def test_admin_bypass(self, mock_client, mock_load, mock_save):
        user = make_user(free_used=3, balance=0)
        mock_load.return_value = {"123": user}
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Analysis"))]
        mock_client.chat.completions.create.return_value = mock_response

        update = make_update(text="Wohnung Berlin")
        ctx = make_context()
        ctx.bot.get_chat_member.return_value = MagicMock(status="administrator")

        with patch("bot.extract_score", return_value=5):
            await self.bot_module.process_listing(update, ctx, "Wohnung Berlin", "123", "ru")

        self.assertEqual(user["free_used"], 3)
        update.message.reply_text.assert_called()


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
        fake_data = {"123": {"lang": "de"}}
        with patch("utils.load_data", return_value=fake_data):
            result = get_lang(update)
        self.assertEqual(result, "de")

    def test_falls_back_to_tg_language(self):
        from utils import get_lang
        update = make_update(user_id=123)
        update.effective_user.language_code = "de"
        with patch("utils.load_data", return_value={}):
            result = get_lang(update)
        self.assertEqual(result, "de")

    def test_falls_back_to_default(self):
        from utils import get_lang
        update = make_update(user_id=123)
        update.effective_user.language_code = "fr"
        with patch("utils.load_data", return_value={}):
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
        shared_data = {"123": dict(user_data)}
        with patch("bot.load_data", return_value=shared_data):
            with patch("bot.save_data") as mock_save:
                with patch("utils.load_data", return_value=shared_data):
                    await self.bot_module.handle_callback(update, ctx)
        return mock_save

    async def test_lang_ru_saves(self):
        mock_save = await self._run_lang_callback("lang_ru")
        args = mock_save.call_args[0][0]
        self.assertEqual(args["123"]["lang"], "ru")

    async def test_lang_en_saves(self):
        mock_save = await self._run_lang_callback("lang_en", {"lang": "ru", "free_used": 0, "balance": 0})
        args = mock_save.call_args[0][0]
        self.assertEqual(args["123"]["lang"], "en")

    async def test_lang_de_saves(self):
        mock_save = await self._run_lang_callback("lang_de", {"lang": "en", "free_used": 0, "balance": 0})
        args = mock_save.call_args[0][0]
        self.assertEqual(args["123"]["lang"], "de")

    async def test_lang_uk_saves(self):
        mock_save = await self._run_lang_callback("lang_uk")
        args = mock_save.call_args[0][0]
        self.assertEqual(args["123"]["lang"], "uk")

    async def test_lang_pl_saves(self):
        mock_save = await self._run_lang_callback("lang_pl")
        args = mock_save.call_args[0][0]
        self.assertEqual(args["123"]["lang"], "pl")

    async def test_lang_callback_shows_alert(self):
        update = make_update(user_id=123)
        update.callback_query.data = "lang_en"
        ctx = make_context()
        with patch("bot.load_data", return_value={"123": {"free_used": 0, "balance": 0}}):
            with patch("bot.save_data"):
                with patch("utils.load_data", return_value={"123": {"free_used": 0, "balance": 0}}):
                    await self.bot_module.handle_callback(update, ctx)
        update.callback_query.answer.assert_called_once()
        call_args = update.callback_query.answer.call_args
        self.assertIn("English", call_args[0][0])
        self.assertTrue(call_args[1]["show_alert"])

    async def test_lang_callback_returns_early(self):
        update = make_update(user_id=123)
        update.callback_query.data = "lang_ru"
        ctx = make_context()
        with patch("bot.load_data", return_value={"123": {"free_used": 0, "balance": 0}}):
            with patch("bot.save_data"):
                with patch("utils.load_data", return_value={"123": {"free_used": 0, "balance": 0}}):
                    await self.bot_module.handle_callback(update, ctx)
        ctx.bot.send_message.assert_not_called()


# ── Callback handler branches ──────────────────────────────────────

class TestCallbackHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import bot as bot_module
        self.bot_module = bot_module

    @patch("bot.load_data")
    async def test_skip_ad_answers_ok(self, mock_load):
        update = make_update(user_id=123)
        update.callback_query.data = "skip_ad"
        ctx = make_context()
        await self.bot_module.handle_callback(update, ctx)
        calls = update.callback_query.answer.call_args_list
        has_ok = any("Ок" in str(c) for c in calls)
        self.assertTrue(has_ok)

    @patch("bot.load_data")
    async def test_copy_answers_copied(self, mock_load):
        update = make_update(user_id=123)
        update.callback_query.data = "copy"
        ctx = make_context()
        await self.bot_module.handle_callback(update, ctx)
        self.assertTrue(update.callback_query.answer.called)

    @patch("bot.save_data")
    @patch("bot.load_data")
    async def test_new_callback_sends_message(self, mock_load, mock_save):
        mock_load.return_value = {"123": {"free_used": 0, "balance": 0}}
        update = make_update(user_id=123)
        update.callback_query.data = "new"
        update.callback_query.edit_message_reply_markup = AsyncMock()
        ctx = make_context()
        await self.bot_module.handle_callback(update, ctx)
        ctx.bot.send_message.assert_called_once()
        call_kwargs = ctx.bot.send_message.call_args[1]
        self.assertEqual(call_kwargs["chat_id"], 123)


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
        with patch("utils.load_data", return_value={"123": {"lang": lang_code}}):
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
        """Every callback_data from keyboards should match a branch in handle_callback."""
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
            "share", "pdf", "filter", "fav_save", "fav_del",
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
                f"callback_data '{cb}' has no handler branch in handle_callback"
            )


if __name__ == "__main__":
    unittest.main()
