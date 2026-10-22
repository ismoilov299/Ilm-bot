"""Adminlar uchun buyruqlar: /stats va /broadcast (admin panel tayyor bo'lguncha). `IsAdmin` bilan himoyalangan."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.bot import texts
from ilmbot.bot.callbacks import BroadcastCb
from ilmbot.bot.filters import IsAdmin
from ilmbot.bot.messaging import edit_text
from ilmbot.db.models import BroadcastJob, JobStatus, User
from ilmbot.services.broadcast import BroadcastService, JobAction

STATUS_UZ = {
    JobStatus.QUEUED.value: "navbatda",
    JobStatus.RUNNING.value: "yuborilmoqda",
    JobStatus.PAUSED.value: "to'xtatilgan",
    JobStatus.DONE.value: "tugadi",
    JobStatus.CANCELLED.value: "bekor qilindi",
}


class BroadcastForm(StatesGroup):
    waiting_message = State()


def status_text(job: BroadcastJob) -> str:
    return (
        f"\U0001f4e3 Broadcast #{job.id}: {STATUS_UZ.get(job.status, job.status)}\n"
        f"Jami: {job.total}\n"
        f"✅ Yuborildi: {job.sent}\n"
        f"\U0001f6ab Bloklagan: {job.blocked}\n"
        f"⚠️ Xato: {job.failed}"
    )


def job_keyboard(job: BroadcastJob) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if job.status in (JobStatus.QUEUED.value, JobStatus.RUNNING.value):
        builder.button(text=texts.BROADCAST_PAUSE, callback_data=BroadcastCb(act="pause", id=job.id))
    if job.status == JobStatus.PAUSED.value:
        builder.button(text=texts.BROADCAST_RESUME, callback_data=BroadcastCb(act="resume", id=job.id))
    if job.status not in (JobStatus.DONE.value, JobStatus.CANCELLED.value):
        builder.button(text=texts.BROADCAST_CANCEL, callback_data=BroadcastCb(act="cancel", id=job.id))
    builder.button(text=texts.BROADCAST_REFRESH, callback_data=BroadcastCb(act="status", id=job.id))
    builder.adjust(2)
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BROADCAST_SEND, callback_data=BroadcastCb(act="go"))
    builder.button(text=texts.BROADCAST_DECLINE, callback_data=BroadcastCb(act="no"))
    return builder.as_markup()


async def stats(message: Message, session: AsyncSession):
    total, blocked, subscribed = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(User.is_blocked.is_(True)),
                func.count().filter(User.subscribed.is_(True), User.is_blocked.is_(False)),
            ).select_from(User)
        )
    ).one()
    await message.answer(
        f"\U0001f465 Foydalanuvchilar: {total}\n"
        f"✅ Faol: {total - blocked}\n"
        f"\U0001f6ab Botni bloklagan: {blocked}\n"
        f"\U0001f514 Eslatma obunachilari: {subscribed}"
    )


async def start_broadcast(message: Message, state: FSMContext):
    await state.set_state(BroadcastForm.waiting_message)
    await message.answer(texts.BROADCAST_ASK)


async def cancel_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.BROADCAST_DECLINED)


async def receive_content(message: Message, state: FSMContext, session: AsyncSession, broadcasts: BroadcastService):
    """Admin yuborgan xabar (istalgan turdagi) saqlanadi va tasdiq so'raladi."""
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    count = await broadcasts.count_recipients(session)
    await message.reply(texts.BROADCAST_CONFIRM.format(count=count), reply_markup=confirm_keyboard())


async def confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, broadcasts: BroadcastService):
    data = await state.get_data()
    message = callback.message
    if "message_id" not in data or not isinstance(message, Message):
        await callback.answer(texts.BROADCAST_EXPIRED, show_alert=True)
        return
    job = await broadcasts.create_job(session, f"tg:{callback.from_user.id}", data["chat_id"], data["message_id"])
    await state.clear()
    await callback.answer()
    await edit_text(message, status_text(job), job_keyboard(job))


async def decline(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.BROADCAST_DECLINED)


async def job_status(message: Message, session: AsyncSession, broadcasts: BroadcastService):
    job = await broadcasts.latest(session)
    if job is None:
        await message.answer(texts.BROADCAST_NONE)
        return
    await message.answer(status_text(job), reply_markup=job_keyboard(job))


async def job_action(
    callback: CallbackQuery, callback_data: BroadcastCb, session: AsyncSession, broadcasts: BroadcastService
):
    message = callback.message
    actions = {"pause": JobAction.PAUSE, "resume": JobAction.RESUME, "cancel": JobAction.CANCEL}
    if callback_data.act in actions:
        job = await broadcasts.apply(session, callback_data.id, actions[callback_data.act])
    else:
        job = await broadcasts.get(session, callback_data.id)
    if job is None or not isinstance(message, Message):
        await callback.answer(texts.BROADCAST_NONE, show_alert=True)
        return
    await callback.answer()
    await edit_text(message, status_text(job), job_keyboard(job))


def create_router() -> Router:
    router = Router(name="admin")
    router.message.filter(IsAdmin())
    router.callback_query.filter(IsAdmin())
    router.message.register(stats, Command("stats"))
    router.message.register(start_broadcast, Command("broadcast"))
    router.message.register(job_status, Command("broadcast_status"))
    router.message.register(cancel_form, Command("cancel"), StateFilter(BroadcastForm.waiting_message))
    router.message.register(receive_content, StateFilter(BroadcastForm.waiting_message))
    router.callback_query.register(
        confirm, BroadcastCb.filter(F.act == "go"), StateFilter(BroadcastForm.waiting_message)
    )
    router.callback_query.register(
        decline, BroadcastCb.filter(F.act == "no"), StateFilter(BroadcastForm.waiting_message)
    )
    router.callback_query.register(job_action, BroadcastCb.filter(F.act.in_({"pause", "resume", "cancel", "status"})))
    return router
