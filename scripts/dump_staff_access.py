#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

filt = {
    "НашаОрганизация": m._org_filter(),
    "ВернутьУволенных": "Нет",
    "Навигация": {"РазмерСтраницы": "100", "Страница": "0"},
}
resp = m.rpc("СБИС.СписокСотрудников", {"Параметр": {"Фильтр": filt}})
items = (resp.get("result") or {}).get("Сотрудник") or []
if isinstance(items, dict):
    items = [items]
with_access = [i for i in items if (i.get("ДоступВСистему") or "").lower() in ("да", "yes", "true", "1")]
print(f"total={len(items)} with_system_access={len(with_access)}")
for i in with_access:
    print(json.dumps({
        "id": i.get("Идентификатор"),
        "fio": f"{i.get('Фамилия')} {i.get('Имя')} {i.get('Отчество')}".strip(),
        "access": i.get("ДоступВСистему"),
        "tab": i.get("ТабельныйНомер"),
    }, ensure_ascii=False))
