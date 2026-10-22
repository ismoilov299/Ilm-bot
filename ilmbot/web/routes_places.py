"""Masjidlar va regionlar boshqaruvi."""

import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Mosque, Region
from ilmbot.services import places_admin
from ilmbot.services.places_admin import PlacesError
from ilmbot.services.prayers import PrayerService
from ilmbot.web.deps import audit, db_session, render, require_admin, verify_csrf
from ilmbot.web.sessions import AdminSession

router = APIRouter()


async def _mosque_or_404(session: AsyncSession, mosque_id: int) -> Mosque:
    mosque = await session.get(Mosque, mosque_id)
    if mosque is None:
        raise HTTPException(status_code=404, detail="Masjid topilmadi")
    return mosque


async def _region_or_404(session: AsyncSession, region_id: int) -> Region:
    region = await session.get(Region, region_id)
    if region is None:
        raise HTTPException(status_code=404, detail="Region topilmadi")
    return region


# --- masjidlar ------------------------------------------------------------------------------------------


@router.get("/mosques")
async def mosques(
    request: Request,
    district: str = "",
    review: str = "",
    q: str = "",
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    return render(
        request, "mosques.html", admin=admin, nav="mosques", district=district, review=bool(review), q=q,
        items=await places_admin.list_mosques(session, district=district, only_review=bool(review), query=q),
        districts=await places_admin.districts(session),
    )  # fmt: skip


@router.get("/mosques/new")
async def mosque_new(request: Request, admin: AdminSession = Depends(require_admin)):
    form = {"name": "", "district": "", "lat": "41.2995", "lon": "69.2401", "is_active": True}
    return render(request, "mosque_form.html", admin=admin, nav="mosques", mosque=None, form=form)


@router.get("/mosques/{mosque_id}")
async def mosque_edit_form(
    request: Request,
    mosque_id: int,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    mosque = await _mosque_or_404(session, mosque_id)
    form = {
        "name": mosque.name, "district": mosque.district or "", "lat": mosque.lat, "lon": mosque.lon,
        "is_active": mosque.is_active,
    }  # fmt: skip
    return render(request, "mosque_form.html", admin=admin, nav="mosques", mosque=mosque, form=form)


async def _save_mosque(
    request: Request,
    session: AsyncSession,
    admin: AdminSession,
    mosque: Mosque | None,
    fields: dict,
    resolved: bool,
):
    form = {**fields, "is_active": bool(fields["is_active"])}
    try:
        saved = await places_admin.save_mosque(session, mosque, **form, resolved=resolved)
    except PlacesError as exc:
        return render(
            request, "mosque_form.html", status_code=400, admin=admin, nav="mosques", mosque=mosque, form=form,
            error=str(exc),
        )  # fmt: skip
    await audit(session, admin, "mosque.save", mosque_id=saved.id, name=saved.name)
    await session.commit()
    return RedirectResponse("/mosques?ok=Saqlandi", status_code=303)


@router.post("/mosques/new")
async def mosque_create(
    request: Request,
    name: str = Form(""),
    district: str = Form(""),
    lat: str = Form(""),
    lon: str = Form(""),
    is_active: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    fields = {"name": name, "district": district, "lat": lat, "lon": lon, "is_active": is_active}
    return await _save_mosque(request, session, admin, None, fields, resolved=False)


@router.post("/mosques/{mosque_id}")
async def mosque_update(
    request: Request,
    mosque_id: int,
    name: str = Form(""),
    district: str = Form(""),
    lat: str = Form(""),
    lon: str = Form(""),
    is_active: str = Form(""),
    resolved: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    mosque = await _mosque_or_404(session, mosque_id)
    fields = {"name": name, "district": district, "lat": lat, "lon": lon, "is_active": is_active}
    return await _save_mosque(request, session, admin, mosque, fields, resolved=bool(resolved))


@router.post("/mosques/{mosque_id}/delete")
async def mosque_delete(
    mosque_id: int,
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    mosque = await _mosque_or_404(session, mosque_id)
    name = mosque.name
    await session.delete(mosque)
    await audit(session, admin, "mosque.delete", mosque_id=mosque_id, name=name)
    await session.commit()
    return RedirectResponse("/mosques?ok=O'chirildi", status_code=303)


# --- regionlar ------------------------------------------------------------------------------------------


@router.get("/regions")
async def regions(
    request: Request, admin: AdminSession = Depends(require_admin), session: AsyncSession = Depends(db_session)
):
    items = (await session.scalars(select(Region).order_by(Region.id))).all()
    return render(request, "regions.html", admin=admin, nav="regions", items=items)


@router.get("/regions/{region_id}")
async def region_form(
    request: Request,
    region_id: int,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    region = await _region_or_404(session, region_id)
    form = {"lat": region.lat, "lon": region.lon, "is_active": region.is_active}
    return render(request, "region_form.html", admin=admin, nav="regions", region=region, form=form)


@router.post("/regions/{region_id}")
async def region_save(
    request: Request,
    region_id: int,
    lat: str = Form(""),
    lon: str = Form(""),
    is_active: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    region = await _region_or_404(session, region_id)
    try:
        await places_admin.save_region(session, region, lat=lat, lon=lon, is_active=bool(is_active))
    except PlacesError as exc:
        form = {"lat": lat, "lon": lon, "is_active": bool(is_active)}
        return render(
            request, "region_form.html", status_code=400, admin=admin, nav="regions", region=region, form=form,
            error=str(exc),
        )  # fmt: skip
    # Koordinata o'zgargan bo'lishi mumkin: bugun va keyingi kunlarning hisoblangan vaqtlari yangilanadi
    today = dt.datetime.now(ZoneInfo(request.app.state.settings.timezone)).date()
    await PrayerService().ensure_times(session, today, days=3)
    await audit(
        session, admin, "region.save", region=region.name, lat=region.lat, lon=region.lon, active=region.is_active
    )
    await session.commit()
    return RedirectResponse("/regions?ok=Saqlandi", status_code=303)
