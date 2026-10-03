"""aiogram 2 handlerlar jadvali uchun xarakterlovchi test.

aiogram 2 da handler modul import qilinganda ro'yxatdan o'tadi. "Ishlatilmagan" importni o'chirish
yoki faylni ko'chirish handlerni jim yo'qotishi mumkin. Bu test ``app`` import qilinganda hosil
bo'ladigan jadvalni qotiradi. Bosqich 3 da esa u bot javob beradigan barcha xabarlarning to'liq
ro'yxati sifatida xizmat qiladi (docs/MIGRATION_2026.md).

Handlerlar tartibi modullar qaysi tartibda import qilinganiga bog'liq: boshqa test ``keyboards`` ni
oldinroq import qilsa, tartib o'zgaradi. Shuning uchun jadval alohida jarayonda, ``python app.py``
dagi kabi ``app`` birinchi import qilinib o'qiladi.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_MESSAGE_HANDLERS = [
    ("handlers.users.help", "bot_help", ("/help",)),
    ("keyboards.default.mainMenu", "back", ("text=Orqaga",)),
    ("keyboards.inline.loacation", "send_link", ("text=Yaqin Masjid🕌",)),
    ("keyboards.inline.books", "book_send", ("text=Kitoblar📚",)),
    ("keyboards.inline.books", "book_send", ("text=Asmaul Husna",)),
    ("keyboards.inline.books", "book_send", ("text=Sahobalar👳🏻‍♂",)),
    ("keyboards.default.namoz_button", "send_regions_keyboard", ("text=Namoz vaqtlari",)),
    ("keyboards.default.namoz_button", "send_zam_suralar", ("text=Zam suralar",)),
    ("keyboards.default.namoz_button", "send_menu", ("text=Namoz🕋 | G'usul va Tahorat | Namozni o'rganish",)),
    ("keyboards.default.namoz_button", "send_menu", ("text=Vojib namozlar | Sunnat namozlar | Nafl namozlar",)),
    ("keyboards.default.namoz_button", "send_menu", ("text=Qur'onga o'tish",)),
    ("keyboards.default.namoz_button", "send_menu", ("text=Qur'on📖",)),
    ("keyboards.default.namoz_button", "send_tahorat", ("text=G'usul | Tahorat",)),
    # Ortiqcha dekorator "Namoz vaqtlari" ni send_tahorat ga ham ulagan. send_regions_keyboard
    # oldinroq ro'yxatdan o'tgani uchun u ishlaydi, bu handler esa hech qachon chaqirilmaydi.
    ("keyboards.default.namoz_button", "send_tahorat", ("text=Namoz vaqtlari",)),
    ("keyboards.default.namoz_button", "send_tahorat", ("text=Hifz uchun tavsiyalar",)),
    ("keyboards.default.namoz_button", "send_tahorat", ("text=Namoz qoidalari | Farz namozlar",)),
    ("keyboards.default.duo", "some_handler_function", ("text=Duo va Salovatlar🤲",)),
    ("keyboards.default.duo", "duo", ("text=Duo",)),
    ("keyboards.default.duo", "duo", ("text=Salovat",)),
    ("keyboards.default.films", "send_movie_menu", ("text=Filmlar🎞",)),
    ("keyboards.default.films", "send_movie_oy", ("text=Olamga nur sochgan oy",)),
    ("keyboards.default.films", "send_bilol", ("text=Bilol ibn Raboh",)),
    ("keyboards.default.lessons", "send_menu", ("text=Darsliklar📕",)),
    ("keyboards.default.lessons", "send_zam_suralar", ("text=Qur'on tartili",)),
    ("keyboards.default.lessons", "send_zam_suralar", ("text=Arab tili uchun kitoblar",)),
    ("keyboards.default.ramazon", "send_menu", ("text=Ramazon🌙",)),
    ("keyboards.default.ramazon", "send_bilol", ("text=Ramazon haqida",)),
    ("keyboards.default.ramazon", "send_bilol", ("text=Ramazon oyidagi amallar",)),
    ("keyboards.default.ramazon", "send_bilol", ("text=Ramazon taqvimi",)),
    ("handlers.users.start", "bot_start", ("/start",)),
    ("handlers.users.start", "main", ("text=boshlash",)),
    ("handlers.users.location_handler", "get_contact", ("content=location",)),
    ("handlers.users.admins", "show_menu", ("admin", "/admins")),
    ("handlers.users.admins", "handle_message", ("text=All users", "admin")),
    ("handlers.users.admins", "count_obuna", ("text=Follow namaz", "admin")),
    ("handlers.users.admins", "broadcast_command_handler", ("text=Broadcast", "admin")),
    # Broadcast holatidagi handlerda admin filtri yo'q (docs/MIGRATION_2026.md, 7-bo'lim).
    ("handlers.users.admins", "start_broadcast", ("state=broadcast_text", "content=any")),
]

EXPECTED_CALLBACK_HANDLERS = [
    ("keyboards.inline.regions", "prayer_times_callback_handler"),
    ("keyboards.inline.regions", "handle_subscription_callback"),
    # Hamma callback larni ushlaydi, shuning uchun oxirida turishi shart. Bu import tartibiga bog'liq.
    ("keyboards.inline.callback", "process_callback"),
]


def describe(handler):
    triggers = []
    for filter_obj in handler.filters:
        flt = filter_obj.filter
        kind = type(flt).__name__
        if kind == "StateFilter":
            triggers += [f"state={state}" for state in flt.states if state is not None]
        elif kind == "ContentTypeFilter":
            if list(flt.content_types) != ["text"]:
                triggers.append("content=" + ",".join(flt.content_types))
        elif kind == "Text":
            triggers.append("text=" + " | ".join(flt.equals))
        elif kind == "IDFilter":
            triggers.append("admin")
        elif hasattr(flt, "commands"):
            triggers.append("/" + " /".join(flt.commands))
        else:
            triggers.append(kind)
    return handler.handler.__module__, handler.handler.__name__, triggers


def collect_handlers():
    """Joriy jarayondagi dispatcher jadvalini JSON ga yaroqli ko'rinishda qaytaradi."""
    from loader import dp

    return {
        "message": [describe(h) for h in dp.message_handlers.handlers],
        "callback": [(h.handler.__module__, h.handler.__name__) for h in dp.callback_query_handlers.handlers],
        "admin_ids": sorted(
            {
                user_id
                for handler in dp.message_handlers.handlers
                for filter_obj in handler.filters
                if type(filter_obj.filter).__name__ == "IDFilter"
                for user_id in filter_obj.filter.user_id
            }
        ),
    }


@pytest.fixture(scope="module")
def production_handlers():
    script = "import app, json; from tests.test_routing import collect_handlers; print(json.dumps(collect_handlers()))"
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, env=os.environ, capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_message_handlers(production_handlers):
    actual = [(module, name, tuple(triggers)) for module, name, triggers in production_handlers["message"]]

    assert actual == EXPECTED_MESSAGE_HANDLERS


def test_callback_handlers_order(production_handlers):
    assert [tuple(item) for item in production_handlers["callback"]] == EXPECTED_CALLBACK_HANDLERS


def test_admin_filter_uses_admins_from_config(production_handlers):
    assert production_handlers["admin_ids"] == sorted(int(admin) for admin in os.environ["ADMINS"].split(","))
