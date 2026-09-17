from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config.config import settings
from core.postgresql.postgresql import postgresql
from routes.auth.router import router as auth_router
from routes.households.router import router as households_router
from routes.profile.router import router as profile_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await postgresql.connect()
    yield
    await postgresql.disconnect()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.API_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(profile_router, prefix="/profile", tags=["profile"])
app.include_router(households_router, prefix="/households", tags=["households"])


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.API_PORT)
