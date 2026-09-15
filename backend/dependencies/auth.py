import asyncpg
from fastapi import Depends, HTTPException, Request

from core.config.config import COOKIE_AUTH, ROLE_RANK_BY_NAME
from core.logger.logger import logger
from core.postgresql.postgresql import postgresql
from core.security.security import verify_token


async def validate_token(
    request: Request,
    conn: asyncpg.Connection,
    expected_type: str = "auth",
) -> dict:
    try:
        token = request.cookies.get(COOKIE_AUTH)

        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user = await verify_token(token, conn=conn, expected_type=expected_type)

        if user is None:
            raise HTTPException(status_code=401, detail="Token has expired")

        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        request.state.token = token

        return user

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(exc)
        raise HTTPException(status_code=401, detail="Invalid token") from exc


async def validate_token_wrapper(
    request: Request,
    conn: asyncpg.Connection = Depends(postgresql.get_db),
) -> dict:
    return await validate_token(request, conn)


def require_minimum_rank(minimum_rank: int):
    async def dependency(user: dict = Depends(validate_token_wrapper)) -> dict:
        rank = ROLE_RANK_BY_NAME.get(user.get("role", "").upper(), 0)

        if rank < minimum_rank:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return user

    return dependency


def require_admin_rank():
    return require_minimum_rank(2)
