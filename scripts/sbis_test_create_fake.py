#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Создать обращение с выдуманными данными + submit с fallback (агент → подразделение)."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m  # noqa: E402

fake = {
    "name": "Мария Тестова",
    "phone": "+7 (926) 555-12-34",
    "email": "maria.test@example.ru",
    "description": "Нужны визитки 500 шт, двусторонние, срочно к пятнице. Тест OpenClaw.",
    "service_type": "Визитки",
    "source": "telegram",
    "channel_id": "tg_fake_20260525_001",
    "auto_submit": True,
    "recipient_mode": "auto",
}

print("=== Fallback chain ===")
for i, (rec, mode) in enumerate(m.submit_recipient_attempts(fake), 1):
    print(f"  {i}. {mode}: {json.dumps(rec, ensure_ascii=False)}")

print("\n=== CREATE + AUTO SUBMIT ===")
r = m.create_appeal(fake)
out = {
    "ok": r.get("ok"),
    "appeal_id": r.get("appeal_id"),
    "number": r.get("number"),
    "draft": r.get("draft"),
    "visible_in_crm": r.get("visible_in_crm"),
    "open_url": r.get("open_url"),
    "warning": r.get("warning"),
}
sub = r.get("submit") or {}
if sub:
    out["submit"] = {
        "ok": sub.get("ok"),
        "submitted": sub.get("submitted"),
        "recipient_mode": sub.get("recipient_mode"),
        "submit_attempts": sub.get("submit_attempts"),
        "attempts": (sub.get("error") or {}).get("attempts") if not sub.get("submitted") else None,
        "error": (sub.get("error") or {}).get("message") if isinstance(sub.get("error"), dict) else sub.get("error"),
        "state": sub.get("state"),
        "draft": sub.get("draft"),
    }
print(json.dumps(out, ensure_ascii=False, indent=2))

if r.get("appeal_id"):
    read = m.find_appeal({"appeal_id": r["appeal_id"]})
    doc = read.get("document") or {}
    st = doc.get("Состояние") or {}
    print("\nСостояние:", st.get("Описание") or st.get("Название"), "| draft=", m.is_appeal_draft(st))
