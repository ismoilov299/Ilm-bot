import sqlite3

from aiogram import types


from data.config import chanel
from keyboards.inline.create import get_inline_keyboards
from loader import dp, bot

@dp.callback_query_handler(lambda callback_query: True)
async def process_callback(callback_query: types.CallbackQuery):
    callback_data = callback_query.data

    if callback_data.isdigit():
        # category_id bilan post id ni olamiz
        category_id = int(callback_data)
        chat_id = callback_query.from_user.id

        with sqlite3.connect('backend/ilmbot/db.sqlite3') as conn:
            c = conn.cursor()

            c.execute("SELECT idishka FROM bot_post WHERE category_id = ?", (category_id,))
            result = c.fetchone()

            if not result:
                await bot.answer_callback_query(callback_query.id, "Kechirasiz, bunday yozuvlar mavjud emas")
                return

            post_id = result[0]
            await bot.copy_message(chat_id=chat_id, from_chat_id=chanel, message_id=post_id)

    else:
        # page larni keyngi va orqa page larga o'tishi
        if callback_data.startswith("next_"):
            id, page = callback_data.split("_")[1:]
            page = int(page) + 1
            await get_inline_keyboards(callback_query.message, int(id), page)
        elif callback_data.startswith("prev_"):
            id, page = callback_data.split("_")[1:]
            page = int(page) - 1
            await get_inline_keyboards(callback_query.message, int(id), page)
        else:
            pass


