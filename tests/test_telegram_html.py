import pytest

from ilmbot.services.telegram_html import HtmlError, sanitize


def test_allowed_markup_is_kept_and_text_is_escaped():
    assert sanitize("a < b & <b>qalin</b>") == "a &lt; b &amp; <b>qalin</b>"


def test_links_are_rebuilt_with_escaped_attributes():
    assert sanitize('<a href="https://t.me/x?a=1&b=2">havola</a>') == '<a href="https://t.me/x?a=1&amp;b=2">havola</a>'


@pytest.mark.parametrize(
    "bad",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<b onclick='x'>a</b>",
        '<a href="javascript:alert(1)">x</a>',
        '<a href="//evil.example">x</a>',
        "<b>yopilmagan",
        "</b>",
        "<b><i>noto'g'ri</b></i>",
        "<br/>",
        "<!-- izoh -->",
        "   ",
        "a" * 4097,
    ],
)
def test_unsafe_or_broken_input_is_rejected(bad):
    with pytest.raises(HtmlError):
        sanitize(bad)


def test_length_limit_counts_visible_characters_only():
    assert sanitize("<b>" + "a" * 4096 + "</b>").startswith("<b>")
