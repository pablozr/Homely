import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from dependencies import auth


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/me",
            "headers": [],
            "query_string": b"",
        }
    )


def bearer(credentials: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)


class BearerDependencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_validates_bearer_authorization_header(self):
        request = make_request()
        conn = object()
        user = {"id": "user-id", "role": "BASIC"}

        with patch.object(auth, "verify_token", AsyncMock(return_value=user)) as verify:
            result = await auth.validate_token(request, bearer("access-token"), conn)

        self.assertEqual(result, user)
        self.assertEqual(request.state.token, "access-token")
        self.assertIs(verify.await_args.kwargs["conn"], conn)
        self.assertEqual(verify.await_args.args[0], "access-token")

    async def test_rejects_missing_credentials(self):
        with self.assertRaises(HTTPException) as context:
            await auth.validate_token(make_request(), None, object())

        self.assertEqual(context.exception.status_code, 401)

    async def test_rejects_expired_token(self):
        with (
            patch.object(auth, "verify_token", AsyncMock(return_value=None)),
            self.assertRaises(HTTPException) as context,
        ):
            await auth.validate_token(make_request(), bearer("access-token"), object())

        self.assertEqual(context.exception.status_code, 401)
