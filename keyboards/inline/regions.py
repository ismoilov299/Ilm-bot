import sqlite3

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# bu yerda mintaqalar bilan ishlash uchun namuna bu namuna namoz vaqtlari uchun inline keyboar yasaydi

import sqlite3

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from loader import dp, bot


async def get_regions_keyboard():
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()

    cursor.execute("SELECT name, id FROM category_categoryregion")
    results = cursor.fetchall()

    if not results:
        print(results)
        return None

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(*[InlineKeyboardButton(text=result[0], callback_data=f"region:{result[0]}:{result[1]}") for result in results])

    cursor.close()
    conn.close()

    return keyboard



@dp.callback_query_handler(lambda c: c.data and c.data.startswith('region:'))
async def prayer_times_callback_handler(callback_query: types.CallbackQuery):
    # Get the region ID and name from the callback data
    region_data = callback_query.data.split(":")[1:]
    region_name = region_data[0]
    region_id = int(region_data[1])

    user_id = callback_query.from_user.id

    # Check if the user is already subscribed to prayer times for this region
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()
    cursor.execute(f"SELECT subscribe FROM bot_namazuser WHERE user_id={user_id} AND region={region_id}")
    subscription = cursor.fetchone()
    cursor.close()
    conn.close()

    # Retrieve today's prayer times from the database for the selected region
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT bomdod, quyosh, peshin, asr, shom, xufton FROM category_categoryregion WHERE id={region_id}")
    prayer_times = cursor.fetchone()
    cursor.close()
    conn.close()

    # Create a message with the selected prayer times
    message = f"Bugungi namoz vaqtlari {region_name}:\n\n" \
              f"🌌Bomdod: {prayer_times[0]}\n" \
              f"🌄Quyosh: {prayer_times[1]}\n" \
              f"🌇Peshin: {prayer_times[2]}\n" \
              f"🌆Asr: {prayer_times[3]}\n" \
              f"🏙Shom: {prayer_times[4]}\n" \
              f"🌃Xufton: {prayer_times[5]}\n"\
                "Namoz vaqlari islom.uz saytidan olindi"

    inline_keyboard = InlineKeyboardMarkup()
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()
    cursor.execute(f"SELECT subscribe FROM bot_namazuser WHERE user_id={user_id}")
    subscription = cursor.fetchone()

    if subscription is None:
        # If the user is not subscribed to prayer times for any region, add a "Subscribe" button to the inline keyboard
        inline_keyboard.add(InlineKeyboardButton(text="kunlik eslatmani yoqish", callback_data=f"subscribe:0"))
    elif subscription[0] == 0:
        # If the user is subscribed to prayer times but has unsubscribed from all regions, add a "Subscribe" button to the inline keyboard
        inline_keyboard.add(InlineKeyboardButton(text="kunlik eslatmani yoqish", callback_data=f"subscribe:0"))
    else:
        # If the user is subscribed to prayer times for at least one region, add an "Unsubscribe" button to the inline keyboard
        inline_keyboard.add(InlineKeyboardButton(text="kunlik eslatamani o'chirish", callback_data=f"unsubscribe:0"))

    # Send the message with inline keyboard as a reply to the original message
    await callback_query.message.reply(message, reply_markup=inline_keyboard)

    # Handle the user's button click
    if callback_query.data.startswith('subscribe:') or callback_query.data.startswith('unsubscribe:'):
        subscribe_value = 1 if callback_query.data.startswith('subscribe:') else 0
        # cursor.execute(f"UPDATE bot_namazuser SET subscribe={subscribe_value} WHERE user_id={user_id}")
        cursor.execute(f"UPDATE bot_namazuser SET region={region_id} WHERE user_id={user_id}")
        conn.commit()
        confirmation_message = f"Siz {message} kunlik eslatmani {'yoqdingiz' if subscribe_value == 1 else 'ochirdingiz'}."
        await callback_query.message.reply(confirmation_message)

    cursor.close()
    conn.close()

