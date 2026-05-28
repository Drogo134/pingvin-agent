#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

# Обращение с контрагентом (физлицо) — как в UI
doc = {
    "Регламент": {"Название": m.SBIS_APPEAL_REGULATION_NAME},
    "Примечание": m.build_appeal_note({
        "name": "Иван Тестов",
        "phone": "+79001234567",
        "email": "ivan.test@mail.ru",
        "description": "Нужны визитки 200 шт, дизайн есть",
        "source": "api_test",
    }),
    "Контрагент": {
        "Описание": "Нужны визитки 200 шт, дизайн есть",
        "Телефон": "+79001234567",
        "Email": "ivan.test@mail.ru",
    },
}
r = m.rpc("СБИС.ЗаписатьДокумент", {"Документ": doc})
print("CREATE:", json.dumps(r.get("error") or {"id": (r.get("result") or {}).get("Идентификатор"), "num": (r.get("result") or {}).get("Номер")}, ensure_ascii=False))
if r.get("result"):
    aid = r["result"]["Идентификатор"]
    for mid in ("27850", "223", "3374"):
        ex = m.execute_appeal_action({"appeal_id": aid, "action": "Выполнить", "manager_id": mid, "description": "в работу"})
        print(f"  Выполнить manager={mid}: ok={ex.get('ok')} err={(ex.get('error') or {}).get('message', '')[:80]}")
    ex2 = m.execute_appeal_action({"appeal_id": aid, "action": "Решено", "description": "закрыто тестом"})
    print(f"  Решено: ok={ex2.get('ok')} err={(ex2.get('error') or {}).get('message', '')[:80]}")
