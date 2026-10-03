"""``prayer_time.vaqt.NamozVaqti`` islomapi.uz javobidan qaysi maydonlarni o'qishini qotiradi.

Javob namunasi soxta. Haqiqiy API formati Bosqich 3 boshida tekshiriladi, yangi API mijozi esa
shu maydonlarni xuddi shunday o'qishi kerak (docs/MIGRATION_2026.md).
"""

from prayer_time import vaqt

SAMPLE_RESPONSE = {
    "region": "Qo'qon",
    "date": "2026-10-03",
    "weekday": "Shanba",
    "times": {
        "tong_saharlik": "05:02",
        "quyosh": "06:21",
        "peshin": "12:12",
        "asr": "15:41",
        "shom_iftor": "18:00",
        "hufton": "19:15",
    },
}


class FakeResponse:
    def json(self):
        return SAMPLE_RESPONSE


def test_reads_prayer_times_from_api_fields(monkeypatch):
    requested_urls = []

    def fake_get(url):
        requested_urls.append(url)
        return FakeResponse()

    monkeypatch.setattr(vaqt.requests, "get", fake_get)

    times = vaqt.NamozVaqti("Qo'qon")

    assert requested_urls == ["https://islomapi.uz/api/present/day?region=Qo'qon"]
    assert (times.get_sana(), times.get_kun()) == ("2026-10-03", "Shanba")
    assert [times.bomdod(), times.quyosh_chiqishi(), times.peshin(), times.asr(), times.shom(), times.xufton()] == [
        "05:02",
        "06:21",
        "12:12",
        "15:41",
        "18:00",
        "19:15",
    ]
