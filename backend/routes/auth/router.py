import asyncpg
from fastapi import APIRouter, Depends, Request

from core.config.config import COOKIE_REFRESH
from core.cookies import delete_auth_cookies, set_session_cookies
from core.postgresql.postgresql import postgresql
from core.responses import default_response
from dependencies import auth
from schemas.auth import LoginRequestModel
from services.auth import auth_service


router = APIRouter()


@router.post("/login")
async def login(
    data: LoginRequestModel,
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        auth_service.login,
        conn,
        data,
        exclude_data=("access_token", "refresh_token"),
        on_success=lambda response, result: set_session_cookies(
            response,
            result["data"]["access_token"],
            result["data"]["refresh_token"],
        ),
    )


@router.post("/refresh")
async def refresh(
    request: Request,
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        auth_service.refresh,
        conn,
        request.cookies.get(COOKIE_REFRESH),
        exclude_data=("access_token", "refresh_token"),
        on_success=lambda response, result: set_session_cookies(
            response,
            result["data"]["access_token"],
            result["data"]["refresh_token"],
        ),
    )


@router.post("/logout")
async def logout(
    request: Request,
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        auth_service.logout,
        conn,
        request.cookies.get(COOKIE_REFRESH),
        on_success=lambda response, _: delete_auth_cookies(response),
    )


@router.get("/me")
async def me(user: dict = Depends(auth.validate_token_wrapper)):
    return {"data": {"user": user}}
