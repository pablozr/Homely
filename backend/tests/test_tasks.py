import importlib.util
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.postgresql.postgresql import postgresql
from dependencies import auth
from dependencies import households as household_dependencies
from main import app
from schemas.tasks import (
    TaskCreateRequestModel,
    TaskUpdateRequestModel,
    task_from_row,
)
from services.tasks import tasks_service


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "0006_tasks_and_occurrences.py"
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
    return datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)


def future_due_local():
    return "2030-01-01T10:00"


def past_due_local():
    return "2000-01-01T10:00"


def occurrence_row(**overrides):
    row = {
        "occurrence_id": uuid4(),
        "task_id": uuid4(),
        "household_id": uuid4(),
        "title": "Lavar roupa",
        "status": "PENDING",
        "assignee_membership_id": None,
        "due_at": None,
        "due_timezone": None,
        "created_by": uuid4(),
        "created_at": created_at(),
        "updated_at": created_at(),
        "cancelled_at": None,
        "cancelled_by": None,
        "assignee_user_id": None,
        "assignee_fullname": None,
    }
    row.update(overrides)

    return row


def task_data(**overrides):
    occurrence_id = overrides.pop("occurrence_id", uuid4())
    data = {
        "id": str(occurrence_id),
        "occurrence_id": str(occurrence_id),
        "task_id": str(uuid4()),
        "household_id": str(uuid4()),
        "title": "Lavar roupa",
        "status": "PENDING",
        "assignee": None,
        "due_at": None,
        "due_timezone": None,
        "due_local": None,
        "is_overdue": False,
        "created_by": str(uuid4()),
        "created_at": created_at().isoformat(),
        "updated_at": created_at().isoformat(),
        "cancelled_at": None,
        "cancelled_by": None,
    }
    data.update(overrides)

    return data


def executed_args(connection, marker):
    return [
        call.args
        for call in connection.execute.await_args_list
        if marker in call.args[0]
    ]


class TaskCreateSchemaTests(unittest.TestCase):
    def test_trims_title_and_accepts_optional_fields(self):
        data = TaskCreateRequestModel(
            title="  Lavar roupa  ",
            assignee_membership_id=None,
            due_local="2030-01-01T10:00",
        )

        self.assertEqual(data.title, "Lavar roupa")
        self.assertIsNone(data.assignee_membership_id)
        self.assertEqual(data.due_local, "2030-01-01T10:00")

    def test_rejects_blank_and_oversized_titles(self):
        for value in ["", "   ", "\t\n"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                TaskCreateRequestModel(title=value)

        with self.assertRaises(ValidationError):
            TaskCreateRequestModel(title="a" * 256)

    def test_rejects_null_title(self):
        with self.assertRaises(ValidationError):
            TaskCreateRequestModel(title=None)

    def test_rejects_due_local_with_offset_or_z(self):
        for value in [
            "2030-01-01T10:00Z",
            "2030-01-01T10:00+03:00",
            "2030-01-01T10:00:00",
            "2030-01-01T10:00-03:00",
        ]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                TaskCreateRequestModel(title="Tarefa", due_local=value)

    def test_rejects_impossible_civil_dates(self):
        with self.assertRaises(ValidationError):
            TaskCreateRequestModel(title="Tarefa", due_local="2030-02-30T10:00")


class TaskUpdateSchemaTests(unittest.TestCase):
    def test_requires_at_least_one_field(self):
        with self.assertRaises(ValidationError):
            TaskUpdateRequestModel()

    def test_rejects_null_title_but_accepts_omission(self):
        with self.assertRaises(ValidationError):
            TaskUpdateRequestModel(title=None)

        data = TaskUpdateRequestModel(assignee_membership_id=None)

        self.assertIn("assignee_membership_id", data.model_fields_set)
        self.assertNotIn("title", data.model_fields_set)

    def test_rejects_blank_title(self):
        with self.assertRaises(ValidationError):
            TaskUpdateRequestModel(title="   ")

    def test_allows_clearing_assignee_and_due(self):
        data = TaskUpdateRequestModel(
            assignee_membership_id=None, due_local=None
        )

        self.assertEqual(
            data.model_fields_set, {"assignee_membership_id", "due_local"}
        )


class DueLocalTimezoneTests(unittest.TestCase):
    def test_parses_civil_due_local_in_household_timezone(self):
        resolved = tasks_service.parse_due_local(
            "2030-01-01T10:00", "America/Sao_Paulo"
        )

        self.assertEqual(
            resolved, datetime(2030, 1, 1, 13, 0, tzinfo=timezone.utc)
        )

    def test_advances_nonexistent_dst_time_to_next_valid_minute(self):
        resolved = tasks_service.parse_due_local(
            "2026-03-08T02:30", "America/New_York"
        )

        self.assertEqual(
            resolved, datetime(2026, 3, 8, 7, 0, tzinfo=timezone.utc)
        )

    def test_uses_first_occurrence_for_ambiguous_dst_time(self):
        resolved = tasks_service.parse_due_local(
            "2026-11-01T01:30", "America/New_York"
        )

        self.assertEqual(
            resolved, datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)
        )


