from datetime import datetime, timedelta, timezone
from uuid import uuid4

import asyncpg

from core.config.config import AUTH_COOKIE_MAX_AGE, settings
from core.logger.logger import logger
from core.security.hashing import verify_password
from core.security.jwt_payloads import auth_jwt_payload_from_row
from core.security.security import create_access_token, create_refresh_token, hash_refresh_token
from schemas.auth import LoginRequestModel, user_from_row


async def login(conn: asyncpg.Connection, data: LoginRequestModel) -> dict:
    try:
        row = await conn.fetchrow(
            """
            SELECT id, fullname, email, role, password, created_at
            FROM users WHERE email = $1
            """,
            data.email,
        )

        if not row or not verify_password(data.password, row["password"]):
            return {
                "status": False,
                "status_code": 401,
                "message": "Invalid email or password",
                "data": {},
            }

        token = create_access_token(
            auth_jwt_payload_from_row(row),
            expires_delta=timedelta(seconds=AUTH_COOKIE_MAX_AGE),
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
            "message": "Login successful",
            "data": {
                "user": user_from_row(row),
                "access_token": token,
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
                expires_delta=timedelta(seconds=AUTH_COOKIE_MAX_AGE),
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
