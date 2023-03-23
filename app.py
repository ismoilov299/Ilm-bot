import asyncio
import datetime
import sqlite3
from handlers.users import keyboards
from aiogram import executor
import aioschedule
from keyboards.inline.regions import get_prayer_times, send_prayer_time_message, get_subscribed_users, get_regions
from loader import dp, db
import middlewares, filters, handlers
from prayer_time.vaqt import api_namaz
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands
print(get_subscribed_users())
async def scheduler():
    aioschedule.every().day.at('20:01').do(api_namaz)
    while True:
        now = datetime.datetime.now().strftime('%H:%M')
        for user in get_subscribed_users():
            print(user[0])
            times = get_prayer_times(user[1])
            print(times[0])

            for i, time in enumerate(times):
                prayer_name = None
                if time == now:
                    if i == 0:
                        prayer_name = 'bomdod'
                    elif i == 1:
                        prayer_name = 'quyosh'
                    elif i == 2 :
                        prayer_name ='peshin'
                    elif i == 3 :
                        prayer_name ='asr'
                    elif i == 4 :
                        prayer_name ='shom'
                    elif i == 5 :
                        prayer_name ='Xufton'

                    # add more conditions for other prayer times if needed

                    if prayer_name:
                        await send_prayer_time_message(user[0], prayer_name)

        await asyncio.sleep(60)

# update_prayer_times()
# update_prayer_times()
async def on_startup(dispatcher):
    asyncio.create_task(scheduler())
    # Birlamchi komandalar (/star va /help)
    await set_default_commands(dispatcher)

    # Bot ishga tushgani haqida adminga xabar berish
    await on_startup_notify(dispatcher)


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
