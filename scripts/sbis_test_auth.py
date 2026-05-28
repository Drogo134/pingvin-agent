#!/usr/bin/env python3
"""Quick SBIS auth check for mvp-check.ps1"""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import importlib.util

spec = importlib.util.spec_from_file_location("sbis", root / "workspace" / "scripts" / "sbis_api.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(json.dumps(mod.test_auth(), ensure_ascii=False))
