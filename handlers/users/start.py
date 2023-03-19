from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
import sqlite3
from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from keyboards.default.mainMenu import get_main_keyboard
from keyboards.inline import  hello
from loader import dp,  db


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    main = await get_main_keyboard()
    with sqlite3.connect('backend/ilmbot/db.sqlite3') as conn:
        c = conn.cursor()
        # foydalanuvchini bazada borligini tekshirish
        c.execute("SELECT * FROM bot_namazuser WHERE user_id = ?", (message.from_user.id,))
        result = c.fetchone()
        await message.answer(f'sizni yana ko\'rganimzdan xursandmiz {message.from_user.full_name}',reply_markup=main)
        if not result:
            # agar foyadlanuvchi bazada bo'lmasa uni bazaga qoshadi va hello keyboardni yuboradi
            c.execute("INSERT INTO bot_namazuser(user_id, user_name, region, subscribe) VALUES(?, ?, ?, ?)",
                      (message.from_user.id, message.from_user.full_name, None, 0))
            conn.commit()

            await message.answer(f"Qadrli foydalanuvchi, diningizga yanada mos musulmon bo’lishingiz ko’magida yaratilgan botga xush kelibsiz. Alloh taolo bilganimizga amal qiladiganlardan qilsin!️", reply_markup=hello.greet_kb2)


@dp.message_handler(text='boshlash')
async def main(message: types.Message):
    with sqlite3.connect('backend/ilmbot/db.sqlite3') as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM category_categorybutton WHERE parent_id IS NULL")
        results = c.fetchall()

        if not results:
            await message.answer("Kechirasiz, hozir bot ish faoliyatida emas.")
            return

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

            await message.answer(f"Assalomu alaykum va rohmatullohi va barokatuhu, {message.from_user.full_name}!",
                                 reply_markup=keyboard)












