"""Admin yozgan matnni Telegram HTML ga xavfsiz va to'g'ri shaklga keltirish.

Faqat Telegram qo'llab-quvvatlaydigan teglar ruxsat etiladi. Chiqish qaytadan quriladi (kiruvchi matn bevosita
o'tmaydi), shuning uchun u ham Telegram, ham veb-ko'rinish (preview) uchun xavfsiz. Qator uzilishi oddiy Enter bilan.
"""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

ALLOWED_TAGS = frozenset(
    {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "code", "pre", "blockquote", "tg-spoiler", "a"}
)
ALLOWED_LINK_SCHEMES = frozenset({"http", "https", "tg"})
MAX_LENGTH = 4096  # Telegram xabarining ko'rinadigan matn chegarasi


class HtmlError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan tushunarli xato."""


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []
        self.visible_length = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ALLOWED_TAGS:
            raise HtmlError(
                f"<{tag}> tegi qo'llab-quvvatlanmaydi. Ruxsat etilganlar: {', '.join(sorted(ALLOWED_TAGS))}"
            )
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if urlparse(href).scheme not in ALLOWED_LINK_SCHEMES:
                raise HtmlError("Havola http://, https:// yoki tg:// bilan boshlanishi kerak")
            self.parts.append(f'<a href="{escape(href, quote=True)}">')
        else:
            if attrs:
                raise HtmlError(f"<{tag}> tegida atribut bo'lmasligi kerak")
            self.parts.append(f"<{tag}>")
        self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raise HtmlError(f"<{tag}/> qo'llab-quvvatlanmaydi. Qator uzilishi uchun Enter ni bosing")

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag:
            raise HtmlError(f"</{tag}> tegi noto'g'ri joyda yopilgan")
        self.stack.pop()
        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(escape(data, quote=False))
        self.visible_length += len(data)

    def handle_comment(self, data: str) -> None:
        raise HtmlError("Izohlar (<!-- -->) qo'llab-quvvatlanmaydi")

    def handle_decl(self, decl: str) -> None:
        raise HtmlError("Bu konstruksiya qo'llab-quvvatlanmaydi")

    def handle_pi(self, data: str) -> None:
        raise HtmlError("Bu konstruksiya qo'llab-quvvatlanmaydi")


def sanitize(text: str) -> str:
    """Tozalangan HTML ni qaytaradi yoki `HtmlError` ko'taradi."""
    parser = _Sanitizer()
    parser.feed(text.strip())
    parser.close()
    if parser.stack:
        raise HtmlError(f"<{parser.stack[-1]}> tegi yopilmagan")
    if not "".join(parser.parts).strip() or parser.visible_length == 0:
        raise HtmlError("Xabar matni bo'sh")
    if parser.visible_length > MAX_LENGTH:
        raise HtmlError(f"Xabar juda uzun: {parser.visible_length} belgi (ruxsat: {MAX_LENGTH})")
    return "".join(parser.parts)
