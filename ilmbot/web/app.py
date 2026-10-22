from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ilmbot.config import Settings
from ilmbot.services.broadcast import BroadcastService
from ilmbot.web import routes_auth, routes_broadcast
from ilmbot.web.deps import LoginRequired, make_templates, render
from ilmbot.web.sessions import SessionManager

STATIC_DIR = Path(__file__).parent / "static"

SECURITY_HEADERS = {
    # Tashqi skript/uslub yo'q: hammasi shu domendan
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cache-Control": "no-store",
}


def create_app(
    *, settings: Settings, sessionmaker: async_sessionmaker[AsyncSession], redis: Redis, broadcasts: BroadcastService
) -> FastAPI:
    if not settings.admin_password_hash:
        raise RuntimeError("ADMIN_PASSWORD_HASH o'rnatilmagan: python -m ilmbot.cli hash-password")
    app = FastAPI(title="Ilm yo'lida", docs_url=None, redoc_url=None, openapi_url=None)  # API hujjatlari yopiq
    app.state.settings = settings
    app.state.sessionmaker = sessionmaker
    app.state.redis = redis
    app.state.broadcasts = broadcasts
    app.state.templates = make_templates(settings)
    app.state.sessions = SessionManager(
        settings.session_secret, max_age_hours=settings.session_max_hours, secure=settings.cookie_secure
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    @app.exception_handler(LoginRequired)
    async def login_required(request: Request, exc: LoginRequired):
        return RedirectResponse("/login", status_code=303)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> HTMLResponse:
        return render(request, "error.html", status_code=exc.status_code, message=exc.detail)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(routes_auth.router)
    app.include_router(routes_broadcast.router)
    return app
