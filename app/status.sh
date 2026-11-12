#!/usr/bin/env bash
# Prueft Prozess und /readyz.
cd "$(dirname "$(readlink -f "$0")")"
PORT="${PORT:-5000}"
if [ -f .env ] && [ -z "${PORT_SET:-}" ] && [ -z "${PORT+x}" ]; then :; fi
if [ -f run/app.pid ] && [ -r "/proc/$(cat run/app.pid)/cmdline" ] && tr '\0' ' ' < "/proc/$(cat run/app.pid)/cmdline" | grep -q "gunicorn.*wsgi:app"; then
  PID="$(cat run/app.pid)"
  # Port aus dem laufenden Prozess ermitteln (ss), sonst $PORT
  P="$(ss -ltnp 2>/dev/null | grep "pid=$PID," | head -1 | sed -E 's/.*:([0-9]+) .*/\1/')"
  PORT="${P:-$PORT}"
  echo "Prozess:   läuft (PID $PID, Port $PORT)"
else
  echo "Prozess:   läuft NICHT"; exit 1
fi
CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/readyz")"
echo "Readiness: HTTP $CODE  (http://localhost:$PORT/readyz)"
[ "$CODE" = "200" ]
