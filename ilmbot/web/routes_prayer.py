"""Namoz vaqtlari: kunlik jadvalni ko'rish, qo'lda tuzatish va hisoblangan qiymatga qaytarish."""

import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Region
from ilmbot.integrations.prayer_calc import PRAYERS
from ilmbot.services.prayers import PrayerService, PrayerTimesError
from ilmbot.web.deps import audit, db_session, render, require_admin, verify_csrf
from ilmbot.web.sessions import AdminSession

router = APIRouter(prefix="/prayer-times")
prayers = PrayerService()

LABELS = {"bomdod": "Bomdod", "quyosh": "Quyosh", "peshin": "Peshin", "asr": "Asr", "shom": "Shom", "xufton": "Xufton"}


def _today(request: Request) -> dt.date:
    return dt.datetime.now(ZoneInfo(request.app.state.settings.timezone)).date()


async def _region_or_404(session: AsyncSession, region_id: int) -> Region:
    region = await session.get(Region, region_id)
    if region is None:
        raise HTTPException(status_code=404, detail="Region topilmadi")
    return region


def _parse_time(value: str) -> dt.time:
    try:
        return dt.time.fromisoformat(value.strip())
    except ValueError as exc:
        raise PrayerTimesError(f"Vaqt formati noto'g'ri: «{value}» (HH:MM bo'lishi kerak)") from exc


@router.get("")
async def index(
    request: Request,
    date: dt.date | None = None,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    day = date or _today(request)
    regions = (await session.scalars(select(Region).where(Region.is_active).order_by(Region.id))).all()
    rows = [(region, await prayers.get_times(session, region, day)) for region in regions]
    await session.commit()  # yo'q kunlar hisoblab yozilgan bo'lishi mumkin
    return render(
        request, "prayer_times.html", admin=admin, nav="prayer", day=day, rows=rows, labels=LABELS, prayers=PRAYERS,
        prev_day=day - dt.timedelta(days=1), next_day=day + dt.timedelta(days=1), today=_today(request),
    )  # fmt: skip


@router.get("/{region_id}/{day}")
async def edit_form(
    request: Request,
    region_id: int,
    day: dt.date,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    region = await _region_or_404(session, region_id)
    row = await prayers.get_times(session, region, day)
    await session.commit()
    return render(
        request, "prayer_edit.html", admin=admin, nav="prayer", region=region, day=day, row=row, labels=LABELS,
        prayers=PRAYERS, values={name: getattr(row, name).strftime("%H:%M") for name in PRAYERS},
    )  # fmt: skip


@router.post("/{region_id}/{day}")
async def save(
    request: Request,
    region_id: int,
    day: dt.date,
    bomdod: str = Form(""),
    quyosh: str = Form(""),
    peshin: str = Form(""),
    asr: str = Form(""),
    shom: str = Form(""),
    xufton: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    region = await _region_or_404(session, region_id)
    values = {"bomdod": bomdod, "quyosh": quyosh, "peshin": peshin, "asr": asr, "shom": shom, "xufton": xufton}
    try:
        await prayers.set_manual(session, region, day, {name: _parse_time(v) for name, v in values.items()})
    except PrayerTimesError as exc:
        row = await prayers.get_times(session, region, day)
        return render(
            request, "prayer_edit.html", status_code=400, admin=admin, nav="prayer", region=region, day=day, row=row,
            labels=LABELS, prayers=PRAYERS, values=values, error=str(exc),
        )  # fmt: skip
    await audit(session, admin, "prayer.manual", region=region.name, date=day.isoformat(), **values)
    await session.commit()
    return RedirectResponse(f"/prayer-times?date={day.isoformat()}&ok=Saqlandi", status_code=303)


@router.post("/{region_id}/{day}/reset")
async def reset(
    region_id: int,
    day: dt.date,
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    region = await _region_or_404(session, region_id)
    await prayers.reset_computed(session, region, day)
    await audit(session, admin, "prayer.reset", region=region.name, date=day.isoformat())
    await session.commit()
    return RedirectResponse(f"/prayer-times?date={day.isoformat()}&ok=Hisoblangan qiymatga qaytarildi", status_code=303)
