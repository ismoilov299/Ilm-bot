import ast, json, sys, pathlib
from collections import defaultdict

root = pathlib.Path(sys.argv[1])
out = defaultdict(list)  # file -> [{trigger, kind, message_ids, chats}]
for p in sorted(root.rglob("*.py")):
    if "__pycache__" in p.parts:
        continue
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        continue
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        triggers = []
        for d in fn.decorator_list:
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in ("message_handler", "callback_query_handler"):
                for kw in d.keywords:
                    if kw.arg in ("text", "text_contains") and isinstance(kw.value, ast.Constant):
                        triggers.append((d.func.attr, kw.value.value))
        ids, chats = [], set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "copy_message":
                kws = {k.arg: k.value for k in n.keywords}
                if isinstance(kws.get("message_id"), ast.Constant):
                    ids.append(kws["message_id"].value)
                if isinstance(kws.get("from_chat_id"), ast.Constant):
                    chats.add(kws["from_chat_id"].value)
        if ids:
            for kind, t in triggers or [("?", fn.name)]:
                out[str(p.relative_to(root))].append({"kind": kind, "trigger": t, "message_ids": ids, "chats": sorted(chats)})
print(json.dumps(out, ensure_ascii=False, indent=1))
