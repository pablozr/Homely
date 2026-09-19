from datetime import datetime
from uuid import UUID

import asyncpg


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
       o.completed_by,
       o.completed_at,
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


async def acquire_idempotency_lock(conn: asyncpg.Connection, key: str) -> None:
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
        key,
    )


async def find_create_idempotency_record(
    conn: asyncpg.Connection,
    user_id: UUID,
    household_id: UUID,
    operation: str,
    idempotency_key: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
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
        operation,
        idempotency_key,
    )


async def find_household_timezone(
    conn: asyncpg.Connection,
    household_id: UUID,
) -> str:
    return await conn.fetchval(
        "SELECT timezone FROM households WHERE id = $1",
        household_id,
    )


async def lock_active_assignee(
    conn: asyncpg.Connection,
    membership_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
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


async def insert_task(
    conn: asyncpg.Connection,
    task_id: UUID,
    household_id: UUID,
    title: str,
    created_by: UUID,
) -> None:
    await conn.execute(
        """
        INSERT INTO tasks (id, household_id, title, created_by)
        VALUES ($1, $2, $3, $4)
        """,
        task_id,
        household_id,
        title,
        created_by,
    )


async def insert_task_occurrence(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    task_id: UUID,
    household_id: UUID,
    assignee_membership_id: UUID | None,
    due_at: datetime | None,
    due_timezone: str | None,
    created_by: UUID,
) -> None:
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
        assignee_membership_id,
        due_at,
        due_timezone,
        created_by,
    )


async def insert_task_activity_event(
    conn: asyncpg.Connection,
    event_id: UUID,
    household_id: UUID,
    actor_user_id: UUID,
    occurrence_id: UUID,
    event_type: str,
    metadata: str,
) -> None:
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
        event_id,
        household_id,
        actor_user_id,
        occurrence_id,
        event_type,
        metadata,
    )


async def find_occurrence(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        OCCURRENCE_SELECT
        + """
        WHERE o.id = $1
          AND o.household_id = $2
        """,
        occurrence_id,
        household_id,
    )


async def list_pending_occurrences(
    conn: asyncpg.Connection,
    household_id: UUID,
) -> list[asyncpg.Record]:
    return await conn.fetch(
        OCCURRENCE_SELECT
        + """
        WHERE o.household_id = $1
          AND o.status IN ('PENDING', 'DONE')
        ORDER BY
            CASE o.status WHEN 'PENDING' THEN 0 ELSE 1 END,
            CASE WHEN o.status = 'PENDING' THEN o.due_at END ASC NULLS LAST,
            CASE WHEN o.status = 'PENDING' THEN o.created_at END ASC,
            CASE WHEN o.status = 'DONE' THEN o.completed_at END DESC NULLS LAST,
            CASE WHEN o.status = 'PENDING' THEN o.id END ASC,
            CASE WHEN o.status = 'DONE' THEN o.id END DESC
        """,
        household_id,
    )


async def upsert_task_idempotency_record(
    conn: asyncpg.Connection,
    record_id: UUID,
    user_id: UUID,
    household_id: UUID,
    operation: str,
    idempotency_key: str,
    fingerprint: str,
    payload: str,
    resource_id: UUID,
    response_data: str,
    expires_at: datetime,
) -> None:
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
        record_id,
        user_id,
        household_id,
        operation,
        idempotency_key,
        fingerprint,
        payload,
        resource_id,
        response_data,
        expires_at,
    )


async def lock_task_occurrence(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
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


async def lock_task(
    conn: asyncpg.Connection,
    task_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, title
        FROM tasks
        WHERE id = $1 AND household_id = $2
        FOR UPDATE
        """,
        task_id,
        household_id,
    )


async def update_task(
    conn: asyncpg.Connection,
    task_id: UUID,
    title: str,
    household_id: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE tasks
        SET title = $2, updated_at = now()
        WHERE id = $1 AND household_id = $3
        """,
        task_id,
        title,
        household_id,
    )


async def update_task_occurrence(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    assignee_membership_id: UUID | None,
    due_at: datetime | None,
    due_timezone: str | None,
    household_id: UUID,
) -> None:
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


async def lock_occurrence_status(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, task_id, status
        FROM task_occurrences
        WHERE id = $1 AND household_id = $2
        FOR UPDATE
        """,
        occurrence_id,
        household_id,
    )


async def cancel_task_occurrence(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    household_id: UUID,
    cancelled_by: UUID,
) -> None:
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
        cancelled_by,
    )


async def lock_task_completion(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, task_id, status, completed_by, completed_at
        FROM task_occurrences
        WHERE id = $1 AND household_id = $2
        FOR UPDATE
        """,
        occurrence_id,
        household_id,
    )


async def complete_task_occurrence(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    household_id: UUID,
    completed_by: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE task_occurrences
        SET status = 'DONE',
            completed_by = $3,
            completed_at = clock_timestamp(),
            updated_at = now()
        WHERE id = $1
          AND household_id = $2
          AND status = 'PENDING'
        """,
        occurrence_id,
        household_id,
        completed_by,
    )


async def undo_task_completion(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    household_id: UUID,
    completed_by: UUID,
) -> bool:
    status = await conn.execute(
        """
        UPDATE task_occurrences
        SET status = 'PENDING',
            completed_by = NULL,
            completed_at = NULL,
            updated_at = now()
        WHERE id = $1
          AND household_id = $2
          AND status = 'DONE'
          AND completed_by = $3
          AND completed_at + interval '10 seconds' >= clock_timestamp()
        """,
        occurrence_id,
        household_id,
        completed_by,
    )

    return status == "UPDATE 1"


async def correct_task_completion(
    conn: asyncpg.Connection,
    occurrence_id: UUID,
    household_id: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE task_occurrences
        SET status = 'PENDING',
            completed_by = NULL,
            completed_at = NULL,
            updated_at = now()
        WHERE id = $1
          AND household_id = $2
          AND status = 'DONE'
        """,
        occurrence_id,
        household_id,
    )
