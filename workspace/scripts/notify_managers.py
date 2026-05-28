#!/usr/bin/env python3
"""
Уведомление менеджеров в Telegram.
Замена bash notify_managers.sh для Windows (нет bash).

Использование:
  python notify_managers.py "Текст сообщения"
  echo "Текст" | python notify_managers.py

Переменные (.env или os.environ):
  MANAGER_TELEGRAM_CHAT_IDS  — через запятую: 1280280963,987654321
  MANAGER_TELEGRAM_CHAT_ID   — один ID (если IDS не задан)
  TELEGRAM_BOT_TOKEN         — токен бота
"""

import json
import os
import sys
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime


def send(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        with urllib.request.urlopen(url, data=payload, timeout=15) as r:
            return json.loads(r.read())
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def log(msg: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} [notify_managers] {msg}\n"
    log_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "logs", "telegram_notify.log"),
        os.path.join(os.path.dirname(__file__), "../../logs/telegram_notify.log"),
    ]
    for p in log_paths:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
            break
        except Exception:
            pass


def notify_managers(message: str) -> dict[str, Any]:
    """Отправить текст всем MANAGER_TELEGRAM_CHAT_IDS. Возвращает {sent, failed, results} или {error}."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return {"error": "TELEGRAM_BOT_TOKEN not set", "sent": 0, "failed": 0}

    ids_raw = os.environ.get("MANAGER_TELEGRAM_CHAT_IDS") or os.environ.get("MANAGER_TELEGRAM_CHAT_ID", "")
    if not ids_raw:
        return {"error": "MANAGER_TELEGRAM_CHAT_IDS not set", "sent": 0, "failed": 0}

    message = (message or "").strip()
    if not message:
        return {"error": "empty message", "sent": 0, "failed": 0}

    ids = [i.strip() for i in ids_raw.replace(";", ",").split(",") if i.strip()]
    sent = 0
    failed = 0
    results = []
    for chat_id in ids:
        resp = send(token, chat_id, message)
        ok = bool(resp.get("ok"))
        if ok:
            sent += 1
            log(f"OK chat_id={chat_id}")
        else:
            failed += 1
            log(f"FAIL chat_id={chat_id} resp={str(resp)[:200]}")
        results.append({"chat_id": chat_id, "ok": ok})

    return {"sent": sent, "failed": failed, "results": results}


def main() -> int:
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = sys.stdin.read().strip()

    out = notify_managers(message)
    print(json.dumps(out, ensure_ascii=False))
    if out.get("error"):
        return 1
    return 0 if out.get("sent", 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
