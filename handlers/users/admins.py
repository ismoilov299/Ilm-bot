import sqlite3

from aiogram.types import Message
from aiogram.dispatcher.filters import Command

from data.config import ADMINS
from loader import dp, bot, db
from keyboards.default.adminKeyboard import adminMenu

# def get_user_count():
#     # Connect to the SQLite database
#     conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
#     cursor = conn.cursor()
#
#     # Execute the query
#     cursor.execute('SELECT COUNT(user_id) FROM bot_namazuser')
#     result = cursor.fetchone()[0]
#
#     # Close the database connection
#     cursor.close()
#     conn.close()
#
#     # Return the result
#     return result
@dp.message_handler(Command("admins"),user_id=ADMINS)
async def show_menu(message: Message):
    await message.answer("Admin menu",reply_markup=adminMenu)

import sqlite3

# Define a function to get the count of user_id in the bot_namazuser table
def get_user_count():
    # Connect to the SQLite database
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()

    # Execute the query
    cursor.execute('SELECT COUNT(user_id) FROM bot_namazuser')
    result = cursor.fetchone()[0]

    # Close the database connection
    cursor.close()
    conn.close()

    # Return the result
    return result

# Define a function to handle the message
@dp.message_handler(text="All users", user_id=ADMINS)
async def handle_message(message: Message):
        count = get_user_count()
        print(count)
        await bot.send_message(message.chat.id, f'userlar soni: {count}')

# async def get_all_users(message: Message):
#     users = f"XAMMA USERSLAR:{db.select_all_users()}"
#
#     await bot.send_message(chat_id=message.from_user.id, text=users)

@dp.message_handler(text="Follow namaz", user_id=ADMINS)
async def count_obuna(message: Message):
    def count():
        # Connect to the SQLite database
        conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
        cursor = conn.cursor()

        # Execute the query to get the list of subscribed users
        cursor.execute('SELECT * FROM bot_namazuser WHERE subscribe = 1')
        subscribed_users = cursor.fetchall()

        # Close the database connection
        cursor.close()
        conn.close()

        # Build the message with the list of subscribed users and the count of subscribed users
        msg = ""
        for i, user in enumerate(subscribed_users):
            msg += f"{i+1}. {user[1]} ({user[2]})\n"
        count_msg = f"\n\nObunachilar soni {len(subscribed_users)}"

        # Return the message
        return f"{msg}{count_msg}"

    # Send the message to the user
    await bot.send_message(chat_id=message.from_user.id, text=count())


from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram import types

from aiogram_broadcaster import MessageBroadcaster

@dp.message_handler(text='Broadcast', user_id=ADMINS)
async def broadcast_command_handler(msg: Message, state: FSMContext):
    await msg.answer('Xammaga jonatish uchun(EHTIYOT BO\'LING):')
    await state.set_state('broadcast_text')

@dp.message_handler(state='broadcast_text', content_types=types.ContentTypes.ANY)
async def start_broadcast(msg: Message, state: FSMContext):
    await state.finish()
    users = db.select_all_users2()
    for user in users:
        try:
            await MessageBroadcaster(user[0], msg).run()
        except:
            pass




