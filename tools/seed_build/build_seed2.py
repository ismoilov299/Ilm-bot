import json, re, pathlib, sys
root = pathlib.Path(sys.argv[1])
exp = json.load(open(root / "result.json", encoding="utf-8")); M = {x["id"]: x for x in exp["messages"] if x["type"] == "message"}
seed = json.load(open(root / "seeds/menu_seed.json", encoding="utf-8")); nodes = seed["nodes"]; keys = {n["key"] for n in nodes}

def txt(x):
    t = x["text"]
    if isinstance(t, list): t = "".join(p if isinstance(p, str) else p.get("text", "") for p in t)
    return " ".join(t.split())
def kind(x): return x.get("media_type") or ("photo" if "photo" in x else "text")
def title(x):
    s = x.get("title") or x.get("file_name") or txt(x)
    s = re.sub(r"\.(mp4|mp3|pdf|PDF|jpg|jpeg|JPG)$", "", s).replace("_", " ").strip()
    return s[:80] or f"post {x['id']}"
def add(key, name, kind_, parent, ids=None, source="channel", review=None, text=""):
    assert key not in keys, key; keys.add(key)
    n = {"key": key, "name": name, "kind": kind_, "parent": parent, "text": text, "message_ids": ids or [], "action": None, "source": source}
    if review: n["review"] = review
    pos = sum(1 for m in nodes if m["parent"] == parent) + 1; n["position"] = pos; nodes.append(n)

N = {n["key"]: n for n in nodes}
used = {i for n in nodes for i in n["message_ids"]}
def rng(a, b, pred=lambda x: True): return [i for i in sorted(M) if a <= i <= b and pred(M[i])]
assigned = {}
def group(label, ids): 
    for i in ids: assigned[i] = label

# Aniq tuzatish: 99 ism (709 video, 479 matn)
N["asmaul_99"].pop("review", None); N["asmaul_99"]["message_ids"] = [479, 709]
N["asmaul_manolari"]["name"] = "Ma'nolari"

# --- Darsliklar
def is_pdf(x): return x.get("mime_type") == "application/pdf"
def episode(x):
    m = re.search(r"(\d+)\s*-?\s*(?:qism|қисм)", (x.get("file_name") or "") + " " + txt(x), re.I)
    return int(m.group(1)) if m else None
muallim = rng(1257, 1329, lambda x: title(x).startswith("Muallimi soniy"))
add("muallimi_soniy", "Muallimi soniy", "list", "darsliklar", review="Video-darslar, nomlar kanal fayllaridan")
for i in muallim: add(f"ms_{i}", title(M[i]).replace("Muallimi soniy | ", ""), "post", "muallimi_soniy", [i])
group("muallimi_soniy", muallim)
tartil = rng(1330, 1360, lambda x: kind(x) == "video_file")
add("quran_tartili", "Qur'on tartili", "list", "darsliklar", review="Video-darslar (Қуръон тартили)")
for i in tartil: add(f"qt_{i}", title(M[i]), "post", "quran_tartili", [i])
group("quran_tartili", tartil)
arab = rng(1524, 1536, is_pdf)
add("arab_kitoblar", "Arab tili uchun kitoblar", "list", "darsliklar", review="PDF lar; bo'lim nomi v2 kodidan")
for i in arab: add(f"arab_{i}", title(M[i]), "post", "arab_kitoblar", [i])
group("arab_kitoblar", arab)

# --- Filmlar (seriallar)
umar = rng(1363, 1392, lambda x: kind(x) == "video_file")
add("umar_serial", "Umar ibn Xattob r.a. (serial)", "list", "filmlar", review="30 qism; sarlavha kanaldagi izohdan")
for k, i in enumerate(umar, 1): add(f"um_{i}", f"{episode(M[i]) or k}-qism", "post", "umar_serial", [i])
group("umar_serial", umar)
oy = rng(1395, 1424, lambda x: kind(x) == "video_file")
N["filmlar"].pop("review", None)
add("olamga_nur", "Olamga nur sochgan oy", "list", "filmlar", review="30 qism, islomiy serial (v2 da 'Olamga nur sochgan oy')")
for k, i in enumerate(oy, 1): add(f"on_{i}", f"{episode(M[i]) or k}-qism", "post", "olamga_nur", [i])
group("olamga_nur", oy)

