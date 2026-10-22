import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from sqlalchemy import select

from ilmbot.db.models import PrayerTime, Region, ReminderRun, User
from ilmbot.integrations.rate_limiter import RateLimiter
from ilmbot.integrations.telegram_sender import TelegramSender
from ilmbot.seed import seed_regions
from ilmbot.services.prayers import PrayerService
from ilmbot.services.reminders import ReminderService, reminder_text
from ilmbot.worker.scheduler import ReminderScheduler
from tests.bot_harness import make_bot

TZ = ZoneInfo("Asia/Tashkent")
TODAY = dt.date(2026, 10, 22)


@pytest.fixture
async def world(session, redis):
    """13 region, bugungi vaqtlar, soxta bot va tezligi cheklanmagan yuboruvchi."""
    await seed_regions(session)
    await PrayerService().ensure_times(session, TODAY, days=2)
    await session.flush()
    toshkent = await session.scalar(select(Region).where(Region.name == "Toshkent"))
    times = await session.scalar(
        select(PrayerTime).where(PrayerTime.region_id == toshkent.id, PrayerTime.date == TODAY)
    )
    sender = TelegramSender(RateLimiter(redis, per_second=100_000))
    return {"region": toshkent, "times": times, "sender": sender, "bot": make_bot()}


def at(time: dt.time, seconds: int = 0, minutes: int = 0) -> dt.datetime:
    moment = dt.datetime.combine(TODAY, time, tzinfo=TZ)
    return moment + dt.timedelta(minutes=minutes, seconds=seconds)


async def add_users(session, region_id, ids, **fields):
    session.add_all(User(id=i, name=f"u{i}", region_id=region_id, subscribed=True, **fields) for i in ids)
    await session.flush()


async def find_due(session, world, now):
    return [
        d for d in await ReminderService(world["sender"]).find_due(session, now) if d.region_id == world["region"].id
    ]


async def test_prayer_is_due_in_its_minute(session, world):
    due = await find_due(session, world, at(world["times"].bomdod, seconds=30))

    assert [(d.prayer, d.time) for d in due] == [("bomdod", world["times"].bomdod)]
    assert due[0].region_name == "Toshkent"


async def test_prayer_is_due_up_to_the_grace_period_but_not_later(session, world):
    start = world["times"].peshin

    assert await find_due(session, world, at(start, minutes=-1)) == []
    assert len(await find_due(session, world, at(start, minutes=3))) == 1  # 3 daqiqa kechikkan: hali yuboriladi
    assert await find_due(session, world, at(start, minutes=4)) == []  # undan keyin "vaqti bo'ldi" deyish noo'rin


async def test_claim_happens_once_per_prayer_region_and_day(session, world):
    service = ReminderService(world["sender"])
    [due] = await find_due(session, world, at(world["times"].asr))

    first = await service.claim(session, due)
    second = await service.claim(session, due)

    assert first is not None and second is None


async def test_reminder_text_contains_time_and_region(session, world):
    [due] = await find_due(session, world, at(world["times"].shom))

    text = reminder_text(due)

    assert "Shom vaqti bo'ldi" in text
    assert f"Toshkent: {world['times'].shom:%H:%M}" in text


async def deliver(session, sessionmaker, world, prayer="bomdod", batch_size=200, last_user_id=None):
    service = ReminderService(world["sender"], batch_size=batch_size)
    [due] = await find_due(session, world, at(getattr(world["times"], prayer)))
    run_id = await service.claim(session, due)
    await session.flush()
    stats = await service.deliver(sessionmaker, world["bot"], run_id, due, last_user_id)
    return run_id, stats


async def test_only_active_subscribers_of_the_region_receive_it(session, sessionmaker, world):
    other = await session.scalar(select(Region).where(Region.name == "Xiva"))
    region_id = world["region"].id
    await add_users(session, region_id, [1, 2, 3])
    await add_users(session, other.id, [5])  # boshqa region
    await add_users(session, region_id, [6], is_blocked=True)  # oldin bloklagan
    session.add(User(id=4, name="obuna emas", region_id=region_id, subscribed=False))
    await session.flush()

    run_id, stats = await deliver(session, sessionmaker, world)

    assert [r.chat_id for r in world["bot"].session.requests] == [1, 2, 3]
    assert dict(stats) == {"sent": 3}
    run = await session.get(ReminderRun, run_id)
    await session.refresh(run)
    assert (run.status, run.last_user_id) == ("done", 3) and run.finished_at is not None


