#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"
dept = {"Идентификатор": "4", "Название": "РПК ПИНГВИН, ООО", "Структура": "Управленческая"}
staff223 = {"Идентификатор": "223", "Фамилия": "Ткачук", "Имя": "Андрей", "Отчество": "Васильевич"}

# patch Получатель dept
m.rpc("СБИС.ЗаписатьДокумент", {"Документ": {"Идентификатор": aid, "Получатель": {"Подразделение": dept}}})
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
print("doc keys with recipient:", {k: doc.get(k) for k in ("Получатель", "Подразделение", "Ответственный") if k in doc})

# submit department only (no manager id)
r1 = m.submit_appeal({"appeal_id": aid, "description": "after poluch dept", "recipient_mode": "department"})
print("DEPT submit:", json.dumps({k: r1.get(k) for k in ("ok", "submitted", "error")}, ensure_ascii=False)[:500])

# patch staff 223 as Получатель
m.rpc("СБИС.ЗаписатьДокумент", {"Документ": {"Идентификатор": aid, "Получатель": {"Сотрудник": staff223}}})
read2 = m.find_appeal({"appeal_id": aid})
doc2 = read2.get("document") or {}
print("after staff patch Получатель:", json.dumps(doc2.get("Получатель"), ensure_ascii=False))

# execute only - minimal stage after patch
doc2 = read2.get("document") or {}
sid, sname, act = m.workflow_stage_from_doc(doc2)
stage = {"Идентификатор": sid, "Действие": [{"Название": act, "Комментарий": "exec only"}]}
ex = m.rpc("СБИС.ВыполнитьДействие", {"Документ": {"Идентификатор": aid, "Этап": stage}})
print("EXEC only:", json.dumps(ex.get("error") or {"ok": True}, ensure_ascii=False)[:400])
