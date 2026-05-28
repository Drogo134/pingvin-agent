#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

r = m.create_appeal({
    "description": "API test create+submit manager 223",
    "manager_id": "223",
    "recipient_mode": "manager",
    "auto_submit": True,
    "source": "test_script",
})
print(json.dumps(r, ensure_ascii=False, indent=2)[:2500])