async def test_users_who_blocked_the_bot_are_marked_and_skipped_next_time(session, sessionmaker, world):
    await add_users(session, world["region"].id, [1, 2, 3])
    world["bot"].session.fail_when(
        lambda m: isinstance(m, SendMessage) and m.chat_id == 2,
        TelegramForbiddenError(SendMessage(chat_id=2, text="x"), "Forbidden: bot was blocked by the user"),
    )

    _, stats = await deliver(session, sessionmaker, world)

    assert dict(stats) == {"sent": 2, "blocked": 1}
    blocked = (await session.scalars(select(User.id).where(User.is_blocked))).all()
    assert blocked == [2]


async def test_delivery_resumes_after_the_last_sent_user(session, sessionmaker, world):
    await add_users(session, world["region"].id, [1, 2, 3, 4])

    _, stats = await deliver(session, sessionmaker, world, last_user_id=2)

    assert [r.chat_id for r in world["bot"].session.requests] == [3, 4]
    assert dict(stats) == {"sent": 2}


async def test_unfinished_runs_are_found_for_resuming(session, sessionmaker, world):
    service = ReminderService(world["sender"])
    [due] = await find_due(session, world, at(world["times"].xufton))
    run_id = await service.claim(session, due)
    await session.flush()
    await session.execute(ReminderRun.__table__.update().where(ReminderRun.id == run_id).values(last_user_id=7))

    pending = await service.unfinished(session)

    assert [(r, d.prayer, last) for r, d, last in pending if d.region_id == world["region"].id] == [
        (run_id, "xufton", 7)
    ]


async def test_delivery_is_split_into_batches_and_reaches_everyone(session, sessionmaker, world):
    await add_users(session, world["region"].id, range(1, 11))

    run_id, stats = await deliver(session, sessionmaker, world, batch_size=3)

    assert dict(stats) == {"sent": 10}
    assert [r.chat_id for r in world["bot"].session.requests] == list(range(1, 11))


async def test_scheduler_tick_sends_once_even_if_called_again(session, sessionmaker, world):
    await add_users(session, world["region"].id, [1, 2])
    scheduler = ReminderScheduler(ReminderService(world["sender"]), sessionmaker, world["bot"])
    now = at(world["times"].peshin, seconds=10)

    claimed_first = await scheduler.tick(now)
    await scheduler.wait_idle()
    claimed_again = await scheduler.tick(now)
    await scheduler.wait_idle()

    assert claimed_first >= 1 and claimed_again == 0
    texts = [r.text for r in world["bot"].session.requests if r.chat_id in (1, 2)]
    assert len(texts) == 2 and all("Peshin vaqti bo'ldi" in t for t in texts)


async def test_scheduler_resumes_unfinished_runs_on_start(session, sessionmaker, world):
    await add_users(session, world["region"].id, [1, 2, 3])
    service = ReminderService(world["sender"])
    [due] = await find_due(session, world, at(world["times"].asr))
    run_id = await service.claim(session, due)
    await session.execute(ReminderRun.__table__.update().where(ReminderRun.id == run_id).values(last_user_id=1))
    await session.flush()
    scheduler = ReminderScheduler(service, sessionmaker, world["bot"])

    resumed = await scheduler.resume()
    await scheduler.wait_idle()

    assert resumed >= 1
    assert [r.chat_id for r in world["bot"].session.requests if r.chat_id in (1, 2, 3)] == [2, 3]


async def test_a_large_audience_is_delivered_completely(session, sessionmaker, world):
    await session.execute(
        User.__table__.insert(),
        [{"id": 10_000 + i, "name": "u", "region_id": world["region"].id, "subscribed": True} for i in range(1500)],
    )

    _, stats = await deliver(session, sessionmaker, world)

    assert dict(stats) == {"sent": 1500}
    chat_ids = [r.chat_id for r in world["bot"].session.requests]
    assert chat_ids == sorted(set(chat_ids)) and len(chat_ids) == 1500
