#!/usr/bin/env python3
"""Проверка всех кандидатов в получатели на одном черновике."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m  # noqa: E402

aid = sys.argv[1] if len(sys.argv) > 1 else None
if not aid:
    r = m.create_appeal({
        "name": "Тест получателя",
        "phone": "+79001112233",
        "description": "Проверка очереди получателей",
        "service_type": "Тест",
        "source": "recipient_probe",
        "channel_id": "test:recipient",
        "auto_submit": False,
    })
    aid = r.get("appeal_id")
    print("created", r.get("number"), aid, r.get("open_url"))

dept = {"Название": "РПК ПИНГВИН, ООО", "Структура": "Управленческая"}

tests = [
    ("manager 27850 ИИ Агент", {"recipient_mode": "manager", "manager_id": "27850"}),
    ("manager 223 Ткачук", {"recipient_mode": "manager", "manager_id": "223"}),
    ("manager 3374 Федоров", {"recipient_mode": "manager", "manager_id": "3374"}),
    ("manager 30 Васьков", {"recipient_mode": "manager", "manager_id": "30"}),
    ("department name", {"recipient_mode": "department", "department_name": dept["Название"]}),
    ("auto", {"recipient_mode": "auto"}),
]

for label, extra in tests:
    sub = m.submit_appeal({"appeal_id": aid, "description": "submit test", **extra})
    err = sub.get("error")
    msg = err.get("message", str(err))[:90] if isinstance(err, dict) else str(err)[:90]
    print(
        f"{label}: submitted={sub.get('submitted')} draft={sub.get('draft')} "
        f"mode={sub.get('recipient_mode')} err={msg or '—'}"
    )
    if sub.get("submitted"):
        print("SUCCESS", json.dumps(sub.get("state"), ensure_ascii=False))
        break

read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
print("\nfinal state:", (doc.get("Состояние") or {}).get("Описание"))
