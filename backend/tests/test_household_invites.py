import importlib.util
import json
import unittest
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.config.config import settings
from core.postgresql.postgresql import postgresql
from core.security.security import derive_invite_token, hash_invite_token
from dependencies import auth
from dependencies import households as household_dependencies
from main import app
from schemas.households import InviteAcceptRequestModel
from services.households import invites_service


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "0005_household_invites.py"
)


class Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self, on_fetchrow=None, on_fetch=None, on_fetchval=None):
        self.fetchrow = AsyncMock(
            side_effect=on_fetchrow if on_fetchrow is not None else (lambda *a: None)
        )
        self.fetch = AsyncMock(
            side_effect=on_fetch if on_fetch is not None else (lambda *a: [])
        )
        self.fetchval = AsyncMock(
            side_effect=on_fetchval if on_fetchval is not None else (lambda *a: None)
        )
        self.execute = AsyncMock()
        self.transactions = 0

    def transaction(self):
        self.transactions += 1
        return Transaction()


def created_at():
    return datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def household_row(**overrides):
    row = {
        "id": uuid4(),
        "name": "Casa",
        "timezone": "America/Sao_Paulo",
        "default_due_time": time(20, 0),
        "created_at": created_at(),
        "deactivated_at": None,
    }
    row.update(overrides)

    return row


def invite_row(**overrides):
    row = {
        "id": uuid4(),
        "household_id": uuid4(),
        "created_at": created_at(),
        "expires_at": created_at() + timedelta(days=7),
        "revoked_at": None,
        "accepted_at": None,
        "accepted_by": None,
        "accepted_membership_id": None,
    }
    row.update(overrides)

    return row


def membership_row(**overrides):
    row = {
        "id": uuid4(),
        "user_id": uuid4(),
        "role": "MEMBER",
        "status": "ACTIVE",
        "joined_at": created_at(),
    }
    row.update(overrides)

    return row


class InviteTokenSecurityTests(unittest.TestCase):
    def test_derives_a_deterministic_opaque_token_per_invite(self):
        invite_id = uuid4()

        first = derive_invite_token(invite_id)
        second = derive_invite_token(invite_id)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, derive_invite_token(uuid4()))

    def test_hashes_the_token_with_sha256(self):
        token = derive_invite_token(uuid4())
        token_hash = hash_invite_token(token)

        self.assertEqual(len(token_hash), 64)
        self.assertNotEqual(token_hash, token)
        self.assertEqual(token_hash, hash_invite_token(token))


class InviteAcceptSchemaTests(unittest.TestCase):
    def test_trims_the_invite_token(self):
        data = InviteAcceptRequestModel(invite_token="  raw-token  ")

        self.assertEqual(data.invite_token, "raw-token")

    def test_rejects_blank_invite_token(self):
        with self.assertRaises(ValidationError):
            InviteAcceptRequestModel(invite_token="   ")


