import json
import unittest
from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.postgresql.postgresql import postgresql
from dependencies import auth
from dependencies import households as household_dependencies
from main import app
from schemas.households import HouseholdCreateRequestModel
from services.households import households_service


class Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self, on_fetchrow=None, on_fetch=None):
        self.fetchrow = AsyncMock(
            side_effect=on_fetchrow if on_fetchrow is not None else (lambda *a: None)
        )
        self.fetch = AsyncMock(
            side_effect=on_fetch if on_fetch is not None else (lambda *a: [])
        )
        self.execute = AsyncMock()
        self.transactions = 0

    def transaction(self):
        self.transactions += 1
        return Transaction()


def created_at():
    return datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def household_row(**overrides):
    row = {
        "id": uuid4(),
        "name": "Casa",
        "timezone": "America/Sao_Paulo",
        "default_due_time": time(20, 0),
        "created_at": created_at(),
    }
    row.update(overrides)

    return row


def joined_row(**overrides):
    row = {
        "id": uuid4(),
        "name": "Casa",
        "timezone": "America/Sao_Paulo",
        "default_due_time": time(20, 0),
        "created_at": created_at(),
        "role": "OWNER",
        "joined_at": created_at(),
        "last_household_id": None,
    }
    row.update(overrides)

    return row


