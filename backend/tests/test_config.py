import unittest

from pydantic import ValidationError

from core.config.config import DEFAULT_INVITE_TOKEN_SECRET, Settings


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

    def test_parses_invite_settings(self):
        settings = Settings(
            INVITE_EXPIRE_DAYS="7",
            INVITE_DEEP_LINK_BASE="homely://invite",
            INVITE_ACCEPT_USER_RATE_LIMIT="10",
            INVITE_ACCEPT_IP_RATE_WINDOW_MINUTES="15",
        )

        self.assertEqual(settings.INVITE_EXPIRE_DAYS, 7)
        self.assertEqual(settings.INVITE_DEEP_LINK_BASE, "homely://invite")
        self.assertEqual(settings.INVITE_ACCEPT_USER_RATE_LIMIT, 10)
        self.assertEqual(settings.INVITE_ACCEPT_IP_RATE_WINDOW_MINUTES, 15)

    def test_rejects_the_development_invite_secret_outside_development(self):
        with self.assertRaises(ValidationError):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="s" * 32,
                INVITE_TOKEN_SECRET=DEFAULT_INVITE_TOKEN_SECRET,
            )

    def test_rejects_a_short_invite_secret_outside_development(self):
        with self.assertRaises(ValidationError):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="s" * 32,
                INVITE_TOKEN_SECRET="short",
            )

    def test_accepts_a_strong_invite_secret_outside_development(self):
        settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="s" * 32,
            INVITE_TOKEN_SECRET="i" * 32,
        )

        self.assertEqual(settings.INVITE_TOKEN_SECRET, "i" * 32)
