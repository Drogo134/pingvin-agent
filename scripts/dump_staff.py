#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m
filt = {
    "НашаОрганизация": m._org_filter(),
    "ВернутьУволенных": "Нет",
    "Навигация": {"РазмерСтраницы": "5", "Страница": "0"},
}
resp = m.rpc("СБИС.СписокСотрудников", {"Параметр": {"Фильтр": filt}})
items = (resp.get("result") or {}).get("Сотрудник") or []
if isinstance(items, dict):
    items = [items]
for item in items[:3]:
    print(json.dumps(item, ensure_ascii=False, indent=2)[:2000])
    print("---")
