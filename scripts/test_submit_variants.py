#!/usr/bin/env python3
"""Try submit with fixed stage structure."""
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

appeal_id = "d0ed9465-510e-4918-b87b-14eb1215d621"
read = m.find_appeal({"appeal_id": appeal_id})
doc = read.get("document") or {}
stage_id, stage_name, action_name = m.workflow_stage_from_doc(doc)

# Try manager with Сотрудник wrapper + name fields
recipient = {"Идентификатор": "30", "Фамилия": "Васьков", "Имя": "Игорь", "Отчество": "Александрович"}
stage = {
    "Идентификатор": stage_id,
    "Название": stage_name or "Отправка",
    "Действие": [{"Название": action_name, "Комментарий": "test"}],
    "Исполнитель": {"Сотрудник": recipient},
    "СледующийЭтап": [{"Исполнитель": [{"Сотрудник": recipient}]}],
}
resp = m.rpc("СБИС.ВыполнитьДействие", {"Документ": {"Идентификатор": appeal_id, "Этап": stage}})
print("MANAGER:", json.dumps(resp, ensure_ascii=False)[:1500])

# Try department name only
recipient2 = {"Название": "РПК ПИНГВИН, ООО", "Структура": "Управленческая"}
stage2 = {
    "Идентификатор": stage_id,
    "Название": stage_name or "Отправка",
    "Действие": [{"Название": action_name, "Комментарий": "test2"}],
    "Исполнитель": {"Подразделение": recipient2},
    "СледующийЭтап": [{"Исполнитель": [{"Подразделение": recipient2}]}],
}
resp2 = m.rpc("СБИС.ВыполнитьДействие", {"Документ": {"Идентификатор": appeal_id, "Этап": stage2}})
print("DEPT:", json.dumps(resp2, ensure_ascii=False)[:1500])
