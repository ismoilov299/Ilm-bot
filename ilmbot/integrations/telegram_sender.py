"""Ommaviy xabarlar (eslatma, broadcast) uchun yuboruvchi: tezlik cheklovi va xatolarni boshqarish."""

import asyncio
import enum
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)

from ilmbot.integrations.rate_limiter import RateLimiter

log = logging.getLogger(__name__)


class SendResult(enum.StrEnum):
    SENT = "sent"
    BLOCKED = "blocked"  # foydalanuvchi botni bloklagan yoki akkaunti o'chirilgan
    FAILED = "failed"


class TelegramSender:
    def __init__(
        self,
        limiter: RateLimiter,
        *,
        max_attempts: int = 3,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._limiter = limiter
        self._max_attempts = max_attempts
        self._sleep = sleep

    async def send_text(self, bot: Bot, chat_id: int, text: str) -> SendResult:
        for attempt in range(1, self._max_attempts + 1):
            await self._limiter.acquire()
            try:
                await bot.send_message(chat_id, text)
                return SendResult.SENT
            except TelegramRetryAfter as exc:
                log.warning("Telegram limiti: %s soniya kutiladi", exc.retry_after)
                await self._sleep(exc.retry_after + 0.5)
            except TelegramForbiddenError:
                return SendResult.BLOCKED
            except TelegramBadRequest as exc:
                log.warning("Xabar yuborilmadi (chat %s): %s", chat_id, exc)
                return SendResult.FAILED
            except TelegramNetworkError as exc:
                log.warning("Tarmoq xatosi (urinish %s/%s): %s", attempt, self._max_attempts, exc)
                await self._sleep(attempt)
            except TelegramAPIError as exc:
                log.warning("Telegram xatosi (chat %s): %s", chat_id, exc)
                return SendResult.FAILED
        return SendResult.FAILED
