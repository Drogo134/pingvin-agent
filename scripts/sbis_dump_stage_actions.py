#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
stages = doc.get("Этап") or []
if isinstance(stages, dict):
    stages = [stages]
print(json.dumps(stages, ensure_ascii=False, indent=2))
