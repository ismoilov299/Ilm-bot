import re, sqlite3, sys, datetime as dt, itertools, statistics as st
sys.path.insert(0, sys.argv[1]); from pt import compute
db = sqlite3.connect("file:" + sys.argv[2] + "?mode=ro", uri=True)
COORD = {"Toshkent": (41.2995, 69.2401), "Andijon": (40.7821, 72.3442), "Buxoro": (39.7747, 64.4286), "Guliston": (40.4897, 68.7842),
 "Samarqand": (39.6542, 66.9597), "Namangan": (40.9983, 71.6726), "Navoiy": (40.1039, 65.3739), "Jizzax": (40.1158, 67.8422),
 "Nukus": (42.4531, 59.6103), "Qarshi": (38.8606, 65.7891), "Qo'qon": (40.5286, 70.9425), "Xiva": (41.3775, 60.3639), "Marg'ilon": (40.4722, 71.7247)}
BAD = []
def mins(s):
    h, m = re.split(r"[:.]", s.strip()); return int(h) * 60 + int(m)
def load(city):
    rows = db.execute("select Sana,Bomdod,[Quyosh chiqishi],Peshin,Asr,Shom,Xufton from namaz where Mintaqa=? order by rowid", (city,)).fetchall()
    out = []
    for r in rows:
        try: d = dt.datetime.strptime(r[0], "%d.%m.%Y").date(); out.append((d, [mins(x) for x in r[1:]]))
        except Exception: BAD.append((city, r))
    return out
names = ["bomdod", "quyosh", "peshin", "asr", "shom", "xufton"]
def errs(city, idx, **kw):
    lat, lng = COORD[city]; e = []
    for d, truth in load(city):
        calc = compute(d, lat, lng, **kw)[idx] * 60
        e.append(calc - truth[idx])
    return e
if sys.argv[3] == "fit":
    city = "Toshkent"
    best = {}
    for idx, param, grid in [(0, "fajr", [x/2 for x in range(30, 42)]), (5, "isha", [x/2 for x in range(30, 42)]),
                              (1, "rise", [0.5, 0.6, 0.7, 0.8, 0.833, 0.9, 1.0]), (4, "rise", [0.5, 0.6, 0.7, 0.8, 0.833, 0.9, 1.0])]:
        res = []
        for v in grid:
            e = errs(city, idx, **{param: v}); res.append((abs(st.mean(e)) + st.pstdev(e), v, st.mean(e), st.pstdev(e)))
        res.sort(); print(f"{names[idx]:7} {param}: eng yaxshi {res[0][1]}  (o'rtacha siljish {res[0][2]:+.2f} daq, tarqoqlik {res[0][3]:.2f})   2-chi: {res[1][1]}")
        best[(idx, param)] = res[0][1]
    for idx in (2, 3):
        e = errs(city, idx); print(f"{names[idx]:7} standart: siljish {st.mean(e):+.2f} daq, tarqoqlik {st.pstdev(e):.2f}")

if sys.argv[3] == "bad":
    for c in COORD: load(c)
    print("noto'g'ri qatorlar:", len(BAD)); [print(" ", b) for b in BAD[:6]]
