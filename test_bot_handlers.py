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

    @patch("bot.save_user")
    @patch("bot.get_user")
    async def test_pay_3(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update()
        update.message.successful_payment = MagicMock(invoice_payload="pay_stars_3")
        ctx = make_context()
        await self.bot_module.successful_payment(update, ctx)
        self.assertEqual(user["balance"], 3)
        self.assertIn("last_paid_at", user)

    @patch("bot.save_user")
    @patch("bot.get_user")
    async def test_pay_9(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update()
        update.message.successful_payment = MagicMock(invoice_payload="pay_stars_9")
        ctx = make_context()
        await self.bot_module.successful_payment(update, ctx)
        self.assertEqual(user["balance"], 10)

    @patch("bot.save_user")
    @patch("bot.get_user")
    async def test_pay_19_unlimited(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update()
        update.message.successful_payment = MagicMock(invoice_payload="pay_stars_19")
        ctx = make_context()
        await self.bot_module.successful_payment(update, ctx)
        self.assertEqual(user["balance"], -1)

    @patch("bot.save_user")
    @patch("bot.get_user")
    async def test_pay_pdf(self, mock_get, mock_save):
        user = make_user()
        mock_get.return_value = user
        update = make_update()
        update.message.successful_payment = MagicMock(invoice_payload="pay_stars_pdf")
        ctx = make_context()
        await self.bot_module.successful_payment(update, ctx)
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

    @patch("bot.save_data")
    @patch("bot.load_data")
    async def test_pay_done_3_admin_works(self, mock_load, mock_save):
        user = make_user()
        mock_load.return_value = {"111": user}
        update = make_update(user_id=111)
        ctx = make_context()
        with patch.dict(os.environ, {"ADMIN_ID": "111"}):
            await self.bot_module.pay_done_3(update, ctx)
        self.assertEqual(user["balance"], 3)

    @patch("bot.save_data")
    @patch("bot.load_data")
    async def test_pay_done_vip_non_admin_silently_ignored(self, mock_load, mock_save):
        user = make_user()
        mock_load.return_value = {"123": user}
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


if __name__ == "__main__":
    unittest.main()
