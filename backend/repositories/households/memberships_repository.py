from datetime import datetime
from uuid import UUID

import asyncpg


async def list_active_members(
    conn: asyncpg.Connection,
    household_id: UUID,
) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT hm.id, hm.user_id, u.fullname, hm.role, hm.status, hm.joined_at
        FROM household_members hm
        JOIN users u ON u.id = hm.user_id
        WHERE hm.household_id = $1
          AND hm.status = 'ACTIVE'
        ORDER BY hm.joined_at, hm.id
        """,
        household_id,
    )


async def lock_removal_target(
    conn: asyncpg.Connection,
    membership_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, user_id, role, status
        FROM household_members
        WHERE id = $1 AND household_id = $2
        FOR UPDATE
        """,
        membership_id,
        household_id,
    )


async def lock_transfer_target(
    conn: asyncpg.Connection,
    membership_id: UUID,
    household_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, role, status
        FROM household_members
        WHERE id = $1 AND household_id = $2
        FOR UPDATE
        """,
        membership_id,
        household_id,
    )


async def deactivate_membership(
    conn: asyncpg.Connection,
    membership_id: UUID,
) -> datetime | None:
    return await conn.fetchval(
        """
        UPDATE household_members
        SET status = 'INACTIVE', left_at = now()
        WHERE id = $1
        RETURNING left_at
        """,
        membership_id,
    )


async def demote_membership_to_member(
    conn: asyncpg.Connection,
    membership_id: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE household_members
        SET role = 'MEMBER'
        WHERE id = $1
        """,
        membership_id,
    )


async def promote_membership_to_owner(
    conn: asyncpg.Connection,
    membership_id: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE household_members
        SET role = 'OWNER'
        WHERE id = $1
        """,
        membership_id,
    )


async def insert_member_removed_event(
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
        VALUES ($1, $2, $3, 'household_member', $4, 'MEMBER_REMOVED', $5::jsonb)
        """,
        event_id,
        household_id,
        actor_user_id,
        entity_id,
        metadata,
    )


async def insert_member_left_event(
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
        VALUES ($1, $2, $3, 'household_member', $4, 'MEMBER_LEFT', $5::jsonb)
        """,
        event_id,
        household_id,
        actor_user_id,
        entity_id,
        metadata,
    )


async def insert_ownership_transferred_event(
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
        VALUES ($1, $2, $3, 'household_member', $4, 'OWNERSHIP_TRANSFERRED', $5::jsonb)
        """,
        event_id,
        household_id,
        actor_user_id,
        entity_id,
        metadata,
    )
