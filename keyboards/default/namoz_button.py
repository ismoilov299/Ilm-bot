import sqlite3

from aiogram import types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from handlers.users.keyboards import get_keyboard, send_post
from keyboards.inline.create import get_inline_keyboards
from keyboards.inline.regions import get_regions_keyboard
from loader import dp, bot

@dp.message_handler(text='Namoz vaqtlari')
async def send_regions_keyboard(message: types.Message):
    keyboard_namaz = await get_regions_keyboard()
    await bot.send_message(message.chat.id, "Mintaqani tanlang:", reply_markup=keyboard_namaz)


@dp.message_handler(text='Zam suralar')
async def send_zam_suralar(message: types.Message):
    category_id = 18
    await get_inline_keyboards(message, category_id, page=1)

@dp.message_handler(text=['Namoz🕋', "G'usul va Tahorat", "Namozni o'rganish"])
async def send_menu(message: types.Message):
    print(message.text)
    category_id = 1 if message.text == 'Namoz🕋' else (2 if message.text == "Namozni o'rganish" else 12)
    await get_keyboard(message, category_id)

@dp.message_handler(text=['Vojib namozlar', "Sunnat namozlar", "Nafl namozlar"])
async def send_menu(message: types.Message):
    category_id = 21 if message.text == 'Vojib namozlar' else (23 if message.text == "Nafl namozlar" else 22)
    await get_inline_keyboards(message, category_id, page=1)

@dp.message_handler(text=["Qur'onga o'tish"])
async def send_menu(message: types.Message):
    category_id = 307
    await get_inline_keyboards(message, category_id, page=1)

@dp.message_handler(text="Qur'on📖")
async def send_menu(message: types.Message):
    print(message.text)
    category_id = 4
    await get_keyboard(message, category_id)
@dp.message_handler(text='Namoz vaqtlari')


@dp.message_handler(text=["G'usul", "Tahorat"])
async def send_tahorat(message: types.Message):
    message_id = 655 if message.text == "G'usul" else 564
    print(message_id)
    await send_post(chat_id=message.from_user.id, message_id=message_id)

@dp.message_handler(text=["Hifz uchun tavsiyalar"])
async def send_tahorat(message: types.Message):
    message_id = 1532
    await send_post(chat_id=message.from_user.id, message_id=message_id)

@dp.message_handler(text=["Namoz qoidalari", "Farz namozlar"])
async def send_tahorat(message: types.Message):
    category_id = 19 if message.text == "Namoz qoidalari" else 20
    await get_inline_keyboards(message, category_id, page=1)

async def region_callback_handler(query: CallbackQuery, callback_data: str):
    # Get the region ID from the callback data
    region_id = int(callback_data)

    # Send the "today" and "note" keyboards
    today_keyboard = InlineKeyboardMarkup()
    today_keyboard.add(InlineKeyboardButton(text="Morning", callback_data=f"bomdod:{region_id}"),
                       InlineKeyboardButton(text="Sun", callback_data=f"quyosh:{region_id}"),
                       InlineKeyboardButton(text="Noon", callback_data=f"peshin:{region_id}"))
    today_keyboard.add(InlineKeyboardButton(text="Century", callback_data=f"asr:{region_id}"),
                       InlineKeyboardButton(text="Evening", callback_data=f"shom:{region_id}"),
                       InlineKeyboardButton(text="Night", callback_data=f"xufton:{region_id}"))

    note_keyboard = InlineKeyboardMarkup()
    note_keyboard.add(InlineKeyboardButton(text="Add Note", callback_data=f"add_note:{region_id}"))

    # Send the "today" and "note" keyboards as a reply to the original message
    await query.message.reply("Please select an option from the Today menu:", reply_markup=today_keyboard)
    await query.message.reply("You can add a note here:", reply_markup=note_keyboard)


async def today_callback_handler(query: CallbackQuery, callback_data: str):
    # Get the selected option and region ID from the callback data
    option, region_id = callback_data.split(":")
    region_id = int(region_id)

    # Query the database to get the corresponding information for the selected region and option
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()

    cursor.execute(f"SELECT {option} FROM category_categoryregion WHERE id=?", (region_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    # Send the information as a message
    await query.message.reply(f"{option.capitalize()}: {result[0]}")