class TaskFingerprintTests(unittest.TestCase):
    def test_is_deterministic_and_sensitive_to_the_payload(self):
        first = TaskCreateRequestModel(title="Tarefa", due_local="2030-01-01T10:00")
        second = TaskCreateRequestModel(
            title="  Tarefa  ", due_local="2030-01-01T10:00"
        )
        different = TaskCreateRequestModel(title="Tarefa")

        self.assertEqual(
            tasks_service.payload_fingerprint(first),
            tasks_service.payload_fingerprint(second),
        )
        self.assertEqual(len(tasks_service.payload_fingerprint(first)), 64)
        self.assertNotEqual(
            tasks_service.payload_fingerprint(first),
            tasks_service.payload_fingerprint(different),
        )


class TaskRowRepresentationTests(unittest.TestCase):
    def test_derives_due_local_overdue_and_assignee(self):
        membership_id = uuid4()
        user_id = uuid4()
        due_at = datetime(2030, 1, 1, 13, 0, tzinfo=timezone.utc)
        row = occurrence_row(
            assignee_membership_id=membership_id,
            assignee_user_id=user_id,
            assignee_fullname="Ana Souza",
            due_at=due_at,
            due_timezone="America/Sao_Paulo",
        )

        task = task_from_row(row, now=datetime(2026, 9, 19, tzinfo=timezone.utc))

        self.assertEqual(task["due_at"], due_at.isoformat())
        self.assertEqual(task["due_local"], "2030-01-01T10:00")
        self.assertEqual(task["due_timezone"], "America/Sao_Paulo")
        self.assertFalse(task["is_overdue"])
        self.assertEqual(task["assignee"]["membership_id"], str(membership_id))
        self.assertEqual(task["assignee"]["user_id"], str(user_id))
        self.assertEqual(task["assignee"]["fullname"], "Ana Souza")

    def test_marks_pending_past_due_as_overdue(self):
        row = occurrence_row(
            due_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            due_timezone="UTC",
        )

        task = task_from_row(row, now=datetime(2026, 9, 19, tzinfo=timezone.utc))

        self.assertTrue(task["is_overdue"])
        self.assertEqual(task["due_local"], "2026-01-01T00:00")


