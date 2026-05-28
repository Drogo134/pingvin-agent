#!/usr/bin/env python3
"""Автоматически найти подразделения и сотрудников Saby для .env (без ручного поиска в UI)."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m  # noqa: E402


def list_departments() -> list[dict]:
    if not m.SBIS_ORG_INN:
        return []
    filt = {
        "НашаОрганизация": m._org_filter(),
        "Навигация": {"РазмерСтраницы": "100", "Страница": "0"},
    }
    resp = m.rpc("СБИС.СписокПодразделений", {"Параметр": {"Фильтр": filt}})
    if "error" in resp:
        print("Ошибка СписокПодразделений:", json.dumps(resp.get("error"), ensure_ascii=False), file=sys.stderr)
        return []
    result = resp.get("result") or {}
    items = result.get("Подразделение") or result.get("Подразделения") or []
    if isinstance(items, dict):
        items = [items]
    out = []
    for item in items:
        out.append({
            "id": item.get("Идентификатор") or item.get("КодПодразделения") or "",
            "name": item.get("Название") or "",
            "code": item.get("КодПодразделения") or "",
        })
    return [x for x in out if x.get("name")]


def list_staff() -> list[dict]:
    if not m.SBIS_ORG_INN:
        return []
    filt = {
        "НашаОрганизация": m._org_filter(),
        "ВернутьУволенных": "Нет",
        "Навигация": {"РазмерСтраницы": "100", "Страница": "0"},
    }
    resp = m.rpc("СБИС.СписокСотрудников", {"Параметр": {"Фильтр": filt}})
    if "error" in resp:
        print("Ошибка СписокСотрудников:", json.dumps(resp.get("error"), ensure_ascii=False), file=sys.stderr)
        return []
    result = resp.get("result") or {}
    items = result.get("Сотрудник") or result.get("Сотрудники") or []
    if isinstance(items, dict):
        items = [items]
    out = []
    for item in items:
        emp_id = item.get("Идентификатор") or ""
        if not emp_id:
            continue
        fio = " ".join(
            filter(None, [item.get("Фамилия"), item.get("Имя"), item.get("Отчество")])
        ).strip()
        dept = item.get("Подразделение") or {}
        dept_name = dept.get("Название") if isinstance(dept, dict) else ""
        pos = item.get("Должность") or {}
        pos_name = pos.get("Название") if isinstance(pos, dict) else ""
        out.append({
            "id": emp_id,
            "name": fio or item.get("Имя") or "?",
            "department": dept_name,
            "position": pos_name,
            "system_access": (item.get("ДоступВСистему") or "").strip(),
        })
    return out


def suggest_recipient(depts: list[dict], staff: list[dict]) -> dict:
  """Pick best department or manager for appeals queue."""
  keywords = ("контакт", "продаж", "прием", "приём", "клиент", "crm", "реклам")
  for d in depts:
    name = (d.get("name") or "").lower()
    if any(k in name for k in keywords):
      return {"type": "department", "id": d["id"], "name": d["name"], "reason": "keyword match"}

  real_staff = [
      s for s in staff
      if "агент" not in (s.get("name") or "").lower()
      and "ии" not in (s.get("name") or "").lower().split()
  ]
  if depts:
    return {"type": "department", "id": depts[0]["id"], "name": depts[0]["name"], "reason": "first department"}
  if real_staff:
    s = real_staff[0]
    return {"type": "manager", "id": s["id"], "name": s["name"], "reason": "first real employee"}
  return {}


def main() -> int:
    auth = m.test_auth()
    if not auth.get("ok"):
        print(json.dumps(auth, ensure_ascii=False, indent=2))
        return 1

    print("=== Saby: что нашли через API (ручной поиск в UI не нужен) ===\n")

    depts = list_departments()
    staff = list_staff()

    print(f"Подразделений: {len(depts)}")
    for d in depts[:20]:
        print(f"  • {d['name']}")
        if d.get("id"):
            print(f"    SBIS_DEPARTMENT_ID={d['id']}")
    if len(depts) > 20:
        print(f"  ... ещё {len(depts) - 20}")

    print(f"\nСотрудников (без уволенных): {len(staff)}")
    for s in staff[:15]:
        extra = f" ({s['department']})" if s.get("department") else ""
        access = s.get("system_access") or "?"
        print(f"  • {s['name']}{extra} — доступ в Saby: {access}")
        print(f"    SBIS_MANAGER_ID={s['id']}")
    if len(staff) > 15:
        print(f"  ... ещё {len(staff) - 15}")

    sug = suggest_recipient(depts, staff)
    print("\n=== Рекомендация для .env ===")
    if not sug:
        print("Не удалось автоматически подобрать получателя.")
        print("Попросите администратора Saby дать UUID подразделения или менеджера.")
        return 1

    agent = next((s for s in staff if "агент" in (s.get("name") or "").lower()), None)
    if agent:
        print("Для API-бота используйте учётку агента (не других сотрудников):")
        print(f"  SBIS_MANAGER_ID={agent['id']}  # {agent['name']}")
        print("  SBIS_RECIPIENT_MODE=manager")
        print()

    if sug["type"] == "department":
        print(f"Вариант A (общая очередь): подразделение «{sug['name']}» ({sug['reason']})")
        print("  ⚠ ID из СписокПодразделений может не работать на этапе «Отправка» — проверьте submit.")
        print()
        print("SBIS_RECIPIENT_MODE=auto")
        print(f"SBIS_DEPARTMENT_NAME={sug['name']}")
        if sug.get("id"):
            print(f"# SBIS_DEPARTMENT_ID={sug['id']}  # часто только для кадров, не для документооборота")
        print("SBIS_AUTO_SUBMIT=true")
    else:
        print(f"Вариант B (конкретный менеджер): {sug['name']} ({sug['reason']})")
        print()
        print("SBIS_RECIPIENT_MODE=manager")
        print(f"SBIS_MANAGER_ID={sug['id']}")
        print("SBIS_AUTO_SUBMIT=true")

    print("\nПосле правки .env:")
    print("  .\\scripts\\start-local.ps1")
    print("  python scripts\\sbis_submit_drafts.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
