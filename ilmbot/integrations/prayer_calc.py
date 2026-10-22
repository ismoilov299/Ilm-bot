"""Namoz vaqtlarini mahalliy hisoblash (tashqi API siz).

PrayTimes.org algoritmi (quyosh holati). Parametrlar O'zbekiston Musulmonlari idorasi jadvaliga moslab topilgan:
13 shahar x 245 kun x 6 namoz bo'yicha hamma qiymat +-1 daqiqa ichida (`tests/test_prayer_calc.py`,
`docs/ARCHITECTURE.md` 6.2.1). Vaqt zonasi: Asia/Tashkent (UTC+5, yozgi vaqt yo'q).
"""

import datetime as dt
import math
from dataclasses import dataclass

UTC_OFFSET_HOURS = 5.0

FAJR_ANGLE = 15.0  # bomdod: quyosh ufqdan 15 daraja pastda...
FAJR_OFFSET_MINUTES = -5  # ...va 5 daqiqa ehtiyot
ISHA_ANGLE = 15.0  # xufton: quyosh ufqdan 15 daraja pastda
SUN_ALTITUDE = 0.833  # quyosh chiqishi va botishi (refraksiya va quyosh radiusi bilan)
ASR_SHADOW_FACTOR = 2  # Hanafiy mazhabi: soya uzunligi narsaning ikki baravari
MAGHRIB_OFFSET_MINUTES = 5  # shom: quyosh botgandan 5 daqiqa keyin

PRAYERS = ("bomdod", "quyosh", "peshin", "asr", "shom", "xufton")


@dataclass(frozen=True, slots=True)
class DayTimes:
    bomdod: dt.time
    quyosh: dt.time
    peshin: dt.time
    asr: dt.time
    shom: dt.time
    xufton: dt.time

    def as_dict(self) -> dict[str, dt.time]:
        return {name: getattr(self, name) for name in PRAYERS}


_RAD = math.pi / 180


def _sin(deg: float) -> float:
    return math.sin(deg * _RAD)


def _cos(deg: float) -> float:
    return math.cos(deg * _RAD)


def _tan(deg: float) -> float:
    return math.tan(deg * _RAD)


def _asin(x: float) -> float:
    return math.asin(x) / _RAD


def _acos(x: float) -> float:
    return math.acos(max(-1.0, min(1.0, x))) / _RAD


def _acot(x: float) -> float:
    return math.atan(1 / x) / _RAD


def _julian_day(year: int, month: int, day: int) -> float:
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5


def _sun_position(jd: float) -> tuple[float, float]:
    """(og'ish darajada, vaqt tenglamasi soatda)."""
    d = jd - 2451545.0
    g = (357.529 + 0.98560028 * d) % 360
    q = (280.459 + 0.98564736 * d) % 360
    lon = (q + 1.915 * _sin(g) + 0.020 * _sin(2 * g)) % 360
    e = 23.439 - 0.00000036 * d
    ra = (math.atan2(_cos(e) * _sin(lon), _cos(lon)) / _RAD / 15) % 24
    return _asin(_sin(e) * _sin(lon)), q / 15 - ra


def _round_minutes(hours: float, offset_minutes: int = 0) -> dt.time:
    total = math.floor((hours % 24) * 60 + offset_minutes + 0.5)
    total %= 24 * 60
    return dt.time(total // 60, total % 60)


def compute_day(date: dt.date, lat: float, lon: float) -> DayTimes:
    """Berilgan sana va koordinata uchun 6 ta vaqt (daqiqagacha yaxlitlangan, Asia/Tashkent bo'yicha)."""
    jd = _julian_day(date.year, date.month, date.day) - lon / (15 * 24)

    def midday(t: float) -> float:
        return (12 - _sun_position(jd + t)[1]) % 24

    def angle_time(angle: float, t: float, *, before_noon: bool = False) -> float:
        decl = _sun_position(jd + t)[0]
        hour_angle = _acos((-_sin(angle) - _sin(decl) * _sin(lat)) / (_cos(decl) * _cos(lat))) / 15
        return midday(t) + (-hour_angle if before_noon else hour_angle)

    def asr_time(t: float) -> float:
        decl = _sun_position(jd + t)[0]
        return angle_time(-_acot(ASR_SHADOW_FACTOR + _tan(abs(lat - decl))), t)

    # Dastlabki taxmin (kun ulushi), so'ng ikki marta aniqlashtiriladi
    t = {"fajr": 5 / 24, "sunrise": 6 / 24, "noon": 12 / 24, "asr": 13 / 24, "sunset": 18 / 24, "isha": 18 / 24}
    for _ in range(2):
        t = {
            "fajr": angle_time(FAJR_ANGLE, t["fajr"], before_noon=True) / 24,
            "sunrise": angle_time(SUN_ALTITUDE, t["sunrise"], before_noon=True) / 24,
            "noon": midday(t["noon"]) / 24,
            "asr": asr_time(t["asr"]) / 24,
            "sunset": angle_time(SUN_ALTITUDE, t["sunset"]) / 24,
            "isha": angle_time(ISHA_ANGLE, t["isha"]) / 24,
        }
    shift = UTC_OFFSET_HOURS - lon / 15  # mahalliy quyosh vaqtidan Asia/Tashkent ga
    return DayTimes(
        bomdod=_round_minutes(t["fajr"] * 24 + shift, FAJR_OFFSET_MINUTES),
        quyosh=_round_minutes(t["sunrise"] * 24 + shift),
        peshin=_round_minutes(t["noon"] * 24 + shift),
        asr=_round_minutes(t["asr"] * 24 + shift),
        shom=_round_minutes(t["sunset"] * 24 + shift, MAGHRIB_OFFSET_MINUTES),
        xufton=_round_minutes(t["isha"] * 24 + shift),
    )
