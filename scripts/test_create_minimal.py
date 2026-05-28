#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

# minimal doc — no dept, no manager
doc = {"Регламент": {"Название": m.SBIS_APPEAL_REGULATION_NAME}, "Примечание": "minimal create test"}
r = m.rpc("СБИС.ЗаписатьДокумент", {"Документ": doc})
print("CREATE:", json.dumps(r, ensure_ascii=False)[:1200])
if r.get("result"):
    aid = r["result"].get("Идентификатор")
    sub = m.submit_appeal({"appeal_id": aid, "description": "minimal submit", "recipient_mode": "department"})
    print("SUBMIT:", json.dumps({k: sub.get(k) for k in ("ok", "submitted", "error", "hint")}, ensure_ascii=False)[:800])
