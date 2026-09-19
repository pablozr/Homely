from uuid import UUID

import asyncpg


async def find_profile(
    conn: asyncpg.Connection,
    user_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, fullname, role, created_at, profile_completed_at
        FROM users WHERE id = $1
        """,
        user_id,
    )


async def update_profile_completion(
    conn: asyncpg.Connection,
    user_id: UUID,
    fullname: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        UPDATE users
        SET fullname = $2,
            profile_completed_at = COALESCE(profile_completed_at, now())
        WHERE id = $1
        RETURNING id, fullname, role, created_at, profile_completed_at
        """,
        user_id,
        fullname,
    )
