import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4
from zoneinfo import ZoneInfo

import asyncpg

from core.logger.logger import logger
from schemas.tasks import (
    DUE_LOCAL_FORMAT,
    TaskCreateRequestModel,
    refresh_task_derived,
    task_from_row,
)
from services.households import households_service


OPERATION_CREATE_TASK = "tasks.create"
CREATE_TASK_MESSAGE = "Task created"
TASKS_MESSAGE = "Tasks retrieved"
UPDATE_TASK_MESSAGE = "Task updated"
CANCEL_TASK_MESSAGE = "Task cancelled"
TASK_NOT_FOUND_MESSAGE = "Task not found"
TASK_NOT_PENDING_MESSAGE = "Task is not pending"
ASSIGNEE_INVALID_MESSAGE = "Assignee must be an active member of the household"
DUE_NOT_FUTURE_MESSAGE = "Due must be in the future"
IDEMPOTENCY_CONFLICT_MESSAGE = "Idempotency key was reused with a different request"
INTERNAL_ERROR_MESSAGE = "Internal server error"


OCCURRENCE_SELECT = """
SELECT o.id AS occurrence_id,
       o.task_id,
       o.household_id,
       t.title,
       o.status,
       o.assignee_membership_id,
       o.due_at,
       o.due_timezone,
       o.created_by,
       o.created_at,
       o.updated_at,
       o.cancelled_at,
       o.cancelled_by,
       hm.user_id AS assignee_user_id,
       u.fullname AS assignee_fullname
FROM task_occurrences o
JOIN tasks t
  ON t.id = o.task_id
 AND t.household_id = o.household_id
LEFT JOIN household_members hm
  ON hm.id = o.assignee_membership_id
LEFT JOIN users u
  ON u.id = hm.user_id
"""


def payload_fingerprint(data: TaskCreateRequestModel) -> str:
    normalized = {
        "title": data.title,
        "assignee_membership_id": (
            str(data.assignee_membership_id)
            if data.assignee_membership_id is not None
            else None
        ),
        "due_local": data.due_local,
    }
    serialized = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return sha256(serialized.encode("utf-8")).hexdigest()


def parse_due_local(value: str, timezone_name: str) -> datetime:
    naive = datetime.strptime(value, DUE_LOCAL_FORMAT)
    tz = ZoneInfo(timezone_name)
    candidate = naive

    while True:
        aware = candidate.replace(tzinfo=tz, fold=0)
        resolved = aware.astimezone(timezone.utc)
        if resolved.astimezone(tz).replace(tzinfo=None) == candidate:
            return resolved

        candidate += timedelta(minutes=1)


async def _lock_active_assignee(conn, household_id, membership_id):
    return await conn.fetchrow(
        """
        SELECT hm.id AS membership_id, hm.user_id, u.fullname
        FROM household_members hm
        JOIN users u ON u.id = hm.user_id
        WHERE hm.id = $1
          AND hm.household_id = $2
          AND hm.status = 'ACTIVE'
        FOR UPDATE
        """,
        membership_id,
        household_id,
    )


async def _fetch_occurrence(conn, occurrence_id, household_id):
    return await conn.fetchrow(
        OCCURRENCE_SELECT
        + """
        WHERE o.id = $1
          AND o.household_id = $2
        """,
        occurrence_id,
        household_id,
    )


async def _household_timezone(conn, household_id) -> str:
    return await conn.fetchval(
        "SELECT timezone FROM households WHERE id = $1",
        household_id,
    )


async def _write_audit(conn, household_id, user_id, occurrence_id, event_type, metadata):
    await conn.execute(
        """
        INSERT INTO activity_events (
            id,
            household_id,
            actor_user_id,
            entity_type,
            entity_id,
            event_type,
            metadata
        )
        VALUES ($1, $2, $3, 'task_occurrence', $4, $5, $6::jsonb)
        """,
        uuid4(),
        household_id,
        user_id,
        occurrence_id,
        event_type,
        json.dumps(metadata, separators=(",", ":")),
    )


def _error(status_code: int, message: str) -> dict:
    return {
        "status": False,
        "status_code": status_code,
        "message": message,
        "data": {},
    }


