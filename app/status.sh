#!/usr/bin/env bash
# Prueft Prozess und /readyz.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
PORT="${PORT:-5000}"
# Prozess-Kommandozeile und Port-Belegung: Linux/WSL2 (/proc, ss) und macOS (ps, lsof)
cmdline() { if [ -r "/proc/$1/cmdline" ]; then tr '\0' ' ' < "/proc/$1/cmdline"; else ps -p "$1" -o command= 2>/dev/null || true; fi; }
is_ours() { [ -n "$1" ] && cmdline "$1" | grep -q "gunicorn.*wsgi:app"; }
if [ -f run/app.pid ] && is_ours "$(cat run/app.pid)"; then
  PID="$(cat run/app.pid)"
  # Port aus dem laufenden Prozess ermitteln (ss bzw. lsof), sonst $PORT
  if command -v ss >/dev/null 2>&1; then
    P="$(ss -ltnp 2>/dev/null | grep "pid=$PID," | head -1 | sed -E 's/.*:([0-9]+) .*/\1/')"
  else
    P="$(lsof -nP -a -p "$PID" -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {sub(/.*:/, "", $9); print $9}')"
  fi
  PORT="${P:-$PORT}"
  echo "Prozess:   läuft (PID $PID, Port $PORT)"
else
  echo "Prozess:   läuft NICHT"; exit 1
fi
CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/readyz")"
echo "Readiness: HTTP $CODE  (http://localhost:$PORT/readyz)"
[ "$CODE" = "200" ]
