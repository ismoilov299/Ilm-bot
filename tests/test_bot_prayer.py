"""Botdagi "Namoz vaqtlari": shahar tanlash, vaqtlar va eslatmani yoqish/o'chirish."""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from aiogram.methods import AnswerCallbackQuery, EditMessageReplyMarkup, EditMessageText, SendMessage
from sqlalchemy import func, select

from ilmbot.bot import texts
from ilmbot.bot.callbacks import RegionCb, ReminderCb
from ilmbot.bot.main import create_dispatcher
from ilmbot.db.models import PrayerTime, Region, User
from ilmbot.integrations.prayer_calc import compute_day
from tests.bot_harness import Harness, keyboard_texts, make_bot

NOW = dt.datetime(2026, 10, 22, 12, 0, tzinfo=ZoneInfo("Asia/Tashkent"))


@pytest.fixture
async def bot(seeded, sessionmaker, redis, settings) -> Harness:
    dp = create_dispatcher(
        sessionmaker=sessionmaker, redis=redis, settings=settings, throttle_interval=0.0, clock=lambda: NOW
    )
    return Harness(dp, make_bot())


async def region_id(session, name: str) -> int:
    return await session.scalar(select(Region.id).where(Region.name == name))


def only(requests, method_type):
    found = [r for r in requests if isinstance(r, method_type)]
    assert len(found) == 1, f"{method_type.__name__}: {len(found)} ta"
    return found[0]


async def open_prayer_times(bot: Harness):
    await bot.say("/start")
    await bot.say("Namoz🕋")
    return await bot.say("Namoz vaqtlari")


async def test_without_a_saved_city_the_cities_are_offered(bot):
    [reply] = await open_prayer_times(bot)

    assert reply.text == texts.CHOOSE_CITY
    names = keyboard_texts(reply)
    assert len(names) == 13 and {"Toshkent", "Qo'qon", "Marg'ilon", "Nukus"} <= set(names)
    assert len(reply.reply_markup.inline_keyboard[0]) == 2  # qatorda 2 tadan


async def test_choosing_a_city_shows_todays_times(bot, session):
    await open_prayer_times(bot)

    edit = only(await bot.press(RegionCb(id=await region_id(session, "Toshkent"))), EditMessageText)

    region = await session.scalar(select(Region).where(Region.name == "Toshkent"))
    expected = compute_day(NOW.date(), region.lat, region.lon)
    assert "<b>Toshkent</b>, 22.10.2026 (Payshanba)" in edit.text
    for label, value in [("Bomdod", expected.bomdod), ("Shom", expected.shom), ("Xufton", expected.xufton)]:
        assert f"{label}: <b>{value:%H:%M}</b>" in edit.text
    assert keyboard_texts(edit) == [texts.REMINDER_ENABLE, texts.OTHER_CITY]
    assert await session.scalar(select(func.count()).select_from(PrayerTime)) >= 1


async def test_enabling_the_reminder_saves_city_and_subscription(bot, session):
    toshkent = await region_id(session, "Toshkent")
    await open_prayer_times(bot)
    await bot.press(RegionCb(id=toshkent))

    requests = await bot.press(ReminderCb(region_id=toshkent, on=True))

    assert only(requests, AnswerCallbackQuery).text == "\U0001f514 Eslatma yoqildi: Toshkent"
    assert keyboard_texts(only(requests, EditMessageReplyMarkup)) == [texts.REMINDER_DISABLE, texts.OTHER_CITY]
    user = await session.get(User, 111)
    await session.refresh(user)
    assert (user.region_id, user.subscribed) == (toshkent, True)


async def test_disabling_keeps_the_saved_city(bot, session):
    toshkent = await region_id(session, "Toshkent")
    await open_prayer_times(bot)
    await bot.press(ReminderCb(region_id=toshkent, on=True))

    requests = await bot.press(ReminderCb(region_id=toshkent, on=False))

    assert only(requests, AnswerCallbackQuery).text == texts.REMINDER_OFF
    user = await session.get(User, 111)
    await session.refresh(user)
    assert (user.region_id, user.subscribed) == (toshkent, False)


async def test_saved_city_opens_its_times_directly_next_time(bot, session):
    toshkent = await region_id(session, "Toshkent")
    await open_prayer_times(bot)
    await bot.press(ReminderCb(region_id=toshkent, on=True))

    [reply] = await bot.say("Namoz vaqtlari")

    assert isinstance(reply, SendMessage)
    assert "<b>Toshkent</b>" in reply.text
    assert keyboard_texts(reply) == [texts.REMINDER_DISABLE, texts.OTHER_CITY]


async def test_other_city_button_returns_to_the_city_list(bot, session):
    toshkent = await region_id(session, "Toshkent")
    await open_prayer_times(bot)
    await bot.press(RegionCb(id=toshkent))

    edit = only(await bot.press(RegionCb(id=0)), EditMessageText)

    assert edit.text == texts.CHOOSE_CITY and len(keyboard_texts(edit)) == 13


async def test_viewing_another_city_does_not_change_the_reminder_until_enabled(bot, session):
    toshkent, samarqand = await region_id(session, "Toshkent"), await region_id(session, "Samarqand")
    await open_prayer_times(bot)
    await bot.press(ReminderCb(region_id=toshkent, on=True))

    edit = only(await bot.press(RegionCb(id=samarqand)), EditMessageText)
    assert keyboard_texts(edit)[0] == texts.REMINDER_ENABLE  # Samarqand uchun eslatma yoqilmagan

    await bot.press(ReminderCb(region_id=samarqand, on=True))
    user = await session.get(User, 111)
    await session.refresh(user)
    assert user.region_id == samarqand  # eslatma yangi shaharga o'tdi


async def test_unknown_city_is_answered_with_an_alert(bot):
    answer = only(await bot.press(RegionCb(id=999_999)), AnswerCallbackQuery)

    assert (answer.text, answer.show_alert) == (texts.STALE_BUTTON, True)


async def test_reminder_for_unknown_city_is_rejected(bot, session):
    await bot.say("/start")

    answer = only(await bot.press(ReminderCb(region_id=999_999, on=True)), AnswerCallbackQuery)

    assert answer.show_alert is True
    user = await session.get(User, 111)
    await session.refresh(user)
    assert user.subscribed is False
