"""Veb-panelni ishga tushirish: `python -m ilmbot.web` (uvicorn, `--factory` rejimida)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from ilmbot.config import get_settings
from ilmbot.db import make_engine, make_sessionmaker
from ilmbot.services.broadcast import BroadcastService
from ilmbot.web.app import create_app


def build_app() -> FastAPI:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await redis.aclose()
        await engine.dispose()

    app = create_app(
        settings=settings,
        sessionmaker=make_sessionmaker(engine),
        redis=redis,
        broadcasts=BroadcastService(),  # panelda yuborish yo'q: faqat ishlarni yaratadi va boshqaradi
    )
    app.router.lifespan_context = lifespan
    return app
