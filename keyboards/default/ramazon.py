from aiogram import types

from handlers.users.keyboards import get_keyboard, send_post
from loader import dp


@dp.message_handler(text="Ramazon🌙")
async def send_menu(message: types.Message):
    print(message.text)
    category_id = 426
    await get_keyboard(message, category_id)

@dp.message_handler(text='Ramazon haqida')
async def send_bilol(message: types.Message):
    await send_post(chat_id=message.from_user.id, message_id=1538)

@dp.message_handler(text='Ramazon oyidagi amallar')
async def send_bilol(message: types.Message):
    await send_post(chat_id=message.from_user.id, message_id=1539)

@dp.message_handler(text='Ramazon taqvimi')
async def send_bilol(message: types.Message):
    await send_post(chat_id=message.from_user.id, message_id=1537)