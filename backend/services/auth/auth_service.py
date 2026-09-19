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
from repositories import auth_repository
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
            await auth_repository.acquire_advisory_lock(conn, f"email:{data.email}")
            if client_ip:
                await auth_repository.acquire_advisory_lock(conn, f"ip:{client_ip}")

            email_requests = await auth_repository.count_magic_link_requests_by_email(
                conn,
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
                ip_requests = await auth_repository.count_magic_link_requests_by_ip(
                    conn,
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
            await auth_repository.insert_magic_link_code(
                conn,
                code_id,
                data.email,
                code_hash,
                client_ip,
                expires_at,
            )

        magic_link = f"{settings.MAGIC_LINK_DEEP_LINK_BASE}?auth_code={code}"
        await asyncio.to_thread(send_magic_link_email, data.email, magic_link)

        async with conn.transaction():
            await auth_repository.acquire_advisory_lock(conn, f"email:{data.email}")
            await auth_repository.invalidate_magic_link_codes_for_email(
                conn,
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
                await auth_repository.acquire_advisory_lock(
                    conn, f"exchange-ip:{client_ip}"
                )
                attempts = await auth_repository.count_exchange_attempts_by_ip(
                    conn,
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
                await auth_repository.insert_exchange_attempt(
                    conn,
                    uuid4(),
                    client_ip,
                )
            consumed = await auth_repository.consume_magic_link_code(conn, code_hash)

            if not consumed:
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid or expired code",
                    "data": {},
                }

            email = consumed["email"]
            row = await auth_repository.find_auth_user_by_email(conn, email)

            if not row:
                row = await auth_repository.create_auth_user(
                    conn,
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
            await auth_repository.insert_refresh_session(
                conn,
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
            session = await auth_repository.find_refresh_session(conn, token_hash)

            if not session:
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid refresh token",
                    "data": {},
                }

            await auth_repository.acquire_advisory_lock(
                conn,
                str(session["family_id"]),
            )
            session = await auth_repository.find_refresh_session_for_update(
                conn,
                token_hash,
            )

            if session["revoked_at"]:
                await auth_repository.revoke_refresh_session_family(
                    conn,
                    session["family_id"],
                )
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid refresh token",
                    "data": {},
                }

            if session["expires_at"] <= datetime.now(timezone.utc):
                await auth_repository.revoke_refresh_session(conn, token_hash)
                return {
                    "status": False,
                    "status_code": 401,
                    "message": "Invalid refresh token",
                    "data": {},
                }

            row = await auth_repository.find_auth_user_by_id(
                conn,
                session["user_id"],
            )

            if not row:
                await auth_repository.revoke_refresh_session(conn, token_hash)
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
            await auth_repository.rotate_refresh_session(
                conn,
                token_hash,
                next_token_hash,
            )
            await auth_repository.insert_refresh_session(
                conn,
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
                session = await auth_repository.find_refresh_session_family(
                    conn,
                    token_hash,
                )

                if session:
                    await auth_repository.acquire_advisory_lock(
                        conn,
                        str(session["family_id"]),
                    )
                    await auth_repository.revoke_refresh_session_family(
                        conn,
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
