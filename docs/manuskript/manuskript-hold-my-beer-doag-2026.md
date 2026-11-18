---
title: "Denn sie wissen nicht was sie tun - Oracle live mit Oehrli, Berger und KI"
subtitle: "Hold my Beer: AI live im DBA-Alltag. Manuskript, DOAG Konferenz 2026, Nürnberg, 17. November 2026"
author:
  - Stefan Oehrli
  - Martin Berger
date: 2026-11-18
lang: de-CH
---

## Worum es geht

Eine Session ohne festgelegten Inhalt: Das Publikum stimmt per Handy ab, welche Oracle-Aufgabe zwei DBAs als
Nächstes angehen, und die beiden lösen sie live mit AI. Die Umgebung ist vorbereitet, das Ergebnis nicht. Dieses
Manuskript fasst zusammen, was dabei und in den Arbeits-Sessions am 17. und 18. November 2026 gelaufen ist - mit
dem Ziel, dass ihr AI im DBA-Alltag mit weniger Lehrgeld einsetzen könnt.

- **Format:** drei Runden ("Warm-up", "DBA-Alltag", "Bruchstelle"), je drei Optionen - eine von Stefan, eine von
  Martin, eine gemeinsame. 60 s Abstimmung, dann live lösen, danach Bewertung auf einer Scorecard ("AI richtig",
  "AI halluziniert", "Falsches Problem gelöst", "DBA-Instinkt gewinnt").
- **Rollen:** Stefan Oehrli (Oracle ACE Director) als Security-Nerd - "Wer hat da GRANT DBA gemacht?". Martin
  Berger (Oracle ACE Pro) als Automation-Nerd - "Warum von Hand, wenn es ein Playbook gibt?".
- **Voting-App:** eine eigene App von Martin (Flask, SQLite) unter `https://hmb.oradba.ch`, Aufruf per QR-Code,
  kein Login, keine personenbezogenen Daten. Veröffentlicht über einen Cloudflare Tunnel: Der Host braucht für
  die App keinen eingehenden Port, HTTPS endet bei Cloudflare, das Publikum nutzt mobile Daten statt
  Konferenz-WLAN. Ergebnis: 90 Geräte, 233 Stimmen.

Alle Zeiten in CET. Detailprotokolle mit jedem Schritt, Tool-Aufruf, Token und dem vollständigen Code liegen in
im ZIP zu dieser Session (siehe "Nächste Schritte").

## So steigt ihr ein

### Setup

<!-- markdownlint-disable MD013 MD060 -->
| Baustein | In der Session |
| ---------- | ------------------------------ |
| AI | Claude Code (CLI), Modell Claude Opus 5.5; weitere Tools bereit (Codex, GitHub Copilot, ChatGPT, Microsoft Copilot) |
| Fachwissen für die AI | Skill `oracle-audit` (Unified Auditing, Namenskonventionen, 19c/26ai-Unterschiede), von der AI selbst geladen |
| Lab | `seclab` aus `oradba-labs`: Docker, Oracle Database 19c (19.27) und Oracle AI Database 26ai Free (23.26.3), PDB `DEMOPDB` mit `SCOTT` und `TVD_HR`, Pure Unified Auditing |
| Reset | Restore Point `LAB_BASELINE`, `make reset LAB=seclab` setzt per Flashback zurück |
| Einstieg | `make talk-start`: Prüfung, Demo-Startpunkte (`setup.sql`), je Runde ein Terminal mit `sqlplus / as sysdba` |
| Beweis | je Demo ein `check.sql` - das Vorher- und Nachher-Bild, nicht die Aussage der AI |
<!-- markdownlint-restore -->

```bash
make talk-check    # liest nur: App, Lab, Demo-Startpunkte
make talk-start    # Startpunkte setzen, Deck, Browser und Terminals öffnen
make reset LAB=seclab    # nach der Session: zurück auf LAB_BASELINE
```

Ein Flashback setzt weder Dateien noch das spfile zurück. Wer `sqlnet.ora` oder `WALLET_ROOT` ändert, braucht
ein `reset.sql` zusätzlich zum Flashback.

### Arbeitsmodus

