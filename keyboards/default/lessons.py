from aiogram import types

from handlers.users.keyboards import get_keyboard
from keyboards.inline.create import get_inline_keyboards
from loader import dp


@dp.message_handler(text='Darsliklar📕')
async def send_menu(message: types.Message):
    category_id =10
    await get_keyboard(message, category_id)

@dp.message_handler(text="Qur'on tartili")
async def send_zam_suralar(message: types.Message):
    category_id = 80
    await get_inline_keyboards(message, category_id, page=1)