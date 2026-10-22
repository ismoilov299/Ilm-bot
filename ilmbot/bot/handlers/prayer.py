"""Namoz vaqtlari: shahar tanlash, bugungi vaqtlar va kunlik eslatmani yoqish/o'chirish."""

import datetime as dt
from collections.abc import Callable
from html import escape

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.bot import texts
from ilmbot.bot.callbacks import RegionCb, ReminderCb
from ilmbot.bot.messaging import answer_text, edit_markup, edit_text
from ilmbot.db.models import PrayerTime, Region, User
from ilmbot.services.prayers import PrayerService
from ilmbot.services.users import UserService

WEEKDAYS = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba")
LABELS = (
    ("bomdod", "\U0001f30c Bomdod"),
    ("quyosh", "\U0001f304 Quyosh"),
    ("peshin", "\U0001f307 Peshin"),
    ("asr", "\U0001f306 Asr"),
    ("shom", "\U0001f3d9 Shom"),
    ("xufton", "\U0001f303 Xufton"),
)
Clock = Callable[[], dt.datetime]


def format_times(region_name: str, date: dt.date, times: PrayerTime) -> str:
    lines = "\n".join(f"{label}: <b>{getattr(times, key):%H:%M}</b>" for key, label in LABELS)
    header = f"\U0001f54c <b>{escape(region_name)}</b>, {date:%d.%m.%Y} ({WEEKDAYS[date.weekday()]})"
    return f"{header}\n\n{lines}\n\n<i>{texts.TIMES_FOOTER}</i>"


def regions_keyboard(regions: list[Region]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for region in regions:
        builder.button(text=region.name, callback_data=RegionCb(id=region.id))
    builder.adjust(2)
    return builder.as_markup()


def times_keyboard(region_id: int, reminder_on: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if reminder_on:
        builder.button(text=texts.REMINDER_DISABLE, callback_data=ReminderCb(region_id=region_id, on=False))
    else:
        builder.button(text=texts.REMINDER_ENABLE, callback_data=ReminderCb(region_id=region_id, on=True))
    builder.button(text=texts.OTHER_CITY, callback_data=RegionCb(id=0))
    builder.adjust(1)
    return builder.as_markup()


async def _active_regions(session: AsyncSession) -> list[Region]:
    return list((await session.scalars(select(Region).where(Region.is_active).order_by(Region.id))).all())


async def _active_region(session: AsyncSession, region_id: int) -> Region | None:
    region = await session.get(Region, region_id)
    return region if region is not None and region.is_active else None


async def _times_view(
    session: AsyncSession, prayers: PrayerService, clock: Clock, region: Region, user: User | None
) -> tuple[str, InlineKeyboardMarkup]:
    today = clock().date()
    times = await prayers.get_times(session, region, today)
    reminder_on = user is not None and user.subscribed and user.region_id == region.id
    return format_times(region.name, today, times), times_keyboard(region.id, reminder_on)


def make_prayer_action(prayers: PrayerService, users: UserService, clock: Clock):
    """`prayer_times` amali: saqlangan shahar bo'lsa shu shahar vaqtlari, bo'lmasa shaharlar ro'yxati."""

    async def show(message: Message, session: AsyncSession, user_id: int) -> None:
        user = await users.get(session, user_id)
        region = await _active_region(session, user.region_id) if user is not None and user.region_id else None
        if region is not None:
            text, markup = await _times_view(session, prayers, clock, region, user)
            await answer_text(message, text, reply_markup=markup)
            return
        await message.answer(texts.CHOOSE_CITY, reply_markup=regions_keyboard(await _active_regions(session)))

    return show


async def on_region(
    callback: CallbackQuery,
    callback_data: RegionCb,
    session: AsyncSession,
    prayers: PrayerService,
    users: UserService,
    clock: Clock,
):
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer(texts.STALE_BUTTON, show_alert=True)
        return
    if callback_data.id == 0:  # "Boshqa shahar"
        await callback.answer()
        await edit_text(message, texts.CHOOSE_CITY, regions_keyboard(await _active_regions(session)))
        return
    region = await _active_region(session, callback_data.id)
    if region is None:
        await callback.answer(texts.STALE_BUTTON, show_alert=True)
        return
    await callback.answer()
    await users.touch(session, callback.from_user.id, callback.from_user.full_name)
    user = await users.get(session, callback.from_user.id)
    text, markup = await _times_view(session, prayers, clock, region, user)
    await edit_text(message, text, markup)


async def on_reminder(callback: CallbackQuery, callback_data: ReminderCb, session: AsyncSession, users: UserService):
    message = callback.message
    region = await _active_region(session, callback_data.region_id)
    if not isinstance(message, Message) or region is None:
        await callback.answer(texts.STALE_BUTTON, show_alert=True)
        return
    await users.touch(session, callback.from_user.id, callback.from_user.full_name)
    await users.set_reminder(session, callback.from_user.id, region.id, callback_data.on)
    toast = texts.REMINDER_ON if callback_data.on else texts.REMINDER_OFF
    await callback.answer(toast.format(region=region.name))
    await edit_markup(message, times_keyboard(region.id, callback_data.on))


def create_router() -> Router:
    router = Router(name="prayer")
    router.callback_query.register(on_region, RegionCb.filter())
    router.callback_query.register(on_reminder, ReminderCb.filter())
    return router
