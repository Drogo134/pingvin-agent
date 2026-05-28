#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Эксперименты: создать обращение, действия Выполнить/Решено, получатель 27850."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m  # noqa: E402

FAKE = {
    "name": "Тестов Клиент OpenClaw",
    "phone": "+7 (495) 000-00-99",
    "email": "test.client@example.com",
    "description": "Тест API: визитки 500 шт, срочно. Выдуманные данные.",
    "service_type": "Визитки",
    "source": "telegram_test",
    "channel_id": "tg_999888777",
    "auto_submit": False,
}


def exec_action(appeal_id: str, action_name: str, recipient: dict | None, mode: str) -> dict:
    read = m.find_appeal({"appeal_id": appeal_id})
    doc = read.get("document") or {}
    stages = doc.get("Этап") or []
    if isinstance(stages, dict):
        stages = [stages]
    st = stages[0] if stages else {}
    sid = str(st.get("Идентификатор") or "")
    stage: dict = {
        "Идентификатор": sid,
        "Название": st.get("Название") or "Отправка",
        "Действие": [{"Название": action_name, "Комментарий": f"API test {action_name}"}],
    }
    if recipient and action_name == "Выполнить":
        if mode == "manager":
            emp = recipient if recipient.get("Фамилия") else m.read_employee_ref(str(recipient.get("Идентификатор", "")))
            ref = {"Сотрудник": emp}
        else:
            ref = {"Подразделение": recipient}
        stage["Исполнитель"] = ref
        stage["СледующийЭтап"] = [{"Исполнитель": [ref]}]
    r = m._execute_submit_action(appeal_id, stage)
    err = r.get("error")
    return {"action": action_name, "ok": "error" not in r, "error": (err or {}).get("message"), "state": (r.get("result") or {}).get("Состояние")}


print("=== 1. CREATE (выдуманный клиент, без auto_submit) ===")
cr = m.create_appeal(FAKE)
print(json.dumps({k: cr.get(k) for k in ("ok", "appeal_id", "number", "draft", "open_url", "error", "warning")}, ensure_ascii=False, indent=2))
if not cr.get("ok"):
    sys.exit(1)
aid = cr["appeal_id"]

agent = m.read_employee_ref("27850")
staff223 = m.read_employee_ref("223")
print("\nИИ Агент из API:", json.dumps(agent, ensure_ascii=False))
print("Ткачук из API:", json.dumps(staff223, ensure_ascii=False))

tests = [
    ("Выполнить + agent 27850", "Выполнить", agent, "manager"),
    ("Выполнить + 223", "Выполнить", staff223, "manager"),
    ("Решено (без получателя)", "Решено", None, ""),
]

print("\n=== 2. ДЕЙСТВИЯ на черновике", aid, "===")
for label, act, rec, mode in tests:
    # re-read — предыдущее действие могло изменить doc
    res = exec_action(aid, act, rec, mode)
    state = res.get("state") or {}
    print(f"{label}: ok={res['ok']} err={res.get('error', '')[:90]}")
    if state:
        print(f"  state: {state.get('Название')} / {state.get('Описание')} code={state.get('Код')}")
    if res.get("ok"):
        print("  >>> УСПЕХ — дальше тесты на этом id могут не сработать")
        break

print("\n=== 3. READ final ===")
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
print("Состояние:", json.dumps(doc.get("Состояние"), ensure_ascii=False))
print("Ответственный:", json.dumps(doc.get("Ответственный"), ensure_ascii=False))
stages = doc.get("Этап") or []
if isinstance(stages, dict):
    stages = [stages]
for st in stages:
    print("Этап:", st.get("Название"), "actions:", [a.get("Название") for a in (st.get("Действие") or [])])
