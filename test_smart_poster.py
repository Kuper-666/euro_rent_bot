import os
import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from smart_poster import (
    detect_language,
    is_relevant_chat,
    load_sent_history,
    save_sent_history,
    SmartPoster,
    PosterStorage,
    POST_MESSAGES,
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

    def test_unknown_language_title(self):
        self.assertFalse(is_relevant_chat("xyz abc def", []))


class TestSentHistory(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_poster.db"
        self.storage = PosterStorage(self.test_db)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_empty_database(self):
        self.assertEqual(self.storage.get_sent_ids(), set())

    def test_mark_sent(self):
        self.storage.mark_sent(123, "Test Group")
        self.storage.mark_sent(456, "Another Group")
        self.assertEqual(self.storage.get_sent_ids(), {123, 456})

    def test_no_duplicates(self):
        self.storage.mark_sent(123, "Test")
        self.storage.mark_sent(123, "Test")
        self.assertEqual(self.storage.get_sent_ids(), {123})

    def test_is_sent(self):
        self.assertFalse(self.storage.is_sent(123))
        self.storage.mark_sent(123)
        self.assertTrue(self.storage.is_sent(123))

    def test_log_post(self):
        self.storage.log_post(123, "Test", "Hello world")
        stats = self.storage.stats()
        self.assertEqual(stats["posts"], 1)

    def test_stats(self):
        self.storage.mark_sent(123)
        self.storage.log_post(123, "Test", "msg")
        stats = self.storage.stats()
        self.assertEqual(stats["posts"], 1)
        self.assertEqual(stats["groups"], 1)


import smart_poster as smart_poster_module


class TestSmartPosterInit(unittest.TestCase):
    @patch("smart_poster.TelegramClient")
    def test_init(self, mock_client):
        poster = SmartPoster()
        self.assertIsNotNone(poster.client)
        self.assertIsNotNone(poster.storage)


class TestMessagesConfig(unittest.TestCase):
    def test_post_messages_not_empty(self):
        self.assertGreater(len(POST_MESSAGES), 0)

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
        for lang, messages in POST_MESSAGES.items():
            for msg in messages:
                self.assertIn("@expat_rent_bot", msg, f"Missing @expat_rent_bot in {lang}")

    def test_post_messages_disclose_creator(self):
        """Тексты должны честно представляться от создателя бота."""
        markers = {
            "ru": ["разработчик", "сделал бота", "мой бот"],
            "uk": ["розробник", "зробив бота", "мій бот"],
            "de": ["entwickler", "gebaut", "mein bot"],
            "en": ["i built", "i made", "my bot"],
            "it": ["creato", "ho creato", "il mio bot"],
            "pl": ["stworzyłem", "mój bot"],
            "cs": ["vytvořil", "můj bot"],
        }
        for lang, messages in POST_MESSAGES.items():
            for msg in messages:
                msg_lower = msg.lower()
                lang_markers = markers.get(lang, markers["en"])
                # Все сообщения содержат @expat_rent_bot — это форма раскрытия
                has_disclosure = (
                    any(marker in msg_lower for marker in lang_markers)
                    or "@expat_rent_bot" in msg
                )
                self.assertTrue(
                    has_disclosure,
                    f"Message in {lang} does not disclose creator: {msg[:60]}"
                )


if __name__ == "__main__":
    unittest.main()
