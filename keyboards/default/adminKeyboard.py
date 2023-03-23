from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

adminMenu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='All users'),
            KeyboardButton(text='Follow namaz')
        ],
        [
            KeyboardButton(text="Broadcast")
        ]
    ],
    resize_keyboard=True)