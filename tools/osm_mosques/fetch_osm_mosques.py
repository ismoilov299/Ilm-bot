"""O'zbekiston masjidlarini OpenStreetMap'dan (Overpass API) olib `seeds/mosques_osm.json` ga yozadi.

OSM faqat koordinata manbai: bot Telegram lokatsiyasini yuboradi, u telefonda Google/Yandex xaritasida ochiladi.
Qo'lda tekshirilgan `seeds/mosques.json` o'zgarmaydi; unga 100 m dan yaqin OSM yozuvlari tashlab yuboriladi.

Ishga tushirish: python tools/osm_mosques/fetch_osm_mosques.py
Ma'lumot © OpenStreetMap contributors (ODbL).
"""

import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = (
    '[out:json][timeout:120];area["ISO3166-1"="UZ"]->.a;'
    '(nwr["amenity"="place_of_worship"]["religion"="muslim"](area.a);'
    'nwr["building"="mosque"](area.a););out center tags;'
)
MERGE_RADIUS_M = 60  # bir masjidning nuqtasi va binosi shu masofada takror hisoblanadi
CURATED_RADIUS_M = 100
DEFAULT_NAME = "Masjid"
GENERIC_NAMES = {"masjid", "jome masjid", "jome masjidi", "jame masjid", "jamie masjid"}

CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ь": "", "ы": "i",
    "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}


def translit(text: str) -> str:
    out = []
    for i, ch in enumerate(text):
        low = ch.lower()
        if low not in CYR:
            out.append(ch)
            continue
        latin = CYR[low]
        if low == "е" and (i == 0 or not text[i - 1].isalpha()):
            latin = "ye"
        out.append(latin.capitalize() if ch.isupper() else latin)
    return "".join(out)


def normalize(text: str) -> str:
    text = translit(text).replace("‘", "'").replace("’", "'").replace("`", "'").replace("ʻ", "'").replace("ʼ", "'")
    text = text.replace("jom'e", "jome").replace("Jom'e", "Jome")
    return " ".join(text.split())


def pick_name(tags: dict) -> str:
    for key in ("name:uz", "name:uz-Latn", "name", "name:uz-Cyrl", "name:uz-cyr", "name:ru", "int_name"):
        value = (tags.get(key) or "").strip()
        if value:
            return normalize(value)
    return DEFAULT_NAME


def address(tags: dict) -> str:
    """Ko'cha va uy raqami; bo'lmasa to'liq manzil; bo'lmasa shahar yoki tuman."""
    street = normalize((tags.get("addr:street") or "").strip())
    house = (tags.get("addr:housenumber") or "").strip()
    if street:
        return f"{street} {house}".strip()
    full = normalize((tags.get("addr:full") or "").strip())
    if full:
        return full
    for key in ("addr:district", "addr:city", "addr:suburb", "addr:place"):
        if tags.get(key):
            return normalize(tags[key].strip())
    return ""


def display_name(tags: dict) -> str:
    """Umumiy yoki nomsiz masjidga manzil qo'shiladi: "Jome masjid, Quva ko'chasi 81a"."""
    name = pick_name(tags)
    if name.lower().replace("'", "") not in GENERIC_NAMES:
        return name
    where = address(tags)
    base = DEFAULT_NAME if name == DEFAULT_NAME else name[:1].upper() + name[1:]
    return f"{base}, {where}"[:255] if where else base


def meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def too_close(point: tuple[float, float], others: list[tuple[float, float]], limit: float) -> bool:
    return any(abs(point[0] - o[0]) < 0.002 and meters(point, o) < limit for o in others)


def fetch() -> list[dict]:
    request = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({"data": QUERY}).encode(),
        headers={"User-Agent": "ilmbot-seed/1.0", "Accept": "*/*"},
    )
    for attempt in range(4):  # Overpass band bo'lsa HTML qaytaradi
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.load(response)["elements"]
        except (ValueError, OSError):
            time.sleep(20 * (attempt + 1))
    raise SystemExit("Overpass javob bermadi, keyinroq urinib ko'ring")


def build(elements: list[dict], curated: list[dict]) -> list[dict]:
    # Bino konturi (way/relation) nuqtadan aniqroq nom va markaz beradi, shuning uchun u oldin keladi
    order = {"relation": 0, "way": 1, "node": 2}
    elements = sorted(elements, key=lambda e: order[e["type"]])
    known = [(m["lat"], m["lon"]) for m in curated]
    result: list[dict] = []
    kept: list[tuple[float, float]] = []
    for element in elements:
        center = element.get("center") or element
        point = (round(center["lat"], 6), round(center["lon"], 6))
        if too_close(point, known, CURATED_RADIUS_M) or too_close(point, kept, MERGE_RADIUS_M):
            continue
        tags = element.get("tags", {})
        name = display_name(tags)
        result.append(
            {
                "name": name,
                "district": None,
                "lat": point[0],
                "lon": point[1],
                "review": f"OSM {element['type']}/{element['id']}",
            }
        )
        kept.append(point)
    return result


def main() -> None:
    curated = json.loads((ROOT / "seeds" / "mosques.json").read_text(encoding="utf-8"))
    mosques = build(fetch(), curated)
    mosques.sort(key=lambda m: (m["lat"], m["lon"]))
    (ROOT / "seeds" / "mosques_osm.json").write_text(
        json.dumps(mosques, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    bare = sum(m["name"] in (DEFAULT_NAME, "Jome masjid") for m in mosques)
    print(f"{len(mosques)} ta masjid yozildi ({bare} tasi manzilsiz va umumiy nomli), qo'lda tekshirilgan: {len(curated)}")


if __name__ == "__main__":
    sys.exit(main())
