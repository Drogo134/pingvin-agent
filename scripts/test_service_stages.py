#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
rev = (doc.get("Редакция") or [{}])[0] if isinstance(doc.get("Редакция"), list) else doc.get("Редакция") or {}
rev_id = rev.get("Идентификатор") if isinstance(rev, dict) else ""

for filt in [
    {"НашаОрганизация": m._org_filter(), "ИдентификаторДокумента": aid},
    {"НашаОрганизация": m._org_filter(), "ИдентификаторДокумента": aid, "ИдентификаторРедакции": rev_id} if rev_id else None,
    {"Документ": {"Идентификатор": aid}},
]:
    if not filt:
        continue
    r = m.rpc("СБИС.СписокСлужебныхЭтапов", {"Фильтр": filt})
    print("filter keys", list(filt.keys()))
    if r.get("error"):
        print("  ERR:", (r["error"].get("details") or r["error"].get("message"))[:120])
    else:
        print("  OK:", json.dumps(r.get("result"), ensure_ascii=False)[:1500])
