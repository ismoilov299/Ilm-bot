from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ilmbot.config import Settings
from ilmbot.services.broadcast import BroadcastService
from ilmbot.services.menu import MENU_VERSION_KEY, MenuService
from ilmbot.web import (
    routes_auth,
    routes_broadcast,
    routes_content,
    routes_inventory,
    routes_menu,
    routes_miniapp,
    routes_places,
    routes_prayer,
    routes_users,
)
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
    app.state.bot_username = None  # web lifespan'da Telegram getMe orqali olinadi
    app.state.sessionmaker = sessionmaker
    app.state.redis = redis
    app.state.broadcasts = broadcasts
    app.state.miniapp_menu = MenuService(version=lambda: redis.get(MENU_VERSION_KEY))
    app.state.templates = make_templates(settings)
    app.state.sessions = SessionManager(
        settings.session_secret, max_age_hours=settings.session_max_hours, secure=settings.cookie_secure
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        headers = dict(SECURITY_HEADERS)
        if request.url.path in ("/app", "/app/") or request.url.path.startswith(("/app/api/", "/app/media/")):
            headers.pop("X-Frame-Options")
            headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' https://telegram.org; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
                "media-src 'self' blob:; worker-src 'self' blob:; "
                "frame-ancestors https://web.telegram.org https://*.telegram.org https://telegram.org; "
                "form-action 'self'; object-src 'none'; base-uri 'self'"
            )
            headers["Permissions-Policy"] = "geolocation=(self)"
        for name, value in headers.items():
            response.headers.setdefault(name, value)
        return response

    @app.exception_handler(LoginRequired)
    async def login_required(request: Request, exc: LoginRequired):
        return RedirectResponse("/login", status_code=303)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> HTMLResponse | JSONResponse:
        if request.url.path.startswith(("/app/api/", "/app/media/")):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
        return render(request, "error.html", status_code=exc.status_code, message=exc.detail)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(routes_auth.router)
    app.include_router(routes_miniapp.router)
    app.include_router(routes_content.router)
    for module in (routes_broadcast, routes_menu, routes_inventory, routes_users, routes_prayer, routes_places):
        app.include_router(module.router)
    return app
