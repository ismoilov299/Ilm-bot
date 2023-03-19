import sqlite3

from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from data.config import chanel
from loader import bot


async def send_post(chat_id: int, message_id: int):
    await bot.copy_message(chat_id=chat_id, from_chat_id=chanel, message_id=message_id)


async def get_keyboard(message: types.Message, id: int):
    with sqlite3.connect('backend/ilmbot/db.sqlite3') as conn:
        c = conn.cursor()

        c.execute("SELECT text FROM category_categorybutton WHERE id = ?", (id,))
        result = c.fetchone()

        if not result:
            await message.answer("Kechirasiz, hozir bu bo'lim tamirlanmoqda")
            return

        category_text = result[0]

        c.execute("SELECT name, id FROM category_categorybutton WHERE parent_id = ?", (id,))
        results = c.fetchall()

        if not results:
            await message.answer("Kechirasiz, hozir bu bo'lim tamirlanmoqda")
            return

        button_names = [result[0] for result in results]

        keyboard_namaz = ReplyKeyboardMarkup(resize_keyboard=True)
        row = []
        for i, name in enumerate(button_names):
            row.append(KeyboardButton(name))
            if i % 2 == 1:
                keyboard_namaz.row(*row)
                row = []
        if row:
            keyboard_namaz.row(*row)
        keyboard_namaz.row(KeyboardButton('Orqaga'))


        await message.answer(category_text, reply_markup=keyboard_namaz)





