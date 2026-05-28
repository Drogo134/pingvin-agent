#!/usr/bin/env python3
"""Повтор: create + submit (все получатели) + execute Выполнить."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m  # noqa: E402

print("=== AUTH ===")
print(json.dumps(m.test_auth(), ensure_ascii=False))

print("\n=== CREATE #87+ ===")
cr = m.create_appeal({
    "name": "Повторная проверка submit",
    "phone": "+79001112233",
    "description": "Тест на выполнение после проверки настроек Saby",
    "service_type": "Визитки",
    "source": "retry_check",
    "channel_id": "retry:submit",
    "auto_submit": False,
})
aid = cr.get("appeal_id")
print(json.dumps({
    "ok": cr.get("ok"),
    "number": cr.get("number"),
    "open_url": cr.get("open_url"),
    "draft": cr.get("draft"),
    "telegram": cr.get("telegram_notify"),
}, ensure_ascii=False, indent=2))

if not aid:
    sys.exit(1)

print("\n=== SUBMIT ATTEMPTS ===")
for label, extra in [
    ("223 Ткачук", {"recipient_mode": "manager", "manager_id": "223"}),
    ("3374 Федоров", {"recipient_mode": "manager", "manager_id": "3374"}),
    ("27850 ИИ Агент", {"recipient_mode": "manager", "manager_id": "27850"}),
    ("dept РПК", {"recipient_mode": "department"}),
    ("auto", {"recipient_mode": "auto"}),
]:
    sub = m.submit_appeal({"appeal_id": aid, "description": "retry", **extra})
    err = sub.get("error")
    msg = err.get("message", str(err))[:90] if isinstance(err, dict) else str(err)[:90]
    print(f"  {label}: submitted={sub.get('submitted')} err={msg or '—'}")
    if sub.get("submitted"):
        print("SUCCESS", json.dumps(sub.get("state"), ensure_ascii=False))
        break

print("\n=== EXECUTE Выполнить ===")
for mid, name in [("223", "Ткачук"), ("3374", "Федоров"), ("27850", "ИИ Агент")]:
    ex = m.execute_appeal_action({
        "appeal_id": aid,
        "action": "Выполнить",
        "manager_id": mid,
        "description": "на выполнение",
    })
    err = ex.get("error") or {}
    msg = err.get("message", "")[:90] if isinstance(err, dict) else ""
    print(f"  {name}: ok={ex.get('ok')} in_cc={ex.get('in_contact_center')} err={msg}")

read = m.find_appeal({"appeal_id": aid})
st = (read.get("document") or {}).get("Состояние") or {}
print("\nФинал:", st.get("Описание") or st.get("Название"), "| draft=", m.is_appeal_draft(st))
