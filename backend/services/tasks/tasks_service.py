import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4
from zoneinfo import ZoneInfo

import asyncpg

from core.logger.logger import logger
from repositories import tasks_repository
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
            await tasks_repository.acquire_idempotency_lock(
                conn,
                f"{OPERATION_CREATE_TASK}:{household_id}:{idempotency_key}",
            )

            record = await tasks_repository.find_create_idempotency_record(
                conn,
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
                timezone_name = await tasks_repository.find_household_timezone(
                    conn, household_id
                )
                due_at = parse_due_local(data.due_local, timezone_name)
                if due_at <= datetime.now(timezone.utc):
                    return _error(400, DUE_NOT_FUTURE_MESSAGE)
                due_timezone = timezone_name

            if data.assignee_membership_id is not None:
                assignee = await tasks_repository.lock_active_assignee(
                    conn,
                    data.assignee_membership_id,
                    household_id,
                )
                if assignee is None:
                    return _error(400, ASSIGNEE_INVALID_MESSAGE)

            task_id = uuid4()
            occurrence_id = uuid4()

            await tasks_repository.insert_task(
                conn,
                task_id,
                household_id,
                data.title,
                user_id,
            )
            await tasks_repository.insert_task_occurrence(
                conn,
                occurrence_id,
                task_id,
                household_id,
                data.assignee_membership_id,
                due_at,
                due_timezone,
                user_id,
            )
            await tasks_repository.insert_task_activity_event(
                conn,
                uuid4(),
                household_id,
                user_id,
                occurrence_id,
                "TASK_CREATED",
                json.dumps(
                    {
                        "task_id": str(task_id),
                        "occurrence_id": str(occurrence_id),
                    },
                    separators=(",", ":"),
                ),
            )

            row = await tasks_repository.find_occurrence(
                conn, occurrence_id, household_id
            )
            task = task_from_row(row)

            await tasks_repository.upsert_task_idempotency_record(
                conn,
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
        rows = await tasks_repository.list_pending_occurrences(conn, household_id)

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

            occurrence = await tasks_repository.lock_task_occurrence(
                conn,
                occurrence_id,
                household_id,
            )

            if not occurrence:
                return _error(404, TASK_NOT_FOUND_MESSAGE)

            if occurrence["status"] != "PENDING":
                return _error(409, TASK_NOT_PENDING_MESSAGE)

            task = await tasks_repository.lock_task(
                conn,
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
                    assignee = await tasks_repository.lock_active_assignee(
                        conn,
                        data.assignee_membership_id,
                        household_id,
                    )
                    if assignee is None:
                        return _error(400, ASSIGNEE_INVALID_MESSAGE)
                    assignee_membership_id = data.assignee_membership_id

            if "due_local" in fields:
                if data.due_local is None:
                    due_at = None
                    due_timezone = None
                else:
                    timezone_name = await tasks_repository.find_household_timezone(
                        conn, household_id
                    )
                    resolved = parse_due_local(data.due_local, timezone_name)
                    if resolved <= datetime.now(timezone.utc):
                        return _error(400, DUE_NOT_FUTURE_MESSAGE)
                    due_at = resolved
                    due_timezone = timezone_name

            await tasks_repository.update_task(
                conn,
                task["id"],
                title,
                household_id,
            )
            await tasks_repository.update_task_occurrence(
                conn,
                occurrence_id,
                assignee_membership_id,
                due_at,
                due_timezone,
                household_id,
            )
            await tasks_repository.insert_task_activity_event(
                conn,
                uuid4(),
                household_id,
                user_id,
                occurrence_id,
                "TASK_UPDATED",
                json.dumps(
                    {
                        "task_id": str(occurrence["task_id"]),
                        "occurrence_id": str(occurrence_id),
                        "fields": sorted(fields),
                    },
                    separators=(",", ":"),
                ),
            )

            row = await tasks_repository.find_occurrence(
                conn, occurrence_id, household_id
            )

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

            occurrence = await tasks_repository.lock_occurrence_status(
                conn,
                occurrence_id,
                household_id,
            )

            if not occurrence:
                return _error(404, TASK_NOT_FOUND_MESSAGE)

            if occurrence["status"] == "CANCELLED":
                row = await tasks_repository.find_occurrence(
                    conn, occurrence_id, household_id
                )
                return {
                    "status": True,
                    "status_code": 200,
                    "message": CANCEL_TASK_MESSAGE,
                    "data": {"task": task_from_row(row)},
                }

            if occurrence["status"] != "PENDING":
                return _error(409, TASK_NOT_PENDING_MESSAGE)

            await tasks_repository.cancel_task_occurrence(
                conn,
                occurrence_id,
                household_id,
                user_id,
            )
            await tasks_repository.insert_task_activity_event(
                conn,
                uuid4(),
                household_id,
                user_id,
                occurrence_id,
                "TASK_CANCELLED",
                json.dumps(
                    {
                        "task_id": str(occurrence["task_id"]),
                        "occurrence_id": str(occurrence_id),
                    },
                    separators=(",", ":"),
                ),
            )

            row = await tasks_repository.find_occurrence(
                conn, occurrence_id, household_id
            )

            return {
                "status": True,
                "status_code": 200,
                "message": CANCEL_TASK_MESSAGE,
                "data": {"task": task_from_row(row)},
            }
    except Exception as exc:
        logger.exception(exc)
        return _error(500, INTERNAL_ERROR_MESSAGE)
