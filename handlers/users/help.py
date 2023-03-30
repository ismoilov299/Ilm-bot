from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandHelp
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from loader import dp


@dp.message_handler(CommandHelp(),state=None)
async def bot_help(message: types.Message):
    text = "Bot bo'yicha savol va takliflaringiz bo'lsa ushbu so'rovnomani to'ldiring!\nAdminlar bilan bog'lanish uchun:@ismoilov299  @davlatovv_z"
    # await message.answer((text))
    await message.answer(text,
reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton(text='taklif kiritish',
web_app=WebAppInfo(url="https://docs.google.com/forms/d/e/1FAIpQLSc7Zv_pE7vfNlJmHH7nanDUbct9uI5Hzy2A8fs-Gk9U5se7SA/viewform?usp=sf_link"))))
