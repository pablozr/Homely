from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

import asyncpg
import jwt

from core.config.config import settings
from core.logger.logger import logger


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire})

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token() -> str:
    return token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


async def verify_token(
    token: str,
    conn: asyncpg.Connection,
    expected_type: str = "auth",
) -> dict | bool | None:
    try:
        if token.startswith("Bearer "):
            token = token[7:]

        payload = decode_access_token(token)

        if payload.get("type") != expected_type:
            raise jwt.InvalidTokenError("Token type mismatch")

        if not payload.get("userId"):
            raise jwt.InvalidTokenError("Invalid token payload")

        try:
            user_id = UUID(payload["userId"])
        except (TypeError, ValueError) as exc:
            raise jwt.InvalidTokenError("Invalid token payload") from exc

        row = await conn.fetchrow(
            """
            SELECT id, fullname, email, role, created_at
            FROM users WHERE id = $1
            """,
            user_id,
        )

        if not row:
            raise jwt.InvalidSignatureError("User not found")

        return dict(row)

    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.error("Invalid token")
        return False
