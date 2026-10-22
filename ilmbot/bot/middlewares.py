from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Update
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    """Har bir update uchun bitta sessiya: muvaffaqiyatli tugasa commit, xato bo'lsa orqaga qaytariladi."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sessionmaker = sessionmaker

    async def __call__(
        self, handler: Callable[[Update, dict[str, Any]], Awaitable[Any]], event: Update, data: dict[str, Any]
    ):
        async with self._sessionmaker() as session:
            data["session"] = session
            result = await handler(event, data)
            await session.commit()
            return result


class ThrottlingMiddleware(BaseMiddleware):
    """Bitta foydalanuvchining juda tez ketma-ket so'rovlarini tashlab yuboradi (Redis, jarayonlar orasida umumiy)."""

    def __init__(self, redis: Redis, interval: float = 0.6):
        self._redis = redis
        self._interval_ms = int(interval * 1000)

    async def __call__(
        self, handler: Callable[[Update, dict[str, Any]], Awaitable[Any]], event: Update, data: dict[str, Any]
    ):
        user = data.get("event_from_user")
        if user is None or self._interval_ms <= 0:
            return await handler(event, data)
        if await self._redis.set(f"throttle:{user.id}", 1, nx=True, px=self._interval_ms):
            return await handler(event, data)
        if event.callback_query is not None:
            await event.callback_query.answer()  # tugma "aylanib" qolmasligi uchun
        return None
