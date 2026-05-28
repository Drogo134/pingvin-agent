#!/bin/bash
# Отправка email через SMTP (curl)
# Вызов: bash send_email.sh '{"to":"client@example.com","subject":"Ответ на заявку","body":"..."}'
# Поддерживает отправку через STARTTLS (порт 587)

SMTP_HOST="${SMTP_HOST:-${EMAIL_SMTP_HOST:-smtp.mail.ru}}"
SMTP_PORT="${SMTP_PORT:-${EMAIL_SMTP_PORT:-465}}"
SMTP_USER="${SMTP_USER:-${EMAIL_IMAP_USER:-${EMAIL_USER:-}}}"
SMTP_PASS="${SMTP_PASS:-${EMAIL_IMAP_PASSWORD:-${EMAIL_PASSWORD:-}}}"
COMPANY_NAME="${COMPANY_NAME:-РПК ПинГвин}"
COMPANY_EMAIL="${COMPANY_EMAIL:-${SMTP_USER:-info@ra-pingvin.ru}}"

if [ -z "$SMTP_HOST" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASS" ]; then
  echo '{"error":"SMTP не настроен в .env"}'
  exit 0
fi

DATA="${1:-{}}"
TO=$(echo "$DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('to',''))")
SUBJECT=$(echo "$DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('subject','Ответ на заявку'))")
BODY=$(echo "$DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('body',''))")

if [ -z "$TO" ]; then
  echo '{"error":"Не задан получатель (to)"}'
  exit 1
fi

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [send_email] $1" >> /app/logs/email.log 2>/dev/null || true
}

log "Sending to $TO | Subject: $SUBJECT"

# Формируем .eml
TMPFILE=$(mktemp /tmp/email_XXXXXX.eml)
cat > "$TMPFILE" << EOF
From: ${COMPANY_NAME} <${COMPANY_EMAIL}>
To: ${TO}
Subject: ${SUBJECT}
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit

${BODY}

---
С уважением,
${COMPANY_NAME}
${COMPANY_EMAIL}
EOF

# Отправка через curl SMTP
RESULT=$(curl -s \
  --url "smtp://${SMTP_HOST}:${SMTP_PORT}" \
  --ssl-reqd \
  --user "${SMTP_USER}:${SMTP_PASS}" \
  --mail-from "${SMTP_USER}" \
  --mail-rcpt "${TO}" \
  --upload-file "$TMPFILE" \
  --max-time 30 2>&1)

EXIT_CODE=$?
rm -f "$TMPFILE"

if [ $EXIT_CODE -eq 0 ]; then
  log "Sent OK to $TO"
  echo '{"ok":true}'
else
  log "Error sending to $TO: $RESULT"
  echo "{\"error\":\"smtp_failed\",\"detail\":\"$(echo $RESULT | head -c 200)\"}"
fi
