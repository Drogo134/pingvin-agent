#!/bin/bash
# Saby — обращения в Контакт-центр (https://online.sbis.ru/page/support-service)
# API: СБИС.ЗаписатьДокумент, регламент «Обращение»
#
# Использование:
#   bash sbis_crm.sh create_appeal '{"name":"Иван","source":"telegram","description":"..."}'
#   bash sbis_crm.sh update_appeal '{"id":"...","status":"waiting_manager"}'
#   bash sbis_crm.sh find_appeal '{"channel_id":"telegram:123456789"}'
#   bash sbis_crm.sh test_auth
#
# Алиасы (совместимость): create_lead, update_lead, find_lead

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python
fi

exec "$PYTHON" "$SCRIPT_DIR/sbis_api.py" "$@"
