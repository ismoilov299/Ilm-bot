from aiogram import types
from keyboards.inline import callback
from data.config import chanel
from handlers.users.keyboards import get_keyboard, send_post
from keyboards.inline.create import get_inline_keyboards
from loader import dp, bot


@dp.message_handler(text='Filmlar🎞')
async def send_movie_menu(message: types.Message):
    category_id = 9
    await get_keyboard(message, category_id)

@dp.message_handler(text='Olamga nur sochgan oy')
async def send_movie_oy(message: types.Message):
    category_id = 44
    await get_inline_keyboards(message, category_id, page=1)

@dp.message_handler(text='Bilol ibn Raboh')
async def send_bilol(message: types.Message):
    await send_post(chat_id=message.from_user.id, message_id=1362)
