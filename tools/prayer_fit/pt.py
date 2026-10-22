"""PrayTimes.org algoritmi (past aniqlikdagi quyosh holati), Asia/Tashkent = UTC+5."""
import math, datetime as dt
d2r, r2d = math.pi / 180, 180 / math.pi
sin = lambda d: math.sin(d * d2r); cos = lambda d: math.cos(d * d2r); tan = lambda d: math.tan(d * d2r)
asin = lambda x: r2d * math.asin(x); acos = lambda x: r2d * math.acos(x)
atan2 = lambda y, x: r2d * math.atan2(y, x); acot = lambda x: r2d * math.atan(1 / x)
fixa = lambda a: a % 360; fixh = lambda h: h % 24

def julian(y, m, d):
    if m <= 2: y -= 1; m += 12
    A = y // 100; B = 2 - A + A // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5

def sunpos(jd):
    D = jd - 2451545.0
    g = fixa(357.529 + 0.98560028 * D); q = fixa(280.459 + 0.98564736 * D)
    L = fixa(q + 1.915 * sin(g) + 0.020 * sin(2 * g)); e = 23.439 - 0.00000036 * D
    RA = fixh(atan2(cos(e) * sin(L), cos(L)) / 15)
    return asin(sin(e) * sin(L)), q / 15 - RA  # decl, eqt (soat)

def compute(date, lat, lng, tz=5.0, fajr=18.0, isha=17.0, rise=0.833, asr_f=2, tune=None):
    """Qaytaradi: bomdod, quyosh, peshin, asr, shom, xufton (kasr soat)."""
    jd = julian(date.year, date.month, date.day) - lng / (15 * 24)
    mid = lambda t: fixh(12 - sunpos(jd + t)[1])
    def sat(angle, t, ccw=False):
        decl = sunpos(jd + t)[0]; noon = mid(t)
        x = (-sin(angle) - sin(decl) * sin(lat)) / (cos(decl) * cos(lat))
        h = acos(max(-1, min(1, x))) / 15
        return noon + (-h if ccw else h)
    def asr(f, t):
        decl = sunpos(jd + t)[0]
        return sat(-acot(f + tan(abs(lat - decl))), t)
    # taxminiy vaqtlar bilan 1 marta aniqlashtirish
    t = {"f": 5/24, "r": 6/24, "d": 12/24, "a": 13/24, "s": 18/24, "i": 18/24}
    for _ in range(2):
        t = {"f": sat(fajr, t["f"]/1, True)/24, "r": sat(rise, t["r"], True)/24, "d": mid(t["d"])/24,
             "a": asr(asr_f, t["a"])/24, "s": sat(rise, t["s"])/24, "i": sat(isha, t["i"])/24}
    off = tz - lng / 15
    return [t[k] * 24 + off for k in "frdasi"]

def hhmm(h): 
    m = round((h % 24) * 60); return f"{m // 60 % 24:02d}:{m % 60:02d}"
