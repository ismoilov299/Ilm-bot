"""Foydalanuvchi Mini App'i: mavjud bot bilan umumiy menyu, profil va namoz sozlamalari."""

import datetime as dt
from dataclasses import asdict
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Region, User
from ilmbot.integrations.prayer_calc import PRAYERS
from ilmbot.services.mosques import MosqueService
from ilmbot.services.prayers import PrayerService
from ilmbot.services.users import UserService
from ilmbot.web.deps import db_session
from ilmbot.web.miniapp_auth import InitDataError, TelegramIdentity, validate_init_data

router = APIRouter(prefix="/app")


async def identity(request: Request, authorization: str = Header("")) -> TelegramIdentity:
    scheme, _, raw = authorization.partition(" ")
    if scheme.lower() != "tma":
        raise HTTPException(401, "Mini App'ni Telegram bot orqali oching")
    settings = request.app.state.settings
    try:
        user = validate_init_data(raw, settings.bot_token, max_age=settings.mini_app_auth_max_age)
    except InitDataError as exc:
        raise HTTPException(401, str(exc)) from exc
    # Har bir shaxs uchun umumiy API limiti; Telegram ma'lumoti faqat imzo tekshirilgach ishlatiladi.
    key = f"miniapp:api:{user.id}:{int(dt.datetime.now(dt.UTC).timestamp()) // 60}"
    count = await request.app.state.redis.incr(key)
    if count == 1:
        await request.app.state.redis.expire(key, 120)
    if count > 120:
        raise HTTPException(429, "So'rovlar ko'p. Bir daqiqadan keyin qayta urinib ko'ring")
    return user


async def current_user(who: TelegramIdentity = Depends(identity), session: AsyncSession = Depends(db_session)) -> User:
    await UserService().touch(session, who.id, who.name, unblock=False)
    await session.commit()
    return await session.get(User, who.id, populate_existing=True)


def today(request: Request) -> dt.date:
    return dt.datetime.now(ZoneInfo(request.app.state.settings.timezone)).date()


async def active_region(session: AsyncSession, region_id: int | None) -> Region:
    region = await session.get(Region, region_id) if region_id else None
    if region is None or not region.is_active:
        raise HTTPException(404, "Shahar topilmadi yoki faol emas")
    return region


def profile(user: User) -> dict:
    return {"id": user.id, "name": user.name, "region_id": user.region_id, "subscribed": user.subscribed}


class PlainText(HTMLParser):
    def __init__(self, raw: str):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.feed(raw)

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


@router.get("")
@router.get("/", include_in_schema=False)
async def shell(request: Request):
    return request.app.state.templates.TemplateResponse(request, "miniapp.html", {})


@router.get("/api/me")
async def me(request: Request, user: User = Depends(current_user)):
    username = request.app.state.bot_username
    return {"user": profile(user), "today": today(request), "bot_url": f"https://t.me/{username}" if username else None}


@router.get("/api/menu")
async def menu(request: Request, _: TelegramIdentity = Depends(identity), session: AsyncSession = Depends(db_session)):
    snapshot = await request.app.state.miniapp_menu.snapshot(session)
    return {
        "nodes": [
            {
                "id": n.id,
                "parent_id": n.parent_id,
                "name": n.name,
                "kind": n.kind,
                "action": n.action,
                "text": "".join(PlainText(n.text).parts),
                "position": n.position,
                "post_count": len(n.message_ids),
            }
            for n in snapshot.nodes.values()
        ]
    }


@router.get("/api/regions")
async def regions(_: TelegramIdentity = Depends(identity), session: AsyncSession = Depends(db_session)):
    rows = await session.scalars(select(Region).where(Region.is_active).order_by(Region.id))
    return {"regions": [{"id": r.id, "name": r.name} for r in rows]}


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    region_id: int = Field(gt=0)
    subscribed: bool | None = None


@router.put("/api/preferences")
async def preferences(
    data: Preferences, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)
):
    region = await active_region(session, data.region_id)
    user.region_id = region.id
    if data.subscribed is not None:
        user.subscribed = data.subscribed
    await session.commit()
    return {"user": profile(user)}


@router.get("/api/prayers")
async def prayers(
    request: Request,
    region_id: int | None = Query(None, gt=0),
    day: dt.date | None = None,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
):
    region = await active_region(session, region_id or user.region_id)
    day = day or today(request)
    if abs((day - today(request)).days) > 7:
        raise HTTPException(400, "Faqat bugundan 7 kun oldingi yoki keyingi jadvalni ochish mumkin")
    times = await PrayerService().get_times(session, region, day)
    await session.commit()
    return {
        "region": {"id": region.id, "name": region.name},
        "date": day,
        "times": {name: getattr(times, name).strftime("%H:%M") for name in PRAYERS},
        "source": times.source,
    }


@router.get("/api/mosques")
async def mosques(
    lat: float = Query(ge=-90, le=90, allow_inf_nan=False),
    lon: float = Query(ge=-180, le=180, allow_inf_nan=False),
    _: TelegramIdentity = Depends(identity),
    session: AsyncSession = Depends(db_session),
):
    found = await MosqueService().nearest(session, lat, lon, limit=5)
    return {"mosques": [asdict(m) for m in found], "far_away": bool(found and found[0].km > 30)}