async def create_task(
    conn: asyncpg.Connection,
    user_id,
    household_id,
    data: TaskCreateRequestModel,
    idempotency_key: str,
) -> dict:
    try:
        fingerprint = payload_fingerprint(data)

        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                f"{OPERATION_CREATE_TASK}:{household_id}:{idempotency_key}",
            )

            record = await conn.fetchrow(
                """
                SELECT fingerprint, response_status, response_data, expires_at
                FROM idempotency_records
                WHERE user_id = $1
                  AND household_id = $2
                  AND operation = $3
                  AND idempotency_key = $4
                """,
                user_id,
                household_id,
                OPERATION_CREATE_TASK,
                idempotency_key,
            )

            if record and record["expires_at"] > datetime.now(timezone.utc):
                if record["fingerprint"] != fingerprint:
                    return _error(409, IDEMPOTENCY_CONFLICT_MESSAGE)

                task = json.loads(record["response_data"])["task"]
                return {
                    "status": True,
                    "status_code": record["response_status"],
                    "message": CREATE_TASK_MESSAGE,
                    "data": {"task": refresh_task_derived(task)},
                }

            _context, error = await households_service.lock_active_membership(
                conn, household_id, user_id
            )
            if error:
                return error

            due_at = None
            due_timezone = None
            if data.due_local is not None:
                timezone_name = await _household_timezone(conn, household_id)
                due_at = parse_due_local(data.due_local, timezone_name)
                if due_at <= datetime.now(timezone.utc):
                    return _error(400, DUE_NOT_FUTURE_MESSAGE)
                due_timezone = timezone_name

            if data.assignee_membership_id is not None:
                assignee = await _lock_active_assignee(
                    conn, household_id, data.assignee_membership_id
                )
                if assignee is None:
                    return _error(400, ASSIGNEE_INVALID_MESSAGE)

            task_id = uuid4()
            occurrence_id = uuid4()

            await conn.execute(
                """
                INSERT INTO tasks (id, household_id, title, created_by)
                VALUES ($1, $2, $3, $4)
                """,
                task_id,
                household_id,
                data.title,
                user_id,
            )
            await conn.execute(
                """
                INSERT INTO task_occurrences (
                    id,
                    task_id,
                    household_id,
                    assignee_membership_id,
                    due_at,
                    due_timezone,
                    status,
                    created_by
                )
                VALUES ($1, $2, $3, $4, $5, $6, 'PENDING', $7)
                """,
                occurrence_id,
                task_id,
                household_id,
                data.assignee_membership_id,
                due_at,
                due_timezone,
                user_id,
            )
            await _write_audit(
                conn,
                household_id,
                user_id,
                occurrence_id,
                "TASK_CREATED",
                {
                    "task_id": str(task_id),
                    "occurrence_id": str(occurrence_id),
                },
            )

            row = await _fetch_occurrence(conn, occurrence_id, household_id)
            task = task_from_row(row)

            await conn.execute(
                """
                INSERT INTO idempotency_records (
                    id,
                    user_id,
                    household_id,
                    operation,
                    idempotency_key,
                    fingerprint,
                    payload,
                    resource_id,
                    response_status,
                    response_data,
                    expires_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, 201, $9::jsonb, $10)
                ON CONFLICT ON CONSTRAINT uq_idempotency_records_scope
                DO UPDATE SET
                    fingerprint = EXCLUDED.fingerprint,
                    payload = EXCLUDED.payload,
                    resource_id = EXCLUDED.resource_id,
                    response_status = EXCLUDED.response_status,
                    response_data = EXCLUDED.response_data,
                    created_at = now(),
                    expires_at = EXCLUDED.expires_at
                """,
                uuid4(),
                user_id,
                household_id,
                OPERATION_CREATE_TASK,
                idempotency_key,
                fingerprint,
                json.dumps(
                    {
                        "title": data.title,
                        "assignee_membership_id": (
                            str(data.assignee_membership_id)
                            if data.assignee_membership_id is not None
                            else None
                        ),
                        "due_local": data.due_local,
                    },
                    separators=(",", ":"),
                ),
                occurrence_id,
                json.dumps({"task": task}, separators=(",", ":")),
                datetime.now(timezone.utc) + households_service.IDEMPOTENCY_TTL,
            )

            return {
                "status": True,
                "status_code": 201,
                "message": CREATE_TASK_MESSAGE,
                "data": {"task": task},
            }
    except Exception as exc:
        logger.exception(exc)
        return _error(500, INTERNAL_ERROR_MESSAGE)


async def list_tasks(conn: asyncpg.Connection, household_id) -> dict:
    try:
        rows = await conn.fetch(
            OCCURRENCE_SELECT
            + """
            WHERE o.household_id = $1
              AND o.status = 'PENDING'
            ORDER BY o.due_at ASC NULLS LAST, o.created_at ASC, o.id ASC
            """,
            household_id,
        )

        return {
            "status": True,
            "status_code": 200,
            "message": TASKS_MESSAGE,
            "data": {"tasks": [task_from_row(row) for row in rows]},
        }
    except Exception as exc:
        logger.exception(exc)
        return _error(500, INTERNAL_ERROR_MESSAGE)


