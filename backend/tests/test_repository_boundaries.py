import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent

SQL_FREE_MODULES = (
    "services/auth/auth_service.py",
    "services/profile/profile_service.py",
    "services/households/households_service.py",
    "services/households/memberships_service.py",
    "services/households/invites_service.py",
    "services/tasks/tasks_service.py",
    "dependencies/households.py",
    "core/security/security.py",
)

QUERY_METHOD_PREFIX = "conn.fetch"
QUERY_METHOD_EXECUTE = "conn.execute"


class ServiceSqlBoundaryTests(unittest.TestCase):
    def test_modules_do_not_call_asyncpg_query_methods_directly(self):
        for relative_path in SQL_FREE_MODULES:
            with self.subTest(module=relative_path):
                source = (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertNotIn(QUERY_METHOD_PREFIX, source)
                self.assertNotIn(QUERY_METHOD_EXECUTE, source)
