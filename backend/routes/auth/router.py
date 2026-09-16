import asyncpg
from fastapi import APIRouter, Depends, Request

from core.postgresql.postgresql import postgresql
from core.responses import default_response
from dependencies import auth
from schemas.auth import (
    ExchangeRequestModel,
    MagicLinkRequestModel,
    RefreshTokenRequestModel,
)
from services.auth import auth_service


router = APIRouter()


@router.post("/magic-link")
async def request_magic_link(
    data: MagicLinkRequestModel,
    request: Request,
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        auth_service.request_magic_link,
        conn,
        data,
        client_ip=request.client.host if request.client else None,
    )


@router.post("/exchange")
async def exchange(
    data: ExchangeRequestModel,
    request: Request,
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        auth_service.exchange,
        conn,
        data,
        client_ip=request.client.host if request.client else None,
    )


@router.post("/refresh")
async def refresh(
    data: RefreshTokenRequestModel,
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(auth_service.refresh, conn, data.refresh_token)


@router.post("/logout")
async def logout(
    data: RefreshTokenRequestModel,
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(auth_service.logout, conn, data.refresh_token)


@router.get("/me")
async def me(user: dict = Depends(auth.validate_token_wrapper)):
    return {"data": {"user": user}}
