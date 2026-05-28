#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

for eid in ("223", "3374", "27850", "30"):
    for method, params in [
        ("СБИС.ПрочитатьСотрудника", {"Параметр": {"Сотрудник": {"Идентификатор": eid}}}),
        ("СБИС.ПрочитатьСотрудника", {"Сотрудник": {"Идентификатор": eid}}),
    ]:
        r = m.rpc(method, params)
        if "error" not in r:
            print(method, eid, "OK:", json.dumps(r.get("result"), ensure_ascii=False)[:800])
            break
        else:
            print(method, eid, "ERR:", (r.get("error") or {}).get("details", "")[:80])
