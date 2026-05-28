#!/usr/bin/env python3
"""Все обращения — ищем хоть одно НЕ черновик для образца."""
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

filt = {
    "НашаОрганизация": m._org_filter(),
    "Тип": m.SBIS_APPEAL_DOC_TYPE,
    "Регламент": m._regulation_filter(),
    "Навигация": {"РазмерСтраницы": "100", "Страница": "0"},
}
resp = m.rpc("СБИС.СписокДокументов", {"Фильтр": filt})
items = (resp.get("result") or {}).get("Документ") or []
if isinstance(items, dict):
    items = [items]
print(f"total={len(items)}")
for item in items:
    state = item.get("Состояние") or {}
    draft = m.is_appeal_draft(state)
    print(f"#{item.get('Номер')} draft={draft} state={state.get('Описание') or state.get('Название')} id={item.get('Идентификатор')}")

# read first non-draft if any
for item in items:
    state = item.get("Состояние") or {}
    if m.is_appeal_draft(state):
        continue
    aid = item.get("Идентификатор")
    read = m.find_appeal({"appeal_id": aid})
    doc = read.get("document") or {}
    print("\n=== SUBMITTED SAMPLE ===")
    for k in ("Получатель", "Ответственный", "Подразделение", "Исполнитель", "Состояние"):
        print(k, json.dumps(doc.get(k), ensure_ascii=False))
    break
else:
    print("\nНет отправленных обращений в выборке — все черновики.")
