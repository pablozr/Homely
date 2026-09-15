import json
import unittest
from datetime import datetime, timezone

from core.responses import default_response


class DefaultResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_formats_async_service_result(self):
        async def service():
            return {
                "status": True,
                "status_code": 201,
                "message": "Created",
                "data": {"id": 1},
            }

        response = await default_response(service)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(json.loads(response.body), {"message": "Created", "data": {"id": 1}})

    async def test_formats_sync_service_result_and_excludes_private_data(self):
        def service():
            return {
                "status": False,
                "status_code": 401,
                "message": "Invalid credentials",
                "data": {"access_token": "secret"},
            }

        response = await default_response(service, exclude_data=("access_token",))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.body),
            {"message": "Invalid credentials", "data": {}},
        )

    async def test_calls_success_handler_after_excluding_private_data(self):
        def service():
            return {
                "status": True,
                "status_code": 200,
                "message": "Logged in",
                "data": {"access_token": "secret"},
            }

        response = await default_response(
            service,
            exclude_data=("access_token",),
            on_success=lambda response, result: response.headers.__setitem__(
                "X-Token", result["data"]["access_token"]
            ),
        )

        self.assertEqual(response.headers["X-Token"], "secret")
        self.assertEqual(json.loads(response.body), {"message": "Logged in", "data": {}})

    async def test_returns_an_empty_response_for_no_content(self):
        def service():
            return {
                "status": True,
                "status_code": 204,
                "message": "Deleted",
                "data": {},
            }

        response = await default_response(service)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.body, b"")

    async def test_serializes_non_json_data(self):
        created_at = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)

        def service():
            return {
                "status": True,
                "status_code": 200,
                "message": "Loaded",
                "data": {"created_at": created_at},
            }

        response = await default_response(service)

        self.assertEqual(
            json.loads(response.body),
            {"message": "Loaded", "data": {"created_at": "2026-08-11T12:00:00+00:00"}},
        )