@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('subscribe:') or c.data.startswith('unsubscribe:')))
async def handle_subscription_callback(callback_query: CallbackQuery):
    # Get the user's ID
    user_id = callback_query.from_user.id

    # Get the region ID from the callback data (always 0 in this case)
    region_id = int(callback_query.data.split(':')[1])

    # Get the message text from the original message
    message = callback_query.message.text

    # Update the subscription status of the user in the database
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()
    subscribe_value = 1 if callback_query.data.startswith('subscribe:') else 0
    cursor.execute(f"UPDATE bot_namazuser SET subscribe={subscribe_value} WHERE user_id={user_id}")
    conn.commit()

    # Send a confirmation message to the user
    confirmation_message = "Siz  kunlik eslatmani " + (
        'yoqdingiz.' if subscribe_value == 1 else "o'chirdingiz.")

    await callback_query.message.reply(confirmation_message)

    cursor.close()
    conn.close()

    # Update the inline keyboard
    inline_keyboard = InlineKeyboardMarkup()
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    cursor = conn.cursor()
    cursor.execute(f"SELECT subscribe FROM bot_namazuser WHERE user_id={user_id}")
    subscription = cursor.fetchone()

    if subscription is None:
        # If the user is not subscribed to prayer times for any region, add a "Subscribe" button to the inline keyboard
        inline_keyboard.add(InlineKeyboardButton(text="kunlik eslatmani yoqish", callback_data=f"subscribe:{region_id}"))
    elif subscription[0] == 0:
        # If the user is subscribed to prayer times but has unsubscribed from all regions, add a "Subscribe" button to the inline keyboard
        inline_keyboard.add(InlineKeyboardButton(text="kunlik eslatmani yoqish", callback_data=f"subscribe:{region_id}"))
    else:
        # If the user is subscribed to prayer times for at least one region, add an "Unsubscribe" button to the inline keyboard
        inline_keyboard.add(InlineKeyboardButton(text="kunlik eslatamani o'chirish", callback_data=f"unsubscribe:{region_id}"))

    cursor.close()
    conn.close()

    # Edit the message to update the inline keyboard
    await callback_query.message.edit_reply_markup(inline_keyboard)


def get_prayer_times(region_id):
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    c = conn.cursor()
    print((f"SELECT bomdod, quyosh, peshin, asr, shom,xufton FROM category_categoryregion WHERE id={region_id}"))
    c.execute(f"SELECT bomdod, quyosh, peshin, asr, shom,xufton FROM category_categoryregion WHERE id={region_id}")
    results = c.fetchone()
    print(f"get_prayer_times: region_id={region_id}, results={results}")
    return results


def get_subscribed_users():
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    c = conn.cursor()
    c.execute("SELECT user_id, region FROM bot_namazuser WHERE subscribe=1")
    subscribers = c.fetchall()
    conn.close()
    return subscribers
def get_regions():
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')
    c = conn.cursor()
    c.execute("SELECT name FROM category_categoryregion")
    regions = c.fetchall()
    conn.close()
    return regions


async def send_prayer_time_message(userID, prayer_time):
    message = None
    if prayer_time == 'bomdod':
        message = '🌌Bomdod vaqti bo\'ldi!'
    elif prayer_time == 'quyosh':
        message = '🌄Quyosh chiqdi!'
    elif prayer_time == 'peshin':
        message = '🌇Peshin vaqti bo\'ldi!'
    elif prayer_time == 'asr':
        message = '🌆Asr vaqti bo\'ldi!'
    elif prayer_time == 'shom':
        message = '🏙Shom vaqti bo\'ldi!'
    elif prayer_time == 'Xufton':
        message = '🌃Xufton vaqti bo\'ldi!'

    if message:
        try:
            await bot.send_message(chat_id=userID, text=message)
        except Exception as ex:
            print(ex)

