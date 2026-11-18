# Session-Protokoll: Runde 1 - Shell Health-Check für Alert-Log und Listener

> Vorläufig: Martin ordnet den Dashboard-Ablauf der Runde 1 zu. Das Transcript nennt Claude Code
> und `claude-sonnet-5`; Martin erinnert Codex. Diese Werkzeugzuordnung ist ungeklärt.
> SSH-Ziel, Schlüsselpfad und lokale Bind-Adresse wurden für die öffentliche Fassung ersetzt.

## Rahmen

| Merkmal | Befund |
| --- | --- |
| Datum und Zeiten | Abstimmung 2026-11-17 15:07, Spielzeit 15:11-15:17 CET (Martin). |
| Werkzeug und Modell | Martin: Codex; zugeordnetes Transcript: Claude Code, `claude-sonnet-5`. |
| Skills/Plugins/Rules | Projektregeln gelesen; `frontend-design` um 15:15 aufgerufen. |
| Ausführung | Die AI führte Befehle aus, schrieb eine Datei und startete den lokalen Prozess. |
| Umgebung | Lokal WSL2; remote Oracle 26ai, CDB DSWNWST und zwei PDBs im API-Ergebnis. |
| Ausgangszustand | SSH-Zugang und Projektstruktur vorhanden; Dashboard-Datei noch nicht vorhanden. |
| Quelle | Claude-JSONL `<session>.jsonl`, Write-Ereignis 15:13. |

## Ablauf in Kürze

| # | Zeit (CET) | Prompt (Kurzform) | Was die AI tat | Ergebnis |
| --- | --- | --- | --- | --- |
| 1 | 15:09 | Listener prüfen | SSH und Prozessabfrage | `tnslsnr LISTENER` lief. |
| 2 | 15:10 | HTML-App, Port 8080 | Bestand/Regeln gelesen; Python-Datei gebaut | Datei um 15:13 erstellt. |
| 3 | 15:13 | derselbe Prompt | App gestartet und HTTP/API abgefragt | HTTP 200; API: SSH-Timeout. |
| 4 | 15:13-15:14 | derselbe Prompt | SSH separat und API erneut geprüft | Drei SSH-Proben ok; API `ok: true`. |
| 5 | 15:15 | Styling | Design-Skill aufgerufen | Änderung vor 15:17 nicht belegt. |

## Prompts im Wortlaut

Die drei Nutzereingaben im zugeordneten Transcript, mit Tippfehlern:

### 2026-11-17 15:09 CET

```text
connect to database server and check for process for listener tnslsnr and show me the result
```

### 2026-11-17 15:10 CET

```text
create a local app in html easy style, show me the process, start local app on port 8080,
gather information in real time by ssh
```

### 2026-11-17 15:15 CET

```text
make it more fashionable
```

## Verlauf Schritt für Schritt

1. Vor dem ersten Befehl des Ausschnitts lag der Listener-Prompt vor. Eine eigene Planungsphase
   davor ist nicht erfasst.
2. Die AI prüfte den Listener per SSH und sah `tnslsnr LISTENER` mit PID 3804.
3. Sie prüfte `app/tools/`, las ein vorhandenes Smoke-Test-Skript und die Projektregeln.
   Danach wählte sie eine Python-Einzeldatei mit SSH-Abfrage und lokaler HTTP-Seite.
4. Um 15:13 schrieb sie `app/tools/dbmonitor.py`, startete Port 8080 und fragte Seite/API ab.
5. HTTP 200 belegte den Seitenstart. Die API meldete SSH-Timeout. Die AI erkannte dies selbst
   an der Ausgabe und prüfte SSH separat; auch dieser Versuch lief zunächst in einen Timeout.
6. Danach gelangen drei SSH-Proben. Die API meldete `ok: true`, Listener- und DB-Status.
   Es ist keine Rückfrage der AI und keine Korrektur durch Martin in diesem Ausschnitt erfasst.
7. Auf den Styling-Prompt rief die AI `frontend-design` auf. Die nächste Dateiänderung lag
   nach 15:17 und zählt nicht zum Bühnen-Endstand.

## Resultate

Gekürzte Befehlsausgaben aus dem Transcript, mit entferntem SSH-Ziel:

