"""Botning haqiqiy username'i token orqali olinadi; qo'lda sozlash kerak emas."""

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError


async def resolve_bot_username(token: str) -> str:
    try:
        async with Bot(token) as bot:
            me = await bot.get_me()
    except TelegramAPIError:
        raise RuntimeError("Telegram getMe ishlamadi: BOT_TOKEN va internet ulanishini tekshiring") from None
    if not me.username:
        raise RuntimeError("Telegram getMe bot username'ini qaytarmadi")
    return me.username
