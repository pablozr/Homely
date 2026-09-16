import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from pydantic import ValidationError

from core.config.config import DEFAULT_SECRET_KEY, Settings
from core.security.jwt_payloads import auth_jwt_payload_from_row
from core.security.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_refresh_token,
    verify_token,
)
from services.auth import auth_service


class Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class RefreshConnection:
    def __init__(self, rows):
        self.fetchrow = AsyncMock(side_effect=rows)
        self.execute = AsyncMock()

    def transaction(self):
        return Transaction()


class RefreshTokenTests(unittest.IsolatedAsyncioTestCase):
    def test_rejects_default_jwt_secret_outside_development(self):
        with self.assertRaises(ValidationError):
            Settings(ENVIRONMENT="production", SECRET_KEY=DEFAULT_SECRET_KEY)

        with self.assertRaises(ValidationError):
            Settings(ENVIRONMENT="production", SECRET_KEY="short")

    def test_refresh_tokens_are_random_and_hashed(self):
        first_token = create_refresh_token()
        second_token = create_refresh_token()

        self.assertNotEqual(first_token, second_token)
        self.assertEqual(hash_refresh_token(first_token), hash_refresh_token(first_token))
        self.assertNotEqual(first_token, hash_refresh_token(first_token))

    def test_access_token_serializes_uuid_user_id(self):
        user_id = uuid4()
        token = create_access_token(
            auth_jwt_payload_from_row(
                {
                    "id": user_id,
                    "email": "user@example.com",
                    "fullname": "User",
                    "role": "BASIC",
                }
            )
        )

        self.assertEqual(decode_access_token(token)["userId"], str(user_id))

    async def test_verifies_access_token_with_uuid_database_parameter(self):
        user_id = uuid4()
        connection = RefreshConnection(
            [
                {
                    "id": user_id,
                    "fullname": "User",
                    "email": "user@example.com",
                    "role": "BASIC",
                    "created_at": datetime.now(timezone.utc),
                }
            ]
        )
        token = create_access_token(
            auth_jwt_payload_from_row(
                {
                    "id": user_id,
                    "email": "user@example.com",
                    "fullname": "User",
                    "role": "BASIC",
                }
            )
        )

        user = await verify_token(token, connection)

        self.assertEqual(user["id"], user_id)
        self.assertEqual(connection.fetchrow.await_args.args[1], user_id)

    async def test_refresh_rotates_the_session_token(self):
        refresh_token = "current-refresh-token"
        family_id = uuid4()
        user_id = uuid4()
        connection = RefreshConnection(
            [
                {
                    "user_id": user_id,
                    "family_id": family_id,
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                    "revoked_at": None,
                },
                {
                    "user_id": user_id,
                    "family_id": family_id,
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                    "revoked_at": None,
                },
                {
                    "id": user_id,
                    "fullname": "User",
                    "email": "user@example.com",
                    "role": "BASIC",
                    "created_at": datetime.now(timezone.utc),
                },
            ]
        )

        with (
            patch.object(auth_service, "create_access_token", return_value="new-access-token"),
            patch.object(auth_service, "create_refresh_token", return_value="next-refresh-token"),
        ):
            result = await auth_service.refresh(connection, refresh_token)

        self.assertTrue(result["status"])
        self.assertEqual(result["data"]["access_token"], "new-access-token")
        self.assertEqual(result["data"]["refresh_token"], "next-refresh-token")
        self.assertEqual(connection.execute.await_count, 3)
        self.assertNotIn(
            refresh_token,
            [argument for call in connection.execute.await_args_list for argument in call.args],
        )

    async def test_reused_refresh_token_revokes_its_family(self):
        connection = RefreshConnection(
            [
                {
                    "user_id": uuid4(),
                    "family_id": uuid4(),
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                    "revoked_at": datetime.now(timezone.utc),
                },
                {
                    "user_id": uuid4(),
                    "family_id": uuid4(),
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                    "revoked_at": datetime.now(timezone.utc),
                },
            ]
        )

        result = await auth_service.refresh(connection, "reused-refresh-token")

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 401)
        self.assertEqual(connection.execute.await_count, 2)

    async def test_logout_revokes_the_current_session_family(self):
        connection = RefreshConnection([{"family_id": uuid4()}])

        result = await auth_service.logout(connection, "current-refresh-token")

        self.assertTrue(result["status"])
        self.assertEqual(connection.execute.await_count, 2)
