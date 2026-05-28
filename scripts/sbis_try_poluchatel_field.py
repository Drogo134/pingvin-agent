#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = "d0ed9465-510e-4918-b87b-14eb1215d621"
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
sid, sname, act = m.workflow_stage_from_doc(doc)

staff223 = {"Идентификатор": "223", "Фамилия": "Ткачук", "Имя": "Андрей", "Отчество": "Васильевич"}
dept = {"Название": "РПК ПИНГВИН, ООО", "Структура": "Управленческая"}

variants = [
    ("action_poluch_staff", {
        "Идентификатор": sid,
        "Действие": [{"Название": act, "Комментарий": "t", "Получатель": {"Сотрудник": staff223}}],
    }),
    ("action_poluch_dept", {
        "Идентификатор": sid,
        "Действие": [{"Название": act, "Комментарий": "t", "Получатель": {"Подразделение": dept}}],
    }),
    ("stage_poluch_staff", {
        "Идентификатор": sid,
        "Получатель": {"Сотрудник": staff223},
        "Действие": [{"Название": act, "Комментарий": "t"}],
    }),
    ("doc_poluch", None),
]

for name, stage in variants:
    if name == "doc_poluch":
        payload = {"Документ": {
            "Идентификатор": aid,
            "Получатель": {"Сотрудник": staff223},
            "Этап": {"Идентификатор": sid, "Действие": [{"Название": act, "Комментарий": "t"}]},
        }}
    else:
        payload = {"Документ": {"Идентификатор": aid, "Этап": stage}}
    r = m._execute_submit_action(aid, stage) if name != "doc_poluch" else m.rpc("СБИС.ВыполнитьДействие", payload)
    if name == "doc_poluch":
        r = m.rpc("СБИС.ВыполнитьДействие", payload)
    e = r.get("error")
    print(name, "OK" if not e else (e.get("message") or "")[:100])
