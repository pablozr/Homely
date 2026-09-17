import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import asyncpg

from core.config.config import settings
from core.email import send_magic_link_email
from core.logger.logger import logger
from core.security.jwt_payloads import auth_jwt_payload_from_row
from core.security.security import (
    create_access_token,
    create_magic_link_code,
    create_refresh_token,
    hash_magic_link_code,
    hash_refresh_token,
)
from schemas.auth import ExchangeRequestModel, MagicLinkRequestModel, user_from_row


async def request_magic_link(
    conn: asyncpg.Connection,
    data: MagicLinkRequestModel,
    client_ip: str | None,
) -> dict:
    try:
        now = datetime.now(timezone.utc)
        code = create_magic_link_code()
        code_hash = hash_magic_link_code(code)
        expires_at = now + timedelta(minutes=settings.MAGIC_LINK_EXPIRE_MINUTES)
        email_window_start = now - timedelta(
            minutes=settings.MAGIC_LINK_EMAIL_RATE_WINDOW_MINUTES
        )
        ip_window_start = now - timedelta(
            minutes=settings.MAGIC_LINK_IP_RATE_WINDOW_MINUTES
        )

        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                f"email:{data.email}",
            )
            if client_ip:
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                    f"ip:{client_ip}",
                )

            email_requests = await conn.fetchval(
                """
                SELECT count(*)
                FROM magic_link_codes
                WHERE email = $1 AND created_at > $2
                """,
                data.email,
                email_window_start,
            )
            if email_requests >= settings.MAGIC_LINK_EMAIL_RATE_LIMIT:
                return {
                    "status": False,
                    "status_code": 429,
                    "message": "Too many magic link requests",
                    "data": {},
                }

            if client_ip:
                ip_requests = await conn.fetchval(
                    """
                    SELECT count(*)
                    FROM magic_link_codes
                    WHERE requested_ip = $1 AND created_at > $2
                    """,
                    client_ip,
                    ip_window_start,
                )
                if ip_requests >= settings.MAGIC_LINK_IP_RATE_LIMIT:
                    return {
                        "status": False,
                        "status_code": 429,
                        "message": "Too many magic link requests",
                        "data": {},
                    }

            code_id = uuid4()
            await conn.execute(
                """
                INSERT INTO magic_link_codes (id, email, code_hash, requested_ip, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                code_id,
                data.email,
                code_hash,
                client_ip,
                expires_at,
            )

        magic_link = f"{settings.MAGIC_LINK_DEEP_LINK_BASE}?auth_code={code}"
        await asyncio.to_thread(send_magic_link_email, data.email, magic_link)

        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                f"email:{data.email}",
            )
            await conn.execute(
                """
                UPDATE magic_link_codes
                SET used_at = now()
                WHERE email = $1 AND id != $2 AND used_at IS NULL
                """,
                data.email,
                code_id,
            )

        return {
            "status": True,
            "status_code": 200,
            "message": "Magic link sent",
            "data": {},
        }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def exchange(
    conn: asyncpg.Connection,
    data: ExchangeRequestModel,
    client_ip: str | None = None,
) -> dict:
    try:
        code_hash = hash_magic_link_code(data.auth_code)

        async with conn.transaction():
            if client_ip:
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                    f"exchange-ip:{client_ip}",
                )
                attempts = await conn.fetchval(
                    """
                    SELECT count(*)
                    FROM magic_link_exchange_attempts
                    WHERE requested_ip = $1
                      AND created_at > now() - ($2 * interval '1 minute')
                    """,
                    client_ip,
                    settings.MAGIC_LINK_EXCHANGE_IP_RATE_WINDOW_MINUTES,
                )
                if attempts >= settings.MAGIC_LINK_EXCHANGE_IP_RATE_LIMIT:
                    return {
                        "status": False,
                        "status_code": 429,
                        "message": "Too many exchange attempts",
                        "data": {},
                    }
                await conn.execute(
                    "INSERT INTO magic_link_exchange_attempts (id, requested_ip) VALUES ($1, $2)",
                    uuid4(),
                    client_ip,
                )
            consumed = await conn.fetchrow(
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

            if not consumed:
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid or expired code",
                    "data": {},
                }

            email = consumed["email"]
            row = await conn.fetchrow(
                """
                SELECT id, fullname, email, role, created_at, profile_completed_at
                FROM users WHERE email = $1
                """,
                email,
            )

            if not row:
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (id, fullname, email)
                    VALUES ($1, $2, $3)
                    RETURNING id, fullname, email, role, created_at, profile_completed_at
                    """,
                    uuid4(),
                    email.split("@", 1)[0],
                    email,
                )

            access_token = create_access_token(
                auth_jwt_payload_from_row(row),
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            )
            refresh_token = create_refresh_token()
            refresh_expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
            await conn.execute(
                """
                INSERT INTO refresh_sessions (token_hash, family_id, user_id, expires_at)
                VALUES ($1, $2, $3, $4)
                """,
                hash_refresh_token(refresh_token),
                uuid4(),
                row["id"],
                refresh_expires_at,
            )

            return {
                "status": True,
                "status_code": 200,
                "message": "Session created",
                "data": {
                    "user": user_from_row(row),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def refresh(conn: asyncpg.Connection, refresh_token: str | None) -> dict:
    if not refresh_token:
        return {
            "status": False,
            "status_code": 401,
            "message": "Invalid refresh token",
            "data": {},
        }

    token_hash = hash_refresh_token(refresh_token)

    try:
        async with conn.transaction():
            session = await conn.fetchrow(
                """
                SELECT user_id, family_id, expires_at, revoked_at
                FROM refresh_sessions
                WHERE token_hash = $1
                """,
                token_hash,
            )

            if not session:
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid refresh token",
                    "data": {},
                }

            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                str(session["family_id"]),
            )
            session = await conn.fetchrow(
                """
                SELECT user_id, family_id, expires_at, revoked_at
                FROM refresh_sessions
                WHERE token_hash = $1
                FOR UPDATE
                """,
                token_hash,
            )

            if session["revoked_at"]:
                await conn.execute(
                    """
                    UPDATE refresh_sessions
                    SET revoked_at = now()
                    WHERE family_id = $1 AND revoked_at IS NULL
                    """,
                    session["family_id"],
                )
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid refresh token",
                    "data": {},
                }

            if session["expires_at"] <= datetime.now(timezone.utc):
                await conn.execute(
                    """
                    UPDATE refresh_sessions
                    SET revoked_at = now()
                    WHERE token_hash = $1
                    """,
                    token_hash,
                )
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid refresh token",
                    "data": {},
                }

            row = await conn.fetchrow(
                """
                SELECT id, fullname, email, role, created_at
                FROM users WHERE id = $1
                """,
                session["user_id"],
            )

            if not row:
                await conn.execute(
                    """
                    UPDATE refresh_sessions
                    SET revoked_at = now()
                    WHERE token_hash = $1
                    """,
                    token_hash,
                )
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid refresh token",
                    "data": {},
                }

            access_token = create_access_token(
                auth_jwt_payload_from_row(row),
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            )
            next_refresh_token = create_refresh_token()
            next_token_hash = hash_refresh_token(next_refresh_token)
            next_expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
            await conn.execute(
                """
                UPDATE refresh_sessions
                SET revoked_at = now(), replaced_by_token_hash = $2
                WHERE token_hash = $1
                """,
                token_hash,
                next_token_hash,
            )
            await conn.execute(
                """
                INSERT INTO refresh_sessions (token_hash, family_id, user_id, expires_at)
                VALUES ($1, $2, $3, $4)
                """,
                next_token_hash,
                session["family_id"],
                session["user_id"],
                next_expires_at,
            )

            return {
                "status": True,
                "status_code": 200,
                "message": "Token refreshed",
                "data": {
                    "access_token": access_token,
                    "refresh_token": next_refresh_token,
                },
            }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def logout(conn: asyncpg.Connection, refresh_token: str | None) -> dict:
    if refresh_token:
        try:
            token_hash = hash_refresh_token(refresh_token)
            async with conn.transaction():
                session = await conn.fetchrow(
                    """
                    SELECT family_id
                    FROM refresh_sessions
                    WHERE token_hash = $1
                    """,
                    token_hash,
                )

                if session:
                    await conn.execute(
                        "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                        str(session["family_id"]),
                    )
                    await conn.execute(
                        """
                        UPDATE refresh_sessions
                        SET revoked_at = now()
                        WHERE family_id = $1 AND revoked_at IS NULL
                        """,
                        session["family_id"],
                    )
        except Exception as exc:
            logger.exception(exc)
            return {
                "status": False,
                "status_code": 500,
                "message": "Internal server error",
                "data": {},
            }

    return {
        "status": True,
        "status_code": 200,
        "message": "Logged out",
        "data": {},
    }
