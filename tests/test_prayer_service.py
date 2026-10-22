import datetime as dt

from sqlalchemy import func, select

from ilmbot.db.models import PrayerTime, Region
from ilmbot.integrations.prayer_calc import compute_day
from ilmbot.seed import seed_regions
from ilmbot.services.prayers import SOURCE_MANUAL, PrayerService

TODAY = dt.date(2026, 10, 22)


async def count_rows(session) -> int:
    return await session.scalar(select(func.count()).select_from(PrayerTime))


async def test_ensure_times_creates_rows_for_every_region_and_day(session):
    await seed_regions(session)

    written = await PrayerService().ensure_times(session, TODAY, days=3)

    assert written == 39
    assert await count_rows(session) == 39


async def test_ensure_times_is_idempotent(session):
    await seed_regions(session)
    service = PrayerService()
    await service.ensure_times(session, TODAY, days=2)

    await service.ensure_times(session, TODAY, days=2)

    assert await count_rows(session) == 26


async def test_stored_values_equal_the_calculation(session):
    await seed_regions(session)
    await PrayerService().ensure_times(session, TODAY, days=1)
    region = await session.scalar(select(Region).where(Region.name == "Toshkent"))

    row = await session.scalar(select(PrayerTime).where(PrayerTime.region_id == region.id))

    expected = compute_day(TODAY, region.lat, region.lon)
    assert (row.bomdod, row.quyosh, row.peshin, row.asr, row.shom, row.xufton) == tuple(expected.as_dict().values())
    assert row.source == "computed"


async def test_manual_edits_are_never_overwritten(session):
    await seed_regions(session)
    service = PrayerService()
    await service.ensure_times(session, TODAY, days=1)
    row = await session.scalar(select(PrayerTime).limit(1))
    row.bomdod, row.source = dt.time(1, 2), SOURCE_MANUAL
    await session.flush()

    await service.ensure_times(session, TODAY, days=1)
    await session.refresh(row)

    assert row.bomdod == dt.time(1, 2)


async def test_computed_rows_are_refreshed_when_the_calculation_changes(session):
    await seed_regions(session)
    service = PrayerService()
    await service.ensure_times(session, TODAY, days=1)
    row = await session.scalar(select(PrayerTime).limit(1))
    stale = dt.time(0, 0)
    row.bomdod = stale
    await session.flush()

    await service.ensure_times(session, TODAY, days=1)
    await session.refresh(row)

    assert row.bomdod != stale


async def test_get_times_calculates_a_missing_day_on_demand(session):
    await seed_regions(session)
    region = await session.scalar(select(Region).where(Region.name == "Samarqand"))
    service = PrayerService()

    first = await service.get_times(session, region, TODAY)
    second = await service.get_times(session, region, TODAY)

    assert first.id == second.id
    assert first.bomdod < first.quyosh < first.peshin < first.asr < first.shom < first.xufton
    assert await count_rows(session) == 1
