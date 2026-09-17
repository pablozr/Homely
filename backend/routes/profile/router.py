import asyncpg
from fastapi import APIRouter, Depends

from core.postgresql.postgresql import postgresql
from core.responses import default_response
from dependencies import auth
from schemas.profile import ProfileUpdateRequestModel
from services.profile import profile_service


router = APIRouter()


@router.get("/me")
async def get_profile(
    user: dict = Depends(auth.validate_token_wrapper),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(profile_service.get_profile, conn, user["id"])


@router.patch("/me")
async def update_profile(
    data: ProfileUpdateRequestModel,
    user: dict = Depends(auth.validate_token_wrapper),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        profile_service.update_profile,
        conn,
        user["id"],
        data,
    )
