# Denn sie wissen nicht, was sie tun – Live-Voting

*Oracle live mit Oehrli, Berger und KI* – Live-Voting für eine 45-minütige Konferenzsession.
Teilnehmer scannen einen QR-Code, wählen pro Runde eines von drei Oracle-Themen und stimmen ab.
Kein Login, keine Namen, keine E-Mail-Adressen.

**Stack:** Python 3 (getestet mit 3.9), Flask (Application Factory, Blueprints), Flask-SQLAlchemy, Flask-Migrate/Alembic,
Flask-WTF (CSRF), Flask-Limiter, SQLite (WAL), Jinja2, Vanilla-JS, Gunicorn (1 Worker, 8 Threads), pytest.
Keine externen Dienste, keine CDN-Abhängigkeiten, keine WebSockets (HTTP-Polling alle 2 s). Läuft nach `pip install` vollständig offline.

Es gibt zwei **getrennte Betriebsarten**: [1. LOCAL WSL2](#1-local-wsl2-primärer-betrieb) und [2. OPTIONAL PUBLIC DEPLOYMENT](#2-optional-public-deployment).

## Architektur

```
Browser (Teilnehmer /, Beamer /screen, Admin /admin)  --Polling GET /api/state (2 s)-->  Flask
POST /api/vote, POST /admin/api/<aktion>  (CSRF-Header X-CSRFToken)                       |
                                                                                          v
                         votingapp/services/voting.py  (Zustandsautomat, Stimmen, Timer)  -->  SQLite (WAL)
```

```
votingapp/
  __init__.py        Application Factory, Security-Header, Fehlerbehandlung, SQLite-PRAGMAs
  config.py          Development / Testing / Production aus Umgebungsvariablen
  models.py          Round, Topic, RoundOption, SessionState, Vote, Scorecard, AuditLog
  clientid.py        anonyme Client-ID (signiertes Cookie), HMAC-Hash für die DB
  blueprints/        public (/), screen (/screen, /qr.svg), admin (/admin ...), api (/api/..., /healthz, /readyz)
  services/          voting.py (Kernlogik), state_machine.py, views.py, seed.py, backup.py, audit.py
  templates/ static/ HTML, CSS, JS (ohne Inline-Skripte, strikte CSP)
migrations/          Alembic
tests/               pytest (39 Tests inkl. Integrationstest)
tools/               loadtest.py, smoke.sh
deploy/              remote-install.sh, systemd- und Nginx-Beispiel
wsgi.py              Entry Point  wsgi:app
gunicorn.conf.py     1 Worker, 8 Threads, Timeout 30 s, Bind aus HOST/PORT
start.sh stop.sh status.sh package.sh deploy-public.sh
```

### Zustandsautomat

`waiting → voting_open → voting_closed → result_visible → challenge_running → scorecard_visible → waiting | closing`

Ungültige Übergänge ergeben serverseitig **HTTP 409**. Nach `voting_ends_at` (UTC, Serverzeit ist autoritativ) werden Stimmen
abgewiesen und die Runde wechselt automatisch zu `voting_closed`; das Ergebnis bleibt verborgen, bis der Admin es freigibt.
Separat (bestätigt und im Auditlog): `reset_round`, `reset_session`, `runoff` (Stichwahl bei Gleichstand – verwirft die Stimmen der Runde, das alte Ergebnis steht im Auditlog).

Abstimmungsergebnis, rechnerischer Gewinner, Gleichstand, gewähltes Challenge-Thema und Begründung der Abweichung sind getrennte Felder.
Eine manuelle Auswahl überschreibt nie das Ergebnis. Bei Gleichstand wird **nie** zufällig entschieden.

### Teilnehmeridentität – wichtig

Jeder Browser bekommt eine zufällige Client-ID im signierten Cookie `olv_cid`; in der DB liegt nur ein HMAC-SHA256-Hash
(Unique Constraint `round_id + client_hash`). Pro Abstimmversuch wird eine Request-ID erzeugt, ein Retry nach Netzfehler zählt keine zweite Stimme.
IP-Adressen werden nicht gespeichert. **Das verhindert versehentliche Doppelstimmen, ist aber kein manipulationssicheres Wahlsystem:**
Inkognito-Modus, ein anderer Browser oder ein anderes Gerät erzeugen eine neue Client-ID. Für diese Konferenzanwendung ist das akzeptiert.

---

## 1. LOCAL WSL2 (primärer Betrieb)

### Installation

```bash
cd /pfad/zum/projekt
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock -r requirements-dev.txt   # reproduzierbar; requirements.txt = direkte Abhängigkeiten
cp .env.example .env            # optional
```

`./start.sh` legt die venv bei Bedarf selbst an.

### Datenbank, Migrationen, Seed

```bash
export FLASK_APP=wsgi:app
.venv/bin/flask db upgrade        # legt instance/voting.db an (DATABASE_URL überschreibt den Pfad)
.venv/bin/flask seed-data         # 4 Runden, 12 Themen, 9 Reserve-Themen; idempotent, löscht nie Stimmen/Ergebnisse/Scorecards
```

`start.sh` führt beides bei jedem Start automatisch aus.

### Start, Stop, Status, Logs

```bash
./start.sh               # Port 5000, Bind 0.0.0.0
PORT=8080 ./start.sh     # anderer Port (belegte Ports werden erkannt, fremde Prozesse nie beendet)
./status.sh              # Prozess + /readyz
./stop.sh                # beendet nur den eigenen Gunicorn (PID aus run/app.pid)
tail -f logs/app.log
```

Nach dem Start werden PID, Port, alle URLs und die WSL2-IP ausgegeben.

| Zweck | URL |
|---|---|
| Teilnehmer | `http://localhost:<PORT>/` |
| Beamer | `http://localhost:<PORT>/screen` |
| Admin | `http://localhost:<PORT>/admin` |
| Liveness / Readiness | `/healthz` / `/readyz` |

### Adminzugriff

Development-Passwort (**nur lokal**): `oracle-dev`. Eigenes Passwort: `ADMIN_PASSWORD=... ./start.sh`.
In `APP_ENV=production` sind `SECRET_KEY` und `ADMIN_PASSWORD` Pflicht, sonst startet die App nicht. Admin-Session: 60 Minuten Inaktivität.
Login-Rate-Limit: 5/Minute und 20/Stunde.

### Konfiguration (Umgebungsvariablen)

`APP_ENV` (`FLASK_ENV` als Fallback), `SECRET_KEY`, `ADMIN_PASSWORD`, `PUBLIC_BASE_URL` (Ziel des QR-Codes; leer = automatisch erkannte lokale IP),
`DATABASE_URL`, `HOST`, `PORT`, `PROXY_FIX_ENABLED` (nur Production, genau ein Proxy-Hop), `SESSION_COOKIE_SECURE`
(Production-Standard `true`; `false` **nur** für den ersten HTTP-Test ohne HTTPS), `BACKUP_DIR`.

### Tests, Lasttest, Smoke-Test

```bash
.venv/bin/python -m pytest -q                      # 39 Tests inkl. Integrationstest einer kompletten Session
./start.sh && .venv/bin/python tools/loadtest.py --clients 150   # nur localhost; anderer Host nur mit --allow-remote
PORT=5000 tools/smoke.sh                            # curl-Smoke-Test gegen die laufende App
```

Der Lasttest öffnet ein Voting, lässt N Clients gleichzeitig pollen und abstimmen (inkl. Doppelstimme), prüft Gesamtzahl,
Verteilung, 409er, 5xx/SQLite-Locks und gibt Antwortzeiten aus. Er setzt die Runde danach zurück – nicht kurz vor einer Session ausführen.
Die gemessenen Latenzen enthalten die Last des Python-Generators selbst.

### WSL2-Netzwerk und Smartphone-Test

WSL2 läuft standardmäßig im NAT-Modus mit eigener IP (z. B. `172.24.x.x`, Ausgabe von `start.sh`). `http://localhost:<PORT>` funktioniert
im Windows-Browser (localhost-Forwarding). Ein Smartphone im selben WLAN erreicht die WSL2-IP in der Regel **nicht**, weil sie nur innerhalb
des Windows-Hosts routbar ist. Optionen, jeweils **manuell** durch dich (die App ändert nichts an Windows):

1. WSL2 im Mirrored-Mode betreiben (`%UserProfile%\.wslconfig`: `[wsl2]` / `networkingMode=mirrored`, danach `wsl --shutdown`) plus eine eingehende Windows-Firewall-Regel für den Port.
2. Portproxy auf Windows (Administrator-PowerShell): `netsh interface portproxy add v4tov4 listenport=5000 listenaddress=0.0.0.0 connectport=5000 connectaddress=<WSL2-IP>` plus Firewall-Regel; die WSL2-IP ändert sich nach Neustarts.
3. Für die Konferenz: Public-Deployment (Abschnitt 2).

`PUBLIC_BASE_URL` muss auf die vom Smartphone erreichbare Adresse zeigen, sonst enthält der QR-Code eine nutzlose Adresse
(`PUBLIC_BASE_URL=http://<windows-lan-ip>:5000 ./start.sh`).

### Backup, Export, Restore, Reset

```bash
.venv/bin/flask backup                   # SQLite-Online-Backup-API -> backups/voting-<zeit>.db (nie per cp!)
.venv/bin/flask export-json --out export.json   # Runden, Themen, Stimmen (nur 8-Zeichen-Hash-Präfix), Ergebnisse, Scorecards, Auditlog
# Restore: ./stop.sh; Backup nach instance/voting.db kopieren (alte *.db-wal/-shm Dateien entfernen); ./start.sh
```

Reset im Admin: „Aktuelle Runde zurücksetzen“ / „Gesamte Session zurücksetzen“ (letzteres mit Eingabe von `RESET`). Beides wird im Auditlog festgehalten.

### Admin-Ablauf einer Runde

Runde aktivieren → Dauer wählen, *Voting öffnen* → Countdown läuft serverseitig → (automatisch oder manuell) *schließen* →
Stimmen/Gewinner/Gleichstand sehen → *Ergebnis freigeben* → Challenge-Thema festlegen (Gewinner, Zweitplatzierter oder anderes mit Begründung) →
*Challenge-Timer starten* (5 Minuten) → *Challenge stoppen* → Scorecard speichern → *Nächste Runde* oder *Closing anzeigen*.
Reserve-Themen lassen sich im Zustand `waiting` einer Option einer noch nicht gespielten Runde zuordnen.

---

## 2. OPTIONAL PUBLIC DEPLOYMENT

Das Deployment ist **nicht** Teil des lokalen Betriebs und wird nur auf ausdrücklichen Wunsch ausgeführt.

### Paket erstellen

```bash
./package.sh        # -> dist/dswnwst-voting-<version>-<zeit>.tar.gz
```

Enthält Anwendung, Migrationen, Skripte, Tests, `requirements.lock`, README und Deploy-Beispiele. Nicht enthalten: `.git`, `.venv`, Datenbanken, `.env`, Logs, Backups, Caches, Bytecode.
Das Skript bricht ab, falls das Paket Verweise auf lokale Home-Pfade enthielte.

### Deployen

```bash
./deploy-public.sh 8080        # Port 1024-65535, Standard 8080
# Ziel überschreibbar: SSH_USER, SSH_HOST, SSH_KEY (Standard: opc@<host-ip>, ~/.ssh/<ssh-key>)
```

Ablauf: Port/Key/SSH prüfen → Zielport per `ss` prüfen (belegt durch Fremdprozess ⇒ Abbruch mit freiem Portvorschlag, nie `kill`) →
Paket bauen → `scp` → Release unter `/opt/oracle-live-voting/releases/<id>` entpacken → venv `/opt/oracle-live-voting/venv` → `requirements.lock` →
Migration und Seed → systemd-Service `oracle-live-voting` → `/readyz` bis 30 s prüfen → bei Fehler **automatischer Rollback** auf das vorherige Release →
nur die 5 neuesten Releases bleiben. Beim SSH-Host wird `StrictHostKeyChecking=accept-new` verwendet.

Zielstruktur:

```
/opt/oracle-live-voting/releases/<release-id>/   current -> aktives Release   venv/
/opt/oracle-live-voting/shared/{app.env, oracle-live-voting.db, logs/, backups/, initial-admin-password.txt}
```

Beim ersten Deployment werden `SECRET_KEY` und `ADMIN_PASSWORD` erzeugt (`app.env`, Rechte 600) und das Passwort einmalig in
`initial-admin-password.txt` (600) abgelegt – Abruf-Befehl und Hinweis zum Löschen gibt das Skript aus. Spätere Deployments überschreiben Secrets nie.
`app.env` setzt `SESSION_COOKIE_SECURE=false` nur, damit der **HTTP-Test ohne HTTPS** funktioniert.

### Betrieb auf dem Server

```bash
systemctl status oracle-live-voting
sudo systemctl restart|stop|start oracle-live-voting
journalctl -u oracle-live-voting -f                        # Logs gehen ins journald (SELinux-sicher)
curl -s http://127.0.0.1:8080/readyz
ss -ltnp | grep 8080
cd /opt/oracle-live-voting/current && set -a && . ../shared/app.env && set +a \
  && /opt/oracle-live-voting/venv/bin/flask --app wsgi:app backup      # Backup der Server-DB
```

Manueller Rollback: `ln -sfn /opt/oracle-live-voting/releases/<alt> /opt/oracle-live-voting/current && sudo systemctl restart oracle-live-voting`.
Bei SELinux-Meldungen (Oracle Linux): `sudo ausearch -m avc -ts recent`, ggf. `sudo restorecon -Rv /opt/oracle-live-voting`.

### Firewall und OCI (immer manuell)

Das Skript ändert weder firewalld noch OCI. Für den gewählten Port (Beispiel 8080):

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

OCI Security List **oder** NSG: *Stateful Ingress*, Source `0.0.0.0/0`, Protocol TCP, Destination Port = gewählter Port.

### Finaler Konferenzbetrieb: Nginx + HTTPS + DNS (empfohlen)

Direkter HTTP-Betrieb auf einem Hochport ist nur ein Test. Besser: DNS-Name auf die öffentliche IP, Nginx auf 80/443, Let's Encrypt.

1. DNS: A-Record `voting.example.org` → `<host-ip>`.
2. Nginx installieren, `deploy/nginx.conf.example` anpassen; Ports 80/443 freigeben (firewalld + OCI, manuell).
3. Zertifikat: `sudo certbot --nginx -d voting.example.org` (oder `certbot certonly --webroot`).
4. `app.env`: `HOST=127.0.0.1` (Gunicorn nur lokal), `PROXY_FIX_ENABLED=true` (genau ein Hop), `SESSION_COOKIE_SECURE=true`,
   `PUBLIC_BASE_URL=https://voting.example.org`; danach `sudo systemctl restart oracle-live-voting`.
5. Den Hochport in Firewall/OCI wieder schließen.

### SQLite-Grenzen und PostgreSQL

SQLite im WAL-Modus mit `busy_timeout=5000` und kurzen Schreibtransaktionen reicht für das Ziel (100–300 Teilnehmer, 45–60 s Voting-Fenster, kurzzeitig 5–10 Stimmen/s,
Polling alle 2 s). Deshalb: **genau ein Gunicorn-Worker mit acht Threads** (Rate-Limit-Zähler und State-Cache liegen im Prozessspeicher). Mehr Worker oder mehrere Server erfordern
PostgreSQL: `DATABASE_URL=postgresql+psycopg://...`, Treiber installieren, `flask db upgrade`, Rate-Limit-Storage auf Redis umstellen. Der Code nutzt nur SQLAlchemy (keine SQLite-spezifischen SQL-Strings).

### Notfallablauf für die Konferenz

- **App hängt/antwortet nicht:** `sudo systemctl restart oracle-live-voting` – der Zustand liegt in SQLite und bleibt erhalten, Teilnehmer-Browser setzen das Polling automatisch fort.
- **Runde verhauen:** Admin → „Aktuelle Runde zurücksetzen“ (löscht nur diese Runde).
- **Gleichstand:** Stichwahl auslösen oder Challenge-Thema manuell wählen.
- **Thema passt nicht:** Reserve-Thema einer Option zuordnen (im Zustand `waiting`).
- **Netz fällt aus:** Challenge läuft auch ohne Teilnehmer-Browser weiter; Admin und Beamer pollen selbst.
- **Vorher:** `flask backup` und Healthcheck von außen (`/readyz`) prüfen; Admin-Passwort bereithalten; Beamer-Seite `/screen` im Vollbild öffnen.
- **Danach:** `flask export-json` sichert Ergebnisse und Scorecards.

### Sicherheit in Kürze

CSRFProtect (Header `X-CSRFToken`, Meta-Tag), strikte CSP ohne Inline-Skripte, `X-Frame-Options`, `nosniff`, Request-Limit 16 KB, Rate Limits
(Admin-Login, Vote 10/min pro Client), Session-Cookies `HttpOnly`/`SameSite=Lax`, Admin-Passwort nur aus Umgebung (Vergleich in konstanter Zeit),
keine Stacktraces im Browser, Auditlog ohne Passwörter, Cookies, Tokens oder vollständige Client-IDs.
