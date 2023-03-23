from aiogram import types

from handlers.users.keyboards import get_keyboard
from loader import dp


@dp.message_handler(text="Ramazon")
async def send_menu(message: types.Message):
    print(message.text)
    category_id = 426
    await get_keyboard(message, category_id)