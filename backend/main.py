from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(
    title="GoodWe API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(
    api_router,
    prefix="/api",
)