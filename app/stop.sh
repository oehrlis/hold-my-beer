#!/usr/bin/env bash
# Beendet ausschliesslich den eigenen Gunicorn-Prozess aus run/app.pid.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if [ ! -f run/app.pid ]; then echo "Nicht gestartet (keine run/app.pid)."; exit 0; fi
# Prozess-Kommandozeile: Linux/WSL2 (/proc) und macOS (ps)
cmdline() { if [ -r "/proc/$1/cmdline" ]; then tr '\0' ' ' < "/proc/$1/cmdline"; else ps -p "$1" -o command= 2>/dev/null || true; fi; }
is_ours() { [ -n "$1" ] && cmdline "$1" | grep -q "gunicorn.*wsgi:app"; }
PID="$(cat run/app.pid)"
if is_ours "$PID"; then
  kill -TERM "$PID"
  for _ in $(seq 1 40); do kill -0 "$PID" 2>/dev/null || break; sleep 0.25; done
  kill -0 "$PID" 2>/dev/null && { echo "PID $PID reagiert nicht auf SIGTERM; bitte manuell prüfen." >&2; exit 1; }
  echo "Gestoppt (PID $PID)."
else
  echo "PID $PID gehört nicht zu dieser App – es wird nichts beendet."
fi
rm -f run/app.pid
