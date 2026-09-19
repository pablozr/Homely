import json
from uuid import uuid4

import asyncpg

from core.logger.logger import logger
from schemas.households import member_from_row
from services.households import households_service


MEMBERS_MESSAGE = "Members retrieved"
REMOVE_MESSAGE = "Member removed"
LEAVE_MESSAGE = "Household left"
TRANSFER_MESSAGE = "Ownership transferred"


async def list_members(conn: asyncpg.Connection, household_id) -> dict:
    try:
        rows = await conn.fetch(
            """
            SELECT hm.id, hm.user_id, u.fullname, hm.role, hm.status, hm.joined_at
            FROM household_members hm
            JOIN users u ON u.id = hm.user_id
            WHERE hm.household_id = $1
              AND hm.status = 'ACTIVE'
            ORDER BY hm.joined_at, hm.id
            """,
            household_id,
        )

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

            target = await conn.fetchrow(
                """
                SELECT id, user_id, role, status
                FROM household_members
                WHERE id = $1 AND household_id = $2
                FOR UPDATE
                """,
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

            removed_at = await conn.fetchval(
                """
                UPDATE household_members
                SET status = 'INACTIVE', left_at = now()
                WHERE id = $1
                RETURNING left_at
                """,
                membership_id,
            )
            await conn.execute(
                """
                INSERT INTO activity_events (
                    id,
                    household_id,
                    actor_user_id,
                    entity_type,
                    entity_id,
                    event_type,
                    metadata
                )
                VALUES ($1, $2, $3, 'household_member', $4, 'MEMBER_REMOVED', $5::jsonb)
                """,
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

            left_at = await conn.fetchval(
                """
                UPDATE household_members
                SET status = 'INACTIVE', left_at = now()
                WHERE id = $1
                RETURNING left_at
                """,
                context["membership_id"],
            )
            await conn.execute(
                """
                INSERT INTO activity_events (
                    id,
                    household_id,
                    actor_user_id,
                    entity_type,
                    entity_id,
                    event_type,
                    metadata
                )
                VALUES ($1, $2, $3, 'household_member', $4, 'MEMBER_LEFT', $5::jsonb)
                """,
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

            target = await conn.fetchrow(
                """
                SELECT id, role, status
                FROM household_members
                WHERE id = $1 AND household_id = $2
                FOR UPDATE
                """,
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

            await conn.execute(
                """
                UPDATE household_members
                SET role = 'MEMBER'
                WHERE id = $1
                """,
                context["membership_id"],
            )
            await conn.execute(
                """
                UPDATE household_members
                SET role = 'OWNER'
                WHERE id = $1
                """,
                target["id"],
            )
            await conn.execute(
                """
                INSERT INTO activity_events (
                    id,
                    household_id,
                    actor_user_id,
                    entity_type,
                    entity_id,
                    event_type,
                    metadata
                )
                VALUES ($1, $2, $3, 'household_member', $4, 'OWNERSHIP_TRANSFERRED', $5::jsonb)
                """,
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
