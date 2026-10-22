"""Menyu: matn orqali reply klaviatura bo'limlari va inline ro'yxatlar."""

from collections.abc import Awaitable, Callable
from html import escape

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.bot import texts
from ilmbot.bot.callbacks import NodeCb
from ilmbot.bot.keyboards import MAX_REPLY_BUTTONS, inline_list, reply_menu
from ilmbot.bot.messaging import answer_text, edit_text
from ilmbot.db.models import ButtonKind
from ilmbot.integrations.telegram_content import ContentSender
from ilmbot.services.menu import MenuService, MenuSnapshot, Node, normalize
from ilmbot.services.navigation import NavigationState
from ilmbot.services.users import UserService


def _title(node: Node) -> str:
    """Bo'lim sarlavhasi: admin yozgan matn (HTML ruxsat etiladi) yoki tugma nomi."""
    return node.text or escape(node.name)


async def send_menu(message: Message, snapshot: MenuSnapshot, nav: NavigationState, user_id: int, node: Node | None):
    """Reply klaviatura bilan bo'lim (yoki `node=None` bo'lsa bosh menyu) ko'rsatadi va joriy o'rinni eslab qoladi."""
    children = snapshot.roots if node is None else snapshot.children(node.id)
    if not children:
        await message.answer(texts.NO_SECTIONS if node is None else texts.SECTION_EMPTY)
        return
    await nav.set(user_id, None if node is None else node.id)
    title = texts.CHOOSE_SECTION if node is None else _title(node)
    await answer_text(message, title, reply_markup=reply_menu(children, back=node is not None))


async def send_list(message: Message, snapshot: MenuSnapshot, node: Node, *, page: int = 1, back_to: int | None = None):
    children = snapshot.children(node.id)
    if not children:
        await message.answer(texts.SECTION_EMPTY)
        return
    await answer_text(message, _title(node), reply_markup=inline_list(node, children, page=page, back_to=back_to))


async def send_posts(bot: Bot, content: ContentSender, chat_id: int, node: Node) -> None:
    if not node.message_ids:
        await bot.send_message(chat_id, texts.SECTION_EMPTY)
        return
    if await content.send_posts(bot, chat_id, node.message_ids) == 0:
        await bot.send_message(chat_id, texts.CONTENT_UNAVAILABLE)


def _back_target(snapshot: MenuSnapshot, node: Node) -> int | None:
    """Ro'yxat ichidagi bola uchun: ota ham ro'yxat bo'lsagina inline 'Orqaga' tugmasi qo'yiladi."""
    parent = snapshot.get(node.parent_id)
    return parent.id if parent is not None and parent.kind == ButtonKind.LIST else None


# `action` turidagi tugunlar uchun: amal nomi -> (xabar, sessiya, foydalanuvchi ID) qabul qiluvchi funksiya
Actions = dict[str, Callable[[Message, AsyncSession, int], Awaitable[None]]]


async def run_action(message: Message, node: Node, session: AsyncSession, actions: Actions, user_id: int) -> None:
    handler = actions.get(node.action or "")
    if handler is None:
        await message.answer(texts.COMING_SOON)  # amal hali amalga oshirilmagan
        return
    await handler(message, session, user_id)


async def open_node(
    message: Message,
    snapshot: MenuSnapshot,
    node: Node,
    *,
    bot: Bot,
    nav: NavigationState,
    content: ContentSender,
    session: AsyncSession,
    actions: Actions,
    user_id: int,
) -> None:
    """Reply klaviatura (matn) orqali tanlangan tugunni ochadi."""
    if node.kind == ButtonKind.MENU:
        if len(snapshot.children(node.id)) > MAX_REPLY_BUTTONS:
            await send_list(message, snapshot, node)
        else:
            await send_menu(message, snapshot, nav, user_id, node)
    elif node.kind == ButtonKind.LIST:
        await send_list(message, snapshot, node)
    elif node.kind == ButtonKind.POST:
        await send_posts(bot, content, user_id, node)
    else:
        await run_action(message, node, session, actions, user_id)


async def go_back(message: Message, snapshot: MenuSnapshot, nav: NavigationState, user_id: int, current: Node | None):
    """Eng yaqin `menu` turidagi ajdodga (yoki bosh menyuga) qaytadi."""
    target = snapshot.get(current.parent_id) if current is not None else None
    while target is not None and target.kind != ButtonKind.MENU:
        target = snapshot.get(target.parent_id)
    await send_menu(message, snapshot, nav, user_id, target)


async def on_text(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    menu: MenuService,
    nav: NavigationState,
    users: UserService,
    content: ContentSender,
    actions: Actions,
):
    user = message.from_user
    await users.touch(session, user.id, user.full_name)
    snapshot = await menu.snapshot(session)
    current = snapshot.get(await nav.get(user.id))  # menyu o'zgargan bo'lsa None (bosh menyu)

    if normalize(message.text) == normalize(texts.BACK):
        await go_back(message, snapshot, nav, user.id, current)
        return

    parent_id = current.id if current is not None else None
    node = snapshot.child_by_name(parent_id, message.text)
    if node is None and current is not None:
        node = snapshot.child_by_name(None, message.text)  # bosh menyudagi bo'limga istalgan joydan o'tish mumkin
    if node is None:
        children = snapshot.children(parent_id)
        await message.answer(texts.NOT_UNDERSTOOD, reply_markup=reply_menu(children, back=current is not None))
        return
    await open_node(
        message, snapshot, node, bot=bot, nav=nav, content=content, session=session, actions=actions, user_id=user.id
    )


async def on_node_callback(
    callback: CallbackQuery,
    callback_data: NodeCb,
    session: AsyncSession,
    bot: Bot,
    menu: MenuService,
    nav: NavigationState,
    content: ContentSender,
    actions: Actions,
):
    if callback_data.act == "x":
        await callback.answer()
        return
    snapshot = await menu.snapshot(session)
    node = snapshot.get(callback_data.id)
    message = callback.message
    if node is None or not isinstance(message, Message):
        await callback.answer(texts.STALE_BUTTON, show_alert=True)
        return
    await callback.answer()

    if callback_data.act == "p":  # ro'yxat sahifasi (yoki ota ro'yxatga qaytish)
        children = snapshot.children(node.id)
        if not children:
            await message.answer(texts.SECTION_EMPTY)
            return
        markup = inline_list(node, children, page=callback_data.page, back_to=_back_target(snapshot, node))
        await edit_text(message, _title(node), markup)
        return

    user_id = callback.from_user.id  # act == "o": ro'yxatdagi elementni ochish
    if node.kind == ButtonKind.LIST:
        children = snapshot.children(node.id)
        if not children:
            await message.answer(texts.SECTION_EMPTY)
            return
        await edit_text(message, _title(node), inline_list(node, children, back_to=_back_target(snapshot, node)))
    elif node.kind == ButtonKind.POST:
        await send_posts(bot, content, user_id, node)
    elif node.kind == ButtonKind.MENU:
        await send_menu(message, snapshot, nav, user_id, node)
    else:
        await run_action(message, node, session, actions, user_id)


async def on_unknown_callback(callback: CallbackQuery):
    """Eski yoki tanilmagan tugmalar uchun (hech qachon 'aylanib' qolmasin)."""
    await callback.answer(texts.STALE_BUTTON, show_alert=True)


def create_router() -> Router:
    router = Router(name="menu")
    router.message.register(on_text, F.text)
    router.callback_query.register(on_node_callback, NodeCb.filter())
    router.callback_query.register(on_unknown_callback)
    return router
