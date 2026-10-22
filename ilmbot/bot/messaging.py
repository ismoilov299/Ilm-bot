"""Xabar yuborish va tahrirlash yordamchilari: admin yozgan HTML noto'g'ri bo'lsa ham bot to'xtamaydi."""

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message


def _is_parse_error(exc: TelegramBadRequest) -> bool:
    return "can't parse entities" in str(exc)


async def answer_text(message: Message, text: str, **kwargs) -> None:
    try:
        await message.answer(text, **kwargs)
    except TelegramBadRequest as exc:
        if not _is_parse_error(exc):
            raise
        await message.answer(text, parse_mode=None, **kwargs)


async def edit_text(message: Message, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return
        if not _is_parse_error(exc):
            raise
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=None)


async def edit_markup(message: Message, reply_markup: InlineKeyboardMarkup) -> None:
    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
