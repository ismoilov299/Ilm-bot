"""v1 repodagi rasmiy jadvaldan (`data/dataNamaz.sqlite`) regression test uchun CSV tayyorlaydi.

Ishlatish: python -I -X utf8 make_fixture.py <dataNamaz.sqlite> <chiqish.csv>   (repo ildizidan: python -m ... emas, to'g'ridan-to'g'ri)

Buzilgan qatorlar (bo'sh qiymat, formatsiz vaqt) va hisoblashdan 30 daqiqadan ko'p farq qiladigan qiymatli qatorlar
(jadvaldagi aniq xatolar) chiqarib tashlanadi; nechtasi tashlangani chop etiladi.
"""

import csv
import datetime as dt
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ilmbot.integrations.prayer_calc import PRAYERS, compute_day  # noqa: E402

COORDINATES = {
    "Toshkent": (41.2995, 69.2401),
    "Andijon": (40.7821, 72.3442),
    "Buxoro": (39.7747, 64.4286),
    "Guliston": (40.4897, 68.7842),
    "Samarqand": (39.6542, 66.9597),
    "Namangan": (40.9983, 71.6726),
    "Navoiy": (40.1039, 65.3739),
    "Jizzax": (40.1158, 67.8422),
    "Nukus": (42.4531, 59.6103),
    "Qarshi": (38.8606, 65.7891),
    "Qo'qon": (40.5286, 70.9425),
    "Xiva": (41.3775, 60.3639),
    "Marg'ilon": (40.4722, 71.7247),
}


def minutes(value: str) -> int:
    hours, mins = re.split(r"[:.]", value.strip())
    return int(hours) * 60 + int(mins)


def main(source: str, target: str) -> None:
    db = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    rows = db.execute("select Mintaqa, Sana, Bomdod, [Quyosh chiqishi], Peshin, Asr, Shom, Xufton from namaz").fetchall()
    kept, broken, wrong = [], 0, 0
    for region, date_text, *values in rows:
        if region not in COORDINATES:
            continue
        try:
            date = dt.datetime.strptime(date_text, "%d.%m.%Y").date()
            truth = [minutes(v) for v in values]
        except (ValueError, TypeError):
            broken += 1
            continue
        calc = compute_day(date, *COORDINATES[region]).as_dict()
        if any(abs(c.hour * 60 + c.minute - t) > 30 for c, t in zip(calc.values(), truth, strict=True)):
            wrong += 1
            continue
        kept.append([region, date.isoformat(), *[f"{t // 60:02d}:{t % 60:02d}" for t in truth]])
    with open(target, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["region", "date", *PRAYERS])
        writer.writerows(sorted(kept))
    print(f"yozildi: {len(kept)} qator | formati buzilgan: {broken} | 30 daqiqadan ko'p farq (jadval xatosi): {wrong}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
