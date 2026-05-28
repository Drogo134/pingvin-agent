#!/usr/bin/env python3
"""Отправить все черновики обращений (draft) в Контакт-центр. Требует SBIS_DEPARTMENT_* или SBIS_MANAGER_ID в .env."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import importlib.util

spec = importlib.util.spec_from_file_location("sbis", root / "workspace" / "scripts" / "sbis_api.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

listed = mod.list_appeals({})
if not listed.get("ok"):
    print(json.dumps(listed, ensure_ascii=False, indent=2))
    sys.exit(1)

drafts = [a for a in listed.get("appeals", []) if a.get("draft")]
if not drafts:
    print(json.dumps({"ok": True, "submitted": 0, "message": "No drafts"}, ensure_ascii=False))
    sys.exit(0)

submitted = 0
errors = []
for a in drafts:
    aid = a.get("appeal_id")
    if not aid:
        continue
    r = mod.submit_appeal({"appeal_id": aid, "description": a.get("title") or "OpenClaw backlog submit"})
    if r.get("submitted"):
        submitted += 1
        print(f"OK #{a.get('number')} {aid}", file=sys.stderr)
    else:
        errors.append({"appeal_id": aid, "number": a.get("number"), "result": r})
        print(f"FAIL #{a.get('number')} {aid}: {r}", file=sys.stderr)

out = {"ok": len(errors) == 0, "submitted": submitted, "failed": len(errors), "errors": errors}
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(0 if not errors else 1)