```text
15:09  oracle 3804 ... tnslsnr LISTENER -inherit
15:13  started ... python3 app/tools/dbmonitor.py 8080
15:13  homepage: 200
15:13  {"ok": false, "error": "ssh: ... Connection timed out"}
15:14  still-ok-1 still-ok-2 still-ok-3
15:14  {"ok": true, "listener": {"running": true},
        "database": {"name": "DSWNWST", "open_mode": "READ WRITE"}}
```

## Wer hat was gemacht

Gezählt werden die belegten Schritte des Dashboards. Der nicht ausgeführte Alert-Log-Teil
bekommt keine Marke.

| # | Schritt | Marke |
| --- | --- | --- |
| 1 | Vorhandenen SSH-Zugang und Projektstruktur bereitstellen | P |
| 2 | Listener-Prozess vor der Spielzeit prüfen | P |
| 3 | Dashboard-Ansatz wählen und Datei schreiben | A |
| 4 | App starten und HTTP prüfen | A |
| 5 | SSH-Timeout aus der Ausgabe erkennen und separat prüfen | A |
| 6 | Status erneut abfragen und Erfolg belegen | A |

AI = (4 + 0,5 x 0) / 6 = 66,7 %. Martin = (0 + 0,5 x 0) / 6 = 0 %.
Vorbereitung = 2 / 6 = 33,3 %. Für die Gesamtaufgabe ist keine Erfolgsquote belegt.

## Zeiten und Token

| Grösse | Befund |
| --- | --- |
| Abstimmung | 2026-11-17 15:07 CET laut Martin; nicht im Transcript gemessen. |
| Spielzeit | 2026-11-17 15:11-15:17 CET laut Martin. |
| Belegter Ablauf | 2026-11-17 15:09-15:15 CET im Claude-Transcript. |
| Claude-Aufrufe 15:09-15:17 | 13 unterschiedliche API-Message-IDs. |
| Claude-Token | Input 26; Cache-Erstellung 24 784; Cache-Lesen 880 533; Output 20 349. |
| Codex-Token für die Spielzeit | nicht erfasst. |

## Was nicht passiert ist

- Ein Lesen oder Auswerten des Oracle-Alert-Logs ist hier nicht belegt.
- Ein Shell-Skript für Alert-Log und Listener wurde hier nicht erstellt.
- Stimmenzahlen der Abstimmung sind im Transcript nicht enthalten.
- Ein Codex-Verlauf für 15:11-15:17 wurde nicht gefunden.
- Die Styling-Änderung, ein Dauertest und ein Sicherheitstest vor 15:17 sind nicht belegt.

## Stand nach der Session

- Um 15:17 lag `app/tools/dbmonitor.py` vor; der Python-Prozess auf Port 8080 lief.
- Die Datei wurde nach 15:17 weiterbearbeitet. Der heutige Dateistand ist nicht der Bühnen-Endstand.
- Ein späteres Stoppen des Prozesses ist in diesem Ablauf nicht erfasst.
- In diesem Ablauf wurden keine Lab-Objekte erstellt oder aufgeräumt.

## Beobachtungen für das Manuskript

1. Der Listener-Prozess war um 15:09 per `ps` sichtbar.
2. Der HTML-App-Prompt führte zu einer lokalen Python-Datei mit SSH-Abfrage.
3. Die Startseite antwortete mit HTTP 200, während die API einen SSH-Timeout meldete.
4. Die AI prüfte den Timeout anhand der Ausgabe mit einem separaten SSH-Versuch.
5. Nach drei gelungenen SSH-Proben meldete die API `ok: true`.
6. Ein Alert-Log-Check ist im Ablauf nicht belegt.
7. Der Design-Skill lief vor Spielende an; die Dateiänderung kam erst danach.
8. Martins Werkzeugangabe und die Modellangabe des Transcripts widersprechen sich.

## Mein Takeaway

Ausstehend - Martin wurde nach seinem eigenen Satz gefragt; die AI formuliert ihn nicht.

## Anhang: Code im Wortlaut, Stand 15:17

