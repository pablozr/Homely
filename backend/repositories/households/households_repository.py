from datetime import datetime
from uuid import UUID

import asyncpg


async def acquire_idempotency_lock(conn: asyncpg.Connection, key: str) -> None:
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
        key,
    )


async def find_idempotency_record(
    conn: asyncpg.Connection,
    user_id: UUID,
    operation: str,
    idempotency_key: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT fingerprint, response_status, response_data, expires_at
        FROM idempotency_records
        WHERE user_id = $1
          AND household_id IS NULL
          AND operation = $2
          AND idempotency_key = $3
        """,
        user_id,
        operation,
        idempotency_key,
    )


async def insert_household(
    conn: asyncpg.Connection,
    household_id: UUID,
    name: str,
    timezone: str,
    created_by: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        INSERT INTO households (id, name, timezone, created_by)
        VALUES ($1, $2, $3, $4)
        RETURNING id, name, timezone, default_due_time, created_at
        """,
        household_id,
        name,
        timezone,
        created_by,
    )


async def insert_owner_membership(
    conn: asyncpg.Connection,
    membership_id: UUID,
    household_id: UUID,
    user_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        INSERT INTO household_members (id, household_id, user_id, role, status)
        VALUES ($1, $2, $3, 'OWNER', 'ACTIVE')
        RETURNING joined_at
        """,
        membership_id,
        household_id,
        user_id,
    )


async def insert_household_created_event(
    conn: asyncpg.Connection,
    event_id: UUID,
    household_id: UUID,
    actor_user_id: UUID,
    entity_id: UUID,
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
        VALUES ($1, $2, $3, 'household', $4, 'HOUSEHOLD_CREATED', $5::jsonb)
        """,
        event_id,
        household_id,
        actor_user_id,
        entity_id,
        metadata,
    )


async def update_user_last_household(
    conn: asyncpg.Connection,
    user_id: UUID,
    household_id: UUID,
) -> None:
    await conn.execute(
        "UPDATE users SET last_household_id = $2 WHERE id = $1",
        user_id,
        household_id,
    )


async def upsert_idempotency_record(
    conn: asyncpg.Connection,
    record_id: UUID,
    user_id: UUID,
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
        VALUES ($1, $2, NULL, $3, $4, $5, $6::jsonb, $7, 201, $8::jsonb, $9)
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
        operation,
        idempotency_key,
        fingerprint,
        payload,
        resource_id,
        response_data,
        expires_at,
    )


async def list_user_households(
    conn: asyncpg.Connection,
    user_id: UUID,
) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT h.id,
               h.name,
               h.timezone,
               h.default_due_time,
               h.created_at,
               hm.role,
               hm.joined_at,
               u.last_household_id
        FROM household_members hm
        JOIN households h ON h.id = hm.household_id
        JOIN users u ON u.id = hm.user_id
        WHERE hm.user_id = $1
          AND hm.status = 'ACTIVE'
          AND h.deactivated_at IS NULL
        ORDER BY hm.joined_at DESC, h.id
        """,
        user_id,
    )


async def set_selected_household(
    conn: asyncpg.Connection,
    user_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        UPDATE users
        SET last_household_id = $2
        WHERE id = $1
        RETURNING last_household_id
        """,
        user_id,
        household_id,
    )


async def lock_household(
    conn: asyncpg.Connection,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        "SELECT id, deactivated_at FROM households WHERE id = $1 FOR UPDATE",
        household_id,
    )


async def lock_active_membership(
    conn: asyncpg.Connection,
    household_id: UUID,
    user_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, role
        FROM household_members
        WHERE household_id = $1
          AND user_id = $2
          AND status = 'ACTIVE'
        FOR UPDATE
        """,
        household_id,
        user_id,
    )


async def find_membership_context(
    conn: asyncpg.Connection,
    household_id: UUID,
    user_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT h.id AS household_id,
               h.deactivated_at,
               hm.id AS membership_id,
               hm.role
        FROM households h
        LEFT JOIN household_members hm
               ON hm.household_id = h.id
              AND hm.user_id = $2
              AND hm.status = 'ACTIVE'
        WHERE h.id = $1
        """,
        household_id,
        user_id,
    )
