#!/usr/bin/env python3
"""Test ПодготовитьДействие + ВыполнитьДействие for appeal submit."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

appeal_id = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"
read = m.find_appeal({"appeal_id": appeal_id})
doc = read.get("document") or {}
stage_id, stage_name, action_name = m.workflow_stage_from_doc(doc)
print("stage_id:", stage_id, "name:", stage_name, "action:", action_name)

# Staff recipient (Васьков)
staff = {"Идентификатор": "30", "Фамилия": "Васьков", "Имя": "Игорь", "Отчество": "Александрович"}

for label, params in [
    ("direct", {"Документ": {"Идентификатор": appeal_id, "Этап": {"Идентификатор": stage_id, "Действие": [{"Название": action_name}]}}}),
    ("param", {"Параметр": {"Документ": {"Идентификатор": appeal_id, "Этап": {"Идентификатор": stage_id, "Действие": [{"Название": action_name}]}}}}),
]:
    prep = m.rpc("СБИС.ПодготовитьДействие", params)
    err = prep.get("error")
    print(f"\n=== PREPARE {label} ===")
    if err:
        print(json.dumps(err, ensure_ascii=False)[:800])
        continue
    result = prep.get("result") or {}
    if isinstance(result, dict):
        stages = result.get("Этап") or []
        if isinstance(stages, dict):
            stages = [stages]
        print("result keys:", list(result.keys())[:15])
        if stages:
            st0 = stages[0]
            print("stage sample:", json.dumps(st0, ensure_ascii=False)[:1200])
            # Try execute with prepared stage + staff
            st_exec = dict(st0)
            st_exec.setdefault("Действие", [{"Название": action_name, "Комментарий": "test"}])
            st_exec["Исполнитель"] = {"Сотрудник": staff}
            st_exec["СледующийЭтап"] = [{"Исполнитель": [{"Сотрудник": staff}]}]
            ex = m.rpc("СБИС.ВыполнитьДействие", {"Параметр": {"Документ": {"Идентификатор": appeal_id, "Этап": st_exec}}})
            if ex.get("error"):
                print("EXEC error:", json.dumps(ex.get("error"), ensure_ascii=False)[:500])
            else:
                print("EXEC ok:", json.dumps(ex.get("result", {}), ensure_ascii=False)[:500])