Geplant war "die AI schreibt, der DBA führt aus". Live lief es anders, weil der Prompt es verlangte: Die AI
führt selbst aus, per `docker exec` und `sqlplus / as sysdba`, und Claude Code fragt vor jedem Aufruf nach einer
Freigabe. Der Review-Punkt verschiebt sich damit vom Statement auf den Freigabe-Dialog und das Resultat danach.
Beide Wege funktionieren - entscheidet euch bewusst.

### Guardrails als Checkliste

Diese Regeln lagen als globale Rules in Claude Code und haben den Verlauf sichtbar beeinflusst:

- [ ] **AUDIT immer mit NOAUDIT** - jede Policy hat ihren Rückweg, und der wird getestet
- [ ] **Klärende Fragen vorab, in einer Runde**, inklusive Autonomie: Darf die AI das Lab jetzt ändern,
  committen, einen PR öffnen?
- [ ] **Plan zeigen ab drei Dateien**, bevor gebaut wird
- [ ] **Nichts still überspringen:** Was nicht gelaufen ist, wird mit Namen genannt
- [ ] **Geteiltes Lab:** kein Reset und kein neuer Mechanismus ohne Absprache
- [ ] **Aufhören statt weiterdrücken,** wenn ein Weg nicht trägt
- [ ] **Nie committen ohne ausdrückliche Anweisung**
- [ ] **Secrets nie in Prompt, Skript oder Befehlszeile:** Lab-Passwörter über stdin oder Secret-Dateien (Modus
  600), nie im Chat
- [ ] **Keine Kundendaten,** nur Lab-Daten

Wichtig: Geladene Rules sind keine befolgten Rules. Wo die AI abgewichen ist, steht im nächsten Abschnitt.

## Was AI heute kann und wo sie scheitert

Belege aus vier Arbeitsaufträgen: ein Live-Dashboard für Listener und Datenbank per SSH (Runde 1, Martin, auf
seinem 26ai-Host), Unified Audit für einen privilegierten User (Runde 2), ein absichtlich fehlerhaftes
PL/SQL-Package für das Code-Review (Runde 3) - beide auf `seclab-db26`, DEMOPDB - und eine APEX-Demo, die in
einer zweiten Session parallel ab 15:35 lief und keine abgestimmte Runde war.

### Was getragen hat

<!-- markdownlint-disable MD013 MD060 -->
| Stärke | Beleg |
| ---------- | ------------------------------ |
| Erst schauen, dann bauen | Vor dem ersten Statement las die AI Repo, Runbook, Container und Datenbank. Befund: der verlangte User CLAUS existiert nicht; APEX, ORDS und HTTP-Port fehlen |
| Fachlicher Mehrwert, ungefragt | Rolle DBA enthält `AUDIT SYSTEM` und `AUDIT ANY` - der Auditierte kann sein Audit abschalten |
| Lücke im eigenen Design belegt | Ein `execute immediate` auf `SCOTT.EMP` erfasste nur die Privilegien-Policy, nicht `ACTIONS ALL ONLY TOPLEVEL` |
| Seiteneffekt im Hersteller-Image | Das ORDS-Image hätte bei der APEX-Installation das DEFAULT-Profil auf `PASSWORD_LIFE_TIME UNLIMITED` gesetzt. Die AI installierte APEX selbst und belegte: Profil vor und nach bei 180 |
| Verifikation am Ergebnis | Rollback ungefragt getestet (NOAUDIT, DROP, 0 Policies übrig, dann neu eingerichtet) |
| Widerspruch in der Ausgabe erkannt | Runde 1: Startseite HTTP 200, die API meldete aber einen SSH-Timeout. Die AI prüfte SSH separat und belegte danach `ok: true` mit Listener- und DB-Status |
| Eigene Fehler selbst gefunden | ORA-00904 (falscher Spaltenname), zweimal `sed -i ''` gegen GNU sed, stiller Abbruch durch SIGPIPE unter `pipefail` - jeder an der Ausgabe erkannt, im nächsten Schritt behoben |
| Tempo bei Routine | Dashboard mit SSH-Abfrage geschrieben, gestartet und geprüft in rund 4 min (15:10 bis 15:14); drei Policies mit Test, Report und getestetem Rückweg in 4 min 21 s; ein Package mit 16 dokumentierten Befunden und Smoke-Test in gut 5 min; APEX-Installation 3 min, ORDS-Start 41 s |
| Grenze bei Daten | commitende Prozeduren im Smoke-Test bewusst nicht aufgerufen; `INHERIT PRIVILEGES` an APEX nicht vergeben |
| Secrets | Lab-Passwörter kamen nie in den Chat oder auf die Befehlszeile; im Trail steht `identified by *` |
<!-- markdownlint-restore -->