Code des Write-Ereignisses um 15:13. SSH-Ziel, Schlüsselpfad und Bind-Adresse sind ersetzt.
Der ausführbare Code im ZIP (`hmb-shell-health-check-martin.zip`) liest beide Angaben aus Umgebungsvariablen
(`HMB_SSH_TARGET`, `HMB_SSH_KEY`).

<!-- markdownlint-disable MD013 -->
```python
#!/usr/bin/env python3
"""Live status dashboard for the DSWNWST demo host.

Polls the listener process and CDB/PDB availability over SSH and serves
a small auto-refreshing HTML page. Standard library only, no deps.

Usage: app/tools/dbmonitor.py [port]   (defaults to 8080)
"""
import json
import re
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SSH_KEY = "[SSH-SCHLUESSELPFAD ENTFERNT]"
SSH_HOST = "[SSH-ZIEL ENTFERNT]"
ORACLE_SID = "DSWNWST"
ORACLE_HOME = "/u01/app/oracle/product/26.0.0/dbhome_1"
CACHE_TTL = 3  # seconds; avoid hammering the shared host on rapid polls

REMOTE_CMD = f"""
echo '===LISTENER==='
ps -ef | grep tnslsnr | grep -v grep
echo '===DB==='
sudo -u oracle bash -lc 'export ORACLE_SID={ORACLE_SID} ORACLE_HOME={ORACLE_HOME}; $ORACLE_HOME/bin/sqlplus -S / as sysdba <<EOF
set heading off feedback off pagesize 0 linesize 300 trimspool on
select name || chr(124) || open_mode || chr(124) || database_role || chr(124) || log_mode from v\\$database;
select instance_name || chr(124) || status || chr(124) || database_status from v\\$instance;
select name || chr(124) || open_mode || chr(124) || restricted from v\\$pdbs;
exit
EOF'
echo '===END==='
"""

_cache = {"data": None, "ts": 0.0}


def gather_status():
    try:
        proc = subprocess.run(
            ["ssh", "-i", SSH_KEY, "-o", "ConnectTimeout=5", SSH_HOST, REMOTE_CMD],
            capture_output=True, text=True, timeout=20,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "timestamp": time.time(), "error": "ssh timeout"}

    out = proc.stdout
    if "===END===" not in out:
        err = proc.stderr.strip() or f"ssh exited {proc.returncode}"
        return {"ok": False, "timestamp": time.time(), "error": err}

    def section(a, b):
        m = re.search(re.escape(a) + r"\n(.*?)\n" + re.escape(b), out, re.S)
        return m.group(1) if m else ""

    listener_raw = section("===LISTENER===", "===DB===").strip()
    db_raw = section("===DB===", "===END===").strip()

    listener = {
        "running": "tnslsnr" in listener_raw,
        "detail": listener_raw or "no tnslsnr process found",
    }

    db_lines = [l for l in db_raw.splitlines() if l.strip() and "|" in l]
    database = instance = None
    pdbs = []
    if db_lines:
        p0 = db_lines[0].split("|")
        if len(p0) >= 4:
            database = {"name": p0[0], "open_mode": p0[1], "role": p0[2], "log_mode": p0[3]}
        if len(db_lines) > 1:
            p1 = db_lines[1].split("|")
            if len(p1) >= 3:
                instance = {"name": p1[0], "status": p1[1], "database_status": p1[2]}
        for l in db_lines[2:]:
            p = l.split("|")
            if len(p) >= 3:
                pdbs.append({"name": p[0], "open_mode": p[1], "restricted": p[2]})

    error = db_raw if "ORA-" in db_raw else None

    return {
        "ok": error is None and database is not None,
        "timestamp": time.time(),
        "listener": listener,
        "database": database,
        "instance": instance,
        "pdbs": pdbs,
        "error": error,
    }


def get_status():
    now = time.time()
    if _cache["data"] is None or now - _cache["ts"] > CACHE_TTL:
        _cache["data"] = gather_status()
        _cache["ts"] = now
    return _cache["data"]


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DSWNWST Live Status</title>
<style>
  body { margin: 0; padding: 2rem; background: #0f172a; color: #e2e8f0; font-family: system-ui, sans-serif; }
  h1 { font-size: 1.4rem; margin-bottom: .25rem; }
  .sub { color: #94a3b8; margin-bottom: 1.5rem; font-size: .9rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; }
  .card { background: #1e293b; border-radius: 10px; padding: 1.25rem; border: 1px solid #334155; }
  .card h2 { margin: 0 0 .75rem; font-size: 1rem; color: #cbd5e1; }
  .row { display: flex; justify-content: space-between; padding: .25rem 0; font-size: .9rem; border-bottom: 1px solid #263349; }
  .row:last-child { border-bottom: none; }
  .row span:first-child { color: #94a3b8; }
  .dot { display: inline-block; width: .6rem; height: .6rem; border-radius: 50%; margin-right: .4rem; }
  .ok { background: #22c55e; }
  .bad { background: #ef4444; }
  .err { color: #fca5a5; font-size: .85rem; margin-top: .75rem; white-space: pre-wrap; }
  footer { margin-top: 1.5rem; color: #64748b; font-size: .8rem; }
</style>
</head>
<body>
  <h1>DSWNWST &mdash; Live Status</h1>
  <div class="sub" id="meta">connecting&hellip;</div>
  <div class="grid">
    <div class="card">
      <h2><span class="dot" id="lsn-dot"></span>Listener</h2>
      <div class="row"><span>Status</span><span id="lsn-status">&ndash;</span></div>
      <div class="row"><span>Process</span><span id="lsn-detail">&ndash;</span></div>
    </div>
    <div class="card">
      <h2><span class="dot" id="db-dot"></span>CDB DSWNWST</h2>
      <div class="row"><span>Open mode</span><span id="db-mode">&ndash;</span></div>
      <div class="row"><span>Role</span><span id="db-role">&ndash;</span></div>
      <div class="row"><span>Log mode</span><span id="db-log">&ndash;</span></div>
      <div class="row"><span>Instance</span><span id="db-instance">&ndash;</span></div>
    </div>
    <div class="card">
      <h2>PDBs</h2>
      <div id="pdb-list"></div>
    </div>
  </div>
  <div class="err" id="err"></div>
  <footer>polling /api/status every 4s &middot; data gathered live via SSH</footer>
<script>
function setText(id, value) { document.getElementById(id).textContent = value; }

async function refresh() {
  try {
    const res = await fetch('/api/status', {cache: 'no-store'});
    const d = await res.json();
    const t = new Date(d.timestamp * 1000).toLocaleTimeString();
    setText('meta', 'last update ' + t + (d.ok ? '' : ' (error)'));

    const lsnOk = d.listener && d.listener.running;
    document.getElementById('lsn-dot').className = 'dot ' + (lsnOk ? 'ok' : 'bad');
    setText('lsn-status', lsnOk ? 'running' : 'not found');
    setText('lsn-detail', (d.listener && d.listener.detail) || '-');

    const dbOk = d.database && d.database.open_mode === 'READ WRITE';
    document.getElementById('db-dot').className = 'dot ' + (dbOk ? 'ok' : 'bad');
    setText('db-mode', d.database ? d.database.open_mode : '-');
    setText('db-role', d.database ? d.database.role : '-');
    setText('db-log', d.database ? d.database.log_mode : '-');
    setText('db-instance', d.instance ? (d.instance.name + ' / ' + d.instance.status + ' / ' + d.instance.database_status) : '-');

    const pdbList = document.getElementById('pdb-list');
    pdbList.innerHTML = '';
    (d.pdbs || []).forEach(p => {
      const row = document.createElement('div');
      row.className = 'row';
      const left = document.createElement('span');
      left.textContent = p.name;
      const right = document.createElement('span');
      right.textContent = p.open_mode + (p.restricted === 'YES' ? ' (restricted)' : '');
      row.appendChild(left); row.appendChild(right);
      pdbList.appendChild(row);
    });

    setText('err', d.error || '');
  } catch (e) {
    setText('meta', 'connection error: ' + e);
  }
}
refresh();
setInterval(refresh, 4000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            body = json.dumps(get_status()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = ThreadingHTTPServer(("localhost", port), Handler)
    print(f"DSWNWST status dashboard on http://localhost:{port}")
    server.serve_forever()
```
<!-- markdownlint-restore -->
