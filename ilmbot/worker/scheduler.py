"""Daqiqalik rejalashtirgich: vaqti kelgan eslatmalarni egallaydi va fonda yuboradi."""

import asyncio
import datetime as dt
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ilmbot.services.reminders import Due, ReminderService

log = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(self, reminders: ReminderService, sessionmaker: async_sessionmaker[AsyncSession], bot: Bot):
        self._reminders = reminders
        self._sessionmaker = sessionmaker
        self._bot = bot
        self._tasks: set[asyncio.Task] = set()

    async def tick(self, now: dt.datetime) -> int:
        """Vaqti kelganlarni egallaydi va yuborishni fonda boshlaydi. Egallanganlar sonini qaytaradi."""
        async with self._sessionmaker() as session:
            claimed = []
            for due in await self._reminders.find_due(session, now):
                if (run_id := await self._reminders.claim(session, due)) is not None:
                    claimed.append((run_id, due))
            await session.commit()
        for run_id, due in claimed:
            self._spawn(run_id, due, None)
        return len(claimed)

    async def resume(self) -> int:
        """Ishga tushganda: oldingi uzilishdan qolgan yuborishlarni davom ettiradi."""
        async with self._sessionmaker() as session:
            pending = await self._reminders.unfinished(session)
        for run_id, due, last_user_id in pending:
            self._spawn(run_id, due, last_user_id)
        return len(pending)

    def _spawn(self, run_id: int, due: Due, last_user_id: int | None) -> None:
        task = asyncio.create_task(self._reminders.deliver(self._sessionmaker, self._bot, run_id, due, last_user_id))
        self._tasks.add(task)
        task.add_done_callback(self._finished)

    def _finished(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            log.error("Eslatma yuborishda xatolik", exc_info=task.exception())

    async def wait_idle(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    def cancel_all(self) -> None:
        for task in self._tasks:
            task.cancel()
