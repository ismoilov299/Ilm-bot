from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.security import verify_password
from ilmbot.services.stats import overview
from ilmbot.web.deps import db_session, render, require_admin, verify_csrf
from ilmbot.web.sessions import AdminSession

router = APIRouter()

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _client_key(request: Request) -> str:
    return f"login:{request.client.host if request.client else 'unknown'}"


@router.get("/login")
async def login_form(request: Request):
    return render(request, "login.html")


@router.post("/login")
async def login(request: Request, username: str = Form(""), password: str = Form("")):
    redis, settings = request.app.state.redis, request.app.state.settings
    key = _client_key(request)
    if int(await redis.get(key) or 0) >= MAX_LOGIN_ATTEMPTS:
        return render(
            request, "login.html", status_code=429, error="Urinishlar ko'p. 15 daqiqadan keyin qayta urinib ko'ring."
        )

    # Foydalanuvchi nomi noto'g'ri bo'lsa ham parol tekshiruvi bajariladi (vaqt farqi orqali nom bilinmasligi uchun)
    password_ok = verify_password(password, settings.admin_password_hash)
    if not (password_ok and username == settings.admin_username):
        attempts = await redis.incr(key)
        if attempts == 1:
            await redis.expire(key, LOCKOUT_SECONDS)
        return render(request, "login.html", status_code=401, error="Login yoki parol noto'g'ri.")

    await redis.delete(key)
    response = RedirectResponse("/", status_code=303)
    request.app.state.sessions.start(response, username)
    return response


@router.post("/logout")
async def logout(request: Request, _: None = Depends(verify_csrf)):
    response = RedirectResponse("/login", status_code=303)
    request.app.state.sessions.end(response)
    return response


@router.get("/")
async def dashboard(
    request: Request, admin: AdminSession = Depends(require_admin), session: AsyncSession = Depends(db_session)
):
    return render(request, "dashboard.html", admin=admin, nav="dashboard", stats=await overview(session))
