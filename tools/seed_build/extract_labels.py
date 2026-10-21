import ast, json, sys, pathlib
root = pathlib.Path(sys.argv[1])
res = {}
for p in sorted((root / "keyboards").rglob("*.py")):
    if "__pycache__" in p.parts: continue
    try: tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError: continue
    pairs = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) in ("InlineKeyboardButton", "KeyboardButton"):
            kw = {k.arg: k.value for k in n.keywords}
            t = kw.get("text") or (n.args[0] if n.args else None)
            cb = kw.get("callback_data")
            if isinstance(t, ast.Constant):
                pairs.append([t.value, cb.value if isinstance(cb, ast.Constant) else None])
    if pairs: res[str(p.relative_to(root)).replace("\\", "/")] = pairs
print(json.dumps(res, ensure_ascii=False))
