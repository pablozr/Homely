from typing import Optional

import asyncpg

from core.config.config import settings


class PostgreSQL:
    pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            dsn=f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}",
            min_size=1,
            max_size=3,
        )

    async def disconnect(self) -> None:
        if self.pool is not None:
            await self.pool.close()

    async def get_db(self):
        if self.pool is None:
            raise RuntimeError("PostgreSQL pool is not initialized")

        async with self.pool.acquire() as conn:
            yield conn


postgresql = PostgreSQL()
