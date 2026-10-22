from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.bot import texts
from ilmbot.bot.handlers.menu import send_posts
from ilmbot.bot.keyboards import reply_menu
from ilmbot.config import Settings
from ilmbot.db.models import ButtonKind
from ilmbot.integrations.telegram_content import ContentSender
from ilmbot.services.menu import MenuService
from ilmbot.services.navigation import NavigationState
from ilmbot.services.users import UserService


async def start(
    message: Message,
    session: AsyncSession,
    menu: MenuService,
    nav: NavigationState,
    users: UserService,
    command: CommandObject,
    content: ContentSender,
):
    user = message.from_user
    is_new = await users.touch(session, user.id, user.full_name)
    await nav.set(user.id, None)
    snapshot = await menu.snapshot(session)
    if command.args and command.args.startswith("content_"):
        key = command.args.removeprefix("content_")
        node = snapshot.get(int(key)) if key.isascii() and key.isdigit() and len(key) < 12 else None
        if node is None or node.kind != ButtonKind.POST:
            await message.answer("Kontent topilmadi yoki vaqtincha yashirilgan.")
        else:
            await send_posts(message.bot, content, user.id, node)
        return
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


async def open_app(message: Message, settings: Settings):
    if not settings.mini_app_url:
        await message.answer("Mini App hozircha sozlanmagan. Bot menyusidan foydalanishingiz mumkin.")
        return
    if message.chat.type != "private":
        await message.answer("Ilovani ochish uchun botga shaxsiy xabar yozing.")
        return
    await message.answer(
        "Ilm yo'lida — bilim, namoz vaqtlari va yaqin masjidlar bir joyda.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Ilovani ochish", web_app=WebAppInfo(url=settings.mini_app_url))]
            ]
        ),
    )


def create_router() -> Router:
    router = Router(name="start")
    router.message.register(start, CommandStart())
    router.message.register(help_command, Command("help"))
    router.message.register(my_id, Command("myid"))
    router.message.register(open_app, Command("app"))
    return router
