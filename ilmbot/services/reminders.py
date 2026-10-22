"""Namoz vaqti eslatmalari: kim, qachon, nima yuboriladi va qayta ishga tushganda davom ettirish."""

import datetime as dt
import logging
from collections import Counter
from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ilmbot.db.models import PrayerTime, Region, ReminderRun, User
from ilmbot.integrations.prayer_calc import PRAYERS
from ilmbot.integrations.telegram_sender import SendResult, TelegramSender

log = logging.getLogger(__name__)

# Worker uzilib qolsa ham eski eslatma "vaqti bo'ldi" deb kech yuborilmasligi uchun
GRACE_MINUTES = 3
BATCH_SIZE = 200

MESSAGES = {
    "bomdod": "\U0001f30c Bomdod vaqti bo'ldi!",
    "quyosh": "\U0001f304 Quyosh chiqdi!",
    "peshin": "\U0001f307 Peshin vaqti bo'ldi!",
    "asr": "\U0001f306 Asr vaqti bo'ldi!",
    "shom": "\U0001f3d9 Shom vaqti bo'ldi!",
    "xufton": "\U0001f303 Xufton vaqti bo'ldi!",
}
assert set(MESSAGES) == set(PRAYERS)


@dataclass(frozen=True, slots=True)
class Due:
    date: dt.date
    prayer: str
    region_id: int
    region_name: str
    time: dt.time


def reminder_text(due: Due) -> str:
    """Xabarda vaqt ham yoziladi: ko'p obunachida yuborish bir necha daqiqa cho'zilishi mumkin."""
    return f"{MESSAGES[due.prayer]}\n{due.region_name}: {due.time:%H:%M}"


class ReminderService:
    def __init__(self, sender: TelegramSender, *, grace_minutes: int = GRACE_MINUTES, batch_size: int = BATCH_SIZE):
        self._sender = sender
        self._grace = dt.timedelta(minutes=grace_minutes)
        self._batch_size = batch_size

    async def find_due(self, session: AsyncSession, now: dt.datetime) -> list[Due]:
        """Oxirgi `grace` daqiqada vaqti kelgan (sana, namoz, region) lar."""
        end = now.replace(second=0, microsecond=0)
        start = end - self._grace
        rows = await session.execute(
            select(PrayerTime, Region.name)
            .join(Region, Region.id == PrayerTime.region_id)
            .where(PrayerTime.date.in_({start.date(), end.date()}), Region.is_active)
        )
        due = []
        for prayer_time, region_name in rows:
            for prayer in PRAYERS:
                moment = dt.datetime.combine(prayer_time.date, getattr(prayer_time, prayer), tzinfo=now.tzinfo)
                if start <= moment <= end:
                    due.append(Due(prayer_time.date, prayer, prayer_time.region_id, region_name, moment.time()))
        return due

    async def claim(self, session: AsyncSession, due: Due) -> int | None:
        """Eslatma yuborishni egallaydi. Allaqachon egallangan bo'lsa (takrorlanish) None qaytaradi."""
        statement = (
            insert(ReminderRun)
            .values(date=due.date, prayer=due.prayer, region_id=due.region_id)
            .on_conflict_do_nothing(index_elements=[ReminderRun.date, ReminderRun.prayer, ReminderRun.region_id])
            .returning(ReminderRun.id)
        )
        return await session.scalar(statement)

    async def unfinished(self, session: AsyncSession) -> list[tuple[int, Due, int | None]]:
        """Worker uzilishi tufayli tugallanmagan yuborishlar: (run_id, Due, oxirgi yuborilgan foydalanuvchi)."""
        rows = await session.execute(
            select(ReminderRun, PrayerTime, Region.name)
            .join(PrayerTime, (PrayerTime.region_id == ReminderRun.region_id) & (PrayerTime.date == ReminderRun.date))
            .join(Region, Region.id == ReminderRun.region_id)
            .where(ReminderRun.status == "running")
        )
        return [
            (
                run.id,
                Due(run.date, run.prayer, run.region_id, region_name, getattr(prayer_time, run.prayer)),
                run.last_user_id,
            )
            for run, prayer_time, region_name in rows
        ]

    async def deliver(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        bot: Bot,
        run_id: int,
        due: Due,
        last_user_id: int | None = None,
    ) -> Counter:
        """Obunachilarga `user_id` tartibida bo'laklab yuboradi; har bo'lakdan keyin holat saqlanadi."""
        text = reminder_text(due)
        last = last_user_id or 0
        stats: Counter = Counter()
        while True:
            async with sessionmaker() as session:
                user_ids = (
                    await session.scalars(
                        select(User.id)
                        .where(
                            User.region_id == due.region_id,
                            User.subscribed.is_(True),
                            User.is_blocked.is_(False),
                            User.id > last,
                        )
                        .order_by(User.id)
                        .limit(self._batch_size)
                    )
                ).all()
                if not user_ids:
                    await session.execute(
                        update(ReminderRun)
                        .where(ReminderRun.id == run_id)
                        .values(status="done", finished_at=func.now())
                    )
                    await session.commit()
                    log.info("Eslatma tugadi: %s %s %s %s", due.date, due.prayer, due.region_name, dict(stats))
                    return stats
                blocked = []
                for user_id in user_ids:
                    result = await self._sender.send_text(bot, user_id, text)
                    stats[result.value] += 1
                    if result is SendResult.BLOCKED:
                        blocked.append(user_id)
                if blocked:
                    await session.execute(update(User).where(User.id.in_(blocked)).values(is_blocked=True))
                last = user_ids[-1]
                await session.execute(update(ReminderRun).where(ReminderRun.id == run_id).values(last_user_id=last))
                await session.commit()
