from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

import sqlite3

from aiogram.utils.exceptions import MessageCantBeDeleted, MessageNotModified

from loader import bot




async def get_inline_keyboards(message: types.Message, id: int, page: int):
    with sqlite3.connect('backend/ilmbot/db.sqlite3') as conn:
        c = conn.cursor()

        # Id ga qarab category matni olamiz
        c.execute("SELECT text FROM category_categorybutton WHERE id = ?", (id,))
        result = c.fetchone()

        if not result:
            await message.answer("Kechirasiz, hozir bu bo'lim tamirlanmoqda")
            return

        category_text = result[0]

        # parent_id ga qarab tegshli buttonlarni id va nomini olamiz
        limit = 5
        offset = (page - 1) * limit

        c.execute("SELECT name, id FROM category_categorybutton WHERE parent_id = ? LIMIT ? OFFSET ?", (id, limit, offset))
        results = c.fetchall()

        if not results:
            await message.answer("Kechirasiz, hozir bu bo'lim tamirlanmoqda")
            return


        keyboard_namaz = InlineKeyboardMarkup(row_width=2)

        for name, sub_id in results:
            button = InlineKeyboardButton(text=name, callback_data=str(sub_id))
            keyboard_namaz.add(button)

        # buttonlarni paglarga bo'lamiz
        c.execute("SELECT COUNT(*) FROM category_categorybutton WHERE parent_id = ?", (id,))
        count = c.fetchone()[0]
        max_page = (count // limit) + (1 if count % limit != 0 else 0)

        if page > 1:
            prev_button = InlineKeyboardButton(text="<<", callback_data=f"prev_{id}_{page}")
            keyboard_namaz.row(prev_button)
        if page < max_page:
            next_button = InlineKeyboardButton(text=">>", callback_data=f"next_{id}_{page}")
            keyboard_namaz.row(next_button)

        # keyboardi yuborish
        if page == 1:
            await message.answer(category_text, reply_markup=keyboard_namaz)
        else:
            try:
                await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=category_text, reply_markup=keyboard_namaz)
            except MessageNotModified:
                pass



# async def get_inline_keyboards(message: types.Message, id: int, page: int):
#     with sqlite3.connect('backend/ilmbot/db.sqlite3') as conn:
#         c = conn.cursor()
#
#         # Retrieve the text of the category based on the id
#         c.execute("SELECT text FROM category_categorybutton WHERE id = ?", (id,))
#         result = c.fetchone()
#
#         if not result:
#             await message.answer("Kechirasiz, hozir bu bo'lim tamirlanmoqda")
#             return
#
#         category_text = result[0]
#
#         # Retrieve the names and ids of the inline keyboards based on the parent_id
#         limit = 5
#         offset = (page - 1) * limit
#         c.execute("SELECT name, id FROM category_categorybutton WHERE parent_id = ? LIMIT ? OFFSET ?", (id, limit, offset))
#         results = c.fetchall()
#
#         if not results:
#             await message.answer("Kechirasiz, hozir bu bo'lim tamirlanmoqda")
#             return
#
#         keyboard_namaz = InlineKeyboardMarkup(row_width=2)
#         keyboard_list = []
#         for name, sub_id in results:
#             keyboard_list.append({'name': name, 'id': str(sub_id)})
#
#         # Create inline keyboard buttons based on the retrieved names and ids
#         for keyboard in keyboard_list:
#             button = InlineKeyboardButton(text=keyboard['name'], callback_data=keyboard['id'])
#             keyboard_namaz.add(button)
#
#         # Add pagination buttons to the keyboard
#         if page > 1:
#             prev_button = InlineKeyboardButton(text="<<", callback_data=f"prev_{id}_{page}")
#             keyboard_namaz.row(prev_button)
#         if len(results) == limit:
#             next_button = InlineKeyboardButton(text=">>", callback_data=f"next_{id}_{page}")
#             keyboard_namaz.row(next_button)
#
#         # Send the message with the subcategories keyboard
#         if page == 1:
#             await message.answer(category_text, reply_markup=keyboard_namaz)
#         else:
#             try:
#                 await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=category_text, reply_markup=keyboard_namaz)
#             except MessageNotModified:
#                 pass

