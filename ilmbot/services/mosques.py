"""Eng yaqin masjidlarni topish (Haversine, ~115 ta yozuv uchun xotirada hisoblash yetarli)."""

import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Mosque

EARTH_RADIUS_KM = 6371.0


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@dataclass(frozen=True, slots=True)
class NearbyMosque:
    name: str
    district: str | None
    lat: float
    lon: float
    km: float


class MosqueService:
    async def nearest(self, session: AsyncSession, lat: float, lon: float, limit: int = 2) -> list[NearbyMosque]:
        mosques = (await session.scalars(select(Mosque).where(Mosque.is_active))).all()
        found = [NearbyMosque(m.name, m.district, m.lat, m.lon, distance_km(lat, lon, m.lat, m.lon)) for m in mosques]
        return sorted(found, key=lambda m: m.km)[:limit]
