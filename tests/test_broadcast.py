import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import CopyMessage
from sqlalchemy import select

from ilmbot.db.models import BroadcastJob, BroadcastRecipient, JobStatus, User
from ilmbot.integrations.rate_limiter import RateLimiter
from ilmbot.integrations.telegram_sender import TelegramSender
from ilmbot.services.broadcast import BroadcastService, JobAction
from tests.bot_harness import make_bot


@pytest.fixture
def bot():
    return make_bot()


@pytest.fixture
def service(redis):
    return BroadcastService(TelegramSender(RateLimiter(redis, per_second=100_000)), batch_size=2)


async def add_users(session, ids, blocked=()):
    session.add_all(User(id=i, name=f"u{i}", is_blocked=i in blocked) for i in ids)
    await session.flush()


async def new_job(session, service):
    job = await service.create_job(session, "tg:1", source_chat_id=555, source_message_id=77)
    await session.commit()
    return job


async def recipients(session, job_id):
    rows = await session.execute(
        select(BroadcastRecipient.user_id, BroadcastRecipient.status).where(BroadcastRecipient.job_id == job_id)
    )
    return dict(rows.all())


async def test_job_snapshot_excludes_users_who_blocked_the_bot(session, service):
    await add_users(session, [1, 2, 3], blocked={3})

    job = await new_job(session, service)

    assert job.total == 2
    assert set(await recipients(session, job.id)) == {1, 2}


async def test_everyone_gets_a_copy_of_the_message_and_the_job_finishes(session, sessionmaker, service, bot):
    await add_users(session, [1, 2, 3, 4, 5])
    job = await new_job(session, service)

    status = await service.process(sessionmaker, bot, job.id)

    copies = [r for r in bot.session.requests if isinstance(r, CopyMessage)]
    assert [(c.chat_id, c.from_chat_id, c.message_id) for c in copies] == [(i, 555, 77) for i in range(1, 6)]
    await session.refresh(job)
    assert (status, job.status, job.sent, job.failed, job.blocked) == ("done", "done", 5, 0, 0)
    assert job.started_at is not None and job.finished_at is not None
    assert set((await recipients(session, job.id)).values()) == {"sent"}


async def test_users_who_blocked_the_bot_are_counted_and_marked(session, sessionmaker, service, bot):
    await add_users(session, [1, 2, 3])
    job = await new_job(session, service)
    bot.session.fail_when(
        lambda m: isinstance(m, CopyMessage) and m.chat_id == 2,
        TelegramForbiddenError(CopyMessage(chat_id=2, from_chat_id=1, message_id=1), "Forbidden: bot was blocked"),
    )

    await service.process(sessionmaker, bot, job.id)

    await session.refresh(job)
    assert (job.sent, job.blocked) == (2, 1)
    assert (await recipients(session, job.id))[2] == "blocked"
    assert (await session.get(User, 2, populate_existing=True)).is_blocked is True


async def test_paused_job_sends_nothing_until_resumed(session, sessionmaker, service, bot):
    await add_users(session, [1, 2, 3])
    job = await new_job(session, service)
    await service.apply(session, job.id, JobAction.PAUSE)
    await session.commit()

    assert await service.process(sessionmaker, bot, job.id) == "paused"
    assert bot.session.requests == []
    assert await service.next_job_id(session) is None  # to'xtatilgan ish navbatga kirmaydi

    await service.apply(session, job.id, JobAction.RESUME)
    await session.commit()
    assert await service.process(sessionmaker, bot, job.id) == "done"
    assert len(bot.session.requests) == 3


async def test_cancelled_job_stays_cancelled_and_finished_jobs_ignore_actions(session, sessionmaker, service, bot):
    await add_users(session, [1, 2])
    job = await new_job(session, service)

    cancelled = await service.apply(session, job.id, JobAction.CANCEL)
    await session.commit()
    assert cancelled.status == JobStatus.CANCELLED.value
    assert await service.process(sessionmaker, bot, job.id) == "cancelled" and bot.session.requests == []

    again = await service.apply(session, job.id, JobAction.RESUME)
    assert again.status == JobStatus.CANCELLED.value


async def test_after_a_restart_only_the_remaining_recipients_get_the_message(session, sessionmaker, service, bot):
    await add_users(session, [1, 2, 3, 4])
    job = await new_job(session, service)
    job.status = JobStatus.RUNNING.value  # worker yarim yo'lda to'xtagan
    job.sent = 2
    await session.execute(
        BroadcastRecipient.__table__.update()
        .where(BroadcastRecipient.job_id == job.id, BroadcastRecipient.user_id.in_([1, 2]))
        .values(status="sent")
    )
    await session.commit()

    assert await service.next_job_id(session) == job.id
    await service.process(sessionmaker, bot, job.id)

    assert [r.chat_id for r in bot.session.requests] == [3, 4]
    await session.refresh(job)
    assert (job.sent, job.status) == (4, "done")


async def test_next_job_is_the_oldest_active_one(session, service):
    await add_users(session, [1])
    first = await new_job(session, service)
    second = await new_job(session, service)
    await service.apply(session, first.id, JobAction.PAUSE)
    await session.commit()

    assert await service.next_job_id(session) == second.id
    assert (await session.scalar(select(BroadcastJob.status).where(BroadcastJob.id == first.id))) == "paused"
