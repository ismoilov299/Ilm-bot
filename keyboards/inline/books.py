
import sqlite3

from aiogram import types
from keyboards.inline import callback
from handlers.users.keyboards import get_keyboard
from keyboards.inline.create import get_inline_keyboards
from loader import dp, bot
from data.config import chanel

# bu funksiyalar namuna uchun qo'yildi

@dp.message_handler(text='Kitoblar📚')
async def book_send(message: types.Message):
    category_id = 6
    await get_inline_keyboards(message, category_id, page=1)

@dp.message_handler(text='Asmaul Husna')
async def book_send(message: types.Message):
    category_id = 7
    await get_inline_keyboards(message, category_id, page=1)

@dp.message_handler(text='Sahobalar👳🏻‍♂')
async def book_send(message: types.Message):
    category_id = 5
    await get_inline_keyboards(message, category_id, page=1)
