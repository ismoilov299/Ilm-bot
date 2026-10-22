"""Masjidlar va regionlarni tahrirlash (admin panel)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Mosque, Region

LAT_RANGE = (37.0, 46.0)  # O'zbekiston chegaralari (taxminan)
LON_RANGE = (55.0, 74.0)


class PlacesError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan tushunarli xato."""


def _coordinates(lat: str, lon: str) -> tuple[float, float]:
    try:
        lat_value, lon_value = float(lat.replace(",", ".")), float(lon.replace(",", "."))
    except ValueError as exc:
        raise PlacesError("Koordinatalar son bo'lishi kerak (masalan, 41.2995 va 69.2401)") from exc
    if not (LAT_RANGE[0] <= lat_value <= LAT_RANGE[1] and LON_RANGE[0] <= lon_value <= LON_RANGE[1]):
        raise PlacesError("Koordinata O'zbekiston hududidan tashqarida: kenglik 37-46, uzunlik 55-74 bo'lishi kerak")
    return lat_value, lon_value


async def list_mosques(
    session: AsyncSession, *, district: str = "", only_review: bool = False, query: str = ""
) -> list[Mosque]:
    statement = select(Mosque).order_by(Mosque.district, Mosque.name, Mosque.id)
    if district:
        statement = statement.where(Mosque.district == district)
    if only_review:
        statement = statement.where(Mosque.review_note.is_not(None))
    if query.strip():
        statement = statement.where(Mosque.name.ilike(f"%{query.strip()}%"))
    return list((await session.scalars(statement)).all())


async def districts(session: AsyncSession) -> list[str]:
    rows = await session.scalars(
        select(Mosque.district).where(Mosque.district.is_not(None)).distinct().order_by(Mosque.district)
    )
    return list(rows.all())


async def save_mosque(
    session: AsyncSession,
    mosque: Mosque | None,
    *,
    name: str,
    district: str,
    lat: str,
    lon: str,
    is_active: bool,
    resolved: bool = False,
) -> Mosque:
    name = " ".join(name.split())
    if not name:
        raise PlacesError("Masjid nomi bo'sh bo'lmasligi kerak")
    lat_value, lon_value = _coordinates(lat, lon)
    mosque = mosque or Mosque(name=name, lat=lat_value, lon=lon_value)
    mosque.name, mosque.district = name, " ".join(district.split()) or None
    mosque.lat, mosque.lon, mosque.is_active = lat_value, lon_value, is_active
    if resolved:
        mosque.review_note = None
    session.add(mosque)
    await session.flush()
    return mosque


async def save_region(session: AsyncSession, region: Region, *, lat: str, lon: str, is_active: bool) -> Region:
    region.lat, region.lon = _coordinates(lat, lon)
    region.is_active = is_active
    await session.flush()
    return region
