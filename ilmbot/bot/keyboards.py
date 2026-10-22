import math
from collections.abc import Sequence

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from ilmbot.bot.callbacks import NodeCb
from ilmbot.bot.texts import BACK
from ilmbot.services.menu import Node

# Telegram reply klaviaturasida tugmalar ko'p bo'lsa noqulay; shundan oshsa ro'yxat (inline) ishlatiladi
MAX_REPLY_BUTTONS = 30


def reply_menu(children: Sequence[Node], *, back: bool) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for child in children:
        builder.button(text=child.name)
    builder.adjust(2)
    if back:
        builder.row(KeyboardButton(text=BACK))
    return builder.as_markup(resize_keyboard=True)


def page_count(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / max(1, page_size)))


def inline_list(
    node: Node, children: Sequence[Node], *, page: int = 1, back_to: int | None = None
) -> InlineKeyboardMarkup:
    """`node` ning bolalari sahifalangan inline ro'yxati. `back_to`: ota ro'yxatga qaytish tugmasi uchun."""
    pages = page_count(len(children), node.page_size)
    page = min(max(1, page), pages)
    start = (page - 1) * node.page_size

    builder = InlineKeyboardBuilder()
    for child in children[start : start + node.page_size]:
        builder.button(text=child.name, callback_data=NodeCb(act="o", id=child.id))
    builder.adjust(1)

    if pages > 1:
        nav = InlineKeyboardBuilder()
        if page > 1:
            nav.button(text="‹", callback_data=NodeCb(act="p", id=node.id, page=page - 1))
        nav.button(text=f"{page}/{pages}", callback_data=NodeCb(act="x", id=node.id))
        if page < pages:
            nav.button(text="›", callback_data=NodeCb(act="p", id=node.id, page=page + 1))
        nav.adjust(3)
        builder.attach(nav)
    if back_to is not None:
        back_row = InlineKeyboardBuilder()
        back_row.button(text=f"‹ {BACK}", callback_data=NodeCb(act="p", id=back_to))
        builder.attach(back_row)
    return builder.as_markup()
