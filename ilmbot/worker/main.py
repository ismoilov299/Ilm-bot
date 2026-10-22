import asyncio
import datetime as dt
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from redis.asyncio import Redis

from ilmbot.config import get_settings
from ilmbot.db import make_engine, make_sessionmaker
from ilmbot.integrations.rate_limiter import RateLimiter
from ilmbot.integrations.telegram_sender import TelegramSender
from ilmbot.services.broadcast import BroadcastService
from ilmbot.services.prayers import PrayerService
from ilmbot.services.reminders import ReminderService
from ilmbot.worker.broadcast_runner import run_broadcasts
from ilmbot.worker.scheduler import ReminderScheduler

log = logging.getLogger(__name__)
PREFETCH_DAYS = 3


def seconds_until_next_minute(now: dt.datetime) -> float:
    return 60 - now.second - now.microsecond / 1_000_000 + 0.05


async def run() -> None:
    settings = get_settings()
    token = settings.require_bot_token()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    tz = ZoneInfo(settings.timezone)
    engine = make_engine(settings.database_url)
    sessionmaker = make_sessionmaker(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    sender = TelegramSender(RateLimiter(redis, per_second=settings.send_rate_per_sec))
    # Bir xil umumiy hisoblagich, lekin eslatma (katta limit) broadcastdan (kichik limit) ustun turadi
    broadcast_sender = TelegramSender(RateLimiter(redis, per_second=settings.broadcast_rate_per_sec))
    broadcasts = BroadcastService(broadcast_sender)
    prayers = PrayerService()
    scheduler = ReminderScheduler(ReminderService(sender), sessionmaker, bot)

    last_prepared: dt.date | None = None
    broadcast_task = asyncio.create_task(run_broadcasts(broadcasts, sessionmaker, bot))
    try:
        resumed = await scheduler.resume()
        log.info("Worker ishga tushdi (davom ettirilgan yuborishlar: %s)", resumed)
        while True:
            now = dt.datetime.now(tz)
            if last_prepared != now.date():  # kuniga bir marta (va ishga tushganda): bugun va keyingi kunlar vaqtlari
                async with sessionmaker() as session, session.begin():
                    await prayers.ensure_times(session, now.date(), days=PREFETCH_DAYS)
                last_prepared = now.date()
            started = await scheduler.tick(now)
            if started:
                log.info("%s ta eslatma yuborish boshlandi (%s)", started, now.strftime("%H:%M"))
            await asyncio.sleep(seconds_until_next_minute(dt.datetime.now(tz)))
    finally:
        broadcast_task.cancel()
        scheduler.cancel_all()  # yarim qolgan yuborishlar keyingi ishga tushishda davom ettiriladi
        await redis.aclose()
        await engine.dispose()
        await bot.session.close()
