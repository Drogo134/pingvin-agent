#!/usr/bin/env python3
"""Test submit with manager ID."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

appeal_id = "d0ed9465-510e-4918-b87b-14eb1215d621"
manager_id = sys.argv[1] if len(sys.argv) > 1 else "30"
r = m.submit_appeal({
    "appeal_id": appeal_id,
    "description": "Test submit manager",
    "manager_id": manager_id,
    "recipient_mode": "manager",
})
print(json.dumps(r, ensure_ascii=False, indent=2))
