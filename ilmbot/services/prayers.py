"""Namoz vaqtlari: hisoblab `prayer_times` jadvaliga yozish va o'qish."""

import datetime as dt

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import PrayerTime, Region
from ilmbot.integrations.prayer_calc import PRAYERS, compute_day

SOURCE_COMPUTED = "computed"
SOURCE_MANUAL = "manual"  # admin qo'lda o'zgartirgan: hisoblash uni hech qachon bosmaydi


class PrayerTimesError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan tushunarli xato."""


def _row(region: Region, date: dt.date) -> dict:
    return {
        "region_id": region.id,
        "date": date,
        "source": SOURCE_COMPUTED,
        **compute_day(date, region.lat, region.lon).as_dict(),
    }


async def _upsert(session: AsyncSession, rows: list[dict]) -> None:
    if not rows:
        return
    statement = insert(PrayerTime).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[PrayerTime.region_id, PrayerTime.date],
        set_={name: getattr(statement.excluded, name) for name in PRAYERS},
        where=PrayerTime.source == SOURCE_COMPUTED,
    )
    await session.execute(statement)


class PrayerService:
    async def ensure_times(self, session: AsyncSession, start: dt.date, days: int = 3) -> int:
        """Faol regionlar uchun `start` dan `days` kunlik vaqtlarni yozadi (qo'lda kiritilganlarga tegmaydi)."""
        regions = (await session.scalars(select(Region).where(Region.is_active))).all()
        rows = [_row(region, start + dt.timedelta(days=offset)) for region in regions for offset in range(days)]
        await _upsert(session, rows)
        return len(rows)

    async def get_times(self, session: AsyncSession, region: Region, date: dt.date) -> PrayerTime:
        """Region va sana uchun vaqtlar; bazada yo'q bo'lsa hisoblab yoziladi."""
        query = select(PrayerTime).where(PrayerTime.region_id == region.id, PrayerTime.date == date)
        found = await session.scalar(query)
        if found is not None:
            return found
        await _upsert(session, [_row(region, date)])
        await session.flush()
        return await session.scalar(query.execution_options(populate_existing=True))

    async def set_manual(
        self, session: AsyncSession, region: Region, date: dt.date, times: dict[str, dt.time]
    ) -> PrayerTime:
        """Admin qo'lda kiritgan vaqtlar: `manual` deb belgilanadi va hisoblash ularni boshqa bosmaydi."""
        if set(times) != set(PRAYERS):
            raise PrayerTimesError("Oltita vaqtning hammasi kiritilishi kerak")
        ordered = [times[name] for name in PRAYERS]
        if any(earlier >= later for earlier, later in zip(ordered, ordered[1:], strict=False)):
            raise PrayerTimesError("Vaqtlar o'sib borishi kerak: bomdod < quyosh < peshin < asr < shom < xufton")
        statement = insert(PrayerTime).values(
            region_id=region.id, date=date, source=SOURCE_MANUAL, **{name: times[name] for name in PRAYERS}
        )
        statement = statement.on_conflict_do_update(
            index_elements=[PrayerTime.region_id, PrayerTime.date],
            set_={"source": SOURCE_MANUAL, **{name: getattr(statement.excluded, name) for name in PRAYERS}},
        )
        await session.execute(statement)
        await session.flush()
        return await session.scalar(
            select(PrayerTime)
            .where(PrayerTime.region_id == region.id, PrayerTime.date == date)
            .execution_options(populate_existing=True)
        )

    async def reset_computed(self, session: AsyncSession, region: Region, date: dt.date) -> PrayerTime:
        """Qo'lda kiritilgan vaqtni o'chirib, hisoblangan qiymatga qaytaradi."""
        await session.execute(delete(PrayerTime).where(PrayerTime.region_id == region.id, PrayerTime.date == date))
        return await self.get_times(session, region, date)
