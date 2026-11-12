#!/usr/bin/env bash
# Laeuft AUF dem Zielsystem (wird von deploy-public.sh per SSH aufgerufen).
# Nutzung: remote-install.sh <archiv.tar.gz> <release-id> <port> <public-base-url>
# Ruft niemals firewall-cmd auf und beendet keine fremden Prozesse.
set -euo pipefail
ARCHIVE="$1"; RID="$2"; PORT="$3"; PUBLIC_URL="$4"
BASE=/opt/oracle-live-voting
SERVICE=oracle-live-voting
SH="$BASE/shared"

say() { echo "[remote] $*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "FEHLER: '$1' fehlt auf dem Zielsystem." >&2; exit 1; }; }
need python3; need curl; need tar; need ss
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { echo "FEHLER: Python >= 3.9 nötig." >&2; exit 1; }
python3 -c 'import venv, ensurepip' 2>/dev/null || { echo "FEHLER: python3-venv/ensurepip fehlt (z.B. sudo dnf install python3)." >&2; exit 1; }

sudo mkdir -p "$BASE/releases" "$SH/logs" "$SH/backups"
sudo chown -R opc:opc "$BASE"
chmod 750 "$SH"

REL="$BASE/releases/$RID"
mkdir -p "$REL"
tar -xzf "$ARCHIVE" -C "$REL" --strip-components=1
say "Release entpackt: $REL"

# virtuelle Umgebung ausserhalb der Releases
[ -x "$BASE/venv/bin/python" ] || python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install -q --upgrade pip
"$BASE/venv/bin/pip" install -q -r "$REL/requirements.lock"
say "Abhängigkeiten installiert."

# Secrets nur beim ersten Deployment erzeugen
if [ ! -f "$SH/app.env" ]; then
  umask 077
  SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  ADMINPW="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
  cat > "$SH/app.env" <<ENV
APP_ENV=production
SECRET_KEY=$SECRET
ADMIN_PASSWORD=$ADMINPW
PUBLIC_BASE_URL=$PUBLIC_URL
DATABASE_URL=sqlite:///$SH/oracle-live-voting.db
HOST=0.0.0.0
PORT=$PORT
PROXY_FIX_ENABLED=false
SESSION_COOKIE_SECURE=false
BACKUP_DIR=$SH/backups
ENV
  printf '%s\n' "$ADMINPW" > "$SH/initial-admin-password.txt"
  chmod 600 "$SH/app.env" "$SH/initial-admin-password.txt"
  say "Neue Secrets erzeugt (app.env, initial-admin-password.txt, je 600)."
else
  # bestehende Secrets bleiben unangetastet; nur Port und URL folgen dem Aufruf
  sed -i -e "s|^PORT=.*|PORT=$PORT|" -e "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=$PUBLIC_URL|" "$SH/app.env"
  chmod 600 "$SH/app.env"
  say "Bestehende app.env beibehalten (nur PORT/PUBLIC_BASE_URL aktualisiert)."
fi

PREV=""; [ -L "$BASE/current" ] && PREV="$(readlink "$BASE/current")"
ln -sfn "$REL" "$BASE/current"

rollback() {
  echo "FEHLER: $1 – Rollback" >&2
  if [ -n "$PREV" ]; then
    ln -sfn "$PREV" "$BASE/current"; sudo systemctl restart "$SERVICE" || true
    echo "Vorheriges Release reaktiviert: $PREV" >&2
  else
    echo "Kein vorheriges Release vorhanden. Logs: journalctl -u $SERVICE -n 50" >&2
  fi
  exit 1
}

# Migration + Seed (idempotent) mit der Produktionsumgebung
(
  set -a; . "$SH/app.env"; set +a
  cd "$BASE/current"
  export FLASK_APP=wsgi:app
  "$BASE/venv/bin/flask" db upgrade
  "$BASE/venv/bin/flask" seed-data
) || rollback "Migration/Seed fehlgeschlagen"

# systemd-Unit
sudo tee /etc/systemd/system/$SERVICE.service >/dev/null <<UNIT
[Unit]
Description=Oracle Live Voting (Gunicorn, 1 Worker / 8 Threads)
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=$BASE/current
EnvironmentFile=$SH/app.env
ExecStart=$BASE/venv/bin/gunicorn -c gunicorn.conf.py wsgi:app
Restart=on-failure
RestartSec=3
KillSignal=SIGTERM
TimeoutStopSec=35
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ReadWritePaths=$SH

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE" >/dev/null 2>&1
sudo systemctl restart "$SERVICE"

ok=0
for _ in $(seq 1 30); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/readyz")" = "200" ]; then ok=1; break; fi
  sleep 1
done
[ "$ok" = 1 ] || rollback "/readyz lieferte binnen 30 s kein HTTP 200"

# nur die fünf neuesten Releases behalten (aktives und vorheriges nie löschen)
CUR="$(readlink "$BASE/current")"
ls -1dt "$BASE"/releases/*/ 2>/dev/null | sed 's:/$::' | tail -n +6 | while read -r old; do
  [ "$old" = "$CUR" ] || [ "$old" = "$PREV" ] || rm -rf -- "$old"
done

PID="$(systemctl show -p MainPID --value "$SERVICE")"
echo "REMOTE_RESULT release=$RID pid=$PID active=$(systemctl is-active "$SERVICE") previous=${PREV:-none}"
for p in /, /screen, /admin, /healthz, /readyz; do
  echo "REMOTE_CHECK $p $(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT${p%,}")"
done
ss -ltnp 2>/dev/null | grep ":$PORT " || true
