#!/usr/bin/env python3
"""Пробуем методы API для получателей обращений."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = "d0ed9465-510e-4918-b87b-14eb1215d621"
reg_id = "c1ea4f59-0751-464b-9f26-940f958469e0"

methods = [
    ("СБИС.СписокРегламентов", {"Фильтр": {"НашаОрганизация": m._org_filter()}}),
    ("СБИС.СписокРегламентов", {"Параметр": {"Фильтр": {"НашаОрганизация": m._org_filter()}}}),
    ("СБИС.СписокРегламентов", {"Фильтр": {"НашаОрганизация": m._org_filter(), "Название": "Обращение"}}),
    ("СБИС.СписокЗадач", {"Фильтр": {"НашаОрганизация": m._org_filter(), "Навигация": {"РазмерСтраницы": "5", "Страница": "0"}}}),
    ("СБИС.СписокДокументов", {"Фильтр": {
        "НашаОрганизация": m._org_filter(),
        "Тип": m.SBIS_APPEAL_DOC_TYPE,
        "Состояние": "Ожидается отправка",
        "Навигация": {"РазмерСтраницы": "3", "Страница": "0"},
    }}),
    ("CRMClients.ListEmployees", {}),
    ("CRMClients.ListEmployees", {"Параметр": {}}),
    ("CRMLead.insertRecord", {"Лид": {"Название": "probe"}}),
    ("СБИС.ПрочитатьДокумент", {"Документ": {"Идентификатор": aid, "ДопПоля": "Расширение,Этап,Событие"}}),
]

for method, params in methods:
    r = m.rpc(method, params)
    if "error" in r:
        det = (r["error"].get("details") or r["error"].get("message") or "")[:100]
        print(f"{method}: ERR {det}")
    else:
        res = r.get("result")
        s = json.dumps(res, ensure_ascii=False)
        print(f"{method}: OK len={len(s)} -> {s[:400]}")

# Full doc keys
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
print("\n=== ALL TOP KEYS ===", list(doc.keys()))
for k in ("Расширение", "ДопПоля", "Контрагент", "НашаОрганизация", "Регламент", "Событие"):
    if k in doc:
        print(f"\n--- {k} ---")
        print(json.dumps(doc[k], ensure_ascii=False)[:2000])

# Prepare without executor - check response for hints
sid, _, act = m.workflow_stage_from_doc(doc)
prep = m.rpc("СБИС.ПодготовитьДействие", {
    "Документ": {"Идентификатор": aid, "Этап": {"Идентификатор": sid, "Действие": [{"Название": act}]}}
})
if prep.get("result"):
    pr = prep["result"]
    print("\n=== PREPARE extras ===")
    for k in pr:
        if k not in ("Идентификатор", "Примечание", "Тип", "Этап", "Редакция"):
            print(k, ":", json.dumps(pr[k], ensure_ascii=False)[:300])
