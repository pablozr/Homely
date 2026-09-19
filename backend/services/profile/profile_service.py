import asyncpg

from core.logger.logger import logger
from repositories import profile_repository
from schemas.profile import ProfileUpdateRequestModel, profile_from_row


async def get_profile(conn: asyncpg.Connection, user_id) -> dict:
    try:
        row = await profile_repository.find_profile(conn, user_id)

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
        row = await profile_repository.update_profile_completion(
            conn,
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