# --- Kitoblar (qo'shimcha PDF lar)
pdfs = [i for i in rng(278, 290) + rng(1228, 1255) if is_pdf(M[i]) and i not in used]
add("kitoblar_qoshimcha", "Boshqa kitoblar", "list", "kitoblar", review="Kanaldagi qolgan PDF kitoblar; bo'limga joylashuvini tasdiqlang")
for i in pdfs: add(f"kq_{i}", title(M[i]), "post", "kitoblar_qoshimcha", [i])
group("kitoblar_qoshimcha", pdfs)

# --- Asmaul Husna
rasm = rng(834, 930, lambda x: kind(x) == "photo")
add("asmaul_rasmlar", "Ismlar va ma'nolari (rasmlar)", "list", "asmaul", review="Rasm-izohlar; ismlar tartibi bo'yicha raqamlangan")
for k, i in enumerate(rasm, 1): add(f"ar_{i}", f"{k}-ism", "post", "asmaul_rasmlar", [i])
group("asmaul_rasmlar", rasm)
dars = rng(931, 980, lambda x: kind(x) == "audio_file")
add("asmaul_audio", "Asmaul Husna darslari (audio)", "list", "asmaul", review="Audio darslar")
for i in dars: add(f"aa_{i}", title(M[i]), "post", "asmaul_audio", [i])
group("asmaul_audio", dars)

# --- Sahobalar (audio darslar)
sau = rng(983, 1025, lambda x: kind(x) == "audio_file")
add("sahobalar_audio", "Sahobalar hayoti (audio)", "list", "sahobalar", review="Audio darslar; sahobalarga bo'lib chiqish mumkin")
for i in sau: add(f"sa_{i}", title(M[i]), "post", "sahobalar_audio", [i])
group("sahobalar_audio", sau)

# --- Zam suralar (matnlar)
zam = rng(1036, 1245, lambda x: kind(x) == "text" and re.search(r"SURASI|СУРАСИ", txt(x).upper()[:60]))
N["zam_suralar"]["review"] = "Sura matnlari kanaldan; tartib/to'liqligini tasdiqlang"
for i in zam:
    nm = re.split(r"Бисмиллаҳ|Bismillah", txt(M[i]), 1)[0].strip().title()
    add(f"zs_{i}", nm or f"post {i}", "post", "zam_suralar", [i])
group("zam_suralar", zam)

# --- Namozni o'rganish
org = [i for i in rng(510, 568) if kind(M[i]) == "video_file" and i not in used]
add("namozni_organish", "Namozni o'rganish", "list", "namoz", review="Namoz/tahorat videolari; v2 dagi bo'lim nomi")
for i in org: add(f"no_{i}", title(M[i]), "post", "namozni_organish", [i])
group("namozni_organish", org)

# --- Qur'on, 2-qori (114 audio)
q2 = rng(1065, 1178, lambda x: kind(x) == "audio_file")
assert len(q2) == 114, len(q2)
add("quran_audio2", "Qur'on audio (qori Badr al-Izi)", "list", "quran", review="114 ta sura audiosi; 'Qur'onga o'tish' bilan almashtirish/qo'shish masalasini hal qiling")
for i in q2: add(f"q2_{i}", title(M[i]), "post", "quran_audio2", [i])
group("quran_audio2", q2)

# --- Inventar
ignore_pat = re.compile(r"\.zip|^time is short|^oke|oddiy knopkan|nma qsa|^Axx|origin|^#(quran|kitoblar|asmaul_husna|duo|sahobalar)", re.I)
inv = []
for i in sorted(M):
    x = M[i]; label = assigned.get(i) or next((n["key"] for n in nodes if i in n["message_ids"]), None)
    t = title(x)
    status = "in_menu" if label else ("ignore" if ignore_pat.search(txt(x)[:80] + " " + (x.get("file_name") or "")) or "Web App" in t or kind(x) in ("sticker", "voice_message") else "unassigned")
    inv.append({"id": i, "date": x["date"][:10], "type": kind(x), "title": t[:90], "status": status, "node": label})
json.dump(inv, open(root / "seeds/channel_inventory.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
json.dump(seed, open(root / "seeds/menu_seed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("tugunlar:", len(nodes), "| menyudagi postlar:", len({i for n in nodes for i in n['message_ids']}))
print("inventar:", Counter(r["status"] for r in inv))
un = [r for r in inv if r["status"] == "unassigned"]
print("biriktirilmagan turlari:", Counter(r["type"] for r in un))
