"""Yaqin masjidlar: lokatsiya so'raladi, eng yaqin ikkita masjid havola va xarita bilan yuboriladi."""

from html import escape
from urllib.parse import quote

from aiogram import F, Router
from aiogram.types import KeyboardButton, LinkPreviewOptions, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.bot import texts
from ilmbot.bot.keyboards import reply_menu
from ilmbot.services.menu import MenuService
from ilmbot.services.mosques import MosqueService, NearbyMosque
from ilmbot.services.navigation import NavigationState

# Eng yaqin masjid shundan uzoq bo'lsa (masalan, chet eldan yuborilgan lokatsiya), foydalanuvchiga buni aytamiz
FAR_AWAY_KM = 30.0


def location_request_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=texts.SEND_LOCATION, request_location=True))
    builder.row(KeyboardButton(text=texts.BACK))
    return builder.as_markup(resize_keyboard=True)


def map_link(mosque: NearbyMosque) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote(f'{mosque.lat},{mosque.lon}')}"


def format_results(mosques: list[NearbyMosque]) -> str:
    blocks = [f"<a href='{map_link(m)}'>{escape(m.name)}</a>\nUzoqlik: {m.km:.1f} km" for m in mosques]
    text = "\n\n".join(blocks)
    if mosques and mosques[0].km > FAR_AWAY_KM:
        text = f"{texts.MOSQUES_FAR}\n\n{text}"
    return text


async def prompt_for_location(message: Message, session: AsyncSession, user_id: int) -> None:
    await message.answer(texts.MOSQUES_PROMPT, reply_markup=location_request_keyboard())


async def on_location(
    message: Message,
    session: AsyncSession,
    menu: MenuService,
    nav: NavigationState,
    mosques: MosqueService,
):
    nearest = await mosques.nearest(session, message.location.latitude, message.location.longitude)
    snapshot = await menu.snapshot(session)
    current = snapshot.get(await nav.get(message.from_user.id))
    keyboard = reply_menu(snapshot.children(current.id if current else None), back=current is not None)
    if not nearest:
        await message.answer(texts.MOSQUES_NONE, reply_markup=keyboard)
        return
    await message.answer(
        format_results(nearest), reply_markup=keyboard, link_preview_options=LinkPreviewOptions(is_disabled=True)
    )
    for mosque in nearest:
        # Venue xaritaning tagida nom va uzoqlikni ko'rsatadi (oddiy lokatsiyaga matn qo'shib bo'lmaydi)
        await message.answer_venue(
            latitude=mosque.lat, longitude=mosque.lon, title=mosque.name[:255], address=f"Uzoqlik: {mosque.km:.1f} km"
        )


def create_router() -> Router:
    router = Router(name="mosques")
    router.message.register(on_location, F.location)
    return router