class HouseholdSchemaTests(unittest.TestCase):
    def test_trims_name_and_timezone(self):
        data = HouseholdCreateRequestModel(
            name="  Casa da Praia  ", timezone="  America/Sao_Paulo  "
        )

        self.assertEqual(data.name, "Casa da Praia")
        self.assertEqual(data.timezone, "America/Sao_Paulo")

    def test_rejects_blank_name(self):
        for value in ["", "   ", "\t\n"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                HouseholdCreateRequestModel(name=value, timezone="UTC")

    def test_rejects_name_longer_than_households_column_after_trim(self):
        with self.assertRaises(ValidationError):
            HouseholdCreateRequestModel(name=" " + "a" * 256 + " ", timezone="UTC")

    def test_accepts_name_whose_trimmed_value_is_at_the_limit(self):
        data = HouseholdCreateRequestModel(name=" " + "a" * 255 + " ", timezone="UTC")

        self.assertEqual(data.name, "a" * 255)

    def test_rejects_blank_timezone(self):
        with self.assertRaises(ValidationError):
            HouseholdCreateRequestModel(name="Casa", timezone="   ")

    def test_rejects_timezone_longer_than_households_column(self):
        with self.assertRaises(ValidationError):
            HouseholdCreateRequestModel(name="Casa", timezone="a" * 65)

    def test_rejects_unknown_iana_timezone(self):
        with self.assertRaises(ValidationError):
            HouseholdCreateRequestModel(name="Casa", timezone="Mars/Olympus")

    def test_accepts_iana_timezone_and_validates_against_zoneinfo(self):
        data = HouseholdCreateRequestModel(name="Casa", timezone="Europe/Lisbon")

        self.assertEqual(str(ZoneInfo(data.timezone)), "Europe/Lisbon")


class PayloadFingerprintTests(unittest.TestCase):
    def test_fingerprint_is_deterministic_for_the_normalized_payload(self):
        first = HouseholdCreateRequestModel(name="Casa", timezone="America/Sao_Paulo")
        second = HouseholdCreateRequestModel(
            name="  Casa  ", timezone="America/Sao_Paulo"
        )

        self.assertEqual(
            households_service.payload_fingerprint(first),
            households_service.payload_fingerprint(second),
        )
        self.assertEqual(len(households_service.payload_fingerprint(first)), 64)

    def test_fingerprint_changes_with_the_payload(self):
        first = HouseholdCreateRequestModel(name="Casa", timezone="America/Sao_Paulo")
        second = HouseholdCreateRequestModel(name="Casa", timezone="UTC")

        self.assertNotEqual(
            households_service.payload_fingerprint(first),
            households_service.payload_fingerprint(second),
        )


class CreateHouseholdTests(unittest.IsolatedAsyncioTestCase):
    def create_data(self):
        return HouseholdCreateRequestModel(
            name="  Casa  ", timezone=" America/Sao_Paulo "
        )

    def connection(self):
        joined_at = created_at()

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return None

            if "INSERT INTO households" in query:
                return household_row(id=args[0], name=args[1], timezone=args[2])

            if "INSERT INTO household_members" in query:
                return {"joined_at": joined_at}

            raise AssertionError(f"unexpected query: {query}")

        return FakeConnection(on_fetchrow=on_fetchrow)

    async def test_creates_household_membership_audit_and_idempotency_in_transaction(
        self,
    ):
        user_id = uuid4()
        connection = self.connection()
        data = self.create_data()

        result = await households_service.create_household(
            connection, user_id, data, "key-1"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(result["message"], "Household created")
        household = result["data"]["household"]
        self.assertEqual(household["name"], "Casa")
        self.assertEqual(household["timezone"], "America/Sao_Paulo")
        self.assertEqual(household["default_due_time"], "20:00:00")
        self.assertEqual(household["role"], "OWNER")
        self.assertEqual(
            result["data"]["selected_household_id"], household["id"]
        )
        self.assertEqual(connection.transactions, 1)

        executes = connection.execute.await_args_list
        lock_query, lock_key = executes[0].args
        self.assertIn("pg_advisory_xact_lock", lock_query)
        self.assertEqual(
            lock_key, f"households.create:{user_id}:key-1"
        )

        household_insert = next(
            call
            for call in connection.fetchrow.await_args_list
            if "INSERT INTO households" in call.args[0]
        )
        self.assertEqual(str(household_insert.args[1]), household["id"])
        self.assertEqual(household_insert.args[2], "Casa")
        self.assertEqual(household_insert.args[3], "America/Sao_Paulo")
        self.assertEqual(household_insert.args[4], user_id)

        owner_insert = next(
            call
            for call in connection.fetchrow.await_args_list
            if "INSERT INTO household_members" in call.args[0]
        )
        self.assertIn("'OWNER'", owner_insert.args[0])
        self.assertIn("'ACTIVE'", owner_insert.args[0])

        audit = next(
            call
            for call in executes
            if "INSERT INTO activity_events" in call.args[0]
        )
        self.assertIn("HOUSEHOLD_CREATED", audit.args[0])
        self.assertEqual(
            json.loads(audit.args[5]),
            {"membership_id": str(owner_insert.args[1])},
        )

        selection = next(call for call in executes if "UPDATE users" in call.args[0])
        self.assertEqual(selection.args[1], user_id)
        self.assertEqual(str(selection.args[2]), household["id"])

        record = next(
            call
            for call in executes
            if "INSERT INTO idempotency_records" in call.args[0]
        )
        self.assertIn(
            "ON CONFLICT ON CONSTRAINT uq_idempotency_records_scope",
            record.args[0],
        )
        self.assertEqual(record.args[2], user_id)
        self.assertEqual(record.args[3], "households.create")
        self.assertEqual(record.args[4], "key-1")
        self.assertEqual(record.args[5], households_service.payload_fingerprint(data))
        self.assertEqual(json.loads(record.args[6])["name"], "Casa")
        self.assertEqual(str(record.args[7]), household["id"])
        self.assertEqual(json.loads(record.args[8]), result["data"])

        remaining = (
            record.args[9] - datetime.now(timezone.utc)
        ).total_seconds()
        self.assertAlmostEqual(
            remaining, households_service.IDEMPOTENCY_TTL.total_seconds(), delta=5
        )

    async def test_replays_original_response_without_new_writes(self):
        user_id = uuid4()
        data = HouseholdCreateRequestModel(name="Casa", timezone="UTC")
        original = {
            "household": {
                "id": str(uuid4()),
                "name": "Casa",
                "timezone": "UTC",
                "default_due_time": "20:00:00",
                "role": "OWNER",
                "joined_at": created_at().isoformat(),
                "created_at": created_at().isoformat(),
            },
            "selected_household_id": str(uuid4()),
        }

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return {
                    "fingerprint": households_service.payload_fingerprint(data),
                    "response_status": 201,
                    "response_data": json.dumps(original),
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await households_service.create_household(
            connection, user_id, data, "key-1"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(result["message"], "Household created")
        self.assertEqual(result["data"], original)
        self.assertEqual(connection.transactions, 1)
        self.assertEqual(connection.fetchrow.await_count, 1)
        self.assertEqual(connection.execute.await_count, 1)
        self.assertIn(
            "pg_advisory_xact_lock", connection.execute.await_args.args[0]
        )
        self.assertFalse(
            any(
                "INSERT" in call.args[0] or "UPDATE" in call.args[0]
                for call in connection.execute.await_args_list
            )
        )

    async def test_conflicts_when_key_is_reused_with_a_different_payload(self):
        user_id = uuid4()
        data = HouseholdCreateRequestModel(name="Casa", timezone="UTC")

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return {
                    "fingerprint": "0" * 64,
                    "response_status": 201,
                    "response_data": "{}",
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await households_service.create_household(
            connection, user_id, data, "key-1"
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)
        self.assertEqual(result["data"], {})
        self.assertEqual(connection.fetchrow.await_count, 1)
        self.assertEqual(connection.execute.await_count, 1)

    async def test_replaces_an_expired_record_with_a_new_household(self):
        user_id = uuid4()
        data = HouseholdCreateRequestModel(name="Casa", timezone="UTC")

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return {
                    "fingerprint": households_service.payload_fingerprint(data),
                    "response_status": 201,
                    "response_data": "{}",
                    "expires_at": datetime.now(timezone.utc) - timedelta(minutes=1),
                }

            if "INSERT INTO households" in query:
                return household_row(id=args[0], name=args[1], timezone=args[2])

            if "INSERT INTO household_members" in query:
                return {"joined_at": created_at()}

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await households_service.create_household(
            connection, user_id, data, "key-1"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(connection.transactions, 1)
        self.assertTrue(
            any(
                "ON CONFLICT ON CONSTRAINT uq_idempotency_records_scope"
                in call.args[0]
                for call in connection.execute.await_args_list
            )
        )


class ListHouseholdsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_empty_list_and_no_selection_without_memberships(self):
        user_id = uuid4()

        def on_fetch(query, *args):
            self.assertIn("hm.status = 'ACTIVE'", query)
            self.assertIn("h.deactivated_at IS NULL", query)
            self.assertIn("ORDER BY hm.joined_at DESC, h.id", query)
            self.assertEqual(args[0], user_id)
            return []

        connection = FakeConnection(on_fetch=on_fetch)

        result = await households_service.list_households(connection, user_id)

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["message"], "Households retrieved")
        self.assertEqual(
            result["data"], {"households": [], "selected_household_id": None}
        )
        connection.execute.assert_not_awaited()

    async def test_selects_the_only_active_household(self):
        user_id = uuid4()
        row = joined_row(last_household_id=None)
        connection = FakeConnection(on_fetch=lambda *a: [row])

        result = await households_service.list_households(connection, user_id)

        self.assertEqual(result["data"]["selected_household_id"], row["id"])
        self.assertEqual(len(result["data"]["households"]), 1)
        self.assertEqual(result["data"]["households"][0]["id"], str(row["id"]))
        self.assertEqual(result["data"]["households"][0]["role"], "OWNER")

    async def test_prefers_the_last_household_when_it_is_authorized(self):
        user_id = uuid4()
        newest = joined_row(joined_at=datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc))
        older = joined_row(joined_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc))
        newest["last_household_id"] = older["id"]
        older["last_household_id"] = older["id"]
        connection = FakeConnection(on_fetch=lambda *a: [newest, older])

        result = await households_service.list_households(connection, user_id)

        self.assertEqual(result["data"]["selected_household_id"], older["id"])

    async def test_falls_back_to_most_recent_join_when_last_household_is_missing(self):
        user_id = uuid4()
        newest = joined_row(joined_at=datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc))
        older = joined_row(joined_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc))
        connection = FakeConnection(on_fetch=lambda *a: [newest, older])

        result = await households_service.list_households(connection, user_id)

        self.assertEqual(result["data"]["selected_household_id"], newest["id"])

    async def test_falls_back_when_last_household_is_not_authorized(self):
        user_id = uuid4()
        newest = joined_row(joined_at=datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc))
        older = joined_row(joined_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc))
        newest["last_household_id"] = uuid4()
        older["last_household_id"] = newest["last_household_id"]
        connection = FakeConnection(on_fetch=lambda *a: [newest, older])

        result = await households_service.list_households(connection, user_id)

        self.assertEqual(result["data"]["selected_household_id"], newest["id"])


