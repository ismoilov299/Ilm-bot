import json, re, sys, pathlib
sp = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
posts = json.load(open(sp / "v1_posts.json", encoding="utf-8"))
lists = json.load(open(sp / "v1_lists.json", encoding="utf-8"))
pagen = json.load(open(sp / "v1_pagenames.json", encoding="utf-8"))["names"]

by_trigger = {}
for f, items in posts.items():
    for it in items:
        by_trigger[it["trigger"]] = it["message_ids"]

def ids(trigger):
    return by_trigger[trigger]

def numbered(file, block):
    return {n: t for n, t in lists[file][block]}

nodes = []
def add(key, name, kind, parent=None, text="", message_ids=None, action=None, source="v1", review=None):
    nodes.append({"key": key, "name": name, "kind": kind, "parent": parent, "text": text,
                  "message_ids": message_ids or [], "action": action, "source": source,
                  **({"review": review} if review else {})})

# --- yuqori daraja
add("namoz", "Namoz🕋", "menu", text="Tanlang!")
add("quran", "Qur'on📖", "menu")
add("duo_zikr", "Duo va Zikirlar🤲", "menu", text="Alloh vaqtlaringizni o'zining zikri ila xush o'tishini nasib etsin!")
add("sahobalar", "Sahobalar", "list")
add("asmaul", "Asmaul Husna", "menu")
add("masjid", "Yaqin Masjid🕌", "action", action="nearest_mosques")
add("kitoblar", "Kitoblar📚", "list")

# --- Namoz
add("namoz_vaqt", "Namoz vaqtlari", "action", "namoz", action="prayer_times")
add("gusl_tahorat", "G'usul va Tahorat", "menu", "namoz")
add("gusl", "G'usul", "post", "gusl_tahorat", message_ids=ids("gusl"))
add("tahorat", "Tahorat", "post", "gusl_tahorat", message_ids=ids("tahorat"))
add("namoz_turlari", "Namoz turlari", "menu", "namoz")
add("farz", "Farz namozlar", "list", "namoz_turlari")
for k, n in [("bomdod", "Bomdod"), ("peshin", "Peshin"), ("asr", "Asr"), ("shom", "Shom"), ("xufton", "Xufton")]:
    add(f"farz_{k}", f"{n} namozi", "post", "farz", message_ids=ids(f"f:{k}"))
add("sunnat", "Sunnat namozlar", "list", "namoz_turlari")
for k, n in [("bomdod", "Bomdod namozi"), ("peshin4", "Peshin namozi (4 rakat)"), ("peshin2", "Peshin namozi (2 rakat)"),
             ("shom", "Shom namozi"), ("xufton", "Xufton namozi")]:
    add(f"sunnat_{k}", n, "post", "sunnat", message_ids=ids(f"s:{k}"))
add("vojib", "Vojib namozlar", "list", "namoz_turlari", review="v1 da bu bo'lim uchun post yo'q; v2 da bor edi (post ID lar yo'qolgan)")
add("juma", "Juma namozi (jamoat)", "post", "namoz_turlari", message_ids=ids("juma"))
add("janoza", "Janoza namozi (jamoat)", "post", "namoz_turlari", message_ids=ids("janoza"))
add("vitr", "Vitr namozi", "post", "namoz_turlari", message_ids=ids("vitr"))
add("hayit", "Ramazon va Qurbon hayit namozlari", "post", "namoz_turlari", message_ids=ids("hayit"))
add("zam_suralar", "Zam suralar", "list", "namoz", source="v2", review="Post ID lar topilmadi (v2 bazada edi)")

# --- Qur'on
quran_text = "\n".join(f"• {t}" for t in [])  # v1 matni kodda; admin panelda to'ldiriladi
add("quran_info", "Qur'on haqida ma'lumot", "post", "quran", source="v1", review="v1 da bu oddiy matn edi (menu.py), post emas; matnni qo'lda ko'chirish kerak")
add("quran_suralar", "Qur'onga o'tish", "list", "quran")
sura = numbered("keyboards/send_data/quranCallback.py", 0)  # nomlar blokdan keyin birlashtiriladi
all_sura = {}
for b in lists["keyboards/send_data/quranCallback.py"]:
    for n, t in b: all_sura.setdefault(n, t)
