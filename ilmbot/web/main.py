"""Veb-panelni ishga tushirish: `python -m ilmbot.web` (uvicorn, `--factory` rejimida)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from ilmbot.config import get_settings
from ilmbot.db import make_engine, make_sessionmaker
from ilmbot.integrations.bot_identity import resolve_bot_username
from ilmbot.services.broadcast import BroadcastService
from ilmbot.web.app import create_app


def build_app() -> FastAPI:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            if settings.bot_token:
                application.state.bot_username = await resolve_bot_username(settings.bot_token)
            yield
        finally:
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


def build_mini_app() -> FastAPI:
    """Tunnel uchun faqat foydalanuvchi interfeysi; admin panel tashqariga chiqmaydi."""
    app = build_app()

    @app.middleware("http")
    async def mini_app_paths_only(request, call_next):
        path = request.url.path
        if (
            path in ("/app", "/app/")
            or path.startswith("/app/api/")
            or path.startswith("/app/media/")
            or path
            in {
                "/static/miniapp.css",
                "/static/miniapp.js",
                "/static/miniapp-reader.js",
                "/static/miniapp-art.svg",
                "/static/miniapp-pattern.svg",
                "/static/vendor/pdfjs/pdf.min.mjs",
                "/static/vendor/pdfjs/pdf.worker.min.mjs",
            }
        ):
            return await call_next(request)
        return JSONResponse({"detail": "Not found"}, status_code=404)

    return app