### Wo sie gescheitert ist

<!-- markdownlint-disable MD013 MD060 -->
| Grenze | Beleg |
| ---------- | ------------------------------ |
| Aufgabe verschoben | Runde 1 hiess "Shell Health-Check für Alert-Log und Listener". Der Prompt verlangte eine HTML-App - gebaut wurde ein Python-Dashboard für Listener- und DB-Status. Das Alert-Log kam nicht vor, und niemand hat es eingefordert |
| Annahmen statt Fragen | CLAUS fehlte - die AI wählte User, PDB und Rolle selbst, ohne Rückfrage. Offen genannt, aber eine Annahme. Gefragt hat sie nur, wo der Prompt es verlangte |
| Nicht gelaufen | Der Data-Pump-Export als Claus lief nie: Die AI wartete auf ein OK, das nicht kam. Die Data-Pump-Policy ist eingeschaltet, aber ungetestet |
| Ohne Browser kein App Builder | Die APEX-App existiert nicht. 11 Aufrufe der internen, gewrappten Wizard-Engine scheiterten an immer neuen Annahmen (Workspace, Session, Theme), dann brach die AI ab und fragte |
| Security-Haltung mit Lücke | `APEX_ADMINISTRATOR_ROLE` an `LAB_ADMIN` als "vorübergehend" vergeben - entzogen erst nach der Session, auf Zuruf. Das Workspace-Passwort steht in `setup.sql` als Literal im SQL-Text |
| Rules nicht durchgehend befolgt | sechs Scripts ohne Plan, keine Task-Datei, zwei Mechanismus-Entscheide ohne Rückfrage, Skill für Script-Header nicht genutzt |
| Zeit ist Warten | Die längsten Abschnitte waren offene Freigaben: 17 h über Nacht, einmal knapp 30 min |
| Nachträglich rekonstruiert | Welches Werkzeug Runde 1 spielte, ist offen: Martin erinnert Codex, das Transcript zeigt Claude Code mit `claude-sonnet-5`. Live mitschreiben schlägt jedes Gedächtnis |
| Geteiltes Lab | Am Slotende liefen zwei AI-Sessions gegen dieselbe PDB; das Lab war am nächsten Morgen noch nicht zurückgesetzt |
<!-- markdownlint-restore -->

## Prompt-Muster, die funktioniert haben

**Rolle, Ziel, Ausführung und Rückweg in einem Satz.** Die AI lud dazu selbst den passenden Skill, entwarf drei
Policies und lieferte NOAUDIT ungefragt getestet mit:

```text
Arbeite als DB Security spezialist und unterstütze mich beim erstellen von Oracle Unified audit policies für hoch
privilegierte User. Erstelle die Scripte für die 26ai Lab db. führe diese direkt aus und erstelle zudem auch gleich
die noaudit policies. der hoch priveligierte user heist Claus.
```

**Beweis nachfordern.** Ein kurzer Nachschub während der Arbeit brachte Testuser, Test- und Report-Script - und
damit 17 Audit-Records als Beleg statt einer Behauptung:

```text
erstell mir doch gleich einen test user in der pdb, mit eine test script und einem reporting script
```

**Erst zeigen, dann ausführen.** Die AI zeigte die Statements, legte einen Plan vor und wartete auf das OK. Das
schützt - aber nur, wenn das OK auch kommt (hier kam es nicht, der Export lief nie):

```text
Teste noch den Data Pump Export als Claus. aber zeige mir zuerst die create audit policy statements
```

**Rückfragen und Vorprüfung verlangen.** Ergebnis: sechs read-only Prüfungen, dann vier Fragen in einer Runde,
jede mit Empfehlung, inklusive "Darf ich jetzt am Lab ändern?":

```text
kannst du eine kleine APEX demo app für die oracle26ai DB DEMOPDB bauen? stelle klärende fragen, prüfe was
vorgängig noch konfiguriert werden muss.
```

**Übungsmaterial erzeugen lassen.** Die AI baute ein kompilierendes Package mit 9 Sicherheitslücken und 7 Fehlern
ohne verräterische Kommentare, plus Smoke-Test und Lösungsschlüssel:

