from unittest.mock import patch
from unittest import TestCase
from PookieBot import run_discord_client


class TestDiscord(TestCase):
    @patch("random.shuffle")
    def test_discord_client(self, shuffle):
        run_discord_client()
