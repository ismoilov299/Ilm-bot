"""Bot ichidagi admin buyruqlari: faqat ADMINS ro'yxatidagilar uchun."""

import pytest
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from sqlalchemy import func, select

from ilmbot.bot import texts
from ilmbot.bot.callbacks import BroadcastCb
from ilmbot.bot.main import create_dispatcher
from ilmbot.db.models import BroadcastJob, BroadcastRecipient, User
from tests.bot_harness import Harness, callback_datas, keyboard_texts, make_bot

ADMIN, USER = 111, 222


@pytest.fixture
async def bot(seeded, sessionmaker, redis, settings) -> Harness:
    settings = settings.model_copy(update={"admins": [ADMIN]})
    dp = create_dispatcher(sessionmaker=sessionmaker, redis=redis, settings=settings, throttle_interval=0.0)
    return Harness(dp, make_bot())


async def job_count(session) -> int:
    return await session.scalar(select(func.count()).select_from(BroadcastJob))


async def test_admin_commands_are_invisible_to_ordinary_users(bot, session):
    [stats] = await bot.say("/stats", user_id=USER)
    [broadcast] = await bot.say("/broadcast", user_id=USER)

    assert stats.text == texts.NOT_UNDERSTOOD and broadcast.text == texts.NOT_UNDERSTOOD


async def test_stats_for_admin(bot, session):
    await bot.say("/start", user_id=ADMIN)
    await bot.say("/start", user_id=USER)
    session.add(User(id=333, name="b", is_blocked=True))
    await session.flush()

    [reply] = await bot.say("/stats", user_id=ADMIN)

    assert "Foydalanuvchilar: 3" in reply.text and "Botni bloklagan: 1" in reply.text


async def test_admin_composes_confirms_and_the_job_is_queued(bot, session):
    await bot.say("/start", user_id=ADMIN)
    await bot.say("/start", user_id=USER)
    [ask] = await bot.say("/broadcast", user_id=ADMIN)
    assert ask.text == texts.BROADCAST_ASK

    [confirm] = await bot.say("Assalomu alaykum, yangilik bor!", user_id=ADMIN)
    assert confirm.text == texts.BROADCAST_CONFIRM.format(count=2)
    assert await job_count(session) == 0  # tasdiqlanmaguncha ish yaratilmaydi

    requests = await bot.press(BroadcastCb(act="go"), user_id=ADMIN)

    edit = next(r for r in requests if isinstance(r, EditMessageText))
    assert edit.text.startswith("\U0001f4e3 Broadcast #") and "Jami: 2" in edit.text
    job = await session.scalar(select(BroadcastJob))
    assert (job.status, job.total, job.source_chat_id, job.created_by) == ("queued", 2, ADMIN, f"tg:{ADMIN}")
    assert await session.scalar(select(func.count()).select_from(BroadcastRecipient)) == 2


async def test_declining_or_cancelling_creates_no_job(bot, session):
    await bot.say("/broadcast", user_id=ADMIN)
    await bot.say("Matn", user_id=ADMIN)
    await bot.press(BroadcastCb(act="no"), user_id=ADMIN)
    await bot.say("/broadcast", user_id=ADMIN)
    [cancelled] = await bot.say("/cancel", user_id=ADMIN)

    assert cancelled.text == texts.BROADCAST_DECLINED
    assert await job_count(session) == 0


async def test_confirming_without_composing_first_is_rejected(bot, session):
    requests = await bot.press(BroadcastCb(act="go"), user_id=ADMIN)

    answer = next(r for r in requests if isinstance(r, AnswerCallbackQuery))
    assert (answer.text, answer.show_alert) == (texts.STALE_BUTTON, True)  # holat yo'q: tugma eskirgan hisoblanadi
    assert await job_count(session) == 0


async def test_ordinary_users_cannot_create_or_control_jobs(bot, session):
    await bot.say("/start", user_id=USER)

    requests = await bot.press(BroadcastCb(act="go"), user_id=USER)

    assert next(r for r in requests if isinstance(r, AnswerCallbackQuery)).text == texts.STALE_BUTTON
    assert await job_count(session) == 0


async def test_admin_can_pause_resume_and_cancel_from_the_status_message(bot, session):
    await bot.say("/start", user_id=USER)
    await bot.say("/broadcast", user_id=ADMIN)
    await bot.say("Xabar", user_id=ADMIN)
    await bot.press(BroadcastCb(act="go"), user_id=ADMIN)
    job = await session.scalar(select(BroadcastJob))

    [status] = await bot.say("/broadcast_status", user_id=ADMIN)
    assert isinstance(status, SendMessage) and texts.BROADCAST_PAUSE in keyboard_texts(status)

    paused = next(
        r for r in await bot.press(BroadcastCb(act="pause", id=job.id), user_id=ADMIN) if isinstance(r, EditMessageText)
    )
    assert "to'xtatilgan" in paused.text and texts.BROADCAST_RESUME in keyboard_texts(paused)
    assert BroadcastCb(act="resume", id=job.id).pack() in callback_datas(paused)

    await bot.press(BroadcastCb(act="resume", id=job.id), user_id=ADMIN)
    cancelled = next(
        r
        for r in await bot.press(BroadcastCb(act="cancel", id=job.id), user_id=ADMIN)
        if isinstance(r, EditMessageText)
    )
    assert "bekor qilindi" in cancelled.text
    assert texts.BROADCAST_CANCEL not in keyboard_texts(cancelled)  # tugagan ishda boshqaruv tugmalari yo'q
