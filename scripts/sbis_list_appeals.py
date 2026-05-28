#!/usr/bin/env python3
"""Показать обращения в Saby (включая черновики) и ссылки на открытие в браузере."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import importlib.util

spec = importlib.util.spec_from_file_location("sbis", root / "workspace" / "scripts" / "sbis_api.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

result = mod.list_appeals({})
print(json.dumps(result, ensure_ascii=False, indent=2))

if result.get("ok") and result.get("appeals"):
    print("\n--- Кратко ---", file=sys.stderr)
    for a in result["appeals"]:
        flag = "ЧЕРНОВИК" if a.get("draft") else "в работе"
        print(
            f"  №{a.get('number')} [{flag}] {a.get('title')}\n"
            f"    {a.get('open_url')}",
            file=sys.stderr,
        )

sys.exit(0 if result.get("ok") else 1)