async def update_task(
    conn: asyncpg.Connection,
    user_id,
    household_id,
    occurrence_id,
    data,
) -> dict:
    try:
        async with conn.transaction():
            _context, error = await households_service.lock_active_membership(
                conn, household_id, user_id
            )
            if error:
                return error

            occurrence = await conn.fetchrow(
                """
                SELECT id,
                       task_id,
                       status,
                       assignee_membership_id,
                       due_at,
                       due_timezone
                FROM task_occurrences
                WHERE id = $1 AND household_id = $2
                FOR UPDATE
                """,
                occurrence_id,
                household_id,
            )

            if not occurrence:
                return _error(404, TASK_NOT_FOUND_MESSAGE)

            if occurrence["status"] != "PENDING":
                return _error(409, TASK_NOT_PENDING_MESSAGE)

            task = await conn.fetchrow(
                """
                SELECT id, title
                FROM tasks
                WHERE id = $1 AND household_id = $2
                FOR UPDATE
                """,
                occurrence["task_id"],
                household_id,
            )

            if not task:
                return _error(404, TASK_NOT_FOUND_MESSAGE)

            fields = data.model_fields_set
            title = task["title"]
            assignee_membership_id = occurrence["assignee_membership_id"]
            due_at = occurrence["due_at"]
            due_timezone = occurrence["due_timezone"]

            if "title" in fields:
                title = data.title

            if "assignee_membership_id" in fields:
                if data.assignee_membership_id is None:
                    assignee_membership_id = None
                else:
                    assignee = await _lock_active_assignee(
                        conn, household_id, data.assignee_membership_id
                    )
                    if assignee is None:
                        return _error(400, ASSIGNEE_INVALID_MESSAGE)
                    assignee_membership_id = data.assignee_membership_id

            if "due_local" in fields:
                if data.due_local is None:
                    due_at = None
                    due_timezone = None
                else:
                    timezone_name = await _household_timezone(conn, household_id)
                    resolved = parse_due_local(data.due_local, timezone_name)
                    if resolved <= datetime.now(timezone.utc):
                        return _error(400, DUE_NOT_FUTURE_MESSAGE)
                    due_at = resolved
                    due_timezone = timezone_name

            await conn.execute(
                """
                UPDATE tasks
                SET title = $2, updated_at = now()
                WHERE id = $1 AND household_id = $3
                """,
                task["id"],
                title,
                household_id,
            )
            await conn.execute(
                """
                UPDATE task_occurrences
                SET assignee_membership_id = $2,
                    due_at = $3,
                    due_timezone = $4,
                    updated_at = now()
                WHERE id = $1 AND household_id = $5
                """,
                occurrence_id,
                assignee_membership_id,
                due_at,
                due_timezone,
                household_id,
            )
            await _write_audit(
                conn,
                household_id,
                user_id,
                occurrence_id,
                "TASK_UPDATED",
                {
                    "task_id": str(occurrence["task_id"]),
                    "occurrence_id": str(occurrence_id),
                    "fields": sorted(fields),
                },
            )

            row = await _fetch_occurrence(conn, occurrence_id, household_id)

            return {
                "status": True,
                "status_code": 200,
                "message": UPDATE_TASK_MESSAGE,
                "data": {"task": task_from_row(row)},
            }
    except Exception as exc:
        logger.exception(exc)
        return _error(500, INTERNAL_ERROR_MESSAGE)


async def cancel_task(
    conn: asyncpg.Connection,
    user_id,
    household_id,
    occurrence_id,
) -> dict:
    try:
        async with conn.transaction():
            _context, error = await households_service.lock_active_membership(
                conn, household_id, user_id
            )
            if error:
                return error

            occurrence = await conn.fetchrow(
                """
                SELECT id, task_id, status
                FROM task_occurrences
                WHERE id = $1 AND household_id = $2
                FOR UPDATE
                """,
                occurrence_id,
                household_id,
            )

            if not occurrence:
                return _error(404, TASK_NOT_FOUND_MESSAGE)

            if occurrence["status"] == "CANCELLED":
                row = await _fetch_occurrence(conn, occurrence_id, household_id)
                return {
                    "status": True,
                    "status_code": 200,
                    "message": CANCEL_TASK_MESSAGE,
                    "data": {"task": task_from_row(row)},
                }

            if occurrence["status"] != "PENDING":
                return _error(409, TASK_NOT_PENDING_MESSAGE)

            await conn.execute(
                """
                UPDATE task_occurrences
                SET status = 'CANCELLED',
                    cancelled_at = now(),
                    cancelled_by = $3,
                    updated_at = now()
                WHERE id = $1 AND household_id = $2
                """,
                occurrence_id,
                household_id,
                user_id,
            )
            await _write_audit(
                conn,
                household_id,
                user_id,
                occurrence_id,
                "TASK_CANCELLED",
                {
                    "task_id": str(occurrence["task_id"]),
                    "occurrence_id": str(occurrence_id),
                },
            )

            row = await _fetch_occurrence(conn, occurrence_id, household_id)

            return {
                "status": True,
                "status_code": 200,
                "message": CANCEL_TASK_MESSAGE,
                "data": {"task": task_from_row(row)},
            }
    except Exception as exc:
        logger.exception(exc)
        return _error(500, INTERNAL_ERROR_MESSAGE)
