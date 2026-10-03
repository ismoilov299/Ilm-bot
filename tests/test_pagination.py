"""``keyboards.inline.create.get_inline_keyboards`` uchun xarakterlovchi testlar.

Funksiya ``backend/ilmbot/db.sqlite3`` ni joriy papkaga nisbatan ochadi, shuning uchun har bir test
vaqtinchalik papkada shu yo'lda kichik baza yaratadi. Bosqich 3 da bu testlar yangi menyu
servisining testlari bilan almashtiriladi (docs/MIGRATION_2026.md).
"""

import asyncio
import sqlite3
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from keyboards.inline import create

PARENT_ID = 1
PARENT_TEXT = "Kitoblar bo'limi"
NOT_AVAILABLE = "Kechirasiz, hozir bu bo'lim tamirlanmoqda"


class FakeMessage:
    def __init__(self):
        self.chat = SimpleNamespace(id=100)
        self.message_id = 200
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


@pytest.fixture
def make_category(tmp_path, monkeypatch):
    """``PARENT_ID`` kategoriyasini ``children`` ta ichki tugma bilan yaratadi."""
    monkeypatch.chdir(tmp_path)
    db_dir = tmp_path / "backend" / "ilmbot"
    db_dir.mkdir(parents=True)

    def make(children):
        with closing(sqlite3.connect(db_dir / "db.sqlite3")) as conn, conn:
            conn.execute(
                "CREATE TABLE category_categorybutton "
                "(id INTEGER PRIMARY KEY, name TEXT, callback TEXT, text TEXT, parent_id INTEGER)"
            )
            conn.execute(
                "INSERT INTO category_categorybutton VALUES (?, 'Kitoblar', '', ?, NULL)", (PARENT_ID, PARENT_TEXT)
            )
            conn.executemany(
                "INSERT INTO category_categorybutton VALUES (?, ?, '', '', ?)",
                [(PARENT_ID + i, f"Kitob {i}", PARENT_ID) for i in range(1, children + 1)],
            )

    return make


@pytest.fixture
def edit_message_text(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(create.bot, "edit_message_text", mock)
    return mock


def rows(markup):
    return [[(button.text, button.callback_data) for button in row] for row in markup.inline_keyboard]


def show_page(page, category_id=PARENT_ID):
    message = FakeMessage()
    asyncio.run(create.get_inline_keyboards(message, category_id, page))
    return message


def test_first_page_sends_five_items_and_next_button(make_category, edit_message_text):
    make_category(children=11)

    message = show_page(1)

    [(text, markup)] = message.answers
    assert text == PARENT_TEXT
    assert rows(markup) == [[(f"Kitob {i}", str(PARENT_ID + i))] for i in range(1, 6)] + [[(">>", "next_1_1")]]
    edit_message_text.assert_not_awaited()


def test_middle_page_edits_message_with_both_arrows(make_category, edit_message_text):
    make_category(children=11)

    message = show_page(2)

    assert message.answers == []
    edit_message_text.assert_awaited_once()
    kwargs = edit_message_text.await_args.kwargs
    assert (kwargs["chat_id"], kwargs["message_id"], kwargs["text"]) == (100, 200, PARENT_TEXT)
    assert rows(kwargs["reply_markup"]) == [[(f"Kitob {i}", str(PARENT_ID + i))] for i in range(6, 11)] + [
        [("<<", "prev_1_2")],
        [(">>", "next_1_2")],
    ]


def test_last_page_has_only_previous_button(make_category, edit_message_text):
    make_category(children=11)

    show_page(3)

    assert rows(edit_message_text.await_args.kwargs["reply_markup"]) == [[("Kitob 11", "12")], [("<<", "prev_1_3")]]


def test_full_last_page_has_no_next_button(make_category, edit_message_text):
    make_category(children=10)

    show_page(2)

    assert rows(edit_message_text.await_args.kwargs["reply_markup"])[-1] == [("<<", "prev_1_2")]


@pytest.mark.parametrize(("children", "category_id"), [(3, 999), (0, PARENT_ID)])
def test_unknown_or_empty_category_is_reported(make_category, edit_message_text, children, category_id):
    make_category(children=children)

    message = show_page(1, category_id=category_id)

    assert message.answers == [(NOT_AVAILABLE, None)]
