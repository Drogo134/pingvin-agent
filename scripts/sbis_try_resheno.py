#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = sys.argv[1] if len(sys.argv) > 1 else "927781fb-f0a5-491e-a6ba-71b793f671e6"
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
sid, sname, _ = m.workflow_stage_from_doc(doc, prefer_action="Решено")

variants = [
    ("resheno_min", {"Идентификатор": sid, "Действие": [{"Название": "Решено", "Комментарий": "Тест закрытия API"}]}),
    ("resheno_with_name", {"Идентификатор": sid, "Название": sname or "Отправка", "Действие": [{"Название": "Решено", "Комментарий": "Решение: тестовый клиент уведомлён"}]}),
    ("vyponit_id_only", {"Идентификатор": sid, "Действие": [{"Название": "Выполнить", "Комментарий": "t"}], "Исполнитель": {"Сотрудник": {"Идентификатор": "27850"}}, "СледующийЭтап": [{"Исполнитель": [{"Сотрудник": {"Идентификатор": "27850"}}]}]}),
]

for name, stage in variants:
    r = m.rpc("СБИС.ВыполнитьДействие", {"Документ": {"Идентификатор": aid, "Этап": stage}})
    e = r.get("error")
    print(name, "OK" if not e else (e.get("message") or "")[:120])
    if not e and r.get("result"):
        st = (r["result"].get("Состояние") or {})
        print("  ->", st.get("Описание") or st.get("Название"))