class SelectHouseholdTests(unittest.IsolatedAsyncioTestCase):
    async def test_persists_selection_and_returns_it(self):
        user_id = uuid4()
        household_id = uuid4()
        connection = FakeConnection(
            on_fetchrow=lambda *a: {"last_household_id": household_id}
        )

        result = await households_service.select_household(
            connection, user_id, household_id
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["message"], "Household selected")
        self.assertEqual(result["data"], {"selected_household_id": household_id})
        query, parameter_user_id, parameter_household_id = (
            connection.fetchrow.await_args.args
        )
        self.assertIn("UPDATE users", query)
        self.assertIn("last_household_id = $2", query)
        self.assertEqual(parameter_user_id, user_id)
        self.assertEqual(parameter_household_id, household_id)

    async def test_returns_not_found_for_missing_user(self):
        connection = FakeConnection(on_fetchrow=lambda *a: None)

        result = await households_service.select_household(
            connection, uuid4(), uuid4()
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class IdempotencyKeyDependencyTests(unittest.TestCase):
    def test_trims_a_valid_header(self):
        self.assertEqual(
            household_dependencies.require_idempotency_key("  key-1  "), "key-1"
        )

    def test_rejects_blank_header(self):
        with self.assertRaises(HTTPException) as context:
            household_dependencies.require_idempotency_key("   ")

        self.assertEqual(context.exception.status_code, 422)

    def test_rejects_header_longer_than_255_characters(self):
        with self.assertRaises(HTTPException) as context:
            household_dependencies.require_idempotency_key("a" * 256)

        self.assertEqual(context.exception.status_code, 422)


class ActiveMembershipDependencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_minimal_context_for_active_member(self):
        user_id = uuid4()
        household_id = uuid4()
        membership_id = uuid4()
        connection = FakeConnection(
            on_fetchrow=lambda *a: {
                "household_id": household_id,
                "deactivated_at": None,
                "membership_id": membership_id,
                "role": "OWNER",
            }
        )

        context = await household_dependencies.require_active_membership(
            household_id, {"id": user_id}, connection
        )

        self.assertEqual(
            context,
            {
                "user_id": user_id,
                "household_id": household_id,
                "membership_id": membership_id,
                "role": "OWNER",
            },
        )
        query, parameter_household_id, parameter_user_id = (
            connection.fetchrow.await_args.args
        )
        self.assertIn("hm.status = 'ACTIVE'", query)
        self.assertEqual(parameter_household_id, household_id)
        self.assertEqual(parameter_user_id, user_id)

    async def test_rejects_missing_household_with_not_found(self):
        connection = FakeConnection(on_fetchrow=lambda *a: None)

        with self.assertRaises(HTTPException) as context:
            await household_dependencies.require_active_membership(
                uuid4(), {"id": uuid4()}, connection
            )

        self.assertEqual(context.exception.status_code, 404)

    async def test_rejects_deactivated_household_with_conflict(self):
        connection = FakeConnection(
            on_fetchrow=lambda *a: {
                "household_id": uuid4(),
                "deactivated_at": datetime.now(timezone.utc),
                "membership_id": None,
                "role": None,
            }
        )

        with self.assertRaises(HTTPException) as context:
            await household_dependencies.require_active_membership(
                uuid4(), {"id": uuid4()}, connection
            )

        self.assertEqual(context.exception.status_code, 409)

    async def test_rejects_inactive_membership_with_forbidden(self):
        connection = FakeConnection(
            on_fetchrow=lambda *a: {
                "household_id": uuid4(),
                "deactivated_at": None,
                "membership_id": None,
                "role": None,
            }
        )

        with self.assertRaises(HTTPException) as context:
            await household_dependencies.require_active_membership(
                uuid4(), {"id": uuid4()}, connection
            )

        self.assertEqual(context.exception.status_code, 403)


class HouseholdRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = uuid4()
        self.connection = FakeConnection(
            on_fetchrow=lambda *a: None, on_fetch=lambda *a: []
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

    def test_create_requires_idempotency_key_header(self):
        response = self.client.post(
            "/households", json={"name": "Casa", "timezone": "UTC"}
        )

        self.assertEqual(response.status_code, 422)

    def test_create_rejects_a_blank_idempotency_key_header(self):
        response = self.client.post(
            "/households",
            json={"name": "Casa", "timezone": "UTC"},
            headers={"Idempotency-Key": "   "},
        )

        self.assertEqual(response.status_code, 422)

    def test_create_rejects_an_oversized_idempotency_key_header(self):
        response = self.client.post(
            "/households",
            json={"name": "Casa", "timezone": "UTC"},
            headers={"Idempotency-Key": "a" * 256},
        )

        self.assertEqual(response.status_code, 422)

    def test_create_passes_the_trimmed_key_to_the_service(self):
        household_id = uuid4()
        data = {
            "household": {
                "id": str(household_id),
                "name": "Casa",
                "timezone": "UTC",
                "default_due_time": "20:00:00",
                "role": "OWNER",
                "joined_at": created_at().isoformat(),
                "created_at": created_at().isoformat(),
            },
            "selected_household_id": str(household_id),
        }
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 201,
                "message": "Household created",
                "data": data,
            }
        )

        with patch.object(households_service, "create_household", service):
            response = self.client.post(
                "/households",
                json={"name": "  Casa  ", "timezone": "UTC"},
                headers={"Idempotency-Key": "  key-1  "},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(), {"message": "Household created", "data": data}
        )
        call = service.await_args
        self.assertEqual(call.args[1], self.user_id)
        self.assertEqual(call.args[3], "key-1")

    def test_get_returns_the_standard_envelope(self):
        data = {"households": [], "selected_household_id": None}
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 200,
                "message": "Households retrieved",
                "data": data,
            }
        )

        with patch.object(households_service, "list_households", service):
            response = self.client.get("/households")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"message": "Households retrieved", "data": data}
        )
        self.assertEqual(service.await_args.args[1], self.user_id)

    def test_selection_route_uses_the_membership_dependency(self):
        household_id = uuid4()
        app.dependency_overrides[
            household_dependencies.require_active_membership
        ] = lambda: {
            "user_id": self.user_id,
            "household_id": household_id,
            "membership_id": uuid4(),
            "role": "OWNER",
        }
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 200,
                "message": "Household selected",
                "data": {"selected_household_id": household_id},
            }
        )

        with patch.object(households_service, "select_household", service):
            response = self.client.patch(f"/households/{household_id}/selection")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "message": "Household selected",
                "data": {"selected_household_id": str(household_id)},
            },
        )
        call = service.await_args
        self.assertEqual(call.args[1], self.user_id)
        self.assertEqual(call.args[2], household_id)

    def test_selection_route_rejects_an_invalid_household_id(self):
        response = self.client.patch("/households/not-a-uuid/selection")

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
