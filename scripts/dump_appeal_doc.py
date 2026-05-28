#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
# keys of interest
for k in ("Ответственный", "Получатель", "Подразделение", "Исполнитель", "Регламент", "Состояние", "Этап"):
    if k in doc:
        print(f"=== {k} ===")
        print(json.dumps(doc[k], ensure_ascii=False, indent=2)[:2000])

prep = m.rpc("СБИС.ПодготовитьДействие", {
    "Документ": {"Идентификатор": aid, "Этап": {"Идентификатор": m.workflow_stage_from_doc(doc)[0], "Действие": [{"Название": "Выполнить"}]}}
})
r = prep.get("result") or {}
print("\n=== PREPARE top keys ===", list(r.keys()))
for k in ("Ответственный", "Получатель", "Этап"):
    if k in r:
        print(f"--- prep {k} ---")
        print(json.dumps(r[k], ensure_ascii=False, indent=2)[:2500])
