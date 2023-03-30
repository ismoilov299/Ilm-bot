import sqlite3

from aiogram.types import Message
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram import types

from aiogram_broadcaster import MessageBroadcaster
from data.config import ADMINS
from loader import dp, bot, db
from keyboards.default.adminKeyboard import adminMenu


@dp.message_handler(Command("admins"),user_id=ADMINS)
async def show_menu(message: Message):
    await message.answer("Admin menu",reply_markup=adminMenu)

def get_user_count():

    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()


    cursor.execute('SELECT COUNT(user_id) FROM bot_namazuser')
    result = cursor.fetchone()[0]


    cursor.close()
    conn.close()


    return result

@dp.message_handler(text="All users", user_id=ADMINS)
async def handle_message(message: Message):
        count = get_user_count()
        print(count)
        await bot.send_message(message.chat.id, f'userlar soni: {count}')



@dp.message_handler(text="Follow namaz", user_id=ADMINS)
async def count_obuna(message: Message):
    def count():
        conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
        cursor = conn.cursor()

        # obunachilar sonini sanash uchun
        cursor.execute('SELECT * FROM bot_namazuser WHERE subscribe = 1')
        subscribed_users = cursor.fetchall()


        cursor.close()
        conn.close()

        msg = ""
        for i, user in enumerate(subscribed_users):
            msg += f"{i+1}. {user[1]} ({user[2]})\n"
        count_msg = f"\n\nObunachilar soni {len(subscribed_users)}"


        return f"{msg}{count_msg}"


    await bot.send_message(chat_id=message.from_user.id, text=count())

@dp.message_handler(text='Broadcast', user_id=ADMINS)
async def broadcast_command_handler(msg: Message, state: FSMContext):
    await msg.answer('Xammaga jo\'natish uchun(EHTIYOT BO\'LING):')
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




