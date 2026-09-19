from datetime import datetime
from uuid import UUID

import asyncpg


async def acquire_advisory_lock(conn: asyncpg.Connection, key: str) -> None:
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
        key,
    )


async def count_magic_link_requests_by_email(
    conn: asyncpg.Connection,
    email: str,
    since: datetime,
) -> int:
    return await conn.fetchval(
        """
        SELECT count(*)
        FROM magic_link_codes
        WHERE email = $1 AND created_at > $2
        """,
        email,
        since,
    )


async def count_magic_link_requests_by_ip(
    conn: asyncpg.Connection,
    client_ip: str,
    since: datetime,
) -> int:
    return await conn.fetchval(
        """
        SELECT count(*)
        FROM magic_link_codes
        WHERE requested_ip = $1 AND created_at > $2
        """,
        client_ip,
        since,
    )


async def insert_magic_link_code(
    conn: asyncpg.Connection,
    code_id: UUID,
    email: str,
    code_hash: str,
    client_ip: str | None,
    expires_at: datetime,
) -> None:
    await conn.execute(
        """
        INSERT INTO magic_link_codes (id, email, code_hash, requested_ip, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        code_id,
        email,
        code_hash,
        client_ip,
        expires_at,
    )


async def invalidate_magic_link_codes_for_email(
    conn: asyncpg.Connection,
    email: str,
    except_code_id: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE magic_link_codes
        SET used_at = now()
        WHERE email = $1 AND id != $2 AND used_at IS NULL
        """,
        email,
        except_code_id,
    )


async def count_exchange_attempts_by_ip(
    conn: asyncpg.Connection,
    client_ip: str,
    window_minutes: int,
) -> int:
    return await conn.fetchval(
        """
        SELECT count(*)
        FROM magic_link_exchange_attempts
        WHERE requested_ip = $1
          AND created_at > now() - ($2 * interval '1 minute')
        """,
        client_ip,
        window_minutes,
    )


async def insert_exchange_attempt(
    conn: asyncpg.Connection,
    attempt_id: UUID,
    client_ip: str,
) -> None:
    await conn.execute(
        "INSERT INTO magic_link_exchange_attempts (id, requested_ip) VALUES ($1, $2)",
        attempt_id,
        client_ip,
    )


async def consume_magic_link_code(
    conn: asyncpg.Connection,
    code_hash: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        UPDATE magic_link_codes
        SET used_at = now()
        WHERE code_hash = $1
          AND used_at IS NULL
          AND expires_at > now()
        RETURNING email
        """,
        code_hash,
    )


async def find_auth_user_by_email(
    conn: asyncpg.Connection,
    email: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, fullname, email, role, created_at, profile_completed_at
        FROM users WHERE email = $1
        """,
        email,
    )


async def create_auth_user(
    conn: asyncpg.Connection,
    user_id: UUID,
    fullname: str,
    email: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        INSERT INTO users (id, fullname, email)
        VALUES ($1, $2, $3)
        RETURNING id, fullname, email, role, created_at, profile_completed_at
        """,
        user_id,
        fullname,
        email,
    )


async def insert_refresh_session(
    conn: asyncpg.Connection,
    token_hash: str,
    family_id: UUID,
    user_id: UUID,
    expires_at: datetime,
) -> None:
    await conn.execute(
        """
        INSERT INTO refresh_sessions (token_hash, family_id, user_id, expires_at)
        VALUES ($1, $2, $3, $4)
        """,
        token_hash,
        family_id,
        user_id,
        expires_at,
    )


async def find_refresh_session(
    conn: asyncpg.Connection,
    token_hash: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT user_id, family_id, expires_at, revoked_at
        FROM refresh_sessions
        WHERE token_hash = $1
        """,
        token_hash,
    )


async def find_refresh_session_for_update(
    conn: asyncpg.Connection,
    token_hash: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT user_id, family_id, expires_at, revoked_at
        FROM refresh_sessions
        WHERE token_hash = $1
        FOR UPDATE
        """,
        token_hash,
    )


async def revoke_refresh_session_family(
    conn: asyncpg.Connection,
    family_id: UUID,
) -> None:
    await conn.execute(
        """
        UPDATE refresh_sessions
        SET revoked_at = now()
        WHERE family_id = $1 AND revoked_at IS NULL
        """,
        family_id,
    )


async def revoke_refresh_session(
    conn: asyncpg.Connection,
    token_hash: str,
) -> None:
    await conn.execute(
        """
        UPDATE refresh_sessions
        SET revoked_at = now()
        WHERE token_hash = $1
        """,
        token_hash,
    )


async def find_auth_user_by_id(
    conn: asyncpg.Connection,
    user_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, fullname, email, role, created_at
        FROM users WHERE id = $1
        """,
        user_id,
    )


async def rotate_refresh_session(
    conn: asyncpg.Connection,
    token_hash: str,
    replaced_by_token_hash: str,
) -> None:
    await conn.execute(
        """
        UPDATE refresh_sessions
        SET revoked_at = now(), replaced_by_token_hash = $2
        WHERE token_hash = $1
        """,
        token_hash,
        replaced_by_token_hash,
    )


async def find_refresh_session_family(
    conn: asyncpg.Connection,
    token_hash: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT family_id
        FROM refresh_sessions
        WHERE token_hash = $1
        """,
        token_hash,
    )


async def find_access_token_user(
    conn: asyncpg.Connection,
    user_id: UUID,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, fullname, email, role, created_at, profile_completed_at
        FROM users WHERE id = $1
        """,
        user_id,
    )
