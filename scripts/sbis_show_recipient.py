#!/usr/bin/env python3
"""Показать поля получателя из обращения Saby (для настройки .env)."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env_path = root / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m  # noqa: E402

appeal_id = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"
r = m.find_appeal({"appeal_id": appeal_id})
if not r.get("ok"):
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(1)

doc = r.get("document") or {}
print("=== Поля для .env ===\n")
resp = doc.get("Ответственный") or {}
dept = doc.get("Подразделение") or {}
print("Ответственный (SBIS_MANAGER_ID):")
print(f"  Идентификатор: {resp.get('Идентификатор') or '(пусто)'}")
print(f"  ФИО: {resp.get('Фамилия', '')} {resp.get('Имя', '')} {resp.get('Отчество', '')}".strip())
print()
print("Подразделение (SBIS_DEPARTMENT_NAME / SBIS_DEPARTMENT_ID):")
print(f"  Идентификатор: {dept.get('Идентификатор') or '(пусто)'}")
print(f"  Название: {dept.get('Название') or '(пусто)'}")
print()
stages = doc.get("Этап") or []
if stages:
    print("Этап «Отправка» (если обращение создано вручную в UI):")
    for st in stages:
        print(f"  - {st.get('Название')}: {json.dumps(st.get('Исполнитель'), ensure_ascii=False)[:300]}")

print("\n=== Подсказка ===")
print("Черновики от ai_agent часто без получателя — создайте ОДНО обращение вручную")
print("в Контакт-центре, назначьте подразделение/менеджера, скопируйте guid из URL")
print("и запустите: python scripts/sbis_show_recipient.py <guid>")
