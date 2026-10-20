#!/bin/sh
set -eu

# Dual static servers in one container (Phase 0: apps are HTML/JS, not Next.js).
# website → :3000 | backoffice → :3001
# Paths match Compose bind mounts at /app/website and /app/backoffice.

WEBSITE_ROOT="${WEBSITE_ROOT:-/app/website}"
BACKOFFICE_ROOT="${BACKOFFICE_ROOT:-/app/backoffice}"
HTTP_SERVER="${HTTP_SERVER:-/app/node_modules/.bin/http-server}"

if [ ! -x "$HTTP_SERVER" ]; then
  echo "error: http-server not found at $HTTP_SERVER (run npm ci in /app)" >&2
  exit 1
fi

"$HTTP_SERVER" "$WEBSITE_ROOT" -p 3000 -a 0.0.0.0 &
WEBSITE_PID=$!

"$HTTP_SERVER" "$BACKOFFICE_ROOT" -p 3001 -a 0.0.0.0 &
BACKOFFICE_PID=$!

SHUTTING_DOWN=0

term() {
  if [ "$SHUTTING_DOWN" -eq 1 ]; then
    return 0
  fi
  SHUTTING_DOWN=1
  kill -TERM "$WEBSITE_PID" "$BACKOFFICE_PID" 2>/dev/null || true
  wait "$WEBSITE_PID" 2>/dev/null || true
  wait "$BACKOFFICE_PID" 2>/dev/null || true
}

trap 'term; exit 143' INT TERM

# If either process exits, stop the other to avoid orphans.
while kill -0 "$WEBSITE_PID" 2>/dev/null && kill -0 "$BACKOFFICE_PID" 2>/dev/null; do
  sleep 1
done

EXIT_CODE=1
if ! kill -0 "$WEBSITE_PID" 2>/dev/null; then
  wait "$WEBSITE_PID" 2>/dev/null || EXIT_CODE=$?
  echo "error: website process (pid $WEBSITE_PID) exited with $EXIT_CODE" >&2
elif ! kill -0 "$BACKOFFICE_PID" 2>/dev/null; then
  wait "$BACKOFFICE_PID" 2>/dev/null || EXIT_CODE=$?
  echo "error: backoffice process (pid $BACKOFFICE_PID) exited with $EXIT_CODE" >&2
fi

term
exit "$EXIT_CODE"
