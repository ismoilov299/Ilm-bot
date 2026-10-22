"""Ommaviy xabar yuborish (broadcast): navbat PostgreSQL da, bajaruvchi worker. Uzilsa qolgan joyidan davom etadi."""

import enum
import logging
from collections import Counter
from collections.abc import Sequence

from aiogram import Bot
from sqlalchemy import func, insert, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ilmbot.db.models import BroadcastJob, BroadcastRecipient, JobStatus, RecipientStatus, User
from ilmbot.integrations.telegram_sender import SendResult, TelegramSender

log = logging.getLogger(__name__)

BATCH_SIZE = 50  # to'xtatish/bekor qilish shu bo'lak tugagach seziladi
ACTIVE = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)
FINAL = (JobStatus.DONE.value, JobStatus.CANCELLED.value)


class JobAction(enum.StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"


class BroadcastService:
    def __init__(
        self,
        sender: TelegramSender | None = None,
        *,
        batch_size: int = BATCH_SIZE,
        content_channel: str | int | None = None,
    ):
        self._sender = sender
        self._batch_size = batch_size
        self._content_channel = content_channel  # `source_chat_id` ko'rsatilmagan ishlar shu kanaldan nusxalanadi

    # --- admin tomoni -------------------------------------------------------------------------------------

    def _audience(self, only_user_ids: Sequence[int] | None):
        """Botni bloklamagan foydalanuvchilar; `only_user_ids` berilsa (sinov) faqat shular."""
        query = select(User.id).where(User.is_blocked.is_(False))
        return query.where(User.id.in_(list(only_user_ids))) if only_user_ids is not None else query

    async def count_recipients(self, session: AsyncSession, only_user_ids: Sequence[int] | None = None) -> int:
        return await session.scalar(select(func.count()).select_from(self._audience(only_user_ids).subquery()))

    async def create_job(
        self,
        session: AsyncSession,
        created_by: str,
        *,
        text: str | None = None,
        source_chat_id: int | None = None,
        source_message_id: int | None = None,
        only_user_ids: Sequence[int] | None = None,
    ) -> BroadcastJob:
        """Ishni yaratadi va qabul qiluvchilarni shu paytdagi holat bo'yicha qayd qiladi (bloklaganlarsiz).

        Mazmun: tayyor `text` (tozalangan HTML) yoki nusxalanadigan xabar (`source_chat_id` + `source_message_id`).
        `only_user_ids` berilsa, bu sinov ishi bo'lib, faqat shu foydalanuvchilarga boradi.
        """
        job = BroadcastJob(
            created_by=created_by,
            text=text,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            is_test=only_user_ids is not None,
        )
        session.add(job)
        await session.flush()
        audience = self._audience(only_user_ids).add_columns().with_only_columns(literal(job.id), User.id)
        await session.execute(insert(BroadcastRecipient).from_select(["job_id", "user_id"], audience))
        job.total = await session.scalar(
            select(func.count()).select_from(BroadcastRecipient).where(BroadcastRecipient.job_id == job.id)
        )
        await session.flush()
        return job

    async def get(self, session: AsyncSession, job_id: int) -> BroadcastJob | None:
        return await session.get(BroadcastJob, job_id, populate_existing=True)

    async def latest(self, session: AsyncSession) -> BroadcastJob | None:
        return await session.scalar(select(BroadcastJob).order_by(BroadcastJob.id.desc()).limit(1))

    async def apply(self, session: AsyncSession, job_id: int, action: JobAction) -> BroadcastJob | None:
        """To'xtatish, davom ettirish yoki bekor qilish. Tugallangan ishga ta'sir qilmaydi."""
        job = await self.get(session, job_id)
        if job is None or job.status in FINAL:
            return job
        if action is JobAction.PAUSE and job.status in ACTIVE:
            job.status = JobStatus.PAUSED.value
        elif action is JobAction.RESUME and job.status == JobStatus.PAUSED.value:
            job.status = JobStatus.QUEUED.value
        elif action is JobAction.CANCEL:
            job.status = JobStatus.CANCELLED.value
            job.finished_at = func.now()
        await session.flush()
        return job

    # --- worker tomoni ------------------------------------------------------------------------------------

    async def next_job_id(self, session: AsyncSession) -> int | None:
        """Navbatdagi (yoki worker uzilishidan qolgan) ish."""
        return await session.scalar(
            select(BroadcastJob.id).where(BroadcastJob.status.in_(ACTIVE)).order_by(BroadcastJob.id).limit(1)
        )

    async def process(self, sessionmaker: async_sessionmaker[AsyncSession], bot: Bot, job_id: int) -> str:
        """Ishni bo'laklab bajaradi. Har bo'lakdan keyin holat saqlanadi va to'xtatish/bekor qilish tekshiriladi."""
        assert self._sender is not None, "process() uchun sender kerak"
        async with sessionmaker() as session:
            job = await self.get(session, job_id)
            if job is None or job.status not in ACTIVE:
                return job.status if job else "missing"
            if job.status == JobStatus.QUEUED.value:
                job.status = JobStatus.RUNNING.value
                job.started_at = job.started_at or func.now()
            text, chat_id, message_id = job.text, job.source_chat_id, job.source_message_id
            await session.commit()

        while True:
            async with sessionmaker() as session:
                job = await self.get(session, job_id)
                if job.status not in ACTIVE:
                    return job.status  # to'xtatildi yoki bekor qilindi
                user_ids = (
                    await session.scalars(
                        select(BroadcastRecipient.user_id)
                        .where(
                            BroadcastRecipient.job_id == job_id,
                            BroadcastRecipient.status == RecipientStatus.PENDING.value,
                        )
                        .order_by(BroadcastRecipient.user_id)
                        .limit(self._batch_size)
                    )
                ).all()
                if not user_ids:
                    job.status = JobStatus.DONE.value
                    job.finished_at = func.now()
                    await session.commit()
                    log.info(
                        "Broadcast #%s tugadi: yuborildi=%s, bloklagan=%s, xato=%s",
                        job_id,
                        job.sent,
                        job.blocked,
                        job.failed,
                    )
                    return JobStatus.DONE.value

                outcome: dict[int, SendResult] = {}
                for user_id in user_ids:
                    if text is not None:
                        outcome[user_id] = await self._sender.send_text(bot, user_id, text)
                    else:
                        outcome[user_id] = await self._sender.copy_message(
                            bot, user_id, chat_id or self._content_channel, message_id
                        )
                await self._save_batch(session, job_id, outcome)
                await session.commit()

    @staticmethod
    async def _save_batch(session: AsyncSession, job_id: int, outcome: dict[int, SendResult]) -> None:
        by_result = {result: [uid for uid, r in outcome.items() if r is result] for result in SendResult}
        status_of = {
            SendResult.SENT: RecipientStatus.SENT.value,
            SendResult.BLOCKED: RecipientStatus.BLOCKED.value,
            SendResult.FAILED: RecipientStatus.FAILED.value,
        }
        for result, ids in by_result.items():
            if ids:
                await session.execute(
                    update(BroadcastRecipient)
                    .where(BroadcastRecipient.job_id == job_id, BroadcastRecipient.user_id.in_(ids))
                    .values(status=status_of[result])
                )
        if by_result[SendResult.BLOCKED]:
            await session.execute(
                update(User).where(User.id.in_(by_result[SendResult.BLOCKED])).values(is_blocked=True)
            )
        counts = Counter({result: len(ids) for result, ids in by_result.items()})
        await session.execute(
            update(BroadcastJob)
            .where(BroadcastJob.id == job_id)
            .values(
                sent=BroadcastJob.sent + counts[SendResult.SENT],
                blocked=BroadcastJob.blocked + counts[SendResult.BLOCKED],
                failed=BroadcastJob.failed + counts[SendResult.FAILED],
            )
        )
