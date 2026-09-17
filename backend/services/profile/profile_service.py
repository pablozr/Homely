import asyncpg

from core.logger.logger import logger
from schemas.profile import ProfileUpdateRequestModel, profile_from_row


async def get_profile(conn: asyncpg.Connection, user_id) -> dict:
    try:
        row = await conn.fetchrow(
            """
            SELECT id, fullname, role, created_at, profile_completed_at
            FROM users WHERE id = $1
            """,
            user_id,
        )

        if not row:
            return {
                "status": False,
                "status_code": 404,
                "message": "User not found",
                "data": {},
            }

        return {
            "status": True,
            "status_code": 200,
            "message": "Profile retrieved",
            "data": {"user": profile_from_row(row)},
        }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def update_profile(
    conn: asyncpg.Connection,
    user_id,
    data: ProfileUpdateRequestModel,
) -> dict:
    try:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET fullname = $2,
                profile_completed_at = COALESCE(profile_completed_at, now())
            WHERE id = $1
            RETURNING id, fullname, role, created_at, profile_completed_at
            """,
            user_id,
            data.fullname,
        )

        if not row:
            return {
                "status": False,
                "status_code": 404,
                "message": "User not found",
                "data": {},
            }

        return {
            "status": True,
            "status_code": 200,
            "message": "Profile updated",
            "data": {"user": profile_from_row(row)},
        }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }
