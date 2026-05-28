#!/usr/bin/env python3
"""
update_memory.py — извлекает правила общения из диалога и сохраняет в памяти агента.

Два уровня памяти (никогда не смешиваются):
  1. global_rules.md        — общие правила стиля (макс. MAX_GLOBAL_RULES)
  2. memory/clients/<id>.md — правила для конкретного клиента (макс. MAX_CLIENT_RULES)

Использование:
  python scripts/update_memory.py \
    --chat-id telegram:123456789 \
    --summary-file memory/sessions/20260528_123456789.txt
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ─── Настройки ────────────────────────────────────────────────────────────────

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
GLOBAL_RULES_FILE = MEMORY_DIR / "global_rules.md"
CLIENTS_DIR = MEMORY_DIR / "clients"
SESSIONS_DIR = MEMORY_DIR / "sessions"

MAX_GLOBAL_RULES = 25
MAX_CLIENT_RULES = 15
MIN_CONVERSATION_LEN = 150  # символов — меньше не анализируем

# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_filename(chat_id: str) -> str:
    return re.sub(r"[^\w\-]", "_", chat_id)


def client_file(chat_id: str) -> Path:
    return CLIENTS_DIR / f"{safe_filename(chat_id)}.md"


def read_rules(path: Path) -> list[str]:
    if not path.exists():
        return []
    rules = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and re.match(r"^[\d\.\-•*]+\s+", s):
            rule = re.sub(r"^[\d\.\-•*]+\s+", "", s).strip()
            if rule:
                rules.append(rule)
    return rules


def write_rules(path: Path, rules: list[str], header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
    path.write_text(
        f"{header}\n\n{body}\n\n_Обновлено: {ts}_\n",
        encoding="utf-8",
    )


def merge_rules(
    existing: list[str],
    to_add: list[str],
    to_remove: list[int],
    max_rules: int,
) -> list[str]:
    result = list(existing)
    for idx in sorted(set(to_remove), reverse=True):
        if 1 <= idx <= len(result):
            result.pop(idx - 1)
    for rule in to_add:
        rule = rule.strip()
        if rule and rule not in result:
            result.append(rule)
    # Если переполнено — удаляем самые старые
    return result[-max_rules:]


# ─── LLM-вызов ────────────────────────────────────────────────────────────────

def extract_rules(
    conversation: str,
    existing_global: list[str],
    existing_client: list[str],
    chat_id: str,
) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        print("openai not installed, skipping LLM extraction", file=sys.stderr)
        return {}

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("OPENAI_API_KEY not set, skipping", file=sys.stderr)
        return {}

    client = OpenAI(api_key=api_key)

    global_block = (
        "\n".join(f"{i+1}. {r}" for i, r in enumerate(existing_global))
        if existing_global else "(пусто)"
    )
    client_block = (
        "\n".join(f"{i+1}. {r}" for i, r in enumerate(existing_client))
        if existing_client else "(пусто)"
    )

    prompt = f"""Ты анализируешь диалог агента продаж «Пинки» (РПК «ПинГвин», Домодедово) с клиентом.

=== СУЩЕСТВУЮЩИЕ ГЛОБАЛЬНЫЕ ПРАВИЛА ОБЩЕНИЯ ===
{global_block}

=== СУЩЕСТВУЮЩИЕ ПРАВИЛА ДЛЯ КЛИЕНТА {chat_id} ===
{client_block}

=== ДИАЛОГ ===
{conversation[:5000]}

Задача: вынести из диалога конкретные инсайты о том, как лучше общаться.

Верни строго JSON (без markdown):
{{
  "global_rules_add": ["...", "..."],
  "global_rules_remove": [],
  "client_rules_add": ["...", "..."],
  "client_rules_remove": []
}}

Поля:
- global_rules_add: 0–2 НОВЫХ общих правила стиля (применимы ко ВСЕМ клиентам).
  Примеры: «После озвучивания цены сразу предлагать 1 уточнение, не список»,
           «Не переспрашивать данные, которые клиент уже давал выше в диалоге».
  Не добавлять если нет реального нового инсайта — лучше пустой массив.

- global_rules_remove: список индексов (1-based) устаревших/дублирующих глобальных правил.

- client_rules_add: 0–3 правила ТОЛЬКО об этом конкретном клиенте.
  Примеры: «Предпочитает короткие ответы, раздражается от длинных»,
           «Хочет быстро — цену сразу, без долгих уточнений»,
           «Общается кратко, сам называет все параметры — не нужно задавать много вопросов».
  Только конкретные наблюдения из этого диалога.

- client_rules_remove: индексы устаревших клиентских правил.

Если диалог короткий или не содержит новых инсайтов — все массивы пустые.
Не добавлять правила о ценах или услугах — только о стиле общения."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.2,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"LLM error: {e}", file=sys.stderr)
        return {}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Update agent memory from conversation")
    parser.add_argument("--chat-id", required=True,
                        help="Telegram channel ID, e.g. telegram:123456789")
    parser.add_argument("--summary-file", help="Path to file with conversation text")
    parser.add_argument("--text", help="Conversation text directly (short summaries)")
    args = parser.parse_args()

    # Читаем текст диалога
    if args.summary_file:
        p = Path(args.summary_file)
        if not p.exists():
            print(f"File not found: {p}", file=sys.stderr)
            sys.exit(1)
        conversation = p.read_text(encoding="utf-8")
    elif args.text:
        conversation = args.text
    else:
        conversation = sys.stdin.read()

    conversation = conversation.strip()
    if len(conversation) < MIN_CONVERSATION_LEN:
        print(f"Conversation too short ({len(conversation)} chars), skipping")
        return

    # Инициализируем директории
    MEMORY_DIR.mkdir(exist_ok=True)
    CLIENTS_DIR.mkdir(exist_ok=True)
    SESSIONS_DIR.mkdir(exist_ok=True)

    # Загружаем существующие правила
    existing_global = read_rules(GLOBAL_RULES_FILE)
    cf = client_file(args.chat_id)
    existing_client = read_rules(cf)

    print(f"[memory] chat={args.chat_id}, global={len(existing_global)}, client={len(existing_client)}")

    # Извлекаем новые правила через LLM
    result = extract_rules(conversation, existing_global, existing_client, args.chat_id)
    if not result:
        print("[memory] No rules extracted")
        return

    # Обновляем глобальные правила
    new_global = merge_rules(
        existing_global,
        result.get("global_rules_add", []),
        result.get("global_rules_remove", []),
        MAX_GLOBAL_RULES,
    )
    if new_global != existing_global:
        write_rules(
            GLOBAL_RULES_FILE,
            new_global,
            "# Правила общения — глобальные\n\nАвтоматически накоплены из диалогов агента.\nНЕ редактировать вручную.",
        )
        print(f"[memory] Global: {len(existing_global)} → {len(new_global)}")
        for r in result.get("global_rules_add", []):
            print(f"  + {r}")

    # Обновляем правила клиента
    new_client = merge_rules(
        existing_client,
        result.get("client_rules_add", []),
        result.get("client_rules_remove", []),
        MAX_CLIENT_RULES,
    )
    if new_client != existing_client:
        write_rules(
            cf,
            new_client,
            f"# Правила общения с клиентом {args.chat_id}\n\nАвтоматически накоплены из диалогов.\nНЕ редактировать вручную.",
        )
        print(f"[memory] Client: {len(existing_client)} → {len(new_client)}")
        for r in result.get("client_rules_add", []):
            print(f"  + {r}")

    print("[memory] Done")


if __name__ == "__main__":
    main()
