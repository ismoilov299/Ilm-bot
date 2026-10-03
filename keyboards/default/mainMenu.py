import sqlite3
from aiogram.dispatcher import FSMContext
from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton  # KeyboardButton("Namoz🕋"),

from loader import dp

# KeyboardButton("Duo va Zikirlar🤲"),
# KeyboardButton("Qur\'on📖"),
# KeyboardButton("Sahobalar👳🏻‍♂"),
# KeyboardButton("Kitoblar📚"),
# KeyboardButton("Asmaul Husna"),
# KeyboardButton("Yaqin Masjid🕌"),
# KeyboardButton("Filmlar🎞"),
# KeyboardButton("Darsliklar📕"),


async def get_main_keyboard() -> ReplyKeyboardMarkup:
    with sqlite3.connect("backend/ilmbot/db.sqlite3") as conn:
        c = conn.cursor()

        c.execute("SELECT name FROM category_categorybutton WHERE parent_id IS NULL")
        results = c.fetchall()

        if not results:
            raise ValueError("mabjud emas")

        button_names = [result[0] for result in results]

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        row = []
        for i, name in enumerate(button_names):
            row.append(KeyboardButton(name))
            if i % 2 == 1:
                keyboard.row(*row)
                row = []
        if row:
            keyboard.row(*row)

        return keyboard


@dp.message_handler(text="Orqaga")
async def back(message: types.Message):
    main = await get_main_keyboard()
    await message.answer("Kerakli bo'limni tanlang:", reply_markup=main)
