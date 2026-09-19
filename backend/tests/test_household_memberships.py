import json
import unittest
from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from core.postgresql.postgresql import postgresql
from dependencies import auth, households as household_dependencies
from main import app
from services.households import memberships_service


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


def actor_owner():
    return {"id": uuid4(), "role": "OWNER"}


class ListMembersTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_active_members_without_email(self):
        household_id = uuid4()
        row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "fullname": "Ana Souza",
            "role": "OWNER",
            "status": "ACTIVE",
            "joined_at": created_at(),
        }

        def on_fetch(query, *args):
            self.assertIn("hm.status = 'ACTIVE'", query)
            self.assertNotIn("email", query)
            self.assertEqual(args[0], household_id)
            return [row]

        connection = FakeConnection(on_fetch=on_fetch)

        result = await memberships_service.list_members(connection, household_id)

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        member = result["data"]["memberships"][0]
        self.assertEqual(member["id"], row["id"])
        self.assertEqual(member["fullname"], "Ana Souza")
        self.assertNotIn("email", member)
        self.assertNotIn("email", json.dumps(result["data"], default=str))


class RemoveMemberTests(unittest.IsolatedAsyncioTestCase):
    def connection(self, target, revoked_at=None):
        actor = actor_owner()

        def on_fetchrow(query, *args):
            if "FROM households" in query:
                return household_row()
            if "WHERE id = $1 AND household_id = $2" in query:
                return target
            if "FROM household_members" in query:
                return actor
            raise AssertionError(f"unexpected query: {query}")

        return FakeConnection(
            on_fetchrow=on_fetchrow,
            on_fetchval=lambda *a: revoked_at or created_at(),
        )

    async def test_removes_an_active_member_and_records_history(self):
        actor_id = uuid4()
        target = {
            "id": uuid4(),
            "user_id": uuid4(),
            "role": "MEMBER",
            "status": "ACTIVE",
        }
        removed_at = datetime.now(timezone.utc)
        connection = self.connection(target, revoked_at=removed_at)

        result = await memberships_service.remove_member(
            connection, actor_id, uuid4(), target["id"]
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["data"]["membership_id"], target["id"])
        self.assertEqual(result["data"]["removed_at"], removed_at.isoformat())

        update = connection.fetchval.await_args
        self.assertIn("SET status = 'INACTIVE'", update.args[0])
        self.assertEqual(update.args[1], target["id"])

        audit = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO activity_events" in call.args[0]
        )
        self.assertIn("MEMBER_REMOVED", audit.args[0])
        self.assertEqual(
            json.loads(audit.args[5]),
            {
                "membership_id": str(target["id"]),
                "removed_user_id": str(target["user_id"]),
            },
        )

    async def test_rejects_removing_the_owner(self):
        target = {
            "id": uuid4(),
            "user_id": uuid4(),
            "role": "OWNER",
            "status": "ACTIVE",
        }
        connection = self.connection(target)

        result = await memberships_service.remove_member(
            connection, uuid4(), uuid4(), target["id"]
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)
        connection.fetchval.assert_not_awaited()

    async def test_returns_not_found_for_a_missing_or_cross_house_member(self):
        connection = self.connection(None)

        result = await memberships_service.remove_member(
            connection, uuid4(), uuid4(), uuid4()
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)

    async def test_returns_not_found_for_an_inactive_member(self):
        target = {
            "id": uuid4(),
            "user_id": uuid4(),
            "role": "MEMBER",
            "status": "INACTIVE",
        }
        connection = self.connection(target)

        result = await memberships_service.remove_member(
            connection, uuid4(), uuid4(), target["id"]
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class LeaveHouseholdTests(unittest.IsolatedAsyncioTestCase):
    def connection(self, role="MEMBER"):
        def on_fetchrow(query, *args):
            if "FROM households" in query:
                return household_row()
            if "FROM household_members" in query:
                return {"id": uuid4(), "role": role}
            raise AssertionError(f"unexpected query: {query}")

        return FakeConnection(on_fetchrow=on_fetchrow, on_fetchval=lambda *a: created_at())

    async def test_member_leaves_the_household(self):
        connection = self.connection(role="MEMBER")

        result = await memberships_service.leave_household(
            connection, uuid4(), uuid4()
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertIn("household_id", result["data"])
        self.assertIn("left_at", result["data"])

        update = connection.fetchval.await_args
        self.assertIn("SET status = 'INACTIVE'", update.args[0])

        audit = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO activity_events" in call.args[0]
        )
        self.assertIn("MEMBER_LEFT", audit.args[0])

    async def test_owner_cannot_leave(self):
        connection = self.connection(role="OWNER")

        result = await memberships_service.leave_household(
            connection, uuid4(), uuid4()
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)
        connection.fetchval.assert_not_awaited()

    async def test_returns_not_found_for_a_missing_household(self):
        connection = FakeConnection(on_fetchrow=lambda *a: None)

        result = await memberships_service.leave_household(
            connection, uuid4(), uuid4()
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class TransferOwnershipTests(unittest.IsolatedAsyncioTestCase):
    def connection(self, target):
        actor = actor_owner()

        def on_fetchrow(query, *args):
            if "FROM households" in query:
                return household_row()
            if "WHERE id = $1 AND household_id = $2" in query:
                return target
            if "FROM household_members" in query:
                return actor
            raise AssertionError(f"unexpected query: {query}")

        return FakeConnection(on_fetchrow=on_fetchrow)

    async def test_transfers_ownership_atomically(self):
        actor_id = uuid4()
        target = {"id": uuid4(), "role": "MEMBER", "status": "ACTIVE"}
        connection = self.connection(target)

        result = await memberships_service.transfer_ownership(
            connection, actor_id, uuid4(), target["id"]
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["data"]["previous_owner_role"], "MEMBER")
        self.assertEqual(result["data"]["new_owner_role"], "OWNER")
        self.assertEqual(result["data"]["new_owner_membership_id"], target["id"])
        self.assertEqual(connection.transactions, 1)

        updates = [
            call
            for call in connection.execute.await_args_list
            if "UPDATE household_members" in call.args[0]
        ]
        self.assertEqual(len(updates), 2)
        self.assertIn("SET role = 'MEMBER'", updates[0].args[0])
        self.assertIn("SET role = 'OWNER'", updates[1].args[0])

        audit = next(
            call
            for call in connection.execute.await_args_list
            if "INSERT INTO activity_events" in call.args[0]
        )
        self.assertIn("OWNERSHIP_TRANSFERRED", audit.args[0])
        metadata = json.loads(audit.args[5])
        self.assertEqual(
            metadata["new_owner_membership_id"], str(target["id"])
        )

    async def test_returns_not_found_for_a_missing_or_cross_house_target(self):
        connection = self.connection(None)

        result = await memberships_service.transfer_ownership(
            connection, uuid4(), uuid4(), uuid4()
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)

    async def test_rejects_transferring_to_another_owner(self):
        target = {"id": uuid4(), "role": "OWNER", "status": "ACTIVE"}
        connection = self.connection(target)

        result = await memberships_service.transfer_ownership(
            connection, uuid4(), uuid4(), target["id"]
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)
        self.assertFalse(
            any(
                "UPDATE household_members" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )


class OwnerMembershipDependencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_the_owner_context(self):
        context = {"user_id": uuid4(), "role": "OWNER"}

        result = await household_dependencies.require_owner_membership(context)

        self.assertEqual(result, context)

    async def test_rejects_a_member_with_forbidden(self):
        with self.assertRaises(HTTPException) as captured:
            await household_dependencies.require_owner_membership(
                {"user_id": uuid4(), "role": "MEMBER"}
            )

        self.assertEqual(captured.exception.status_code, 403)


class MembershipRouteTests(unittest.TestCase):
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
            household_dependencies.require_active_membership
        ] = lambda: {
            "user_id": self.user_id,
            "household_id": self.household_id,
            "membership_id": uuid4(),
            "role": "OWNER",
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

    def test_list_members_uses_the_standard_envelope(self):
        data = {"memberships": []}
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 200,
                "message": "Members retrieved",
                "data": data,
            }
        )

        with patch.object(memberships_service, "list_members", service):
            response = self.client.get(f"/households/{self.household_id}/members")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"message": "Members retrieved", "data": data}
        )
        self.assertEqual(service.await_args.args[1], self.household_id)

    def test_transfer_route_rejects_an_invalid_target_membership_id(self):
        response = self.client.post(
            f"/households/{self.household_id}/ownership-transfer",
            json={"target_membership_id": "not-a-uuid"},
        )

        self.assertEqual(response.status_code, 422)

    def test_leave_route_returns_the_standard_envelope(self):
        left_at = created_at().isoformat()
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 200,
                "message": "Household left",
                "data": {"household_id": self.household_id, "left_at": left_at},
            }
        )

        with patch.object(memberships_service, "leave_household", service):
            response = self.client.post(f"/households/{self.household_id}/leave")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "message": "Household left",
                "data": {"household_id": str(self.household_id), "left_at": left_at},
            },
        )


if __name__ == "__main__":
    unittest.main()
