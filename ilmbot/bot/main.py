import datetime as dt
import logging
from collections.abc import Callable
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ilmbot.bot.handlers import create_routers
from ilmbot.bot.handlers.mosques import prompt_for_location
from ilmbot.bot.handlers.prayer import make_prayer_action
from ilmbot.bot.middlewares import DbSessionMiddleware, ThrottlingMiddleware
from ilmbot.config import Settings, get_settings
from ilmbot.db import make_engine, make_sessionmaker
from ilmbot.db.models import ButtonAction
from ilmbot.integrations.telegram_content import ContentSender
from ilmbot.services.broadcast import BroadcastService
from ilmbot.services.menu import MenuService
from ilmbot.services.mosques import MosqueService
from ilmbot.services.navigation import NavigationState
from ilmbot.services.prayers import PrayerService
from ilmbot.services.users import UserService

COMMANDS = [
    BotCommand(command="start", description="Botni ishga tushirish"),
    BotCommand(command="help", description="Adminlar bilan bog'lanish"),
]


def create_dispatcher(
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
    settings: Settings,
    throttle_interval: float = 0.6,
    clock: Callable[[], dt.datetime] | None = None,
) -> Dispatcher:
    """Global holatsiz: har bir bog'liqlik shu yerda beriladi (testlarda ham shu funksiya ishlatiladi)."""
    dp = Dispatcher(storage=RedisStorage(redis))  # admin formalari holati qayta ishga tushganda yo'qolmaydi
    # Sessiya ochishdan oldin: tashlangan so'rovlar bazaga tegmaydi
    dp.update.outer_middleware(ThrottlingMiddleware(redis, interval=throttle_interval))
    dp.update.outer_middleware(DbSessionMiddleware(sessionmaker))
    tz = ZoneInfo(settings.timezone)
    clock = clock or (lambda: dt.datetime.now(tz))
    users, prayers = UserService(), PrayerService()
    dp.workflow_data.update(
        menu=MenuService(),
        nav=NavigationState(redis),
        users=users,
        prayers=prayers,
        mosques=MosqueService(),
        broadcasts=BroadcastService(),
        settings=settings,
        clock=clock,
        content=ContentSender(settings.content_channel, settings.protect_content),
        actions={
            ButtonAction.PRAYER_TIMES.value: make_prayer_action(prayers, users, clock),
            ButtonAction.NEAREST_MOSQUES.value: prompt_for_location,
        },
    )
    dp.include_routers(*create_routers())
    return dp


async def run() -> None:
    settings = get_settings()
    token = settings.require_bot_token()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    engine = make_engine(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher(sessionmaker=make_sessionmaker(engine), redis=redis, settings=settings)
    try:
        await bot.set_my_commands(COMMANDS)
        me = await bot.get_me()
        logging.getLogger(__name__).info("Bot ishga tushdi: @%s", me.username)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await redis.aclose()
        await engine.dispose()
        await bot.session.close()
