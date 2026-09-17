import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import asyncpg

from core.logger.logger import logger
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
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                f"{OPERATION_CREATE}:{user_id}:{idempotency_key}",
            )

            record = await conn.fetchrow(
                """
                SELECT fingerprint, response_status, response_data, expires_at
                FROM idempotency_records
                WHERE user_id = $1
                  AND household_id IS NULL
                  AND operation = $2
                  AND idempotency_key = $3
                """,
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

            household = await conn.fetchrow(
                """
                INSERT INTO households (id, name, timezone, created_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id, name, timezone, default_due_time, created_at
                """,
                household_id,
                data.name,
                data.timezone,
                user_id,
            )
            membership = await conn.fetchrow(
                """
                INSERT INTO household_members (id, household_id, user_id, role, status)
                VALUES ($1, $2, $3, 'OWNER', 'ACTIVE')
                RETURNING joined_at
                """,
                membership_id,
                household_id,
                user_id,
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
                VALUES ($1, $2, $3, 'household', $4, 'HOUSEHOLD_CREATED', $5::jsonb)
                """,
                uuid4(),
                household_id,
                user_id,
                household_id,
                json.dumps(
                    {"membership_id": str(membership_id)},
                    separators=(",", ":"),
                ),
            )
            await conn.execute(
                "UPDATE users SET last_household_id = $2 WHERE id = $1",
                user_id,
                household_id,
            )

            response_data = {
                "household": household_summary_from_row(
                    household, "OWNER", membership["joined_at"]
                ),
                "selected_household_id": str(household_id),
            }
            await conn.execute(
                """
                INSERT INTO idempotency_records (
                    id,
                    user_id,
                    household_id,
                    operation,
                    idempotency_key,
                    fingerprint,
                    payload,
                    resource_id,
                    response_status,
                    response_data,
                    expires_at
                )
                VALUES ($1, $2, NULL, $3, $4, $5, $6::jsonb, $7, 201, $8::jsonb, $9)
                ON CONFLICT ON CONSTRAINT uq_idempotency_records_scope
                DO UPDATE SET
                    fingerprint = EXCLUDED.fingerprint,
                    payload = EXCLUDED.payload,
                    resource_id = EXCLUDED.resource_id,
                    response_status = EXCLUDED.response_status,
                    response_data = EXCLUDED.response_data,
                    created_at = now(),
                    expires_at = EXCLUDED.expires_at
                """,
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
        rows = await conn.fetch(
            """
            SELECT h.id,
                   h.name,
                   h.timezone,
                   h.default_due_time,
                   h.created_at,
                   hm.role,
                   hm.joined_at,
                   u.last_household_id
            FROM household_members hm
            JOIN households h ON h.id = hm.household_id
            JOIN users u ON u.id = hm.user_id
            WHERE hm.user_id = $1
              AND hm.status = 'ACTIVE'
              AND h.deactivated_at IS NULL
            ORDER BY hm.joined_at DESC, h.id
            """,
            user_id,
        )

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
        row = await conn.fetchrow(
            """
            UPDATE users
            SET last_household_id = $2
            WHERE id = $1
            RETURNING last_household_id
            """,
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
