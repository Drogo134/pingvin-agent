#!/bin/bash
# Уведомление одного или нескольких менеджеров в Telegram
# Использование:
#   bash notify_managers.sh "Текст сообщения"
#   echo "Текст" | bash notify_managers.sh
#
# Переменные (.env):
#   MANAGER_TELEGRAM_CHAT_IDS — через запятую: 1280280963,987654321
#   MANAGER_TELEGRAM_CHAT_ID  — один ID (устаревший, если IDS не задан)

set -e

TOKEN="${TELEGRAM_BOT_TOKEN:-}"
IDS_RAW="${MANAGER_TELEGRAM_CHAT_IDS:-${MANAGER_TELEGRAM_CHAT_ID:-}}"

if [ -z "$TOKEN" ]; then
  echo '{"error":"TELEGRAM_BOT_TOKEN not set"}'
  exit 1
fi

if [ -z "$IDS_RAW" ]; then
  echo '{"error":"MANAGER_TELEGRAM_CHAT_IDS not set"}'
  exit 1
fi

if [ -n "$1" ]; then
  MESSAGE="$1"
else
  MESSAGE="$(cat)"
fi

if [ -z "$MESSAGE" ]; then
  echo '{"error":"empty message"}'
  exit 1
fi

# Нормализовать список ID: запятая, точка с запятой, пробел
IDS_CLEAN=$(echo "$IDS_RAW" | tr ';' ',' | tr -s ' ')

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [notify_managers] $1" >> /app/logs/telegram_notify.log 2>/dev/null \
    || echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [notify_managers] $1" >> "$(dirname "$0")/../logs/telegram_notify.log" 2>/dev/null \
    || true
}

SENT=0
FAILED=0
RESULTS="["

IFS=',' read -ra ID_LIST <<< "$IDS_CLEAN"
for raw_id in "${ID_LIST[@]}"; do
  CHAT_ID=$(echo "$raw_id" | tr -d ' ')
  [ -z "$CHAT_ID" ] && continue

  RESP=$(curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${MESSAGE}" \
    --max-time 15 2>/dev/null || echo '{"ok":false}')

  if echo "$RESP" | grep -q '"ok":true'; then
    SENT=$((SENT + 1))
    log "OK chat_id=${CHAT_ID}"
    RESULTS="${RESULTS}{\"chat_id\":\"${CHAT_ID}\",\"ok\":true},"
  else
    FAILED=$((FAILED + 1))
    log "FAIL chat_id=${CHAT_ID} resp=$(echo $RESP | head -c 200)"
    RESULTS="${RESULTS}{\"chat_id\":\"${CHAT_ID}\",\"ok\":false},"
  fi
done

RESULTS="${RESULTS%,}]"
echo "{\"sent\":${SENT},\"failed\":${FAILED},\"results\":${RESULTS}}"

if [ "$SENT" -eq 0 ]; then
  exit 1
fi
