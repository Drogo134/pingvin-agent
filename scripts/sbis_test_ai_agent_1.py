#!/usr/bin/env python3
"""Тест учётки ai_agent_1: auth, create, submit, execute."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))

# Задайте в shell: $env:SBIS_LOGIN='ai_agent_1'; $env:SBIS_PASSWORD='...'
if not os.environ.get("SBIS_LOGIN"):
    print("Set SBIS_LOGIN and SBIS_PASSWORD for ai_agent_1", file=sys.stderr)
    sys.exit(1)

import importlib
import sbis_api as m

importlib.reload(m)
m.TOKEN_CACHE.unlink(missing_ok=True)

print("=== AUTH ===")
print(json.dumps(m.test_auth(), ensure_ascii=False, indent=2))

print("\n=== CURRENT USER ===")
r = m.rpc("СБИС.ИнформацияОТекущемПользователе", {})
if r.get("result"):
    print(json.dumps(r["result"], ensure_ascii=False, indent=2)[:2000])
else:
    print("ERR:", json.dumps(r.get("error"), ensure_ascii=False)[:300])

print("\n=== STAFF (agent in name) ===")
sfilt = {
    "НашаОрганизация": m._org_filter(),
    "ВернутьУволенных": "Нет",
    "Навигация": {"РазмерСтраницы": "100", "Страница": "0"},
}
sresp = m.rpc("СБИС.СписокСотрудников", {"Параметр": {"Фильтр": sfilt}})
items = (sresp.get("result") or {}).get("Сотрудник") or []
if isinstance(items, dict):
    items = [items]
for item in items:
    fio = " ".join(filter(None, [item.get("Фамилия"), item.get("Имя"), item.get("Отчество")]))
    low = fio.lower()
    if "агент" in low or "agent" in low:
        print(
            f"  id={item.get('Идентификатор')} {fio} "
            f"access={item.get('ДоступВСистему')}"
        )

print("\n=== CREATE + AUTO SUBMIT ===")
cr = m.create_appeal({
    "name": "Тест ai_agent_1",
    "phone": "+79005556677",
    "description": "Учётка ai_agent_1 — сняты ограничения",
    "service_type": "Визитки",
    "source": "ai_agent_1_test",
    "channel_id": "test:ai_agent_1",
    "auto_submit": True,
    "notify_managers": False,
})
print(json.dumps({
    "number": cr.get("number"),
    "appeal_id": cr.get("appeal_id"),
    "open_url": cr.get("open_url"),
    "draft": cr.get("draft"),
    "visible_in_crm": cr.get("visible_in_crm"),
    "submit_ok": (cr.get("submit") or {}).get("submitted"),
    "submit_error": (
        ((cr.get("submit") or {}).get("error") or {}).get("message")
        if isinstance((cr.get("submit") or {}).get("error"), dict)
        else (cr.get("submit") or {}).get("error")
    ),
}, ensure_ascii=False, indent=2))

aid = cr.get("appeal_id")
if aid:
    print("\n=== EXECUTE Выполнить ===")
    for mid, name in [("223", "Ткачук"), ("3374", "Федоров"), ("27850", "ИИ Агент")]:
        ex = m.execute_appeal_action({
            "appeal_id": aid,
            "action": "Выполнить",
            "manager_id": mid,
            "description": "ai_agent_1 test",
        })
        err = ex.get("error") or {}
        msg = err.get("message", "")[:80] if isinstance(err, dict) else ""
        print(f"  {name} ({mid}): ok={ex.get('ok')} in_cc={ex.get('in_contact_center')} err={msg}")