for n in range(1, 115):
    add(f"sura_{n}", f"{n:02d}. {all_sura[n]}", "post", "quran_suralar", message_ids=ids(str(n)))

# --- Duo va Zikr
add("zikr", "Zikr", "list", "duo_zikr")
for i in range(1, 25):
    add(f"zikr_{i}", pagen[f"zikr{i}"], "post", "zikr", message_ids=ids(f"zikr{i}"))
add("duo", "Duo", "list", "duo_zikr")
for i in range(1, 41):
    add(f"duo_{i}", pagen[f"duo{i}"], "post", "duo", message_ids=ids(f"duo{i}"))
add("salovat", "Salovat", "list", "duo_zikr")
for i in range(1, 9):
    add(f"salovat_{i}", pagen[f"salovat{i}"], "post", "salovat", message_ids=ids(f"salovat{i}"))

# --- Sahobalar va kitoblar (menu.py: 0-blok sahobalar, 1-blok kitoblar; raqamlarga qarab aniqlanadi)
blocks = lists["handlers/users/menu.py"]
sah = {n: t for n, t in blocks[0]}; kit = {n: t for n, t in blocks[1]}
assert sah[1].startswith("Abu Bakr") and kit[1].startswith("Musulmonning"), (sah[1], kit[1])
for i in range(1, 11):
    add(f"sahoba_{i}", sah[i], "post", "sahobalar", message_ids=ids(f"s{i}"))
    add(f"kitob_{i}", kit[i], "post", "kitoblar", message_ids=ids(f"k{i}"))

# --- Asmaul Husna
add("asmaul_99", "Allohning 99 ismi", "post", "asmaul", message_ids=[709, 479], review="709/479: qaysi biri ism, qaysi biri ma'nosi ekanini tekshirish")
add("asmaul_manolari", "Ma'nolari", "post", "asmaul", message_ids=[707])

# --- v2 da kodda qolgan post ID lar
add("ramazon", "Ramazon🌙", "menu", source="v2")
add("ramazon_haqida", "Ramazon haqida", "post", "ramazon", message_ids=[1538], source="v2")
add("ramazon_amallar", "Ramazon oyidagi amallar", "post", "ramazon", message_ids=[1539], source="v2")
add("ramazon_taqvim", "Ramazon taqvimi", "post", "ramazon", message_ids=[1537], source="v2")
add("hifz", "Hifz uchun tavsiyalar", "post", "quran", message_ids=[1532], source="v2")
add("bilol", "Bilol ibn Raboh", "post", "filmlar", message_ids=[1362], source="v2")
add("filmlar", "Filmlar🎞", "menu", source="v2", review="Faqat 'Bilol ibn Raboh' posti ma'lum; qolgan filmlar ID lari yo'qolgan")
add("darsliklar", "Darsliklar📕", "menu", source="v2", review="Qur'on tartili va Arab tili kitoblari post ID lari yo'qolgan")

# tartib: parent bo'yicha pozitsiya
pos = {}
for n in nodes:
    p = n["parent"]; pos[p] = pos.get(p, 0) + 1; n["position"] = pos[p]
keys = [n["key"] for n in nodes]; assert len(keys) == len(set(keys)), "takroriy key"
assert all(n["parent"] in keys or n["parent"] is None for n in nodes), "noma'lum parent"
json.dump({"channel": "@testislomyolida", "nodes": nodes}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
tot = sum(len(n["message_ids"]) for n in nodes)
print("tugunlar:", len(nodes), "| post ID (jami):", tot, "| noyob:", len({i for n in nodes for i in n['message_ids']}),
      "| tekshirish kerak:", sum('review' in n for n in nodes))
