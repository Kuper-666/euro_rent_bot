import os
import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from smart_poster import (
    detect_language,
    is_relevant_chat,
    should_reply,
    load_sent_history,
    save_sent_history,
    SmartPoster,
    POST_MESSAGES,
    REPLY_MESSAGES,
    QUESTION_TRIGGERS,
    GROUP_KEYWORDS,
    STOP_WORDS,
    RENT_KEYWORDS,
    ALLOWED_LANGUAGES,
)


class TestDetectLanguage(unittest.TestCase):
    def test_russian(self):
        self.assertEqual(detect_language("аренда квартиры в берлине"), "ru")

    def test_german(self):
        self.assertEqual(detect_language("Wohnung mieten in München"), "de")

    def test_english(self):
        self.assertEqual(detect_language("apartment for rent in Berlin"), "en")

    def test_empty_string(self):
        self.assertEqual(detect_language(""), "unknown")

    def test_whitespace_only(self):
        self.assertEqual(detect_language("   "), "unknown")

    def test_none_like(self):
        self.assertEqual(detect_language(""), "unknown")


class TestIsRelevantChat(unittest.TestCase):
    def test_rental_group_de(self):
        msgs = [
            "Wohnung 3 Zimmer, 75m², 1200€ warm",
            "Kaltmiete 950€ + Nebenkosten 250€",
            "Keine Provision!",
        ]
        self.assertTrue(is_relevant_chat("WG Berlin Mitte", msgs))

    def test_rental_group_ru(self):
        msgs = [
            "Сдаю квартиру 2-комнатную, 50м²",
            "Аренда 800€ в месяц, залог",
        ]
        self.assertTrue(is_relevant_chat("Аренда жилья Berlin", msgs))

    def test_buy_sell_group_rejected(self):
        msgs = ["Kaufe Wohnung", "Verkaufe Auto"]
        self.assertFalse(is_relevant_chat("Kauf und Verkauf Berlin", msgs))

    def test_no_keyword_in_title_rejected(self):
        self.assertFalse(is_relevant_chat("Random Chat Berlin", []))

    def test_stop_word_in_title(self):
        self.assertFalse(is_relevant_chat("Wohnung kaufen Berlin", []))

    def test_no_rental_messages(self):
        msgs = ["Привет всем", "Как дела?", "Погода сегодня"]
        self.assertFalse(is_relevant_chat("Аренда Berlin", msgs))

    def test_few_rental_messages_rejected(self):
        msgs = [
            "Привет",
            "Квартира 2 комнаты",
            "Как дела?",
            "Погода",
        ]
        self.assertFalse(is_relevant_chat("Жильё Berlin", msgs))

    def test_empty_messages_with_keyword_title(self):
        self.assertTrue(is_relevant_chat("Аренда Berlin", []))

    def test_unknown_language_title(self):
        self.assertFalse(is_relevant_chat("xyz abc def", []))


class TestShouldReply(unittest.TestCase):
    def test_triggers_on_housing_question(self):
        self.assertTrue(should_reply("Как найти квартиру в Берлине?"))

    def test_triggers_on_nebenkosten(self):
        self.assertTrue(should_reply("А что такое Nebenkosten?"))

    def test_no_trigger_on_random(self):
        self.assertFalse(should_reply("Привет, как дела?"))

    def test_no_trigger_on_empty(self):
        self.assertFalse(should_reply(""))


class TestSentHistory(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_sent_history.txt"
        self._orig = smart_poster_module.SENT_HISTORY_FILE

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_load_nonexistent(self):
        import smart_poster as sp
        with patch.object(sp, "SENT_HISTORY_FILE", self.test_file):
            result = load_sent_history()
            self.assertEqual(result, set())

    def test_save_and_load(self):
        import smart_poster as sp
        with patch.object(sp, "SENT_HISTORY_FILE", self.test_file):
            history = set()
            save_sent_history(123, history)
            save_sent_history(456, history)
            loaded = load_sent_history()
            self.assertEqual(loaded, {123, 456})

    def test_no_duplicates(self):
        import smart_poster as sp
        with patch.object(sp, "SENT_HISTORY_FILE", self.test_file):
            history = set()
            save_sent_history(123, history)
            save_sent_history(123, history)
            loaded = load_sent_history()
            self.assertEqual(loaded, {123})


import smart_poster as smart_poster_module


class TestSmartPosterInit(unittest.TestCase):
    @patch("smart_poster.TelegramClient")
    def test_init(self, mock_client):
        poster = SmartPoster()
        self.assertIsNotNone(poster.client)
        self.assertIsInstance(poster.sent_history, set)
        self.assertEqual(poster.COOLDOWN_SECONDS, 300)

    @patch("smart_poster.TelegramClient")
    def test_can_reply_first_time(self, mock_client):
        poster = SmartPoster()
        self.assertTrue(poster._can_reply(123))

    @patch("smart_poster.TelegramClient")
    def test_cooldown_blocks_reply(self, mock_client):
        poster = SmartPoster()
        poster._mark_replied(123)
        self.assertFalse(poster._can_reply(123))

    @patch("smart_poster.TelegramClient")
    def test_cooldown_expires(self, mock_client):
        poster = SmartPoster()
        poster.COOLDOWN_SECONDS = 0
        poster._mark_replied(123)
        self.assertTrue(poster._can_reply(123))

    @patch("smart_poster.TelegramClient")
    def test_different_groups_independent(self, mock_client):
        poster = SmartPoster()
        poster._mark_replied(123)
        self.assertTrue(poster._can_reply(456))


class TestMessagesConfig(unittest.TestCase):
    def test_post_messages_not_empty(self):
        self.assertGreater(len(POST_MESSAGES), 0)

    def test_reply_messages_not_empty(self):
        self.assertGreater(len(REPLY_MESSAGES), 0)

    def test_question_triggers_not_empty(self):
        self.assertGreater(len(QUESTION_TRIGGERS), 0)

    def test_group_keywords_not_empty(self):
        self.assertGreater(len(GROUP_KEYWORDS), 0)

    def test_stop_words_not_empty(self):
        self.assertGreater(len(STOP_WORDS), 0)

    def test_rent_keywords_not_empty(self):
        self.assertGreater(len(RENT_KEYWORDS), 0)

    def test_allowed_languages_contains_ru_en_de(self):
        self.assertIn("ru", ALLOWED_LANGUAGES)
        self.assertIn("en", ALLOWED_LANGUAGES)
        self.assertIn("de", ALLOWED_LANGUAGES)

    def test_all_post_messages_mention_bot(self):
        for msg in POST_MESSAGES:
            self.assertIn("@EuroRentAIBot", msg)

    def test_most_reply_messages_mention_bot(self):
        mentioned = sum(1 for msg in REPLY_MESSAGES if "@EuroRentAIBot" in msg)
        self.assertGreater(mentioned, 0, "At least one reply message should mention the bot")


if __name__ == "__main__":
    unittest.main()
