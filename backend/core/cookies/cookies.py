from starlette.responses import Response

from core.config.config import (
    AUTH_COOKIE_MAX_AGE,
    COOKIE_AUTH,
    COOKIE_REFRESH,
    IS_DEVELOPMENT,
    REFRESH_COOKIE_MAX_AGE,
)


def set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=COOKIE_AUTH,
        value=access_token,
        httponly=True,
        secure=not IS_DEVELOPMENT,
        samesite="strict",
        path="/",
        max_age=AUTH_COOKIE_MAX_AGE,
    )
    response.set_cookie(
        key=COOKIE_REFRESH,
        value=refresh_token,
        httponly=True,
        secure=not IS_DEVELOPMENT,
        samesite="strict",
        path="/auth",
        max_age=REFRESH_COOKIE_MAX_AGE,
    )


def delete_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=COOKIE_AUTH, path="/", samesite="strict")
    response.delete_cookie(key=COOKIE_REFRESH, path="/auth", samesite="strict")
