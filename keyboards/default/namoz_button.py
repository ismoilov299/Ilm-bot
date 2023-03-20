from aiogram import types

from handlers.users.keyboards import get_keyboard, send_post
from keyboards.inline.create import get_inline_keyboards
from keyboards.inline.regions import get_regions_keyboard
from loader import dp, bot

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

@dp.message_handler(text='Namoz vaqtlari')
async def send_regions_keyboard(message: types.Message):
    keyboard = await get_regions_keyboard()
    await bot.send_message(message.chat.id, "Mintaqani tanlang:", reply_markup=keyboard)

@dp.message_handler(text=["G'usul", "Tahorat"])
async def send_tahorat(message: types.Message):
    message_id = 655 if message.text == "G'usul" else 564
    print(message_id)
    await send_post(chat_id=message.from_user.id, message_id=message_id)

@dp.message_handler(text=["Namoz qoidalari", "Farz namozlar"])
async def send_tahorat(message: types.Message):
    category_id = 19 if message.text == "Namoz qoidalari" else 20
    print(category_id)
    await get_inline_keyboards(message, category_id, page=1)



