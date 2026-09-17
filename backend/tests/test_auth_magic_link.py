import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from pydantic import ValidationError

from core.config.config import settings
from core.security.security import hash_magic_link_code, hash_refresh_token
from schemas.auth import (
    ExchangeRequestModel,
    MagicLinkRequestModel,
    RefreshTokenRequestModel,
)
from services.auth import auth_service


class Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class MagicLinkConnection:
    def __init__(self, fetchval=None, fetchrow=None):
        self.fetchval = AsyncMock(
            side_effect=fetchval if fetchval is not None else [0]
        )
        self.fetchrow = AsyncMock(
            side_effect=fetchrow if fetchrow is not None else [None]
        )
        self.execute = AsyncMock()

    def transaction(self):
        return Transaction()


class MagicLinkRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_persists_only_hash_and_sends_deep_link(self):
        connection = MagicLinkConnection(fetchval=[0, 0])
        sent = MagicMock()

        with (
            patch.object(auth_service, "create_magic_link_code", return_value="raw-code"),
            patch.object(auth_service, "send_magic_link_email", sent),
        ):
            result = await auth_service.request_magic_link(
                connection,
                MagicLinkRequestModel(email="  User@Example.COM  "),
                "203.0.113.7",
            )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["data"], {})

        insert_call = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO magic_link_codes" in call.args[0]
        )
        parameters = insert_call.args[1:]
        self.assertEqual(parameters[1], "user@example.com")
        self.assertEqual(parameters[2], hash_magic_link_code("raw-code"))
        self.assertEqual(parameters[3], "203.0.113.7")
        self.assertNotIn("raw-code", parameters)

        expires_at = parameters[4]
        remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()
        self.assertAlmostEqual(remaining, settings.MAGIC_LINK_EXPIRE_MINUTES * 60, delta=5)

        sent.assert_called_once()
        to_email, magic_link = sent.call_args.args
        self.assertEqual(to_email, "user@example.com")
        self.assertTrue(magic_link.startswith(settings.MAGIC_LINK_DEEP_LINK_BASE))
        self.assertIn("auth_code=raw-code", magic_link)

    async def test_invalidates_prior_active_codes_for_the_email(self):
        connection = MagicLinkConnection(fetchval=[0, 0])

        with patch.object(auth_service, "send_magic_link_email", MagicMock()):
            await auth_service.request_magic_link(
                connection,
                MagicLinkRequestModel(email="user@example.com"),
                "203.0.113.7",
            )

        invalidation = next(
            call
            for call in connection.execute.await_args_list
            if "UPDATE magic_link_codes" in call.args[0]
        )
        self.assertIn("used_at", invalidation.args[0])
        self.assertEqual(invalidation.args[1], "user@example.com")

        locks = [
            call
            for call in connection.execute.await_args_list
            if "pg_advisory_xact_lock" in call.args[0]
        ]
        self.assertEqual(len(locks), 3)

    async def test_rate_limits_requests_per_email(self):
        connection = MagicLinkConnection(fetchval=[settings.MAGIC_LINK_EMAIL_RATE_LIMIT, 0])
        sent = MagicMock()

        with patch.object(auth_service, "send_magic_link_email", sent):
            result = await auth_service.request_magic_link(
                connection,
                MagicLinkRequestModel(email="user@example.com"),
                "203.0.113.7",
            )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 429)
        sent.assert_not_called()
        self.assertFalse(
            any(
                "INSERT INTO magic_link_codes" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )

    async def test_rate_limits_requests_per_ip(self):
        connection = MagicLinkConnection(fetchval=[0, settings.MAGIC_LINK_IP_RATE_LIMIT])

        with patch.object(auth_service, "send_magic_link_email", MagicMock()):
            result = await auth_service.request_magic_link(
                connection,
                MagicLinkRequestModel(email="user@example.com"),
                "203.0.113.7",
            )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 429)

    async def test_does_not_query_account_existence(self):
        connection = MagicLinkConnection(fetchval=[0, 0])

        with patch.object(auth_service, "send_magic_link_email", MagicMock()):
            result = await auth_service.request_magic_link(
                connection,
                MagicLinkRequestModel(email="unknown@example.com"),
                "203.0.113.7",
            )

        self.assertTrue(result["status"])
        executed = [call.args[0] for call in connection.execute.await_args_list] + [
            call.args[0] for call in connection.fetchval.await_args_list
        ]
        self.assertFalse(any("users" in sql for sql in executed))


