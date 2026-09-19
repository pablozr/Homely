from uuid import UUID

import asyncpg
from fastapi import Depends, Header, HTTPException

from core.postgresql.postgresql import postgresql
from dependencies import auth
from repositories.households import households_repository

IDEMPOTENCY_KEY_MAX_LENGTH = 255


def require_idempotency_key(
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> str:
    key = idempotency_key.strip()

    if not key or len(key) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise HTTPException(
            status_code=422,
            detail="Idempotency-Key header must have 1 to 255 characters",
        )

    return key


async def require_active_membership(
    household_id: UUID,
    user: dict = Depends(auth.validate_token_wrapper),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
) -> dict:
    row = await households_repository.find_membership_context(
        conn,
        household_id,
        user["id"],
    )

    if not row:
        raise HTTPException(status_code=404, detail="Household not found")

    if row["deactivated_at"] is not None:
        raise HTTPException(status_code=409, detail="Household is deactivated")

    if row["membership_id"] is None:
        raise HTTPException(status_code=403, detail="Active membership required")

    return {
        "user_id": user["id"],
        "household_id": row["household_id"],
        "membership_id": row["membership_id"],
        "role": row["role"],
    }


async def require_owner_membership(
    membership: dict = Depends(require_active_membership),
) -> dict:
    if membership["role"] != "OWNER":
        raise HTTPException(status_code=403, detail="Owner membership required")

    return membership
