#!/usr/bin/env python3
"""Patch appeal with Получатель/Ответственный then submit."""
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"
staff = {"Идентификатор": "30", "Фамилия": "Васьков", "Имя": "Игорь", "Отчество": "Александрович"}
dept = {"Идентификатор": "4", "Название": "РПК ПИНГВИН, ООО", "Структура": "Управленческая"}

for label, patch in [
    ("resp", {"Идентификатор": aid, "Ответственный": staff}),
    ("poluch", {"Идентификатор": aid, "Получатель": {"Сотрудник": staff}}),
    ("poluch_dept", {"Идентификатор": aid, "Получатель": {"Подразделение": dept}}),
    ("both", {"Идентификатор": aid, "Ответственный": staff, "Получатель": {"Сотрудник": staff}, "Подразделение": dept}),
]:
    w = m.rpc("СБИС.ЗаписатьДокумент", {"Документ": patch})
    err = w.get("error")
    print(f"WRITE {label}:", "OK" if not err else err.get("message", err)[:100])
    if err:
        continue
    r = m.submit_appeal({"appeal_id": aid, "description": f"patch {label}", "recipient_mode": "manager", "manager_id": "30"})
    print(f"  SUBMIT:", r.get("ok"), (r.get("error") or {}).get("message", r.get("submitted")))
