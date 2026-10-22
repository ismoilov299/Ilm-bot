"""Veb-panel bog'liqliklari: sessiya, CSRF, ma'lumotlar bazasi sessiyasi va shablonlarni chizish."""

import datetime as dt
import hmac
from collections.abc import AsyncIterator
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.config import Settings
from ilmbot.db.models import AdminAudit
from ilmbot.services.telegram_html import HtmlError, sanitize
from ilmbot.web.sessions import COOKIE_NAME, AdminSession

TEMPLATES_DIR = Path(__file__).parent / "templates"


class LoginRequired(Exception):
    """Kirmagan foydalanuvchi: kirish sahifasiga yo'naltiriladi."""


def make_templates(settings: Settings) -> Jinja2Templates:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    tz = ZoneInfo(settings.timezone)

    def localtime(value: dt.datetime | None) -> str:
        return value.astimezone(tz).strftime("%d.%m.%Y %H:%M") if value else "-"

    def tghtml(value: str | None) -> Markup:
        """Admin matnini ko'rsatish uchun: ruxsat etilgan teglar saqlanadi, noto'g'ri bo'lsa to'liq escape qilinadi."""
        if not value:
            return Markup("")
        try:
            return Markup(sanitize(value))
        except HtmlError:
            return Markup(escape(value))

    templates.env.filters["localtime"] = localtime
    templates.env.filters["tghtml"] = tghtml
    return templates


async def db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yozuvchi marshrutlar `await session.commit()` ni o'zlari chaqiradi (javob yuborilishidan oldin)."""
    async with request.app.state.sessionmaker() as session:
        yield session


def require_admin(request: Request) -> AdminSession:
    session = request.app.state.sessions.read(request.cookies.get(COOKIE_NAME))
    if session is None:
        raise LoginRequired
    return session


async def verify_csrf(admin: AdminSession = Depends(require_admin), csrf: str = Form("")) -> None:
    if not hmac.compare_digest(admin.csrf.encode(), csrf.encode()):
        raise HTTPException(status_code=403, detail="CSRF tokeni noto'g'ri. Sahifani yangilab qayta urinib ko'ring.")


def render(request: Request, name: str, *, status_code: int = 200, **context):
    admin = context.pop("admin", None)
    return request.app.state.templates.TemplateResponse(
        request,
        name,
        {"admin": admin, "settings": request.app.state.settings, "ok": request.query_params.get("ok"), **context},
        status_code=status_code,
    )


async def audit(session: AsyncSession, admin: AdminSession, action: str, **details) -> None:
    session.add(AdminAudit(actor=admin.username, action=action, details=details or None))
