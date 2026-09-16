"""
tests/test_discord_kit.py — Unit tests for MAX AI Discord Kit helpers.
"""

import sys
import unittest
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from max_ai.discord.bot import split_discord_message, create_max_bot, MaxDiscordBot  # type: ignore[import-not-found]


class TestDiscordKit(unittest.TestCase):
    def test_split_discord_message_short(self):
        msg = "Short message under limit"
        chunks = split_discord_message(msg, limit=100)
        self.assertEqual(chunks, [msg])

    def test_split_discord_message_multiline(self):
        lines = ["Line " + str(i) for i in range(50)]
        long_msg = "\n".join(lines)
        chunks = split_discord_message(long_msg, limit=100)
        self.assertTrue(len(chunks) > 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 100)

    def test_split_discord_message_very_long_line(self):
        long_line = "A" * 250
        chunks = split_discord_message(long_line, limit=100)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 100)
        self.assertEqual(len(chunks[1]), 100)
        self.assertEqual(len(chunks[2]), 50)

    def test_create_max_bot_factory(self):
        bot = create_max_bot(
            discord_token="dummy-token-12345",
            max_api_key="test-api-key",
            model="deepseek-v4.1-flash",
            command_prefix="!ai ",
        )
        self.assertIsInstance(bot, MaxDiscordBot)
        self.assertEqual(bot.discord_token, "dummy-token-12345")
        self.assertEqual(bot.command_prefix, "!ai ")
        self.assertEqual(bot.agent.model, "deepseek-v4.1-flash")


if __name__ == "__main__":
    unittest.main()