```text
wir wollen ein fehlerhaftes PL/SQL package analisieren. erstell zuerst ein package für das scott oder hr schema
in der 26ai db (DEMOPDB) baue das falsch package mit sicherheitslücken und fehler. Martin soll es dann analisiere.
```

**Kontext statt Lösung (vorbereitet, live nicht verwendet).** Release, Architektur und Werkzeug in den Prompt,
die Fallen nicht verraten, den Beweis verlangen:

```text
Ich bin DBA einer Oracle Database 19c (19.27, Multitenant), Unified Auditing im Pure Mode. In der PDB
DEMOPDB hat ein neuer Kollege, HMB_DBA, die Rolle DBA bekommen. Der Applikations-Account HMB_APP liest
Daten aus TVD_HR.EMPLOYEES. Ich arbeite in SQL*Plus als SYSDBA.

Auftrag:
1. Auditiere alles, was privilegierte User in DEMOPDB tun - aber nicht den Applikations-Account.
2. Liefere den Rückweg gleich mit: wie schalte ich das sauber wieder ab?
3. Beweis es mir im Audit-Trail: HMB_DBA erscheint, HMB_APP nicht.

Gib mir die SQL-Statements Schritt für Schritt, jeweils mit einem Satz, was sie tun.
```

**Kurz und offen - schnell, aber am Auftrag vorbei.** Martins drei Prompts in Runde 1 brachten in vier
Minuten ein laufendes Dashboard. Das Alert-Log aus der abgestimmten Aufgabe stand in keinem davon - also baute
die AI es auch nicht:

```text
connect to database server and check for process for listener tnslsnr and show me the result

create a local app in html easy style, show me the process, start local app on port 8080,
gather information in real time by ssh

make it more fashionable
```

Prompts im Wortlaut, Tippfehler belassen.

## Session-Ablauf und Ergebnis

### Abstimmungen

<!-- markdownlint-disable MD013 MD060 -->
| Runde | Abstimmung | A (Stefan) | B (Martin) | C (gemeinsam) | Gespielt | Scorecard |
| --- | --- | --- | --- | --- | --- | --- |
| 1 Warm-up | 15:07 | 10G-Verifier: 16 | Shell Health-Check Alert-Log/Listener: **37** | Data Pump Remap: 27 | B, 15:11-15:17 | leer |
| 2 DBA-Alltag | 15:18 | Unified Audit inkl. NOAUDIT: **29** | RMAN CLI-Skript: 24 | Listener/sqlnet.ora Hardening: 25 | A, 15:20-15:31 | "Aufgabe teilweise abgeschlossen" |
| 3 Bruchstelle | 15:31 | TDE mit WALLET_ROOT: 10 | Refreshable PDB Clone: 24 | AI-Code-Review PL/SQL: **41** | C gewonnen, Challenge nicht gestartet (Slotende 15:45) | - |
<!-- markdownlint-restore -->

### Runden kompakt

- **Runde 1 - Shell Health-Check (Martin):** drei Prompts, Martins 26ai-Host per SSH, WSL2. Um 15:09 der
  Listener-Prozess per `ps` belegt, um 15:13 `dbmonitor.py` geschrieben und gestartet: lokale Seite auf Port
  8080, Listener-, CDB- und PDB-Status alle 4 s per SSH. Der erste API-Aufruf lief in einen SSH-Timeout, die AI
  prüfte selbst nach, um 15:14 `ok: true`. Kein Alert-Log, kein Shell-Skript; der Styling-Prompt um 15:15
  wirkte erst nach Spielende.
- **Runde 2 - Unified Audit (Stefan):** Statt des vorbereiteten 19c-Prompts lief ein eigener Prompt auf 26ai.
  Ergebnis: User CLAUS, drei lokale Policies (`ACTIONS ALL ONLY TOPLEVEL`, 20 kritische Systemprivilegien,
  `COMPONENT = DATAPUMP ALL`), Test, Report, getesteter Rückweg. Offen: Data-Pump-Test. Die AI arbeitete in der
  Runde rund 5 min, alle Prompts liegen zwischen 15:22 und 15:31.
- **Runde 3 - AI-Code-Review:** Das Package `SCOTT.HMB_EMP_API` entstand zwischen 15:34 und 15:39 noch im Slot,
  die Analyse durch Martin nicht mehr - sie ist auch danach nicht dokumentiert. Der Schlüssel in Kurzform:

