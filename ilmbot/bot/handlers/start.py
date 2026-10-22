from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.bot import texts
from ilmbot.bot.keyboards import reply_menu
from ilmbot.services.menu import MenuService
from ilmbot.services.navigation import NavigationState
from ilmbot.services.users import UserService


async def start(message: Message, session: AsyncSession, menu: MenuService, nav: NavigationState, users: UserService):
    user = message.from_user
    is_new = await users.touch(session, user.id, user.full_name)
    await nav.set(user.id, None)
    snapshot = await menu.snapshot(session)
    template = texts.WELCOME_NEW if is_new else texts.WELCOME_BACK
    if not snapshot.roots:
        await message.answer(template.format(name=escape(user.full_name)))
        await message.answer(texts.NO_SECTIONS)
        return
    await message.answer(
        template.format(name=escape(user.full_name)), reply_markup=reply_menu(snapshot.roots, back=False)
    )


async def help_command(message: Message):
    await message.answer(texts.HELP)


async def my_id(message: Message):
    """Foydalanuvchi o'z Telegram ID sini bilishi uchun (ADMINS ni sozlashda kerak)."""
    await message.answer(f"Sizning Telegram ID: <code>{message.from_user.id}</code>")


def create_router() -> Router:
    router = Router(name="start")
    router.message.register(start, CommandStart())
    router.message.register(help_command, Command("help"))
    router.message.register(my_id, Command("myid"))
    return router
