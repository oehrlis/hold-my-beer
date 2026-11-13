#!/usr/bin/env bash
# OPTIONAL: Deployment auf einen eigenen Linux-Host (z.B. OCI Compute).
# Nutzung: SSH_USER=<user> SSH_HOST=<host> SSH_KEY=<pfad-zum-key> [PUBLIC_BASE_URL=<url>] ./deploy-public.sh [PORT]   (Standard 8080)
# PUBLIC_BASE_URL: beim ersten Deployment Standard http://<host>:<port>; beim Redeploy ohne Angabe bleibt der Wert in app.env.
# Aendert keine Firewall und keine Cloud-Regeln. Beendet keine fremden Prozesse.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

PORT="${1:-8080}"
SSH_USER="${SSH_USER:-}"
SSH_HOST="${SSH_HOST:-}"
SSH_KEY="${SSH_KEY:-}"
MISSING=""
for v in SSH_USER SSH_HOST SSH_KEY; do [ -n "${!v}" ] || MISSING="$MISSING $v"; done
if [ -n "$MISSING" ]; then
  echo "FEHLER: Pflichtvariable(n) nicht gesetzt:$MISSING" >&2
  echo "Beispiel: SSH_USER=<user> SSH_HOST=<host> SSH_KEY=~/.ssh/<key> ./deploy-public.sh ${PORT}" >&2
  exit 2
fi
SERVICE=oracle-live-voting

[[ "$PORT" =~ ^[0-9]+$ ]] && [ "$PORT" -ge 1024 ] && [ "$PORT" -le 65535 ] \
  || { echo "FEHLER: Port muss eine Zahl von 1024 bis 65535 sein (war: '$PORT')." >&2; exit 2; }
for f in package.sh deploy/remote-install.sh requirements.lock wsgi.py; do
  [ -e "$f" ] || { echo "FEHLER: lokale Datei fehlt: $f" >&2; exit 2; }
done
[ -f "$SSH_KEY" ] || { echo "FEHLER: SSH-Key nicht gefunden: $SSH_KEY" >&2; exit 2; }
chmod 600 "$SSH_KEY"

SSH=(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o BatchMode=yes "$SSH_USER@$SSH_HOST")
SCP=(scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o BatchMode=yes)

echo "==> SSH-Verbindung testen"
"${SSH[@]}" 'echo verbunden: $(hostname)' || { echo "FEHLER: SSH-Verbindung fehlgeschlagen." >&2; exit 3; }

echo "==> Port $PORT auf dem Ziel prüfen"
LISTEN="$("${SSH[@]}" "ss -ltnp 2>/dev/null | grep -E ':${PORT}[[:space:]]' || true")"
if [ -n "$LISTEN" ]; then
  OWN_PID="$("${SSH[@]}" "systemctl show -p MainPID --value $SERVICE 2>/dev/null || true")"
  if [ -n "$OWN_PID" ] && [ "$OWN_PID" != "0" ] && grep -q "pid=$OWN_PID," <<<"$LISTEN"; then
    echo "    Port $PORT wird vom eigenen Service $SERVICE genutzt (Redeploy)."
  else
    echo "FEHLER: Port $PORT ist auf dem Ziel bereits belegt (fremder Prozess, wird nicht beendet):" >&2
    echo "$LISTEN" >&2
    FREE="$("${SSH[@]}" "for p in 8081 8082 8090 8443 9000 9090; do ss -ltn | grep -qE ':\$p[[:space:]]' || { echo \$p; break; }; done")"
    echo "Vorschlag: ./deploy-public.sh ${FREE:-8081}" >&2
    exit 4
  fi
fi

echo "==> Release-Paket bauen"
ARCHIVE="$(./package.sh | tail -1)"
RID="$(basename "$ARCHIVE" .tar.gz | sed 's/^dswnwst-voting-//')"
# leer = Redeploy behaelt PUBLIC_BASE_URL aus app.env (z.B. https://hmb.oradba.ch hinter dem Tunnel)
PUBLIC_URL="${PUBLIC_BASE_URL:-}"
SHOW_URL="${PUBLIC_URL:-<PUBLIC_BASE_URL aus app.env>}"
echo "    $ARCHIVE (Release $RID)"

echo "==> Übertragen (scp)"
"${SCP[@]}" "$ARCHIVE" deploy/remote-install.sh "$SSH_USER@$SSH_HOST:/tmp/"

echo "==> Installieren (systemd, venv, Migration, Seed, Healthcheck)"
"${SSH[@]}" "bash /tmp/remote-install.sh /tmp/$(basename "$ARCHIVE") '$RID' '$PORT' '$PUBLIC_URL' 'http://$SSH_HOST:$PORT'; rc=\$?; rm -f /tmp/$(basename "$ARCHIVE") /tmp/remote-install.sh; exit \$rc"

cat <<REPORT

============================================================
 Deployment abgeschlossen
============================================================
 TCP Port:        $PORT
 Service:         $SERVICE   (Status: systemctl status $SERVICE)
 Release:         $RID
 Verzeichnis:     /opt/oracle-live-voting/current -> releases/$RID

 URLs (nach Freigabe von Firewall + OCI):
   Teilnehmer:    $SHOW_URL/
   Beamer:        $SHOW_URL/screen
   Admin:         $SHOW_URL/admin
   Healthcheck:   $SHOW_URL/healthz
   Readiness:     $SHOW_URL/readyz

 Initiales Admin-Passwort einmalig abrufen:
   ssh -i $SSH_KEY $SSH_USER@$SSH_HOST 'cat /opt/oracle-live-voting/shared/initial-admin-password.txt'
 Danach die Datei löschen:
   ssh -i $SSH_KEY $SSH_USER@$SSH_HOST 'shred -u /opt/oracle-live-voting/shared/initial-admin-password.txt'

 MANUELL auf dem Server (wurde NICHT ausgeführt):
   sudo firewall-cmd --permanent --add-port=$PORT/tcp
   sudo firewall-cmd --reload
   sudo firewall-cmd --list-ports

 MANUELL in OCI (Security List ODER NSG, wurde NICHT geändert):
   Stateful Ingress | Source CIDR 0.0.0.0/0 | Protocol TCP | Destination Port $PORT

 Hinweis: HTTP ohne TLS (SESSION_COOKIE_SECURE=false) ist nur für den Test gedacht.
 Für die Konferenz: Nginx + HTTPS + DNS (siehe README).
============================================================
REPORT