<!-- markdownlint-disable MD013 MD060 -->
| Art | Befunde |
| ---------- | ------------------------------ |
| Sicherheitslücken (9) | hartkodiertes Passwort in der Spec, für PUBLIC lesbar; Klartext-Passwort im Log; Fail-open-Login über `when others then return true`; SQL Injection in vier Unterprogrammen (String-Verkettung, ORDER BY, VARCHAR2-Parameter, freie WHERE-Klausel); `GRANT EXECUTE TO PUBLIC` mit Definer Rights; `sqlerrm` an den Aufrufer |
| Fehler (7) | Salär **auf** statt **um** p_pct Prozent; Grenzwerte mit `>`/`<` statt `between`; nicht initialisierter Zähler; Puffer zu klein (ORA-06502); `delete_dept` löscht still alle Mitarbeitenden; Log-Insert ohne Längenbegrenzung (Ursache des Fail-open); keine Bind-Variable |
<!-- markdownlint-restore -->

- **APEX (eigene Arbeits-Session, 17./18.11.):** APEX 26.2 und ORDS 26.3.1 in DEMOPDB laufen, Workspace
  angelegt und verifiziert. Die App fehlt; die vereinbarte Klick-Runde im App Builder fand nicht statt.

### Wer hat was gemacht - Runde 2

**Nachträglich aus dem Protokoll vom 17.11. gezählt, nicht live erfasst.** Methode aus dem Runbook: Jeder
Schritt der erwarteten Lösung bekommt eine Marke - `P` Vorbereitung, `A` AI korrekt, `A~` AI mit Korrektur oder
Nachschub (halb/halb), `S` Stefan. Ein Fehler, den niemand korrigiert, bekommt keine Marke.

<!-- markdownlint-disable MD013 MD060 -->
| # | Schritt der Referenzlösung | Im Protokoll | Marke |
| -- | ------------ | ---------------- | ---- |
| 0 | Lab und Startpunkt | Lab mit DEMOPDB und Baseline bereit; `setup.sql` der Demo nicht verwendet | `P` |
| 1 | lokale Policy `ACTIONS ALL ONLY TOPLEVEL` | `HMB_LOC_CLAUS_ALL_ACT` | `A` |
| 2 | einschalten `BY USERS WITH GRANTED ROLES dba` | `BY CLAUS`; die AI nannte "BY USER statt BY GRANTED ROLE" selbst als Risiko, niemand korrigierte | keine |
| 3 | (Bonus) Policy für kritische Privilegien | `HMB_LOC_CLAUS_PRIV_USE`, im Trail belegt | `A` |
| 4 | Prüfung `AUDIT_UNIFIED_ENABLED_POLICIES` | im Script und Report | `A` |
| 5 | `NOAUDIT` mit derselben BY-Klausel, `DROP` | ausgeführt und ungefragt getestet | `A` |
| 6 | Beweis im Audit-Trail | erst auf Stefans Nachschub (Prompt 2); Negativbeweis fehlt, weil der Prompt keinen App-Account nannte | `A~` |
<!-- markdownlint-restore -->

Rechnung über 7 Schritte (`P` 1, `A` 4, `A~` 1, `S` 0, ohne Marke 1):

- AI: (4 + 0,5 x 1) / 7 = **64 %**
- Stefan: (0 + 0,5 x 1) / 7 = **7 %**
- Vorbereitung: 1 / 7 = **14 %**, ohne Marke: 1 / 7 = **14 %**

Gemessen am Prompt, der den User Claus ausdrücklich nannte, ist Schritt 2 korrekt (`A`): dann AI 79 %, Stefan
7 %, Vorbereitung 14 %. Die Wahl der Referenz verschiebt das Ergebnis um 15 Prozentpunkte - genau das ist der
Punkt "Kontext ist Pflicht".

### Wer hat was gemacht - Runde 1

**Von Martin nachträglich aus dem Transcript gezählt**, mit eigenen Schritten - das Runbook hatte für Runde 1
keine Referenzlösung:

