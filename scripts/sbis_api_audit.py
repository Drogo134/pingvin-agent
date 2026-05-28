#!/usr/bin/env python3
"""Полная диагностика Saby API: права, черновики, submit, create."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m  # noqa: E402

report: dict = {"auth": None, "env": {}, "staff_with_access": [], "departments": [], "drafts": [], "tests": {}}


def ok(msg: str) -> None:
    print(f"OK  {msg}")


def fail(msg: str, detail: str = "") -> None:
    print(f"FAIL {msg}")
    if detail:
        print(f"     {detail[:300]}")


print("=== SBIS API AUDIT ===\n")

# Auth
auth = m.test_auth()
report["auth"] = auth
if auth.get("ok"):
    ok("Аутентификация")
else:
    fail("Аутентификация", json.dumps(auth, ensure_ascii=False))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1)

report["env"] = {
    "login": m.SBIS_LOGIN,
    "recipient_mode": m.SBIS_RECIPIENT_MODE,
    "department_id": m.SBIS_DEPARTMENT_ID,
    "department_name": m.SBIS_DEPARTMENT_NAME,
    "manager_id": m.SBIS_MANAGER_ID,
    "org_inn": m.SBIS_ORG_INN,
    "auto_submit": m.SBIS_AUTO_SUBMIT,
}
print("\n--- .env (из sbis_api) ---")
for k, v in report["env"].items():
    print(f"  {k} = {v or '(пусто)'}")

# Departments
if m.SBIS_ORG_INN:
    filt = {
        "НашаОрганизация": m._org_filter(),
        "Навигация": {"РазмерСтраницы": "50", "Страница": "0"},
    }
    dresp = m.rpc("СБИС.СписокПодразделений", {"Параметр": {"Фильтр": filt}})
    if "error" in dresp:
        fail("СписокПодразделений", json.dumps(dresp["error"], ensure_ascii=False))
    else:
        items = (dresp.get("result") or {}).get("Подразделение") or []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            report["departments"].append({
                "id": item.get("Идентификатор") or item.get("КодПодразделения"),
                "name": item.get("Название"),
                "code": item.get("КодПодразделения"),
            })
        ok(f"Подразделений: {len(report['departments'])}")

# Staff + access
if m.SBIS_ORG_INN:
    sfilt = {
        "НашаОрганизация": m._org_filter(),
        "ВернутьУволенных": "Нет",
        "Навигация": {"РазмерСтраницы": "100", "Страница": "0"},
    }
    sresp = m.rpc("СБИС.СписокСотрудников", {"Параметр": {"Фильтр": sfilt}})
    if "error" in sresp:
        fail("СписокСотрудников", json.dumps(sresp["error"], ensure_ascii=False))
    else:
        staff = (sresp.get("result") or {}).get("Сотрудник") or []
        if isinstance(staff, dict):
            staff = [staff]
        for item in staff:
            access = (item.get("ДоступВСистему") or "").strip()
            rec = {
                "id": item.get("Идентификатор"),
                "name": " ".join(filter(None, [item.get("Фамилия"), item.get("Имя"), item.get("Отчество")])),
                "access": access,
                "login": item.get("Логин", ""),
            }
            if access.lower() == "да":
                report["staff_with_access"].append(rec)
        ok(f"Сотрудников: {len(staff)}, с доступом в Saby: {len(report['staff_with_access'])}")

print("\n--- Сотрудники с доступом в Saby ---")
for s in report["staff_with_access"]:
    print(f"  id={s['id']} login={s.get('login')} {s['name']}")

# Read ai_agent employee rights
for eid in [m.SBIS_MANAGER_ID or "223", "27850"]:
    if not eid:
        continue
    r = m.rpc("СБИС.ПрочитатьСотрудника", {"Параметр": {"Сотрудник": {"Идентификатор": str(eid)}}})
    if "error" in r:
        report["tests"][f"read_employee_{eid}"] = r.get("error")
        fail(f"ПрочитатьСотрудника {eid}", (r["error"].get("message") or "")[:120])
    else:
        emp = (r.get("result") or {}).get("Сотрудник") or {}
        roles = ((r.get("result") or {}).get("Права") or {}).get("Роли") or []
        role_names = [x.get("Название") for x in roles if isinstance(x, dict)]
        report["tests"][f"read_employee_{eid}"] = {
            "name": f"{emp.get('Фамилия')} {emp.get('Имя')}",
            "access": emp.get("ДоступВСистему"),
            "roles": role_names[:8],
        }
        ok(f"Сотрудник {eid}: {emp.get('Фамилия')} {emp.get('Имя')}, роли: {', '.join(role_names[:5]) or '—'}")

# List appeals
listed = m.list_appeals({"limit": 20})
report["list_appeals"] = {"ok": listed.get("ok"), "count": listed.get("count"), "drafts": listed.get("drafts")}
if listed.get("ok"):
    ok(f"Список обращений: {listed.get('count')}, черновиков: {listed.get('drafts')}")
    for a in listed.get("appeals", [])[:10]:
        if a.get("draft"):
            report["drafts"].append({
                "number": a.get("number"),
                "appeal_id": a.get("appeal_id"),
                "title": a.get("title"),
            })
            print(f"  draft #{a.get('number')} {a.get('appeal_id')}")
else:
    fail("СписокДокументов", json.dumps(listed.get("error"), ensure_ascii=False))

# Test submit on first draft
if report["drafts"]:
    aid = report["drafts"][0]["appeal_id"]
    read = m.find_appeal({"appeal_id": aid})
    doc = read.get("document") or {}
    report["sample_doc"] = {
        "Ответственный": doc.get("Ответственный"),
        "Подразделение": doc.get("Подразделение"),
        "Получатель": doc.get("Получатель"),
        "Состояние": doc.get("Состояние"),
    }
    print(f"\n--- Документ {aid} (ключевые поля) ---")
    print(json.dumps(report["sample_doc"], ensure_ascii=False, indent=2))

    # Try submit modes
    tests = []
    if m.SBIS_DEPARTMENT_NAME or m.SBIS_DEPARTMENT_ID:
        tests.append(("department_env", {"appeal_id": aid, "description": "audit dept", "recipient_mode": "department"}))
    if m.SBIS_MANAGER_ID:
        tests.append(("manager_env", {"appeal_id": aid, "description": "audit mgr", "recipient_mode": "manager", "manager_id": m.SBIS_MANAGER_ID}))
    for s in report["staff_with_access"]:
        if "агент" in (s.get("name") or "").lower():
            continue
        tests.append((f"manager_{s['id']}", {"appeal_id": aid, "description": "audit", "recipient_mode": "manager", "manager_id": s["id"]}))
        break  # one real manager

    print("\n--- Тест submit (один черновик) ---")
    for label, data in tests:
        sub = m.submit_appeal(data)
        err = (sub.get("error") or {})
        msg = err.get("message") if isinstance(err, dict) else str(err)
        report["tests"][f"submit_{label}"] = {"ok": sub.get("ok"), "submitted": sub.get("submitted"), "message": msg, "hint": sub.get("hint")}
        if sub.get("submitted"):
            ok(f"submit {label}")
        else:
            fail(f"submit {label}", msg or json.dumps(sub, ensure_ascii=False)[:200])

# Test minimal create + submit
print("\n--- Тест create (без подразделения) + submit ---")
cr = m.create_appeal({
    "description": "API audit test",
    "recipient_mode": "manager",
    "manager_id": (report["staff_with_access"][1]["id"] if len(report["staff_with_access"]) > 1 else report["staff_with_access"][0]["id"]) if report["staff_with_access"] else m.SBIS_MANAGER_ID,
    "auto_submit": True,
    "department_id": "",
    "department_name": "",
})
if cr.get("ok"):
    ok(f"create appeal_id={cr.get('appeal_id')} draft={cr.get('draft')}")
    subinfo = cr.get("submit") or {}
    report["tests"]["create_auto_submit"] = subinfo
    if subinfo.get("submitted"):
        ok("auto submit после create")
    else:
        fail("auto submit после create", (subinfo.get("error") or subinfo.get("hint") or json.dumps(subinfo))[:200])
else:
    err = cr.get("error") or cr
    report["tests"]["create"] = err
    fail("create", json.dumps(err, ensure_ascii=False)[:200])

out_path = root / "scripts" / "sbis_audit_report.json"
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n=== Отчёт сохранён: {out_path} ===")
