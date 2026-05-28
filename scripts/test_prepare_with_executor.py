#!/usr/bin/env python3
import json, sys, copy
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
sid, _, act = m.workflow_stage_from_doc(doc)

recipients = [
    ("223", {"Сотрудник": {"Идентификатор": "223", "Фамилия": "Ткачук", "Имя": "Андрей", "Отчество": "Васильевич"}}),
    ("dept", {"Подразделение": {"Идентификатор": "4", "Название": "РПК ПИНГВИН, ООО", "Структура": "Управленческая"}}),
]

for label, exec_obj in recipients:
    stage = {
        "Идентификатор": sid,
        "Действие": [{"Название": act}],
        "Исполнитель": exec_obj,
        "СледующийЭтап": [{"Исполнитель": [exec_obj]}],
    }
    prep = m.rpc("СБИС.ПодготовитьДействие", {"Документ": {"Идентификатор": aid, "Этап": stage}})
    if prep.get("error"):
        print(label, "PREP ERR:", (prep["error"].get("message") or "")[:100])
        continue
    result = prep.get("result") or {}
    stages = result.get("Этап") or []
    if isinstance(stages, dict):
        stages = [stages]
    st = stages[0] if stages else stage
    st = copy.deepcopy(st)
    st.setdefault("Действие", [{"Название": act, "Комментарий": "prep flow"}])
    st["Исполнитель"] = exec_obj
    st["СледующийЭтап"] = [{"Исполнитель": [exec_obj]}]
    ex = m.rpc("СБИС.ВыполнитьДействие", {"Документ": {"Идентификатор": aid, "Этап": st}})
    err = ex.get("error")
    print(label, "EXEC:", (err or {}).get("message", "OK")[:120])