<!-- markdownlint-disable MD013 MD060 -->
| # | Schritt | Marke |
| -- | ------------------------------ | ---- |
| 1 | SSH-Zugang und Projektstruktur bereitstellen | `P` |
| 2 | Listener-Prozess vor der Spielzeit prüfen | `P` |
| 3 | Dashboard-Ansatz wählen und Datei schreiben | `A` |
| 4 | App starten und HTTP prüfen | `A` |
| 5 | SSH-Timeout aus der Ausgabe erkennen und separat prüfen | `A` |
| 6 | Status erneut abfragen und Erfolg belegen | `A` |
<!-- markdownlint-restore -->

- Martins Zählung (6 Schritte, das Alert-Log zählt nicht mit): AI 4 / 6 = **67 %**, Martin **0 %**,
  Vorbereitung 2 / 6 = **33 %**
- Gegen die abgestimmte Aufgabe gezählt, wie in Runde 2 (Alert-Log als Schritt ohne Marke, 7 Schritte): AI
  4 / 7 = **57 %**, Vorbereitung 2 / 7 = **29 %**, ohne Marke 1 / 7 = **14 %**

Die AI hat alles gemacht, was verlangt war - verlangt war aber nicht die ganze Aufgabe. Runde 3 wurde nicht
gespielt, die APEX-Session war keine Runde; beide werden nicht gezählt.

## Takeaways und nächste Schritte

**AI ist kein Selbstläufer.** Nutzt sie - gezielt, mit Kontext, und prüft, was rauskommt.

1. **Ausprobieren lohnt sich.** Für Routine, Entwürfe und Übungsmaterial ist die AI schnell: wenige
   Minuten, inklusive Test und Rückweg.
2. **Kontext ist Pflicht.** Release, CDB/PDB, betroffene User: Fehlt etwas, setzt die AI Defaults - mit grosser
   Überzeugung und manchmal ohne zu fragen.
3. **Prüfen vor Ausführen.** AUDIT braucht NOAUDIT, ein Restore ein Backup, ein Skript ein Review. Lässt ihr die
   AI ausführen, ist jede Freigabe euer Review - und was nicht gelaufen ist, muss benannt werden.

So geht ihr weiter:

- [ ] Lab aufsetzen (`oradba-labs`, `seclab`) und Restore Point setzen, bevor die AI etwas ändert
- [ ] Guardrails oben als Rules oder Projekt-Instruktionen in euer AI-Werkzeug übernehmen
- [ ] Mit einer Aufgabe mit klarem Beweis starten (`check.sql`, Audit-Trail), nicht mit einer offenen
- [ ] Rückweg immer im selben Auftrag verlangen und testen lassen
- [ ] Rechte, die die AI "vorübergehend" vergibt, am Ende selbst prüfen

**Material zum Nachbauen** im ZIP zu dieser Session (DOAG-Portal) - vollständiger Code, Detailprotokolle mit
jedem Schritt, Zeiten und Token. Das ZIP enthält keine Passwörter:

<!-- markdownlint-disable MD013 MD060 -->
| Paket | Inhalt |
| ---------- | ------------------------------ |
| `hmb-unified-audit-claus.zip` | Runde 2: User, Policies, Test, Report, NOAUDIT, Drop |
| `hmb-plsql-review-martin.zip` | Runde 3: Package, Smoke-Test, Drop - ohne Lösungsschlüssel, zum selbst Reviewen |
| `loesung/18_findings_key.md` | Lösungsschlüssel zum Package: 9 Sicherheitslücken, 7 Fehler, je mit Stelle und Beleg |
| `hmb-apex-demopdb-lab.zip` | APEX und ORDS für DEMOPDB (`apex.sh`, `compose.yml`, SQL-Scripts) |
| `hmb-apex-app-build.zip` | Klick-Anleitung für die App im App Builder, Export- und Prüfschritte |
| `hmb-shell-health-check-martin.zip` | Runde 1: `dbmonitor.py` (Listener- und DB-Status per SSH, lokale Seite), SSH-Ziel und Schlüssel per Umgebungsvariable |
| `protokolle/`, `prompts/` | Session-Protokolle 17. und 18.11. (inkl. Runde 1 von Martin) (Prompts im Wortlaut, Schritte, Zeiten, Token) und die vorbereiteten Runden-Prompts |
<!-- markdownlint-restore -->

Deck, Voting-App, Themen-Pool und dieses Material:
[github.com/oehrlis/hold-my-beer](https://github.com/oehrlis/hold-my-beer).