class CreateInviteTests(unittest.IsolatedAsyncioTestCase):
    def connection(self, invite):
        membership_id = uuid4()

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return None

            if "FROM households" in query:
                return household_row(id=invite["household_id"])

            if "FROM household_members" in query:
                return {"id": membership_id, "role": "OWNER"}

            if "INSERT INTO household_invites" in query:
                return invite_row(
                    id=args[0],
                    household_id=args[1],
                    created_at=created_at(),
                    expires_at=args[4],
                )

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)
        connection.membership_id = membership_id

        return connection

    async def test_persists_only_the_hash_and_returns_a_derived_link(self):
        user_id = uuid4()
        household_id = uuid4()
        invite = invite_row(household_id=household_id)
        connection = self.connection(invite)

        result = await invites_service.create_invite(
            connection, user_id, household_id, "key-1"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(result["message"], "Invite created")
        self.assertEqual(connection.transactions, 1)

        insert = next(
            call
            for call in connection.fetchrow.await_args_list
            if "INSERT INTO household_invites" in call.args[0]
        )
        invite_id = insert.args[1]
        token = derive_invite_token(invite_id)
        self.assertEqual(result["data"]["id"], str(invite_id))
        self.assertEqual(
            result["data"]["invite_url"],
            invites_service.invite_url(token),
        )
        self.assertEqual(insert.args[2], household_id)
        self.assertEqual(insert.args[3], hash_invite_token(token))
        self.assertEqual(insert.args[4], user_id)
        self.assertNotIn(token, insert.args)

        remaining = (insert.args[5] - datetime.now(timezone.utc)).total_seconds()
        self.assertAlmostEqual(
            remaining, settings.INVITE_EXPIRE_DAYS * 86400, delta=5
        )

        audit = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO activity_events" in call.args[0]
        )
        self.assertIn("INVITE_CREATED", audit.args[0])
        self.assertEqual(json.loads(audit.args[5]), {"invite_id": str(invite_id)})

        record = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO idempotency_records" in call.args[0]
        )
        self.assertEqual(record.args[2], user_id)
        self.assertEqual(record.args[3], household_id)
        self.assertEqual(record.args[4], "household_invites.create")
        self.assertEqual(record.args[5], "key-1")
        self.assertEqual(record.args[6], invites_service.INVITE_PAYLOAD_FINGERPRINT)
        self.assertEqual(record.args[7], invite_id)
        stored = json.loads(record.args[8])
        self.assertNotIn("invite_url", stored)
        self.assertNotIn(token, json.dumps(stored))

    async def test_replays_the_advisory_lock_and_derived_link(self):
        user_id = uuid4()
        household_id = uuid4()
        invite = invite_row(household_id=household_id)
        stored = {
            "id": str(invite["id"]),
            "household_id": str(household_id),
            "created_at": invite["created_at"].isoformat(),
            "expires_at": invite["expires_at"].isoformat(),
        }

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return {
                    "fingerprint": invites_service.INVITE_PAYLOAD_FINGERPRINT,
                    "resource_id": invite["id"],
                    "response_status": 201,
                    "response_data": json.dumps(stored),
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await invites_service.create_invite(
            connection, user_id, household_id, "key-1"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(result["data"]["id"], str(invite["id"]))
        self.assertEqual(
            result["data"]["invite_url"],
            invites_service.invite_url(derive_invite_token(invite["id"])),
        )
        self.assertEqual(connection.transactions, 1)
        self.assertEqual(connection.fetchrow.await_count, 1)
        self.assertEqual(connection.execute.await_count, 1)
        self.assertFalse(
            any(
                "INSERT" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )

    async def test_conflicts_when_the_key_is_reused_with_a_different_payload(self):
        user_id = uuid4()
        household_id = uuid4()

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return {
                    "fingerprint": "0" * 64,
                    "resource_id": uuid4(),
                    "response_status": 201,
                    "response_data": "{}",
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await invites_service.create_invite(
            connection, user_id, household_id, "key-1"
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)

    async def test_rejects_a_member_who_is_not_the_owner(self):
        user_id = uuid4()
        household_id = uuid4()

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return None

            if "FROM households" in query:
                return household_row(id=household_id)

            if "FROM household_members" in query:
                return {"id": uuid4(), "role": "MEMBER"}

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await invites_service.create_invite(
            connection, user_id, household_id, "key-1"
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 403)
        self.assertFalse(
            any(
                "INSERT INTO household_invites" in call.args[0]
                for call in connection.fetchrow.await_args_list
            )
        )

    async def test_returns_not_found_for_a_missing_household(self):
        connection = FakeConnection(on_fetchrow=lambda *a: None)

        result = await invites_service.create_invite(
            connection, uuid4(), uuid4(), "key-1"
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class ListInvitesTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_only_usable_invites(self):
        household_id = uuid4()
        rows = [invite_row(household_id=household_id)]

        def on_fetch(query, *args):
            self.assertIn("revoked_at IS NULL", query)
            self.assertIn("accepted_at IS NULL", query)
            self.assertIn("expires_at > now()", query)
            self.assertEqual(args[0], household_id)
            return rows

        connection = FakeConnection(on_fetch=on_fetch)

        result = await invites_service.list_invites(connection, household_id)

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(len(result["data"]["invites"]), 1)
        invite = result["data"]["invites"][0]
        self.assertEqual(set(invite), {"id", "household_id", "created_at", "expires_at"})
        self.assertNotIn("invite_url", json.dumps(invite, default=str))


class RevokeInviteTests(unittest.IsolatedAsyncioTestCase):
    def connection(self, invite, revoked_at=None):
        def on_fetchrow(query, *args):
            if "FROM households" in query:
                return household_row(id=invite["household_id"])

            if "FROM household_members" in query:
                return {"id": uuid4(), "role": "OWNER"}

            if "FROM household_invites" in query:
                return invite

            raise AssertionError(f"unexpected query: {query}")

        return FakeConnection(
            on_fetchrow=on_fetchrow,
            on_fetchval=lambda *a: revoked_at,
        )

    async def test_revokes_an_outstanding_invite(self):
        user_id = uuid4()
        invite = invite_row()
        revoked_at = datetime.now(timezone.utc)
        connection = self.connection(invite, revoked_at=revoked_at)

        result = await invites_service.revoke_invite(
            connection, user_id, invite["household_id"], invite["id"]
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["data"]["invite_id"], invite["id"])
        self.assertEqual(result["data"]["revoked_at"], revoked_at.isoformat())

        update = next(
            call
            for call in connection.fetchval.await_args_list
            if "UPDATE household_invites" in call.args[0]
        )
        self.assertEqual(update.args[1], invite["id"])
        self.assertEqual(update.args[3], user_id)

        audit = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO activity_events" in call.args[0]
        )
        self.assertIn("INVITE_REVOKED", audit.args[0])

    async def test_is_idempotent_for_an_already_revoked_invite(self):
        revoked_at = datetime.now(timezone.utc)
        invite = invite_row(revoked_at=revoked_at, revoked_by=uuid4())
        connection = self.connection(invite)
        connection.fetchval = AsyncMock(
            side_effect=AssertionError("should not update again")
        )

        result = await invites_service.revoke_invite(
            connection, uuid4(), invite["household_id"], invite["id"]
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["data"]["revoked_at"], revoked_at.isoformat())
        connection.fetchval.assert_not_awaited()

    async def test_conflicts_when_the_invite_was_already_accepted(self):
        invite = invite_row(
            accepted_at=datetime.now(timezone.utc),
            accepted_by=uuid4(),
            accepted_membership_id=uuid4(),
        )
        connection = self.connection(invite)

        result = await invites_service.revoke_invite(
            connection, uuid4(), invite["household_id"], invite["id"]
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)

    async def test_returns_not_found_for_an_unknown_invite(self):
        def on_fetchrow(query, *args):
            if "FROM households" in query:
                return household_row()
            if "FROM household_members" in query:
                return {"id": uuid4(), "role": "OWNER"}
            if "FROM household_invites" in query:
                return None
            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await invites_service.revoke_invite(
            connection, uuid4(), uuid4(), uuid4()
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class AcceptInviteTests(unittest.IsolatedAsyncioTestCase):
    def request(self, token="raw-token"):
        return InviteAcceptRequestModel(invite_token=token)

    async def test_creates_a_membership_then_consumes_the_invite(self):
        user_id = uuid4()
        invite = invite_row()
        membership = membership_row(user_id=user_id)
        household = household_row(id=invite["household_id"])

        def on_fetchrow(query, *args):
            if "WHERE token_hash = $1" in query:
                return invite
            if "FROM households" in query:
                return household
            if "FROM household_members" in query and "FOR UPDATE" in query:
                return None
            if "INSERT INTO household_members" in query:
                return membership

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow, on_fetchval=lambda *a: 0)

        result = await invites_service.accept_invite(
            connection, user_id, self.request(), "203.0.113.7"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 201)
        self.assertTrue(result["data"]["membership_created"])
        self.assertEqual(result["data"]["selected_household_id"], household["id"])
        self.assertEqual(result["data"]["membership"]["id"], membership["id"])

        lookup = connection.fetchrow.await_args_list[0]
        self.assertEqual(lookup.args[1], hash_invite_token("raw-token"))

        consume = next(
            call
            for call in connection.execute.await_args_list
            if "UPDATE household_invites" in call.args[0]
        )
        self.assertEqual(consume.args[1], invite["id"])
        self.assertEqual(consume.args[2], user_id)
        self.assertEqual(consume.args[3], membership["id"])

        selection = next(
            call
            for call in connection.execute.await_args_list
            if "UPDATE users" in call.args[0]
        )
        self.assertEqual(selection.args[2], household["id"])

        audit = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO activity_events" in call.args[0]
        )
        metadata = json.loads(audit.args[5])
        self.assertEqual(metadata["membership_id"], str(membership["id"]))
        self.assertNotIn("raw-token", json.dumps(metadata))
        self.assertNotIn("email", json.dumps(metadata))
        self.assertTrue(
            any(
                "MEMBER_JOINED" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )

    async def test_inserts_a_new_membership_when_only_inactive_history_exists(self):
        user_id = uuid4()
        invite = invite_row()
        membership = membership_row(user_id=user_id)

        def on_fetchrow(query, *args):
            if "WHERE token_hash = $1" in query:
                return invite
            if "FROM households" in query:
                return household_row(id=invite["household_id"])
            if "FROM household_members" in query and "FOR UPDATE" in query:
                return None
            if "INSERT INTO household_members" in query:
                return membership

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow, on_fetchval=lambda *a: 0)

        result = await invites_service.accept_invite(
            connection, user_id, self.request(), "203.0.113.7"
        )

        self.assertEqual(result["status_code"], 201)
        self.assertFalse(
            any(
                "SET status = 'ACTIVE'" in call.args[0]
                or "SET role" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )
        insert = next(
            call
            for call in connection.fetchrow.await_args_list
            if "INSERT INTO household_members" in call.args[0]
        )
        self.assertIn("'MEMBER'", insert.args[0])
        self.assertIn("'ACTIVE'", insert.args[0])

    async def test_reuses_an_existing_active_membership(self):
        user_id = uuid4()
        invite = invite_row()
        membership = membership_row(user_id=user_id, role="OWNER")

        def on_fetchrow(query, *args):
            if "WHERE token_hash = $1" in query:
                return invite
            if "FROM households" in query:
                return household_row(id=invite["household_id"])
            if "FROM household_members" in query and "FOR UPDATE" in query:
                return membership

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow, on_fetchval=lambda *a: 0)

        result = await invites_service.accept_invite(
            connection, user_id, self.request(), "203.0.113.7"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertFalse(result["data"]["membership_created"])
        self.assertEqual(result["data"]["membership"]["role"], "OWNER")
        self.assertFalse(
            any(
                "INSERT INTO household_members" in call.args[0]
                for call in connection.fetchrow.await_args_list
            )
        )
        self.assertFalse(
            any(
                "MEMBER_JOINED" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )
        self.assertTrue(
            any(
                "INVITE_ACCEPTED" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )

    async def test_returns_200_when_the_same_user_repeats_an_accepted_invite(self):
        user_id = uuid4()
        membership = membership_row(user_id=user_id)
        invite = invite_row(
            accepted_at=datetime.now(timezone.utc),
            accepted_by=user_id,
            accepted_membership_id=membership["id"],
        )

        def on_fetchrow(query, *args):
            if "WHERE token_hash = $1" in query:
                return invite
            if "FROM household_members" in query:
                return membership
            if "FROM households" in query:
                return household_row(id=invite["household_id"])

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow, on_fetchval=lambda *a: 0)

        result = await invites_service.accept_invite(
            connection, user_id, self.request(), "203.0.113.7"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertFalse(result["data"]["membership_created"])
        self.assertFalse(
            any(
                "UPDATE household_invites" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )

    async def test_returns_409_when_the_invite_was_used_by_another_user(self):
        invite = invite_row(
            accepted_at=datetime.now(timezone.utc),
            accepted_by=uuid4(),
            accepted_membership_id=uuid4(),
        )

        def on_fetchrow(query, *args):
            if "WHERE token_hash = $1" in query:
                return invite
            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow, on_fetchval=lambda *a: 0)

        result = await invites_service.accept_invite(
            connection, uuid4(), self.request(), "203.0.113.7"
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)

    async def test_returns_404_for_an_unknown_token(self):
        connection = FakeConnection(on_fetchrow=lambda *a: None, on_fetchval=lambda *a: 0)

        result = await invites_service.accept_invite(
            connection, uuid4(), self.request(), "203.0.113.7"
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)

    async def test_returns_409_for_expired_and_revoked_invites(self):
        cases = [
            invite_row(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)),
            invite_row(revoked_at=datetime.now(timezone.utc), revoked_by=uuid4()),
        ]

        for invite in cases:
            with self.subTest(invite=invite):
                connection = FakeConnection(
                    on_fetchrow=lambda *a, invite=invite: invite,
                    on_fetchval=lambda *a: 0,
                )

                result = await invites_service.accept_invite(
                    connection, uuid4(), self.request(), "203.0.113.7"
                )

                self.assertFalse(result["status"])
                self.assertEqual(result["status_code"], 409)

    async def test_rate_limits_acceptance_per_user(self):
        connection = FakeConnection(
            on_fetchval=lambda *a: settings.INVITE_ACCEPT_USER_RATE_LIMIT,
            on_fetchrow=lambda *a: None,
        )

        result = await invites_service.accept_invite(
            connection, uuid4(), self.request(), "203.0.113.7"
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 429)
        connection.fetchrow.assert_not_awaited()

    async def test_rate_limits_acceptance_per_ip(self):
        values = iter([0, settings.INVITE_ACCEPT_IP_RATE_LIMIT])
        connection = FakeConnection(
            on_fetchval=lambda *a: next(values),
            on_fetchrow=lambda *a: None,
        )

        result = await invites_service.accept_invite(
            connection, uuid4(), self.request(), "203.0.113.7"
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 429)
        connection.fetchrow.assert_not_awaited()

    async def test_records_the_attempt_before_looking_up_the_invite(self):
        connection = FakeConnection(on_fetchrow=lambda *a: None, on_fetchval=lambda *a: 0)

        await invites_service.accept_invite(
            connection, uuid4(), self.request(), "203.0.113.7"
        )

        attempt = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO household_invite_accept_attempts" in call.args[0]
        )
        self.assertEqual(attempt.args[3], "203.0.113.7")


class InviteMigrationTests(unittest.TestCase):
    def load_migration(self):
        spec = importlib.util.spec_from_file_location(
            "migration_0005", MIGRATION_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def test_follows_the_households_revision(self):
        module = self.load_migration()

        self.assertEqual(module.revision, "0005")
        self.assertEqual(module.down_revision, "0004")


class InviteRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = uuid4()
        self.household_id = uuid4()
        self.connection = FakeConnection()

        async def override_connection():
            yield self.connection

        app.dependency_overrides[postgresql.get_db] = override_connection
        app.dependency_overrides[auth.validate_token_wrapper] = lambda: {
            "id": self.user_id,
            "role": "BASIC",
        }
        app.dependency_overrides[
            household_dependencies.require_owner_membership
        ] = lambda: {
            "user_id": self.user_id,
            "household_id": self.household_id,
            "membership_id": uuid4(),
            "role": "OWNER",
        }
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_accept_route_returns_the_standard_envelope(self):
        membership_id = uuid4()
        data = {
            "household": {
                "id": str(self.household_id),
                "name": "Casa",
                "timezone": "UTC",
                "default_due_time": "20:00:00",
                "role": "MEMBER",
                "joined_at": created_at().isoformat(),
                "created_at": created_at().isoformat(),
            },
            "membership": {
                "id": str(membership_id),
                "user_id": str(self.user_id),
                "role": "MEMBER",
                "status": "ACTIVE",
                "joined_at": created_at().isoformat(),
            },
            "membership_created": True,
            "selected_household_id": str(self.household_id),
        }
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 201,
                "message": "Invite accepted",
                "data": data,
            }
        )

        with patch.object(invites_service, "accept_invite", service):
            response = self.client.post(
                "/households/invites/accept",
                json={"invite_token": "  raw-token  "},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(), {"message": "Invite accepted", "data": data}
        )
        call = service.await_args
        self.assertEqual(call.args[1], self.user_id)
        self.assertEqual(call.args[2].invite_token, "raw-token")

    def test_create_invite_requires_the_idempotency_key_header(self):
        response = self.client.post(f"/households/{self.household_id}/invites")

        self.assertEqual(response.status_code, 422)

    def test_accept_route_redacts_the_token_from_validation_errors(self):
        token = "t" * 300

        response = self.client.post(
            "/households/invites/accept", json={"invite_token": token}
        )

        self.assertEqual(response.status_code, 422)
        self.assertNotIn(token, response.text)
        detail = response.json()["detail"][0]
        self.assertEqual(detail["loc"], ["body", "invite_token"])
        self.assertEqual(detail["type"], "string_too_long")
        self.assertIn("msg", detail)
        self.assertNotIn("input", detail)
        self.assertNotIn("ctx", detail)


if __name__ == "__main__":
    unittest.main()
