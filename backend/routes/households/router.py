import asyncpg
from fastapi import APIRouter, Depends

from core.postgresql.postgresql import postgresql
from core.responses import default_response
from dependencies import auth, households
from schemas.households import (
    HouseholdCreateRequestModel,
    HouseholdCreatedResponseModel,
    HouseholdSelectionResponseModel,
    HouseholdsResponseModel,
)
from services.households import households_service


router = APIRouter()


@router.post("", status_code=201, response_model=HouseholdCreatedResponseModel)
async def create_household(
    data: HouseholdCreateRequestModel,
    idempotency_key: str = Depends(households.require_idempotency_key),
    user: dict = Depends(auth.validate_token_wrapper),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        households_service.create_household,
        conn,
        user["id"],
        data,
        idempotency_key,
    )


@router.get("", response_model=HouseholdsResponseModel)
async def list_households(
    user: dict = Depends(auth.validate_token_wrapper),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        households_service.list_households,
        conn,
        user["id"],
    )


@router.patch("/{household_id}/selection", response_model=HouseholdSelectionResponseModel)
async def select_household(
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        households_service.select_household,
        conn,
        membership["user_id"],
        membership["household_id"],
    )
