"""Telegramga yuborish tezligini cheklash: bot va worker o'rtasida umumiy (Redis).

Telegram umumiy limiti ~30 xabar/s. Vaqt qisqa oynalarga (0,2 s) bo'linadi va har bir oynada ruxsat etilgan sondan ko'p
xabar yuborilmaydi; shu tufayli istalgan 1 soniyada limitdan kam yoki biroz ko'p (bitta oyna hajmicha) yuboriladi.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis


class RateLimiter:
    def __init__(
        self,
        redis: Redis,
        *,
        per_second: int,
        key: str = "tg:send",
        window: float = 0.2,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._redis = redis
        self._key = key
        self._window = window
        self._per_window = max(1, round(per_second * window))
        self._clock = clock
        self._sleep = sleep

    async def acquire(self) -> None:
        """Navbat kelguncha kutadi; qaytganda yuborishga ruxsat bor."""
        while True:
            now = self._clock()
            slot = int(now / self._window)
            key = f"{self._key}:{slot}"
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, 2)
            if count <= self._per_window:
                return
            await self._sleep((slot + 1) * self._window - now + 0.001)
