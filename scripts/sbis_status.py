#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Краткий статус Saby API на русском — запуск: python scripts/sbis_status.py"""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m  # noqa: E402

print("=" * 60)
print("  SBIS / Saby — статус интеграции OpenClaw")
print("=" * 60)

auth = m.test_auth()
print(f"\n1. Авторизация ({m.SBIS_LOGIN}):", "OK" if auth.get("ok") else "ОШИБКА")

print("\n2. Настройки .env:")
print(f"   Режим получателя: {m.SBIS_RECIPIENT_MODE}")
print(f"   Подразделение:  {m.SBIS_DEPARTMENT_NAME or '—'} (id={m.SBIS_DEPARTMENT_ID or 'не задан'})")
print(f"   Менеджер:       {m.SBIS_MANAGER_ID or 'не задан'}")
print(f"   Авто-отправка:  {m.SBIS_AUTO_SUBMIT}")

listed = m.list_appeals({"limit": 50})
drafts = [a for a in (listed.get("appeals") or []) if a.get("draft")]
sent = [a for a in (listed.get("appeals") or []) if not a.get("draft")]
print(f"\n3. Обращения в Saby: всего {listed.get('count', 0)}, черновиков {len(drafts)}, отправлено {len(sent)}")

if drafts:
    print("   Черновики (не видны в Контакт-центре до «Отправки»):")
    for a in drafts[:5]:
        print(f"     №{a.get('number')} — {a.get('appeal_id')}")
    if len(drafts) > 5:
        print(f"     ... ещё {len(drafts) - 5}")

print("\n4. Сотрудники с доступом в Saby (из API):")
sfilt = {
    "НашаОрганизация": m._org_filter(),
    "ВернутьУволенных": "Нет",
    "Навигация": {"РазмерСтраницы": "100", "Страница": "0"},
}
sresp = m.rpc("СБИС.СписокСотрудников", {"Параметр": {"Фильтр": sfilt}})
staff = (sresp.get("result") or {}).get("Сотрудник") or []
if isinstance(staff, dict):
    staff = [staff]
for item in staff:
    if (item.get("ДоступВСистему") or "").lower() != "да":
        continue
    eid = item.get("Идентификатор")
    fio = " ".join(filter(None, [item.get("Фамилия"), item.get("Имя"), item.get("Отчество")]))
    mark = " ← SBIS_MANAGER_ID" if str(eid) == str(m.SBIS_MANAGER_ID) else ""
    print(f"     {eid}: {fio}{mark}")

print("\n5. Тест submit (первый черновик):")
if drafts:
    aid = drafts[0]["appeal_id"]
    sub = m.submit_appeal({"appeal_id": aid, "description": "sbis_status probe"})
    if sub.get("submitted"):
        print("   OK — обращение отправлено в документооборот")
    else:
        err = sub.get("error") or {}
        msg = err.get("message") if isinstance(err, dict) else str(err)
        print(f"   ОШИБКА: {msg}")
        if sub.get("hint"):
            print(f"   Подсказка: {sub['hint'][:200]}...")
else:
    print("   Нет черновиков для теста")

print("\n" + "=" * 60)
if sent:
    print("  ИТОГ: есть отправленные обращения — интеграция работает.")
elif drafts and not (sub.get("submitted") if drafts else False):
    print("  ИТОГ: черновики создаются, но API не может выполнить «Отправку».")
    print("  Что сделать:")
    print("  • В Saby вручную отправьте ОДНО обращение (№ любой черновик → Отправить → выберите сотрудника)")
    print("  • Скопируйте guid из URL и: python scripts/sbis_show_recipient.py <guid>")
    print("  • Попросите админа: роль ai_agent в КОНТАКТ-ЦЕНТРЕ + очередь получателей регламента «Обращение»")
    print("  • Подробно: scripts/SBIS-SETUP.md")
print("=" * 60)
