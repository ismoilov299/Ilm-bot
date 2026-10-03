from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from loader import dp

# masjidlar uchun keyboard yaratish va location qabul qilish
location_button = KeyboardButton(text="Manzilingizni yuboring📍", request_location=True)
menu_button = KeyboardButton(text="Orqaga")

Keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(location_button).add(menu_button)


@dp.message_handler(text="Yaqin Masjid🕌")
async def send_link(message: Message):
    await message.answer("Sizga eng yaqin masjidlar :\nHozircha faqat Toshkent shahari uchun", reply_markup=Keyboard)
