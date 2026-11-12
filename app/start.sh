#!/usr/bin/env bash
# Startet die App lokal (Gunicorn, 1 Worker, 8 Threads) im Hintergrund.  PORT=8080 ./start.sh
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
ROOT="$PWD"

# .env laden, ohne bereits gesetzte Umgebungsvariablen zu ueberschreiben
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    key="${key// /}"; [[ -z "$key" || "$key" == \#* ]] && continue
    value="${value%%#*}"; value="$(echo "$value" | sed -e 's/[[:space:]]*$//' -e "s/^['\"]//" -e "s/['\"]$//")"
    [ -z "${!key+x}" ] && export "$key=$value"
  done < .env
fi
export HOST="${HOST:-0.0.0.0}" PORT="${PORT:-5000}"
mkdir -p run logs instance

if [ ! -x .venv/bin/gunicorn ]; then
  echo "Erstelle virtuelle Umgebung ..."
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r "$( [ -f requirements.lock ] && echo requirements.lock || echo requirements.txt )"
fi
export PATH="$ROOT/.venv/bin:$PATH" FLASK_APP=wsgi:app

is_ours() { [ -r "/proc/$1/cmdline" ] && tr '\0' ' ' < "/proc/$1/cmdline" | grep -q "gunicorn.*wsgi:app"; }
if [ -f run/app.pid ] && is_ours "$(cat run/app.pid)"; then
  echo "Läuft bereits (PID $(cat run/app.pid)). Erst ./stop.sh ausführen."; exit 1
fi
if ss -ltn "( sport = :$PORT )" | grep -q LISTEN; then
  echo "FEHLER: Port $PORT ist bereits belegt (fremder Prozess wird nicht beendet)." >&2
  echo "Anderen Port wählen, z.B.: PORT=$((PORT+1)) ./start.sh" >&2; exit 1
fi

flask db upgrade >> logs/app.log 2>&1
flask seed-data >> logs/app.log 2>&1
gunicorn -c gunicorn.conf.py --daemon --pid run/app.pid --log-file logs/app.log wsgi:app

for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:$PORT/readyz" >/dev/null 2>&1 && break; sleep 0.5
done
curl -fsS "http://127.0.0.1:$PORT/readyz" >/dev/null 2>&1 || { echo "FEHLER: /readyz antwortet nicht, siehe logs/app.log" >&2; exit 1; }

WSL_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}' || true)"
echo "Oracle Live Voting läuft."
echo "  PID:           $(cat run/app.pid)"
echo "  Port:          $PORT (Bind $HOST)"
echo "  Teilnehmer:    http://localhost:$PORT/"
echo "  Beamer:        http://localhost:$PORT/screen"
echo "  Admin:         http://localhost:$PORT/admin"
echo "  Healthcheck:   http://localhost:$PORT/healthz"
echo "  Readiness:     http://localhost:$PORT/readyz"
[ -n "$WSL_IP" ] && echo "  WSL2-IP:       http://$WSL_IP:$PORT/  (für Smartphones nur nach manueller Windows-Konfiguration erreichbar, siehe README)"
echo "  Logs:          $ROOT/logs/app.log"