class ExchangeTests(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limits_exchange_attempts_per_ip(self):
        connection = MagicLinkConnection(
            fetchval=[settings.MAGIC_LINK_EXCHANGE_IP_RATE_LIMIT]
        )

        result = await auth_service.exchange(
            connection,
            ExchangeRequestModel(auth_code="raw-code"),
            "203.0.113.7",
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 429)
        connection.fetchrow.assert_not_awaited()

    async def test_records_exchange_attempt_before_consuming_code(self):
        connection = MagicLinkConnection(fetchval=[0], fetchrow=[None])

        await auth_service.exchange(
            connection,
            ExchangeRequestModel(auth_code="raw-code"),
            "203.0.113.7",
        )

        attempt = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO magic_link_exchange_attempts" in call.args[0]
        )
        self.assertEqual(attempt.args[2], "203.0.113.7")

    async def test_consumes_code_then_creates_user_only_after_validation(self):
        user_id = uuid4()
        connection = MagicLinkConnection(
            fetchrow=[
                {"email": "new@example.com"},
                None,
                {
                    "id": user_id,
                    "fullname": "new",
                    "email": "new@example.com",
                    "role": "BASIC",
                    "created_at": datetime.now(timezone.utc),
                    "profile_completed_at": None,
                },
            ]
        )

        with (
            patch.object(auth_service, "create_access_token", return_value="access-token"),
            patch.object(auth_service, "create_refresh_token", return_value="refresh-token"),
        ):
            result = await auth_service.exchange(
                connection, ExchangeRequestModel(auth_code="raw-code")
            )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["data"]["user"]["email"], "new@example.com")
        self.assertFalse(result["data"]["user"]["profile_completed"])
        self.assertEqual(result["data"]["access_token"], "access-token")
        self.assertEqual(result["data"]["refresh_token"], "refresh-token")

        consume = connection.fetchrow.await_args_list[0]
        self.assertIn("UPDATE magic_link_codes", consume.args[0])
        self.assertIn("used_at IS NULL", consume.args[0])
        self.assertIn("expires_at > now()", consume.args[0])
        self.assertEqual(consume.args[1], hash_magic_link_code("raw-code"))

        create_user = connection.fetchrow.await_args_list[2]
        self.assertIn("INSERT INTO users (id, fullname, email)", create_user.args[0])
        self.assertIn(
            "RETURNING id, fullname, email, role, created_at, profile_completed_at",
            create_user.args[0],
        )
        self.assertEqual(create_user.args[2], "new")
        self.assertEqual(create_user.args[3], "new@example.com")
        self.assertNotIn("password", create_user.args[0])

        session = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO refresh_sessions" in call.args[0]
        )
        self.assertNotIn("refresh-token", session.args)
        self.assertIn(hash_refresh_token("refresh-token"), session.args)

    async def test_rejects_reused_expired_or_unknown_code_without_creating_user(self):
        connection = MagicLinkConnection(fetchrow=[None])

        result = await auth_service.exchange(
            connection, ExchangeRequestModel(auth_code="used-code")
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 401)
        self.assertEqual(connection.fetchrow.await_count, 1)
        connection.execute.assert_not_awaited()

    async def test_reuses_existing_user_without_creating_a_new_one(self):
        user_id = uuid4()
        connection = MagicLinkConnection(
            fetchrow=[
                {"email": "existing@example.com"},
                {
                    "id": user_id,
                    "fullname": "Existing",
                    "email": "existing@example.com",
                    "role": "BASIC",
                    "created_at": datetime.now(timezone.utc),
                    "profile_completed_at": datetime.now(timezone.utc),
                },
            ]
        )

        with (
            patch.object(auth_service, "create_access_token", return_value="access-token"),
            patch.object(auth_service, "create_refresh_token", return_value="refresh-token"),
        ):
            result = await auth_service.exchange(
                connection, ExchangeRequestModel(auth_code="raw-code")
            )

        self.assertTrue(result["status"])
        self.assertTrue(result["data"]["user"]["profile_completed"])
        self.assertEqual(connection.fetchrow.await_count, 2)
        self.assertFalse(
            any(
                "INSERT INTO users" in call.args[0]
                for call in connection.fetchrow.await_args_list
            )
        )


class AuthRequestSchemaTests(unittest.TestCase):
    def test_normalizes_magic_link_email(self):
        data = MagicLinkRequestModel(email="  User@Example.COM  ")

        self.assertEqual(data.email, "user@example.com")

    def test_rejects_invalid_magic_link_email(self):
        for value in ["", "no-at", "a@", "@b", "a b@example.com", "user@ example.com"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                MagicLinkRequestModel(email=value)

    def test_requires_non_empty_auth_code(self):
        with self.assertRaises(ValidationError):
            ExchangeRequestModel(auth_code="")

    def test_requires_refresh_token(self):
        with self.assertRaises(ValidationError):
            RefreshTokenRequestModel()
