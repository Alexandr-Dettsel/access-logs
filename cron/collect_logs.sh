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

HTTP_CODE="$({
  tail -n "$NEW_COUNT" "$NGINX_ACCESS_LOG" | python3 -c '
import sys, json, datetime
lines = [line.rstrip("\n") for line in sys.stdin if line.strip()]
payload = {
    "sent_at_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "lines": lines,
}
print(json.dumps(payload, ensure_ascii=False))
' | curl -sS -o /tmp/ingest.out -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -X POST "$FLASK_INGEST_URL" \
    --data-binary @-
} || true)"

if [ "$HTTP_CODE" = "200" ]; then
  echo "$TOTAL" > "$STATE_FILE"
  echo "[send_logs] sent $NEW_COUNT lines, new offset=$TOTAL"
else
  echo "[send_logs] ERROR http=$HTTP_CODE response=$(cat /tmp/ingest.out 2>/dev/null || true)"
  exit 1
fi