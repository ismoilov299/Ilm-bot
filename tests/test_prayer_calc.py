"""Mahalliy hisoblash rasmiy jadvalga mos kelishi (docs/ARCHITECTURE.md 6.2.1)."""

import csv
import datetime as dt
from pathlib import Path

import pytest

from ilmbot.integrations.prayer_calc import PRAYERS, compute_day
from ilmbot.seed import load_seed

FIXTURE = Path(__file__).parent / "fixtures" / "prayer_times_2022.csv"
COORDINATES = {region["name"]: (region["lat"], region["lon"]) for region in load_seed("regions.json")}


def _minutes(value: str | dt.time) -> int:
    if isinstance(value, dt.time):
        return value.hour * 60 + value.minute
    hours, mins = value.split(":")
    return int(hours) * 60 + int(mins)


@pytest.fixture(scope="module")
def official_rows() -> list[dict[str, str]]:
    with FIXTURE.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_fixture_covers_all_regions_and_most_of_the_year(official_rows):
    assert {row["region"] for row in official_rows} == set(COORDINATES)
    assert len(official_rows) > 3100


def test_every_value_is_within_one_minute_of_the_official_table(official_rows):
    too_far = []
    exact = total = 0
    for row in official_rows:
        computed = compute_day(dt.date.fromisoformat(row["date"]), *COORDINATES[row["region"]]).as_dict()
        for prayer in PRAYERS:
            diff = _minutes(computed[prayer]) - _minutes(row[prayer])
            total += 1
            exact += diff == 0
            if abs(diff) > 1:
                too_far.append((row["region"], row["date"], prayer, diff))

    assert not too_far, f"{len(too_far)} ta qiymat 1 daqiqadan ko'p farq qiladi, masalan: {too_far[:5]}"
    assert total > 19_000
    assert exact / total > 0.85  # ko'pi aynan mos; pasaysa, hisoblash siljigan


def test_known_day_in_tashkent():
    times = compute_day(dt.date(2022, 5, 1), *COORDINATES["Toshkent"])

    expected = {
        "bomdod": "03:50",
        "quyosh": "05:21",
        "peshin": "12:20",
        "asr": "17:16",
        "shom": "19:25",
        "xufton": "20:46",
    }
    for prayer, text in expected.items():
        assert abs(_minutes(getattr(times, prayer)) - _minutes(text)) <= 1, prayer


@pytest.mark.parametrize("region", sorted(COORDINATES))
def test_prayers_are_in_chronological_order_all_year(region):
    day = dt.date(2026, 1, 1)
    while day.year == 2026:
        values = [_minutes(t) for t in compute_day(day, *COORDINATES[region]).as_dict().values()]
        assert values == sorted(values) and len(set(values)) == 6, (region, day, values)
        day += dt.timedelta(days=1)


def test_result_is_deterministic():
    first = compute_day(dt.date(2026, 10, 22), 41.2995, 69.2401)

    assert first == compute_day(dt.date(2026, 10, 22), 41.2995, 69.2401)
    assert first.bomdod < first.quyosh < first.peshin < first.asr < first.shom < first.xufton
