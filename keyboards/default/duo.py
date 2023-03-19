from aiogram import types
from handlers.users.keyboards import get_keyboard
from loader import dp

@dp.message_handler(text='Duo va Zikirlar🤲')
async def some_handler_function(message: types.Message):
    category_id = 3
    await get_keyboard(message, category_id)

