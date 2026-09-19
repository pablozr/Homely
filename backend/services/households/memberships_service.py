import json
from uuid import uuid4

import asyncpg

from core.logger.logger import logger
from repositories.households import memberships_repository
from schemas.households import member_from_row
from services.households import households_service


MEMBERS_MESSAGE = "Members retrieved"
REMOVE_MESSAGE = "Member removed"
LEAVE_MESSAGE = "Household left"
TRANSFER_MESSAGE = "Ownership transferred"


async def list_members(conn: asyncpg.Connection, household_id) -> dict:
    try:
        rows = await memberships_repository.list_active_members(conn, household_id)

        return {
            "status": True,
            "status_code": 200,
            "message": MEMBERS_MESSAGE,
            "data": {"memberships": [member_from_row(row) for row in rows]},
        }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def remove_member(
    conn: asyncpg.Connection,
    actor_user_id,
    household_id,
    membership_id,
) -> dict:
    try:
        async with conn.transaction():
            _context, error = await households_service.lock_active_membership(
                conn, household_id, actor_user_id, required_role="OWNER"
            )
            if error:
                return error

            target = await memberships_repository.lock_removal_target(
                conn,
                membership_id,
                household_id,
            )

            if not target or target["status"] != "ACTIVE":
                return {
                    "status": False,
                    "status_code": 404,
                    "message": "Membership not found",
                    "data": {},
                }

            if target["role"] == "OWNER":
                return {
                    "status": False,
                    "status_code": 409,
                    "message": "Owner cannot be removed",
                    "data": {},
                }

            removed_at = await memberships_repository.deactivate_membership(
                conn,
                membership_id,
            )
            await memberships_repository.insert_member_removed_event(
                conn,
                uuid4(),
                household_id,
                actor_user_id,
                membership_id,
                json.dumps(
                    {
                        "membership_id": str(membership_id),
                        "removed_user_id": str(target["user_id"]),
                    },
                    separators=(",", ":"),
                ),
            )

            return {
                "status": True,
                "status_code": 200,
                "message": REMOVE_MESSAGE,
                "data": {
                    "membership_id": membership_id,
                    "removed_at": removed_at.isoformat(),
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


async def leave_household(conn: asyncpg.Connection, user_id, household_id) -> dict:
    try:
        async with conn.transaction():
            context, error = await households_service.lock_active_membership(
                conn, household_id, user_id
            )
            if error:
                return error

            if context["role"] == "OWNER":
                return {
                    "status": False,
                    "status_code": 409,
                    "message": "Owner cannot leave the household",
                    "data": {},
                }

            left_at = await memberships_repository.deactivate_membership(
                conn,
                context["membership_id"],
            )
            await memberships_repository.insert_member_left_event(
                conn,
                uuid4(),
                household_id,
                user_id,
                context["membership_id"],
                json.dumps(
                    {"membership_id": str(context["membership_id"])},
                    separators=(",", ":"),
                ),
            )

            return {
                "status": True,
                "status_code": 200,
                "message": LEAVE_MESSAGE,
                "data": {
                    "household_id": household_id,
                    "left_at": left_at.isoformat(),
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


async def transfer_ownership(
    conn: asyncpg.Connection,
    actor_user_id,
    household_id,
    target_membership_id,
) -> dict:
    try:
        async with conn.transaction():
            context, error = await households_service.lock_active_membership(
                conn, household_id, actor_user_id, required_role="OWNER"
            )
            if error:
                return error

            target = await memberships_repository.lock_transfer_target(
                conn,
                target_membership_id,
                household_id,
            )

            if not target or target["status"] != "ACTIVE":
                return {
                    "status": False,
                    "status_code": 404,
                    "message": "Membership not found",
                    "data": {},
                }

            if target["role"] != "MEMBER":
                return {
                    "status": False,
                    "status_code": 409,
                    "message": "Target must be an active member",
                    "data": {},
                }

            await memberships_repository.demote_membership_to_member(
                conn,
                context["membership_id"],
            )
            await memberships_repository.promote_membership_to_owner(
                conn,
                target["id"],
            )
            await memberships_repository.insert_ownership_transferred_event(
                conn,
                uuid4(),
                household_id,
                actor_user_id,
                target["id"],
                json.dumps(
                    {
                        "previous_owner_membership_id": str(context["membership_id"]),
                        "new_owner_membership_id": str(target["id"]),
                    },
                    separators=(",", ":"),
                ),
            )

            return {
                "status": True,
                "status_code": 200,
                "message": TRANSFER_MESSAGE,
                "data": {
                    "household_id": household_id,
                    "previous_owner_membership_id": context["membership_id"],
                    "previous_owner_role": "MEMBER",
                    "new_owner_membership_id": target["id"],
                    "new_owner_role": "OWNER",
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
