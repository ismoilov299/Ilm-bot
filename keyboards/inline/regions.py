import sqlite3
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loader import dp

# bu yerda mintaqalar bilan ishlash uchun namuna bu namuna namoz vaqtlari uchun inline keyboar yasaydi
@dp.message_handler(text='Namoz vaqtlari')
async def get_keyboard(message: types.Message):
        with sqlite3.connect('backend/ilmbot/db.sqlite3') as conn:
            c = conn.cursor()

            c.execute("SELECT name, id FROM category_categoryregion")
            results = c.fetchall()

            if not results:
                await message.answer("Kechirasiz, hozir bot ish faoliyatida emas.")
                return

            button_names = [result[0] for result in results]
            button_values = [result[1] for result in results]

            keyboard_namozvaqtlari = InlineKeyboardMarkup(row_width=1)
            for name, value in zip(button_names, button_values):
                keyboard_namozvaqtlari.add(InlineKeyboardButton(text=name, callback_data=value))

            await message.answer("Mintaqani tanlang:", reply_markup=keyboard_namozvaqtlari)

