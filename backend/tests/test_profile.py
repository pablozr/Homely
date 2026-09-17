import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.postgresql.postgresql import postgresql
from core.security.security import create_access_token, verify_token
from dependencies import auth
from main import app
from schemas.auth import user_from_row
from schemas.profile import (
    ProfileUpdateRequestModel,
    initials_from_fullname,
    profile_from_row,
)
from services.profile import profile_service


class FakeConnection:
    def __init__(self, rows):
        self.fetchrow = AsyncMock(side_effect=rows)


def profile_row(**overrides):
    row = {
        "id": uuid4(),
        "fullname": "Ana Maria Silva",
        "email": "ana@example.com",
        "role": "BASIC",
        "created_at": datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        "profile_completed_at": None,
    }
    row.update(overrides)

    return row


class ProfileSchemaTests(unittest.TestCase):
    def test_trims_fullname(self):
        data = ProfileUpdateRequestModel(fullname="  Ana Maria  ")

        self.assertEqual(data.fullname, "Ana Maria")

    def test_rejects_blank_fullname(self):
        for value in ["", "   ", "\t\n"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ProfileUpdateRequestModel(fullname=value)

    def test_requires_fullname(self):
        with self.assertRaises(ValidationError):
            ProfileUpdateRequestModel()

    def test_rejects_fullname_longer_than_users_column(self):
        with self.assertRaises(ValidationError):
            ProfileUpdateRequestModel(fullname="a" * 256)

    def test_accepts_fullname_whose_trimmed_value_is_at_the_limit(self):
        data = ProfileUpdateRequestModel(fullname=" " + "a" * 255 + " ")

        self.assertEqual(data.fullname, "a" * 255)

    def test_rejects_fullname_longer_than_the_limit_after_trim(self):
        with self.assertRaises(ValidationError):
            ProfileUpdateRequestModel(fullname=" " + "a" * 256 + " ")

    def test_computes_initials_from_first_and_last_name(self):
        self.assertEqual(initials_from_fullname("Ana Maria Silva"), "AS")
        self.assertEqual(initials_from_fullname("ana"), "A")
        self.assertEqual(initials_from_fullname("  Ana   Maria  "), "AM")


class ProfileSerializationTests(unittest.TestCase):
    def test_serializes_profile_with_initials_and_completion_without_email(self):
        profile = profile_from_row(
            profile_row(profile_completed_at=datetime.now(timezone.utc))
        )

        self.assertEqual(profile["fullname"], "Ana Maria Silva")
        self.assertEqual(profile["initials"], "AS")
        self.assertTrue(profile["profile_completed"])
        self.assertEqual(profile["created_at"], "2026-09-16T12:00:00+00:00")
        self.assertNotIn("email", profile)

    def test_serializes_incomplete_profile(self):
        profile = profile_from_row(profile_row())

        self.assertFalse(profile["profile_completed"])

    def test_auth_user_serialization_exposes_profile_completed(self):
        user = user_from_row(profile_row(profile_completed_at=None))

        self.assertFalse(user["profile_completed"])
        self.assertEqual(user["email"], "ana@example.com")

        completed = user_from_row(
            profile_row(profile_completed_at=datetime.now(timezone.utc))
        )
        self.assertTrue(completed["profile_completed"])


class VerifyTokenProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_loads_profile_completion_marker_from_database(self):
        user_id = uuid4()
        connection = FakeConnection([profile_row(id=user_id)])

        token = create_access_token({"userId": str(user_id), "type": "auth"})

        user = await verify_token(token, connection)

        query, parameter = connection.fetchrow.await_args.args
        self.assertIn("profile_completed_at", query)
        self.assertEqual(parameter, user_id)
        self.assertIsNone(user["profile_completed_at"])


class GetProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_authenticated_profile_without_email(self):
        user_id = uuid4()
        connection = FakeConnection([profile_row(id=user_id)])

        result = await profile_service.get_profile(connection, user_id)

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        profile = result["data"]["user"]
        self.assertEqual(profile["id"], user_id)
        self.assertFalse(profile["profile_completed"])
        self.assertNotIn("email", profile)

        query, parameter = connection.fetchrow.await_args.args
        self.assertIn("FROM users WHERE id = $1", query)
        self.assertNotIn("email", query)
        self.assertEqual(parameter, user_id)

    async def test_returns_not_found_for_missing_user(self):
        connection = FakeConnection([None])

        result = await profile_service.get_profile(connection, uuid4())

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class UpdateProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_updates_name_and_marks_profile_completed_in_one_query(self):
        user_id = uuid4()
        connection = FakeConnection(
            [
                profile_row(
                    id=user_id,
                    fullname="Ana Maria",
                    profile_completed_at=datetime.now(timezone.utc),
                )
            ]
        )

        result = await profile_service.update_profile(
            connection,
            user_id,
            ProfileUpdateRequestModel(fullname="  Ana Maria  "),
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        updated = result["data"]["user"]
        self.assertEqual(updated["fullname"], "Ana Maria")
        self.assertEqual(updated["initials"], "AM")
        self.assertTrue(updated["profile_completed"])

        query, parameter_user_id, fullname = connection.fetchrow.await_args.args
        self.assertIn("UPDATE users", query)
        self.assertIn(
            "profile_completed_at = COALESCE(profile_completed_at, now())", query
        )
        self.assertEqual(parameter_user_id, user_id)
        self.assertEqual(fullname, "Ana Maria")
        self.assertEqual(connection.fetchrow.await_count, 1)

    async def test_returns_not_found_when_user_does_not_exist(self):
        connection = FakeConnection([None])

        result = await profile_service.update_profile(
            connection,
            uuid4(),
            ProfileUpdateRequestModel(fullname="Ana"),
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class ProfileRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = uuid4()
        self.connection = FakeConnection(
            [
                profile_row(
                    id=self.user_id,
                    fullname="Ana Maria",
                    profile_completed_at=datetime.now(timezone.utc),
                )
            ]
        )

        async def override_connection():
            yield self.connection

        app.dependency_overrides[postgresql.get_db] = override_connection
        app.dependency_overrides[auth.validate_token_wrapper] = lambda: {
            "id": self.user_id,
            "role": "BASIC",
        }
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_update_profile_returns_updated_user_in_standard_envelope(self):
        response = self.client.patch("/profile/me", json={"fullname": "  Ana Maria  "})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["message"], "Profile updated")
        self.assertEqual(
            body["data"]["user"],
            {
                "id": str(self.user_id),
                "fullname": "Ana Maria",
                "initials": "AM",
                "role": "BASIC",
                "profile_completed": True,
                "created_at": "2026-09-16T12:00:00+00:00",
            },
        )

    def test_update_profile_rejects_blank_fullname(self):
        response = self.client.patch("/profile/me", json={"fullname": "   "})

        self.assertEqual(response.status_code, 422)
