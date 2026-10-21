import ast, json, re, sys, pathlib
root = pathlib.Path(sys.argv[1])
pat = re.compile(r"^\s*0*(\d+)\s*[-–.)]\s*(.+?)\s*$")
res = {}
for p in sorted(root.rglob("*.py")):
    if "__pycache__" in p.parts: continue
    try: tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError: continue
    blocks = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and "\n" in n.value:
            items = [(int(m.group(1)), m.group(2)) for line in n.value.split("\n") if (m := pat.match(line))]
            if len(items) >= 3: blocks.append(items)
    if blocks: res[str(p.relative_to(root)).replace("\\", "/")] = blocks
print(json.dumps(res, ensure_ascii=False))
