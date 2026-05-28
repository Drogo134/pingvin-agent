#!/bin/bash
# Email IMAP checker via curl (OpenSSL required)
# Проверяет IMAP ящик и возвращает список непрочитанных в JSON
# Вызов: bash email_check.sh
# Ответ: JSON массив [{from, subject, body, date, uid}]

set -e

IMAP_HOST="${IMAP_HOST:-${EMAIL_IMAP_HOST:-${EMAIL_IMAP:-}}}"
IMAP_PORT="${IMAP_PORT:-${EMAIL_IMAP_PORT:-993}}"
IMAP_USER="${IMAP_USER:-${EMAIL_IMAP_USER:-${EMAIL_USER:-}}}"
IMAP_PASS="${IMAP_PASS:-${EMAIL_IMAP_PASSWORD:-${EMAIL_PASSWORD:-}}}"
LAST_UID_FILE="/tmp/.email_last_uid"

if [ -z "$IMAP_HOST" ] || [ -z "$IMAP_USER" ] || [ -z "$IMAP_PASS" ]; then
  echo '{"error":"IMAP_HOST/IMAP_USER/IMAP_PASS не заданы"}'
  exit 0
fi

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [email_check] $1" >> /app/logs/email.log 2>/dev/null || true
}

# Получить последний UID
LAST_UID=0
if [ -f "$LAST_UID_FILE" ]; then
  LAST_UID=$(cat "$LAST_UID_FILE")
fi

# Поиск непрочитанных (UID > LAST_UID)
IMAP_SEARCH="A1 LOGIN \"${IMAP_USER}\" \"${IMAP_PASS}\"
A2 SELECT INBOX
A3 SEARCH UNSEEN UID $(( LAST_UID + 1 )):*
A4 LOGOUT
"

RESULTS=$(echo "$IMAP_SEARCH" | curl -s \
  --url "imaps://${IMAP_HOST}:${IMAP_PORT}/INBOX" \
  --user "${IMAP_USER}:${IMAP_PASS}" \
  -X "SEARCH UNSEEN" \
  --max-time 15 2>/dev/null || echo "")

# Парсим UIDs из ответа
UIDS=$(echo "$RESULTS" | grep "SEARCH" | grep -oP '\d+' | tr '\n' ',' | sed 's/,$//')

if [ -z "$UIDS" ]; then
  log "No new emails"
  echo '[]'
  exit 0
fi

log "Found UIDs: $UIDS"

# Для каждого UID получаем заголовки и тело
python3 -c "
import imaplib, email, json, os, sys
from email.header import decode_header

host = os.environ.get('IMAP_HOST') or os.environ.get('EMAIL_IMAP_HOST') or os.environ.get('EMAIL_IMAP') or ''
user = os.environ.get('IMAP_USER') or os.environ.get('EMAIL_IMAP_USER') or os.environ.get('EMAIL_USER') or ''
pwd  = os.environ.get('IMAP_PASS') or os.environ.get('EMAIL_IMAP_PASSWORD') or os.environ.get('EMAIL_PASSWORD') or ''
port = int(os.environ.get('IMAP_PORT') or os.environ.get('EMAIL_IMAP_PORT') or '993')
last_uid = int(open('/tmp/.email_last_uid').read().strip() if os.path.exists('/tmp/.email_last_uid') else '0')

try:
    M = imaplib.IMAP4_SSL(host, port)
    M.login(user, pwd)
    M.select('INBOX')
    _, data = M.uid('search', None, 'UNSEEN')
    uids = data[0].split()
    
    results = []
    max_uid = last_uid
    
    for uid in uids[-20:]:  # Макс 20 писем за раз
        uid_int = int(uid)
        if uid_int <= last_uid:
            continue
        
        _, msg_data = M.uid('fetch', uid, '(RFC822)')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        
        def decode_str(s):
            if not s: return ''
            parts = decode_header(s)
            result = []
            for part, enc in parts:
                if isinstance(part, bytes):
                    result.append(part.decode(enc or 'utf-8', errors='replace'))
                else:
                    result.append(str(part))
            return ''.join(result)
        
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')[:2000]
                    break
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='replace')[:2000]
        
        results.append({
            'uid': uid_int,
            'from': decode_str(msg.get('From','')),
            'subject': decode_str(msg.get('Subject','')),
            'date': msg.get('Date',''),
            'body': body.strip()
        })
        max_uid = max(max_uid, uid_int)
    
    M.logout()
    
    if max_uid > last_uid:
        with open('/tmp/.email_last_uid', 'w') as f:
            f.write(str(max_uid))
    
    print(json.dumps(results, ensure_ascii=False))

except Exception as e:
    print(json.dumps({'error': str(e)}))
"
