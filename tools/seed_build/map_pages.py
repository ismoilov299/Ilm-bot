import ast, json, re, sys, pathlib
root = pathlib.Path(sys.argv[1])
pat = re.compile(r"^\s*0*(\d+)\s*[-–.)]\s*(.+?)\s*$")

# 1) klaviatura nomi -> [callback_data, ...] (faqat raqamli tugmalar), barcha keyboards/inline fayllaridan
kbs = {}
for p in (root / "keyboards" / "inline").glob("*.py"):
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            cbs = []
            for c in ast.walk(n.value):
                if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "InlineKeyboardButton":
                    kw = {k.arg: k.value for k in c.keywords}
                    t, cb = kw.get("text"), kw.get("callback_data")
                    if isinstance(t, ast.Constant) and isinstance(cb, ast.Constant) and re.fullmatch(r"(duo|zikr|salovat)\d+", cb.value):
                        cbs.append(cb.value)
            if cbs: kbs[n.targets[0].id] = cbs

# 2) handlerlar: ro'yxat matni + reply_markup nomi
names = {}
for f in ["duo.py", "zikr.py", "salovat.py"]:
    tree = ast.parse((root / "keyboards" / "send_data" / f).read_text(encoding="utf-8"))
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.AsyncFunctionDef, ast.FunctionDef)): continue
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "answer":
                kw = {k.arg: k.value for k in c.keywords}
                rm = kw.get("reply_markup")
                txt = c.args[0] if c.args else None
                if isinstance(txt, ast.Constant) and isinstance(rm, ast.Name) and rm.id in kbs:
                    items = [(int(m.group(1)), m.group(2)) for line in txt.value.split("\n") if (m := pat.match(line))]
                    if items:
                        for (num, title), cb in zip(items, kbs[rm.id]):
                            names.setdefault(cb, title)
out = {k: names[k] for k in sorted(names, key=lambda s: (re.sub(r"\d+", "", s), int(re.sub(r"\D", "", s))))}
print(json.dumps({"keyboards": {k: len(v) for k, v in kbs.items()}, "names": out}, ensure_ascii=False, indent=0))
