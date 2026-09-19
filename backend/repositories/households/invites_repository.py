from datetime import datetime
from uuid import UUID

import asyncpg


async def acquire_advisory_lock(conn: asyncpg.Connection, key: str) -> None:
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
        key,
    )


async def find_create_invite_idempotency_record(
    conn: asyncpg.Connection,
    user_id: UUID,
    household_id: UUID,
    operation: str,
    idempotency_key: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT fingerprint, resource_id, response_status, response_data, expires_at
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


async def insert_invite(
    conn: asyncpg.Connection,
    invite_id: UUID,
    household_id: UUID,
    token_hash: str,
    created_by: UUID,
    expires_at: datetime,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        INSERT INTO household_invites (
            id,
            household_id,
            token_hash,
            created_by,
            expires_at
        )
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, household_id, created_at, expires_at
        """,
        invite_id,
        household_id,
        token_hash,
        created_by,
        expires_at,
    )


async def insert_invite_created_event(
    conn: asyncpg.Connection,
    event_id: UUID,
    household_id: UUID,
    actor_user_id: UUID,
    invite_id: UUID,
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
        VALUES ($1, $2, $3, 'household_invite', $4, 'INVITE_CREATED', $5::jsonb)
        """,
        event_id,
        household_id,
        actor_user_id,
        invite_id,
        metadata,
    )


async def upsert_invite_idempotency_record(
    conn: asyncpg.Connection,
    record_id: UUID,
    user_id: UUID,
    household_id: UUID,
    operation: str,
    idempotency_key: str,
    fingerprint: str,
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
        VALUES ($1, $2, $3, $4, $5, $6, '{}'::jsonb, $7, 201, $8::jsonb, $9)
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
        resource_id,
        response_data,
        expires_at,
    )


async def list_active_invites(
    conn: asyncpg.Connection,
    household_id: UUID,
) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT id, household_id, created_at, expires_at
        FROM household_invites
        WHERE household_id = $1
          AND revoked_at IS NULL
          AND accepted_at IS NULL
          AND expires_at > now()
        ORDER BY created_at DESC, id
        """,
        household_id,
    )


async def lock_invite(
    conn: asyncpg.Connection,
    invite_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, accepted_at, revoked_at
        FROM household_invites
        WHERE id = $1 AND household_id = $2
        FOR UPDATE
        """,
        invite_id,
        household_id,
    )


async def revoke_invite(
    conn: asyncpg.Connection,
    invite_id: UUID,
    household_id: UUID,
    revoked_by: UUID,
) -> datetime | None:
    return await conn.fetchval(
        """
        UPDATE household_invites
        SET revoked_at = now(), revoked_by = $3
        WHERE id = $1 AND household_id = $2
        RETURNING revoked_at
        """,
        invite_id,
        household_id,
        revoked_by,
    )


async def insert_invite_revoked_event(
    conn: asyncpg.Connection,
    event_id: UUID,
    household_id: UUID,
    actor_user_id: UUID,
    invite_id: UUID,
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
        VALUES ($1, $2, $3, 'household_invite', $4, 'INVITE_REVOKED', $5::jsonb)
        """,
        event_id,
        household_id,
        actor_user_id,
        invite_id,
        metadata,
    )


async def count_user_accept_attempts(
    conn: asyncpg.Connection,
    user_id: UUID,
    since: datetime,
) -> int:
    return await conn.fetchval(
        """
        SELECT count(*)
        FROM household_invite_accept_attempts
        WHERE user_id = $1 AND created_at > $2
        """,
        user_id,
        since,
    )


async def count_ip_accept_attempts(
    conn: asyncpg.Connection,
    client_ip: str,
    since: datetime,
) -> int:
    return await conn.fetchval(
        """
        SELECT count(*)
        FROM household_invite_accept_attempts
        WHERE requested_ip = $1 AND created_at > $2
        """,
        client_ip,
        since,
    )


async def insert_accept_attempt(
    conn: asyncpg.Connection,
    attempt_id: UUID,
    user_id: UUID,
    client_ip: str | None,
) -> None:
    await conn.execute(
        """
        INSERT INTO household_invite_accept_attempts (id, user_id, requested_ip)
        VALUES ($1, $2, $3)
        """,
        attempt_id,
        user_id,
        client_ip,
    )


async def lock_invite_by_token(
    conn: asyncpg.Connection,
    token_hash: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id,
               household_id,
               expires_at,
               revoked_at,
               accepted_at,
               accepted_by,
               accepted_membership_id
        FROM household_invites
        WHERE token_hash = $1
        FOR UPDATE
        """,
        token_hash,
    )


async def find_household(
    conn: asyncpg.Connection,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, name, timezone, default_due_time, created_at, deactivated_at
        FROM households
        WHERE id = $1
        """,
        household_id,
    )


async def find_active_membership_by_id(
    conn: asyncpg.Connection,
    membership_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, user_id, role, status, joined_at
        FROM household_members
        WHERE id = $1 AND household_id = $2 AND status = 'ACTIVE'
        """,
        membership_id,
        household_id,
    )


async def find_active_membership_for_update(
    conn: asyncpg.Connection,
    household_id: UUID,
    user_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, user_id, role, status, joined_at
        FROM household_members
        WHERE household_id = $1 AND user_id = $2 AND status = 'ACTIVE'
        FOR UPDATE
        """,
        household_id,
        user_id,
    )


async def insert_active_membership(
    conn: asyncpg.Connection,
    membership_id: UUID,
    household_id: UUID,
    user_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        INSERT INTO household_members (id, household_id, user_id, role, status)
        VALUES ($1, $2, $3, 'MEMBER', 'ACTIVE')
        RETURNING id, user_id, role, status, joined_at
        """,
        membership_id,
        household_id,
        user_id,
    )


async def mark_invite_accepted(
    conn: asyncpg.Connection,
    invite_id: UUID,
    accepted_by: UUID,
    accepted_membership_id: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE household_invites
        SET accepted_at = now(),
            accepted_by = $2,
            accepted_membership_id = $3
        WHERE id = $1
        """,
        invite_id,
        accepted_by,
        accepted_membership_id,
    )


async def insert_invite_accepted_event(
    conn: asyncpg.Connection,
    event_id: UUID,
    household_id: UUID,
    actor_user_id: UUID,
    invite_id: UUID,
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
        VALUES ($1, $2, $3, 'household_invite', $4, 'INVITE_ACCEPTED', $5::jsonb)
        """,
        event_id,
        household_id,
        actor_user_id,
        invite_id,
        metadata,
    )


async def insert_member_joined_event(
    conn: asyncpg.Connection,
    event_id: UUID,
    household_id: UUID,
    actor_user_id: UUID,
    membership_id: UUID,
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
        VALUES ($1, $2, $3, 'household_member', $4, 'MEMBER_JOINED', $5::jsonb)
        """,
        event_id,
        household_id,
        actor_user_id,
        membership_id,
        metadata,
    )
