"""Broadcast ishlarini navbat bilan bajaradi (eslatma siklidan mustaqil, alohida asyncio vazifasida)."""

import asyncio
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ilmbot.services.broadcast import BroadcastService

log = logging.getLogger(__name__)


async def run_broadcasts(
    service: BroadcastService,
    sessionmaker: async_sessionmaker[AsyncSession],
    bot: Bot,
    *,
    poll_seconds: float = 2.0,
) -> None:
    """Abadiy sikl: navbatdagi ish bo'lsa bajaradi, bo'lmasa kutadi. To'xtatilgan ishlar o'tkazib yuborilmaydi (ular
    `paused` holatida turadi va navbatga kirmaydi)."""
    while True:
        try:
            async with sessionmaker() as session:
                job_id = await service.next_job_id(session)
            if job_id is None:
                await asyncio.sleep(poll_seconds)
                continue
            log.info("Broadcast #%s boshlandi", job_id)
            await service.process(sessionmaker, bot, job_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Broadcast siklida xatolik")
            await asyncio.sleep(poll_seconds)
