#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Кто в списке сотрудников API и к какой организации привязан."""
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

print("Организация в .env: ИНН", m.SBIS_ORG_INN, "—", m.SBIS_DEPARTMENT_NAME)
print()

sfilt = {
    "НашаОрганизация": m._org_filter(),
    "ВернутьУволенных": "Нет",
    "Навигация": {"РазмерСтраницы": "100", "Страница": "0"},
}
resp = m.rpc("СБИС.СписокСотрудников", {"Параметр": {"Фильтр": sfilt}})
staff = (resp.get("result") or {}).get("Сотрудник") or []
if isinstance(staff, dict):
    staff = [staff]

with_access = []
for item in staff:
    access = (item.get("ДоступВСистему") or "").strip()
    dept = item.get("Подразделение") or {}
    dept_name = dept.get("Название") if isinstance(dept, dict) else ""
    fio = " ".join(filter(None, [item.get("Фамилия"), item.get("Имя"), item.get("Отчество")]))
    if access.lower() == "да":
        with_access.append((item.get("Идентификатор"), fio, dept_name, item.get("Логин", "")))

print(f"Всего сотрудников по фильтру организации: {len(staff)}")
print(f"С доступом в Saby: {len(with_access)}\n")
for eid, fio, dept, login in with_access:
    print(f"  id={eid}  {fio}")
    print(f"         подразделение: {dept or '(пусто)'}  логин: {login or '(нет)'}")
    print()

# Права ai_agent
r = m.rpc("СБИС.ПрочитатьСотрудника", {"Параметр": {"Сотрудник": {"Идентификатор": "27850"}}})
roles = ((r.get("result") or {}).get("Права") or {}).get("Роли") or []
print("ИИ Агент (27850) — роли в Saby:")
for role in roles:
    print(" ", role.get("Название"))
