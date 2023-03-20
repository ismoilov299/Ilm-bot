from aiogram import types
from handlers.users.keyboards import get_keyboard
from keyboards.inline.create import get_inline_keyboards
from loader import dp

@dp.message_handler(text='Duo va Salovatlar🤲')
async def some_handler_function(message: types.Message):
    category_id = 3
    await get_keyboard(message, category_id)

@dp.message_handler(text='Duo')
async def duo(message: types.Message):
    category_id = 15
    await get_inline_keyboards(message, category_id, page=1)

@dp.message_handler(text='Salovat')
async def duo(message: types.Message):
    category_id = 17
    await get_inline_keyboards(message, category_id, page=1)