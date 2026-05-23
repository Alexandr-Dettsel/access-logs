#!/bin/sh
set -eu

FLASK_INGEST_URL="${FLASK_INGEST_URL:-http://flask:5000/ingest}"
NGINX_ACCESS_LOG="${NGINX_ACCESS_LOG:-/var/log/nginx/access.log}"
STATE_FILE="/tmp/access.offset"

if [ ! -f "$NGINX_ACCESS_LOG" ]; then
  echo "[send_logs] access log not found: $NGINX_ACCESS_LOG"
  exit 0
fi

# offset = сколько строк уже отправили
if [ -f "$STATE_FILE" ]; then
  OFFSET="$(cat "$STATE_FILE" || echo 0)"
else
  OFFSET="0"
fi

TOTAL="$(wc -l < "$NGINX_ACCESS_LOG" | tr -d ' ')"

# если лог ротировался/обнулился
if [ "$TOTAL" -lt "$OFFSET" ]; then
  OFFSET="0"
fi

NEW_COUNT=$((TOTAL - OFFSET))
if [ "$NEW_COUNT" -le 0 ]; then
  echo "[send_logs] no new lines (total=$TOTAL offset=$OFFSET)"
  exit 0
fi

# берём только новые строки
LINES="$(tail -n "$NEW_COUNT" "$NGINX_ACCESS_LOG")"

# готовим JSON (каждая строка как элемент массива)
# безопасно для JSON-строк: экранируем обратный слеш и кавычки
JSON_LINES="$(printf '%s\n' "$LINES" | python3 - << 'PY'
import json, sys
lines = [l.rstrip("\n") for l in sys.stdin if l.strip()]
print(json.dumps(lines))
PY
)"

PAYLOAD="$(python3 - << PY
import json, datetime
print(json.dumps({
  "sent_at_utc": datetime.datetime.utcnow().isoformat() + "Z",
  "lines": json.loads('''$JSON_LINES''')
}))
PY
)"

HTTP_CODE="$(curl -sS -o /tmp/ingest.out -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -X POST "$FLASK_INGEST_URL" \
  --data "$PAYLOAD" || true)"

if [ "$HTTP_CODE" = "200" ]; then
  echo "$TOTAL" > "$STATE_FILE"
  echo "[send_logs] sent $NEW_COUNT lines, new offset=$TOTAL"
else
  echo "[send_logs] ERROR http=$HTTP_CODE response=$(cat /tmp/ingest.out 2>/dev/null || true)"
  exit 1
fi