class CreateTaskTests(unittest.IsolatedAsyncioTestCase):
    async def test_creates_task_occurrence_audit_and_idempotency(self):
        user_id = uuid4()
        household_id = uuid4()
        assignee = {
            "membership_id": uuid4(),
            "user_id": uuid4(),
            "fullname": "Ana Souza",
        }

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return None
            if "FROM households" in query:
                return {"id": household_id, "deactivated_at": None}
            if "SELECT id, role" in query and "FROM household_members" in query:
                return {"id": uuid4(), "role": "MEMBER"}
            if "AS membership_id" in query:
                return assignee
            if "FROM task_occurrences o" in query:
                occurrence_insert = executed_args(
                    connection, "INSERT INTO task_occurrences"
                )[-1]
                task_insert = executed_args(connection, "INSERT INTO tasks")[-1]
                return occurrence_row(
                    occurrence_id=occurrence_insert[1],
                    task_id=task_insert[1],
                    household_id=occurrence_insert[3],
                    assignee_membership_id=occurrence_insert[4],
                    due_at=occurrence_insert[5],
                    due_timezone=occurrence_insert[6],
                    created_by=occurrence_insert[7],
                    assignee_user_id=assignee["user_id"],
                    assignee_fullname=assignee["fullname"],
                )

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)
        connection.fetchval.side_effect = lambda *a: "America/Sao_Paulo"

        data = TaskCreateRequestModel(
            title="  Lavar roupa  ",
            assignee_membership_id=assignee["membership_id"],
            due_local=future_due_local(),
        )

        result = await tasks_service.create_task(
            connection, user_id, household_id, data, "key-1"
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(result["message"], "Task created")
        self.assertEqual(connection.transactions, 1)

        task = result["data"]["task"]
        self.assertEqual(task["title"], "Lavar roupa")
        self.assertEqual(task["status"], "PENDING")
        self.assertEqual(task["household_id"], str(household_id))
        self.assertEqual(task["due_timezone"], "America/Sao_Paulo")
        self.assertEqual(task["due_local"], future_due_local())
        self.assertEqual(
            task["due_at"],
            tasks_service.parse_due_local(
                future_due_local(), "America/Sao_Paulo"
            ).isoformat(),
        )
        self.assertEqual(
            task["assignee"],
            {
                "membership_id": str(assignee["membership_id"]),
                "user_id": str(assignee["user_id"]),
                "fullname": "Ana Souza",
            },
        )
        self.assertFalse(task["is_overdue"])

        lock = connection.execute.await_args_list[0].args
        self.assertIn("pg_advisory_xact_lock", lock[0])
        self.assertEqual(
            lock[1], f"tasks.create:{household_id}:key-1"
        )

        task_insert = executed_args(connection, "INSERT INTO tasks")[0]
        self.assertEqual(str(task_insert[1]), task["task_id"])
        self.assertEqual(task_insert[2], household_id)
        self.assertEqual(task_insert[3], "Lavar roupa")
        self.assertEqual(task_insert[4], user_id)

        occurrence_insert = executed_args(connection, "INSERT INTO task_occurrences")[0]
        self.assertIn("'PENDING'", occurrence_insert[0])
        self.assertEqual(str(occurrence_insert[1]), task["id"])
        self.assertEqual(str(occurrence_insert[2]), task["task_id"])

        audit = executed_args(connection, "INSERT INTO activity_events")[0]
        self.assertIn("task_occurrence", audit[0])
        self.assertEqual(audit[5], "TASK_CREATED")
        self.assertEqual(json.loads(audit[6])["occurrence_id"], task["id"])

        record_args = executed_args(connection, "INSERT INTO idempotency_records")[0]
        self.assertIn(
            "ON CONFLICT ON CONSTRAINT uq_idempotency_records_scope",
            record_args[0],
        )
        self.assertEqual(record_args[2], user_id)
        self.assertEqual(record_args[3], household_id)
        self.assertEqual(record_args[4], "tasks.create")
        self.assertEqual(record_args[5], "key-1")
        self.assertEqual(
            record_args[6], tasks_service.payload_fingerprint(data)
        )
        self.assertEqual(str(record_args[8]), task["id"])
        self.assertEqual(json.loads(record_args[9]), {"task": task})

    async def test_creates_a_task_without_due_or_assignee(self):
        user_id = uuid4()
        household_id = uuid4()

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return None
            if "FROM households" in query:
                return {"id": household_id, "deactivated_at": None}
            if "SELECT id, role" in query:
                return {"id": uuid4(), "role": "OWNER"}
            if "FROM task_occurrences o" in query:
                occurrence_insert = executed_args(
                    connection, "INSERT INTO task_occurrences"
                )[-1]
                task_insert = executed_args(connection, "INSERT INTO tasks")[-1]
                return occurrence_row(
                    occurrence_id=occurrence_insert[1],
                    task_id=task_insert[1],
                    household_id=occurrence_insert[3],
                    created_by=occurrence_insert[7],
                )

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await tasks_service.create_task(
            connection,
            user_id,
            household_id,
            TaskCreateRequestModel(title="Tarefa"),
            "key-2",
        )

        self.assertTrue(result["status"])
        task = result["data"]["task"]
        self.assertIsNone(task["due_at"])
        self.assertIsNone(task["due_timezone"])
        self.assertIsNone(task["due_local"])
        self.assertIsNone(task["assignee"])
        connection.fetchval.assert_not_awaited()

    async def test_replays_the_original_response_without_new_writes(self):
        user_id = uuid4()
        household_id = uuid4()
        stored_task = task_data()
        record = {
            "fingerprint": tasks_service.payload_fingerprint(
                TaskCreateRequestModel(title="Lavar roupa")
            ),
            "response_status": 201,
            "response_data": json.dumps({"task": stored_task}),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        connection = FakeConnection(on_fetchrow=lambda *a: record)

        result = await tasks_service.create_task(
            connection,
            user_id,
            household_id,
            TaskCreateRequestModel(title="Lavar roupa"),
            "key-1",
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(result["data"]["task"]["id"], stored_task["id"])
        self.assertEqual(connection.fetchrow.await_count, 1)
        self.assertEqual(connection.execute.await_count, 1)
        self.assertIn(
            "pg_advisory_xact_lock", connection.execute.await_args.args[0]
        )

    async def test_conflicts_when_the_key_is_reused_with_a_different_payload(self):
        record = {
            "fingerprint": "0" * 64,
            "response_status": 201,
            "response_data": "{}",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        connection = FakeConnection(on_fetchrow=lambda *a: record)

        result = await tasks_service.create_task(
            connection,
            uuid4(),
            uuid4(),
            TaskCreateRequestModel(title="Lavar roupa"),
            "key-1",
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)
        self.assertEqual(connection.fetchrow.await_count, 1)

    async def test_rejects_a_due_in_the_past(self):
        user_id = uuid4()
        household_id = uuid4()

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return None
            if "FROM households" in query:
                return {"id": household_id, "deactivated_at": None}
            if "SELECT id, role" in query:
                return {"id": uuid4(), "role": "MEMBER"}

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)
        connection.fetchval.side_effect = lambda *a: "America/Sao_Paulo"

        result = await tasks_service.create_task(
            connection,
            user_id,
            household_id,
            TaskCreateRequestModel(title="Tarefa", due_local=past_due_local()),
            "key-1",
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 400)
        self.assertFalse(any("INSERT INTO tasks" in args[0] for args in executed_args(connection, "INSERT")))

    async def test_rejects_an_inactive_or_cross_house_assignee(self):
        user_id = uuid4()
        household_id = uuid4()

        def on_fetchrow(query, *args):
            if "FROM idempotency_records" in query:
                return None
            if "FROM households" in query:
                return {"id": household_id, "deactivated_at": None}
            if "SELECT id, role" in query:
                return {"id": uuid4(), "role": "MEMBER"}
            if "AS membership_id" in query:
                return None

            raise AssertionError(f"unexpected query: {query}")

        connection = FakeConnection(on_fetchrow=on_fetchrow)

        result = await tasks_service.create_task(
            connection,
            user_id,
            household_id,
            TaskCreateRequestModel(
                title="Tarefa", assignee_membership_id=uuid4()
            ),
            "key-1",
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 400)
        self.assertFalse(executed_args(connection, "INSERT INTO tasks"))

    async def test_propagates_household_and_membership_errors(self):
        cases = [
            (None, 404),
            ({"id": uuid4(), "deactivated_at": datetime.now(timezone.utc)}, 409),
            ({"id": uuid4(), "deactivated_at": None}, 403),
        ]

        for household, expected in cases:
            with self.subTest(expected=expected):
                membership = None if expected == 403 else {"id": uuid4(), "role": "MEMBER"}

                def on_fetchrow(query, *args):
                    if "FROM idempotency_records" in query:
                        return None
                    if "FROM households" in query:
                        return household
                    if "SELECT id, role" in query:
                        return membership

                    raise AssertionError(f"unexpected query: {query}")

                connection = FakeConnection(on_fetchrow=on_fetchrow)

                result = await tasks_service.create_task(
                    connection,
                    uuid4(),
                    uuid4(),
                    TaskCreateRequestModel(title="Tarefa"),
                    "key-1",
                )

                self.assertFalse(result["status"])
                self.assertEqual(result["status_code"], expected)


class ListTasksTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_pending_tasks_in_priority_order(self):
        household_id = uuid4()
        overdue = occurrence_row(
            household_id=household_id,
            due_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            due_timezone="UTC",
        )
        no_due = occurrence_row(household_id=household_id)

        def on_fetch(query, *args):
            self.assertIn("o.status = 'PENDING'", query)
            self.assertIn(
                "ORDER BY o.due_at ASC NULLS LAST, o.created_at ASC, o.id ASC",
                query,
            )
            self.assertEqual(args[0], household_id)
            return [overdue, no_due]

        connection = FakeConnection(on_fetch=on_fetch)

        result = await tasks_service.list_tasks(connection, household_id)

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["message"], "Tasks retrieved")
        self.assertEqual(len(result["data"]["tasks"]), 2)
        self.assertTrue(result["data"]["tasks"][0]["is_overdue"])
        self.assertIsNone(result["data"]["tasks"][1]["due_at"])

    async def test_returns_an_empty_list(self):
        connection = FakeConnection(on_fetch=lambda *a: [])

        result = await tasks_service.list_tasks(connection, uuid4())

        self.assertEqual(result["data"], {"tasks": []})


class UpdateTaskTests(unittest.IsolatedAsyncioTestCase):
    def connection(
        self,
        occurrence,
        task,
        representation,
        *,
        assignee=None,
        household=None,
        membership=None,
    ):
        connection = FakeConnection()

        def on_fetchrow(query, *args):
            if "SELECT id, deactivated_at FROM households" in query:
                return household if household is not None else {"id": uuid4(), "deactivated_at": None}
            if "SELECT id, role" in query:
                return membership if membership is not None else {"id": uuid4(), "role": "MEMBER"}
            if "FROM task_occurrences" in query and "FOR UPDATE" in query:
                return occurrence
            if "FROM tasks" in query and "FOR UPDATE" in query:
                return task
            if "AS membership_id" in query:
                return assignee
            if "FROM task_occurrences o" in query:
                return representation

            raise AssertionError(f"unexpected query: {query}")

        connection.fetchrow.side_effect = on_fetchrow

        return connection

    async def test_updates_title_and_clears_assignee_and_due(self):
        user_id = uuid4()
        household_id = uuid4()
        occurrence = {
            "id": uuid4(),
            "task_id": uuid4(),
            "status": "PENDING",
            "assignee_membership_id": uuid4(),
            "due_at": datetime(2030, 1, 1, tzinfo=timezone.utc),
            "due_timezone": "UTC",
        }
        task = {"id": occurrence["task_id"], "title": "Antigo"}
        representation = occurrence_row(
            occurrence_id=occurrence["id"],
            task_id=occurrence["task_id"],
            household_id=household_id,
            title="Novo",
        )
        connection = self.connection(occurrence, task, representation)

        data = TaskUpdateRequestModel(
            title="  Novo  ", assignee_membership_id=None, due_local=None
        )

        result = await tasks_service.update_task(
            connection, user_id, household_id, occurrence["id"], data
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["message"], "Task updated")
        self.assertEqual(connection.transactions, 1)

        task_update = executed_args(connection, "UPDATE tasks")[0]
        self.assertEqual(task_update[1], occurrence["task_id"])
        self.assertEqual(task_update[2], "Novo")
        self.assertEqual(task_update[3], household_id)

        occurrence_update = executed_args(connection, "UPDATE task_occurrences")[0]
        self.assertIsNone(occurrence_update[2])
        self.assertIsNone(occurrence_update[3])
        self.assertIsNone(occurrence_update[4])

        audit = executed_args(connection, "INSERT INTO activity_events")[0]
        self.assertEqual(audit[5], "TASK_UPDATED")
        self.assertEqual(
            json.loads(audit[6])["fields"],
            ["assignee_membership_id", "due_local", "title"],
        )

    async def test_keeps_omitted_fields_unchanged(self):
        user_id = uuid4()
        household_id = uuid4()
        assignee_membership_id = uuid4()
        due_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
        occurrence = {
            "id": uuid4(),
            "task_id": uuid4(),
            "status": "PENDING",
            "assignee_membership_id": assignee_membership_id,
            "due_at": due_at,
            "due_timezone": "UTC",
        }
        task = {"id": occurrence["task_id"], "title": "Antigo"}
        representation = occurrence_row(
            occurrence_id=occurrence["id"],
            task_id=occurrence["task_id"],
            household_id=household_id,
            title="Novo",
            assignee_membership_id=assignee_membership_id,
            due_at=due_at,
            due_timezone="UTC",
        )
        connection = self.connection(occurrence, task, representation)

        result = await tasks_service.update_task(
            connection,
            user_id,
            household_id,
            occurrence["id"],
            TaskUpdateRequestModel(title="Novo"),
        )

        self.assertEqual(result["status_code"], 200)
        occurrence_update = executed_args(connection, "UPDATE task_occurrences")[0]
        self.assertEqual(occurrence_update[2], assignee_membership_id)
        self.assertEqual(occurrence_update[3], due_at)

    async def test_revalidates_a_new_assignee(self):
        user_id = uuid4()
        household_id = uuid4()
        assignee = {
            "membership_id": uuid4(),
            "user_id": uuid4(),
            "fullname": "Ana Souza",
        }
        occurrence = {
            "id": uuid4(),
            "task_id": uuid4(),
            "status": "PENDING",
            "assignee_membership_id": None,
            "due_at": None,
            "due_timezone": None,
        }
        task = {"id": occurrence["task_id"], "title": "Tarefa"}
        representation = occurrence_row(
            occurrence_id=occurrence["id"],
            task_id=occurrence["task_id"],
            household_id=household_id,
            assignee_membership_id=assignee["membership_id"],
            assignee_user_id=assignee["user_id"],
            assignee_fullname=assignee["fullname"],
        )
        connection = self.connection(
            occurrence, task, representation, assignee=assignee
        )

        result = await tasks_service.update_task(
            connection,
            user_id,
            household_id,
            occurrence["id"],
            TaskUpdateRequestModel(
                assignee_membership_id=assignee["membership_id"]
            ),
        )

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(
            result["data"]["task"]["assignee"]["fullname"], "Ana Souza"
        )

    async def test_rejects_an_invalid_assignee(self):
        occurrence = {
            "id": uuid4(),
            "task_id": uuid4(),
            "status": "PENDING",
            "assignee_membership_id": None,
            "due_at": None,
            "due_timezone": None,
        }
        task = {"id": occurrence["task_id"], "title": "Tarefa"}
        connection = self.connection(
            occurrence, task, occurrence_row(), assignee=None
        )

        result = await tasks_service.update_task(
            connection,
            uuid4(),
            uuid4(),
            occurrence["id"],
            TaskUpdateRequestModel(assignee_membership_id=uuid4()),
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 400)
        self.assertFalse(executed_args(connection, "UPDATE tasks"))

    async def test_rejects_a_due_in_the_past(self):
        occurrence = {
            "id": uuid4(),
            "task_id": uuid4(),
            "status": "PENDING",
            "assignee_membership_id": None,
            "due_at": None,
            "due_timezone": None,
        }
        task = {"id": occurrence["task_id"], "title": "Tarefa"}
        connection = self.connection(occurrence, task, occurrence_row())
        connection.fetchval.side_effect = lambda *a: "America/Sao_Paulo"

        result = await tasks_service.update_task(
            connection,
            uuid4(),
            uuid4(),
            occurrence["id"],
            TaskUpdateRequestModel(due_local=past_due_local()),
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 400)
        self.assertFalse(executed_args(connection, "UPDATE tasks"))

    async def test_rejects_editing_a_task_that_is_not_pending(self):
        occurrence = {
            "id": uuid4(),
            "task_id": uuid4(),
            "status": "DONE",
            "assignee_membership_id": None,
            "due_at": None,
            "due_timezone": None,
        }
        task = {"id": occurrence["task_id"], "title": "Tarefa"}
        connection = self.connection(occurrence, task, occurrence_row())

        result = await tasks_service.update_task(
            connection,
            uuid4(),
            uuid4(),
            occurrence["id"],
            TaskUpdateRequestModel(title="Outra"),
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)
        self.assertFalse(executed_args(connection, "UPDATE tasks"))

    async def test_returns_not_found_for_an_unknown_occurrence(self):
        connection = self.connection(None, None, occurrence_row())

        result = await tasks_service.update_task(
            connection,
            uuid4(),
            uuid4(),
            uuid4(),
            TaskUpdateRequestModel(title="Outra"),
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class CancelTaskTests(unittest.IsolatedAsyncioTestCase):
    def connection(self, occurrence, representation):
        connection = FakeConnection()

        def on_fetchrow(query, *args):
            if "SELECT id, deactivated_at FROM households" in query:
                return {"id": uuid4(), "deactivated_at": None}
            if "SELECT id, role" in query:
                return {"id": uuid4(), "role": "MEMBER"}
            if "SELECT id, task_id, status" in query:
                return occurrence
            if "FROM task_occurrences o" in query:
                return representation

            raise AssertionError(f"unexpected query: {query}")

        connection.fetchrow.side_effect = on_fetchrow

        return connection

    async def test_cancels_a_pending_task_and_records_audit(self):
        user_id = uuid4()
        household_id = uuid4()
        occurrence = {"id": uuid4(), "task_id": uuid4(), "status": "PENDING"}
        representation = occurrence_row(
            occurrence_id=occurrence["id"],
            task_id=occurrence["task_id"],
            household_id=household_id,
            status="CANCELLED",
            cancelled_at=created_at(),
            cancelled_by=user_id,
        )
        connection = self.connection(occurrence, representation)

        result = await tasks_service.cancel_task(
            connection, user_id, household_id, occurrence["id"]
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["message"], "Task cancelled")
        self.assertEqual(result["data"]["task"]["status"], "CANCELLED")
        self.assertEqual(
            result["data"]["task"]["cancelled_by"], str(user_id)
        )

        update = executed_args(connection, "UPDATE task_occurrences")[0]
        self.assertIn("status = 'CANCELLED'", update[0])
        self.assertEqual(update[1], occurrence["id"])
        self.assertEqual(update[3], user_id)

        audit = executed_args(connection, "INSERT INTO activity_events")[0]
        self.assertEqual(audit[5], "TASK_CANCELLED")

    async def test_repeated_cancellation_returns_same_without_audit(self):
        user_id = uuid4()
        household_id = uuid4()
        cancelled_at = datetime.now(timezone.utc)
        occurrence = {"id": uuid4(), "task_id": uuid4(), "status": "CANCELLED"}
        representation = occurrence_row(
            occurrence_id=occurrence["id"],
            task_id=occurrence["task_id"],
            household_id=household_id,
            status="CANCELLED",
            cancelled_at=cancelled_at,
            cancelled_by=user_id,
        )
        connection = self.connection(occurrence, representation)

        result = await tasks_service.cancel_task(
            connection, user_id, household_id, occurrence["id"]
        )

        self.assertTrue(result["status"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["data"]["task"]["cancelled_at"], cancelled_at.isoformat())
        self.assertFalse(executed_args(connection, "UPDATE task_occurrences"))
        self.assertFalse(executed_args(connection, "INSERT INTO activity_events"))

    async def test_rejects_cancelling_a_task_that_is_not_pending(self):
        occurrence = {"id": uuid4(), "task_id": uuid4(), "status": "DONE"}
        connection = self.connection(occurrence, occurrence_row(status="DONE"))

        result = await tasks_service.cancel_task(
            connection, uuid4(), uuid4(), occurrence["id"]
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 409)
        self.assertFalse(executed_args(connection, "UPDATE task_occurrences"))

    async def test_returns_not_found_for_an_unknown_occurrence(self):
        connection = self.connection(None, occurrence_row())

        result = await tasks_service.cancel_task(
            connection, uuid4(), uuid4(), uuid4()
        )

        self.assertFalse(result["status"])
        self.assertEqual(result["status_code"], 404)


class TaskRouteTests(unittest.TestCase):
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
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_create_requires_the_idempotency_key_header(self):
        response = self.client.post(
            f"/households/{self.household_id}/tasks",
            json={"title": "Lavar roupa"},
        )

        self.assertEqual(response.status_code, 422)

    def test_create_returns_the_standard_envelope(self):
        data = {"task": task_data()}
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 201,
                "message": "Task created",
                "data": data,
            }
        )

        with patch.object(tasks_service, "create_task", service):
            response = self.client.post(
                f"/households/{self.household_id}/tasks",
                json={"title": "  Lavar roupa  ", "due_local": "2030-01-01T10:00"},
                headers={"Idempotency-Key": "  key-1  "},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(), {"message": "Task created", "data": data}
        )
        call = service.await_args
        self.assertEqual(call.args[1], self.user_id)
        self.assertEqual(call.args[2], self.household_id)
        self.assertEqual(call.args[3].title, "Lavar roupa")
        self.assertEqual(call.args[4], "key-1")

    def test_list_returns_the_standard_envelope(self):
        data = {"tasks": [task_data()]}
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 200,
                "message": "Tasks retrieved",
                "data": data,
            }
        )

        with patch.object(tasks_service, "list_tasks", service):
            response = self.client.get(
                f"/households/{self.household_id}/tasks"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"message": "Tasks retrieved", "data": data}
        )
        self.assertEqual(service.await_args.args[1], self.household_id)

    def test_update_rejects_an_empty_body(self):
        occurrence_id = uuid4()

        response = self.client.patch(
            f"/households/{self.household_id}/tasks/{occurrence_id}",
            json={},
        )

        self.assertEqual(response.status_code, 422)

    def test_update_rejects_a_null_title(self):
        occurrence_id = uuid4()

        response = self.client.patch(
            f"/households/{self.household_id}/tasks/{occurrence_id}",
            json={"title": None},
        )

        self.assertEqual(response.status_code, 422)

    def test_update_returns_the_standard_envelope(self):
        occurrence_id = uuid4()
        data = {"task": task_data(occurrence_id=occurrence_id)}
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 200,
                "message": "Task updated",
                "data": data,
            }
        )

        with patch.object(tasks_service, "update_task", service):
            response = self.client.patch(
                f"/households/{self.household_id}/tasks/{occurrence_id}",
                json={"title": "Novo"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"message": "Task updated", "data": data}
        )
        self.assertEqual(service.await_args.args[3], occurrence_id)

    def test_cancel_returns_the_standard_envelope(self):
        occurrence_id = uuid4()
        data = {
            "task": task_data(
                occurrence_id=occurrence_id,
                status="CANCELLED",
                cancelled_at=created_at().isoformat(),
                cancelled_by=str(self.user_id),
            )
        }
        service = AsyncMock(
            return_value={
                "status": True,
                "status_code": 200,
                "message": "Task cancelled",
                "data": data,
            }
        )

        with patch.object(tasks_service, "cancel_task", service):
            response = self.client.post(
                f"/households/{self.household_id}/tasks/{occurrence_id}/cancel"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"message": "Task cancelled", "data": data}
        )
        self.assertEqual(service.await_args.args[3], occurrence_id)


class TaskMigrationTests(unittest.TestCase):
    def load_migration(self):
        spec = importlib.util.spec_from_file_location(
            "migration_0006", MIGRATION_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def test_follows_the_invites_revision(self):
        module = self.load_migration()

        self.assertEqual(module.revision, "0006")
        self.assertEqual(module.down_revision, "0005")

    def test_declares_task_tables_and_membership_composite_key(self):
        source = MIGRATION_PATH.read_text(encoding="utf-8")

        self.assertIn('"tasks"', source)
        self.assertIn('"task_occurrences"', source)
        self.assertIn("uq_household_members_id_household_id", source)


if __name__ == "__main__":
    unittest.main()
