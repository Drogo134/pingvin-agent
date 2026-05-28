#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

appeal_id = "d0ed9465-510e-4918-b87b-14eb1215d621"
read = m.find_appeal({"appeal_id": appeal_id})
doc = read.get("document") or {}
sid, sname, act = m.workflow_stage_from_doc(doc)
dept = {"Идентификатор": "4", "Название": "РПК ПИНГВИН, ООО"}
staff = {"Идентификатор": "30", "Фамилия": "Васьков", "Имя": "Игорь", "Отчество": "Александрович"}

variants = [
    ("dept_next", {
        "Идентификатор": sid, "Действие": [{"Название": act, "Комментарий": "t"}],
        "СледующийЭтап": [{"Исполнитель": [{"Подразделение": dept}]}],
    }),
    ("dept_exec", {
        "Идентификатор": sid, "Действие": [{"Название": act, "Комментарий": "t"}],
        "Исполнитель": {"Подразделение": dept},
        "СледующийЭтап": [{"Исполнитель": [{"Подразделение": dept}]}],
    }),
    ("staff_next", {
        "Идентификатор": sid, "Действие": [{"Название": act, "Комментарий": "t"}],
        "СледующийЭтап": [{"Исполнитель": [{"Сотрудник": staff}]}],
    }),
    ("doc_poluchatel_dept", None),  # special
]

for name, stage in variants:
    if name == "doc_poluchatel_dept":
        payload = {"Документ": {
            "Идентификатор": appeal_id,
            "Получатель": {"Подразделение": dept},
            "Этап": {"Идентификатор": sid, "Действие": [{"Название": act}]},
        }}
    else:
        payload = {"Документ": {"Идентификатор": appeal_id, "Этап": stage}}
    r = m.rpc("СБИС.ВыполнитьДействие", payload)
    e = r.get("error")
    print(name, "OK" if not e else e.get("message", str(e))[:120])
