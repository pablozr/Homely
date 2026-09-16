import unittest

from core.config.config import Settings


class SettingsTests(unittest.TestCase):
    def test_parses_local_email_and_push_settings(self):
        settings = Settings(
            SMTP_HOST="mailpit",
            SMTP_PORT="1025",
            SMTP_FROM_EMAIL="no-reply@example.com",
            PUSH_ENABLED="false",
        )

        self.assertEqual(settings.SMTP_HOST, "mailpit")
        self.assertEqual(settings.SMTP_PORT, 1025)
        self.assertEqual(settings.SMTP_FROM_EMAIL, "no-reply@example.com")
        self.assertFalse(settings.PUSH_ENABLED)
