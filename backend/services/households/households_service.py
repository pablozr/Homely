import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import asyncpg

from core.logger.logger import logger
from repositories.households import households_repository
from schemas.households import (
    HouseholdCreateRequestModel,
    household_summary_from_row,
)

OPERATION_CREATE = "households.create"
IDEMPOTENCY_TTL = timedelta(hours=24)
CREATE_MESSAGE = "Household created"


def payload_fingerprint(data: HouseholdCreateRequestModel) -> str:
    normalized = {"name": data.name, "timezone": data.timezone}
    serialized = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return sha256(serialized.encode("utf-8")).hexdigest()


async def create_household(
    conn: asyncpg.Connection,
    user_id,
    data: HouseholdCreateRequestModel,
    idempotency_key: str,
) -> dict:
    try:
        fingerprint = payload_fingerprint(data)

        async with conn.transaction():
            await households_repository.acquire_idempotency_lock(
                conn,
                f"{OPERATION_CREATE}:{user_id}:{idempotency_key}",
            )

            record = await households_repository.find_idempotency_record(
                conn,
                user_id,
                OPERATION_CREATE,
                idempotency_key,
            )

            if record and record["expires_at"] > datetime.now(timezone.utc):
                if record["fingerprint"] != fingerprint:
                    return {
                        "status": False,
                        "status_code": 409,
                        "message": "Idempotency key was reused with a different request",
                        "data": {},
                    }

                return {
                    "status": True,
                    "status_code": record["response_status"],
                    "message": CREATE_MESSAGE,
                    "data": json.loads(record["response_data"]),
                }

            household_id = uuid4()
            membership_id = uuid4()

            household = await households_repository.insert_household(
                conn,
                household_id,
                data.name,
                data.timezone,
                user_id,
            )
            membership = await households_repository.insert_owner_membership(
                conn,
                membership_id,
                household_id,
                user_id,
            )
            await households_repository.insert_household_created_event(
                conn,
                uuid4(),
                household_id,
                user_id,
                household_id,
                json.dumps(
                    {"membership_id": str(membership_id)},
                    separators=(",", ":"),
                ),
            )
            await households_repository.update_user_last_household(
                conn,
                user_id,
                household_id,
            )

            response_data = {
                "household": household_summary_from_row(
                    household, "OWNER", membership["joined_at"]
                ),
                "selected_household_id": str(household_id),
            }
            await households_repository.upsert_idempotency_record(
                conn,
                uuid4(),
                user_id,
                OPERATION_CREATE,
                idempotency_key,
                fingerprint,
                json.dumps(
                    {"name": data.name, "timezone": data.timezone},
                    separators=(",", ":"),
                ),
                household_id,
                json.dumps(response_data, separators=(",", ":")),
                datetime.now(timezone.utc) + IDEMPOTENCY_TTL,
            )

            return {
                "status": True,
                "status_code": 201,
                "message": CREATE_MESSAGE,
                "data": response_data,
            }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def list_households(conn: asyncpg.Connection, user_id) -> dict:
    try:
        rows = await households_repository.list_user_households(conn, user_id)

        selected_household_id = None
        if len(rows) == 1:
            selected_household_id = rows[0]["id"]
        elif rows:
            household_ids = [row["id"] for row in rows]
            preferred = rows[0]["last_household_id"]
            selected_household_id = (
                preferred if preferred in household_ids else rows[0]["id"]
            )

        return {
            "status": True,
            "status_code": 200,
            "message": "Households retrieved",
            "data": {
                "households": [
                    household_summary_from_row(row, row["role"], row["joined_at"])
                    for row in rows
                ],
                "selected_household_id": selected_household_id,
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


async def select_household(conn: asyncpg.Connection, user_id, household_id) -> dict:
    try:
        row = await households_repository.set_selected_household(
            conn,
            user_id,
            household_id,
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
            "message": "Household selected",
            "data": {"selected_household_id": row["last_household_id"]},
        }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def lock_active_membership(
    conn: asyncpg.Connection,
    household_id,
    user_id,
    required_role: str | None = None,
) -> tuple[dict | None, dict | None]:
    household = await households_repository.lock_household(conn, household_id)

    if not household:
        return None, {
            "status": False,
            "status_code": 404,
            "message": "Household not found",
            "data": {},
        }

    if household["deactivated_at"] is not None:
        return None, {
            "status": False,
            "status_code": 409,
            "message": "Household is deactivated",
            "data": {},
        }

    membership = await households_repository.lock_active_membership(
        conn,
        household_id,
        user_id,
    )

    if not membership:
        return None, {
            "status": False,
            "status_code": 403,
            "message": "Active membership required",
            "data": {},
        }

    if required_role is not None and membership["role"] != required_role:
        return None, {
            "status": False,
            "status_code": 403,
            "message": "Owner membership required",
            "data": {},
        }

    return {"membership_id": membership["id"], "role": membership["role"]}, None
