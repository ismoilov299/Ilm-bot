"""Kontent kanalidagi postlarni foydalanuvchiga nusxalash."""

import asyncio
import logging
from collections.abc import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

log = logging.getLogger(__name__)


class ContentSender:
    def __init__(self, channel: str, protect_content: bool = True):
        self._channel = channel
        self._protect = protect_content

    async def send_posts(self, bot: Bot, chat_id: int, message_ids: Iterable[int]) -> int:
        """Postlarni ketma-ket yuboradi. Yuborilganlar sonini qaytaradi (topilmagan post o'tkazib yuboriladi)."""
        sent = 0
        for message_id in message_ids:
            try:
                await self._copy(bot, chat_id, message_id)
                sent += 1
            except TelegramBadRequest as exc:
                log.warning("Post %s nusxalanmadi: %s", message_id, exc)
        return sent

    async def _copy(self, bot: Bot, chat_id: int, message_id: int) -> None:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=self._channel,
                message_id=message_id,
                protect_content=self._protect,
            )
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=self._channel,
                message_id=message_id,
                protect_content=self._protect,
            )
