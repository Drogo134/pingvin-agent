#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

def read_emp(eid: str) -> dict:
    r = m.rpc("СБИС.ПрочитатьСотрудника", {"Параметр": {"Сотрудник": {"Идентификатор": eid}}})
    return (r.get("result") or {}).get("Сотрудник") or r.get("result") or {}

for eid in ("223", "3374", "27850"):
    emp = read_emp(eid)
    keys = [k for k in emp if "идентиф" in k.lower() or "uuid" in k.lower() or "пользов" in k.lower()]
    print(f"\n=== {eid} {emp.get('Фамилия')} {emp.get('Имя')} access={emp.get('ДоступВСистему')} ===")
    for k in keys:
        print(f"  {k}: {emp.get(k)}")
    # full dump id-related
    subset = {k: emp[k] for k in emp if any(x in k for x in ("Идент", "Внешн", "Табель", "Логин", "User"))}
    print(json.dumps(subset, ensure_ascii=False, indent=2))
