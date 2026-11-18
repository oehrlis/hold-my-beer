# Session-Protokoll: Claude Code im Lab - Unified Audit und PL/SQL-Review

Rohmaterial für das Session-Manuskript. Hier ist gesammelt, was in der Claude-Code-Session am
2026-11-17 auf der 26ai-Lab-DB gelaufen ist: die Prompts im Wortlaut, das Vorgehen der AI, der Code und die
Resultate. Das Protokoll wertet nicht, die Beobachtungen für das Manuskript stehen gesammelt am Ende.

## Rahmen

<!-- markdownlint-disable MD013 -->
| Punkt | Wert |
| --- | --- |
| Datum | 2026-11-17, ab etwa 15:24 (Talk-Tag DOAG, Slot hold-my-beer 15:00-15:45) |
| AI | Claude Code, Modell Claude Opus 5.5, Skill `oracle-audit` geladen |
| Ausführung | die AI führt direkt aus (per Prompt verlangt), via `docker exec` und `sqlplus / as sysdba` |
| Datenbank | `seclab-db26`, Oracle AI Database 26ai Free 23.26.3, CDB FREE, PDB `DEMOPDB` |
| Audit-Modus | Pure Unified Auditing (`V$OPTION` = TRUE) |
| Ausgangszustand | Restore Point `LAB_BASELINE`, kein `WALLET_ROOT`, keine Reste vom Privesc-Talk |
| Scripts | lokal im Scratchpad der Session, Kopie im Container unter `/tmp/audit-claus/` und `/tmp/plsql-review/` |
<!-- markdownlint-restore -->

Die Prompts weichen von [`prompts-stefan-rounds.md`](prompts-stefan-rounds.md) ab: Runde 2 lief hier auf
db26 statt db19, mit dem User CLAUS statt HMB_DBA. Das PL/SQL-Package für Martin ist neu dazugekommen.

## Ablauf in Kürze

<!-- markdownlint-disable MD013 -->
| # | Prompt (Kurzform) | Was die AI tat | Ergebnis |
| --- | --- | --- | --- |
| 1 | Unified Audit Policies für den hoch privilegierten User Claus, ausführen, NOAUDIT gleich mit | Lab gesucht, DB inspiziert, CLAUS fehlte, Defaults gewählt | Rechte-Befund: DBA hat `AUDIT SYSTEM` |
| 2 | (während der Arbeit) Testuser, Test-Script, Reporting-Script | User, 3 Policies, Test, Report, Rollback getestet | 17 Audit-Records, Rollback sauber |
| 3 | Data Pump Export als Claus testen, aber zuerst die CREATE-Statements zeigen | Statements und DB-Stand gezeigt, Plan, auf OK gewartet | Export **nicht** gelaufen, kein OK |
| 4 | Absolute Pfade zu den Scripts | Pfade lokal und im Container | - |
| 5 | Fehlerhaftes PL/SQL-Package für SCOTT, Martin soll es analysieren | Package mit 9 Lücken und 7 Fehlern, Smoke-Test, Lösungsschlüssel | 5 Fehler reproduziert |
| 6 | Session fertig, Dokumentation als md | dieses Dokument | - |
<!-- markdownlint-restore -->

## Teil 1 - Unified Audit für Claus

### Prompt 1 (Wortlaut)

```text
Arbeite als DB Security spezialist und unterstütze mich beim erstellen von Oracle Unified audit policies für hoch
privilegierte User. Erstelle die Scripte für die 26ai Lab db. führe diese direkt aus und erstelle zudem auch gleich
die noaudit policies. der hoch priveligierte user heist Claus.
```

### Was die AI vor dem ersten Statement tat

1. Skill `oracle-audit` geladen, Repo und Runbook gelesen, um das Lab zu finden: `seclab-db26`, Port 1572.
2. DB inspiziert: Version, Audit-Modus, PDBs (`LABPDB1`, `DEMOPDB`), User CLAUS, Rollen, `V$PWFILE_USERS`.
   **Befund: CLAUS existiert nicht**, weder common noch lokal.
3. Aktive Policies je Container gelesen: In `LABPDB1` liegen schon die `ORADBA_LOC_*`-Policies, unter
   anderem `BY GRANTED ROLE DBA`. In `DEMOPDB` sind nur die Oracle-Defaults aktiv.
4. Uhrzeit und Lab-Zustand geprüft (15:24, `LAB_BASELINE`, kein `WALLET_ROOT`), weil es Talk-Tag war.
5. Defaults selbst gewählt, ohne Rückfrage: lokaler User `CLAUS` in `DEMOPDB` mit Rolle DBA, Präfix
   `HMB_LOC_`. In der Antwort genannt.
6. Rechte der Rolle DBA geprüft. **Befund:** DBA enthält `AUDIT SYSTEM` und `AUDIT ANY`. Claus kann damit
   seine eigene Policy abschalten.

Ein Tippfehler der AI kostete einen Durchlauf: Die erste Abfrage auf `CDB_AUDIT_POLICIES` scheiterte mit
ORA-00904 (Spalte `FAILURE`). Die zweite Abfrage auf `AUDIT_UNIFIED_ENABLED_POLICIES` lief.

### Prompt 2 (Wortlaut, kam während der Arbeit)

```text
erstell mir doch gleich einen test user in der pdb, mit eine test script und einem reporting script
```

### Design-Entscheide der AI

- **`HMB_LOC_CLAUS_ALL_ACT`:** `ACTIONS ALL ONLY TOPLEVEL`, also jedes Statement, das Claus direkt absetzt.
  Das schliesst LOGON/LOGOFF und Änderungen an der Audit-Konfiguration ein.
- **`HMB_LOC_CLAUS_PRIV_USE`:** 20 kritische Systemprivilegien. Damit wird auch die Nutzung innerhalb von
  PL/SQL erfasst, die `ONLY TOPLEVEL` nicht sieht.
- **`HMB_LOC_CLAUS_DATAPUMP`:** `ACTIONS COMPONENT = DATAPUMP ALL`, weil Data Pump nicht zu `ACTIONS ALL`
  gehört.
- Alle drei sind lokale Policies, eingeschaltet mit `BY CLAUS`, für Erfolg und Fehler. Jede hat einen
  Kommentar mit Verweis auf das Rollback-Script.
- Das Passwort ist zufällig erzeugt, liegt in einer Datei mit Modus 600 und geht über stdin an SQL*Plus,
  also nie auf die Befehlszeile und nie in den Chat.
- Das Test-Script setzt die Client-ID `hmb-audit-test`, damit sich die Test-Events filtern lassen.
- Die Tabellen von Runde 3 (`HMB_TDE.CUSTOMER_CARDS` in DEMOPDB) fasst keines der Scripts an.

### Resultate

Die drei Policies sind angelegt und mit `BY CLAUS` eingeschaltet (`CLAUS` erstellt 2026-11-17 15:26:05):

```text
POLICY_NAME             ENABLED_OPTION ENTITY_NAME SUC FAI
HMB_LOC_CLAUS_ALL_ACT   BY USER        CLAUS       YES YES
HMB_LOC_CLAUS_DATAPUMP  BY USER        CLAUS       YES YES
HMB_LOC_CLAUS_PRIV_USE  BY USER        CLAUS       YES YES
```

Der Test als Claus lief um 15:26:08. Der Report fasst die Events nach Aktion zusammen:

```text
ACTION_NAME   RETURN_CODE CNT
SELECT        0           4
COMMIT        0           2
EXECUTE       0           2
CREATE TABLE  0           1
CREATE USER   0           1
DROP TABLE    0           1
DROP TABLE    942         1
DROP USER     0           1
INSERT        0           1
LOGOFF        0           1
LOGON         0           1
```

Die wichtigsten Detailzeilen:

```text
ACTION      OBJECT            PRIV_USED         POLICIES
SELECT      SCOTT.EMP         SELECT ANY TABLE  HMB_LOC_CLAUS_PRIV_USE          <- execute immediate im Block
SELECT      TVD_HR.EMPLOYEES  SELECT ANY TABLE  HMB_LOC_CLAUS_ALL_ACT, HMB_LOC_CLAUS_PRIV_USE
SELECT      SYS.DBA_USERS     -                 HMB_LOC_CLAUS_ALL_ACT
CREATE USER .CLAUS_TMP        CREATE USER       HMB_LOC_CLAUS_ALL_ACT, ORA_SECURECONFIG, HMB_LOC_CLAUS_PRIV_USE
DROP TABLE  CLAUS.DOES_NOT_EXIST (RC 942)       HMB_LOC_CLAUS_ALL_ACT
LOGON       -                 CREATE SESSION    HMB_LOC_CLAUS_ALL_ACT
```

- Den Zugriff `execute immediate 'select ... from scott.emp'` hat **nur** `HMB_LOC_CLAUS_PRIV_USE` erfasst.
  Mit der Top-Level-Policy allein wäre er unsichtbar geblieben.
- `SELECT` auf `DBA_USERS` zeigt kein `SELECT ANY DICTIONARY`. Claus liest die View über die Objektrechte
  aus SELECT_CATALOG_ROLE.
- Das CREATE USER mit Passwort steht als `identified by *` im Trail.
- Die Prüfung auf Änderungen an den Policies zeigt die drei `AUDIT POLICY ... BY CLAUS` von SYS.

Rollback-Test: Die AI liess `09_noaudit_policies.sql` laufen (3 × NOAUDIT, 3 × DROP, danach 0 Policies
und 0 eingeschaltete) und danach `01_audit_policies.sql` erneut. Der Endzustand war derselbe wie vorher.
Das hat niemand verlangt. Die AI begründete es damit, dass das NOAUDIT-Script sonst ungetestet bliebe.

### Prompt 3 und 4 (Wortlaut)

```text
Teste noch den Data Pump Export als Claus. aber zeige mir zuerst die create audit policy statements
```

```text
absolute pfade zu den scripts
```

Die AI zeigte die CREATE-Statements und den Stand in `AUDIT_UNIFIED_POLICIES` (22 Zeilen, alle
`COMMON = NO`) und `DATA_PUMP_DIR` in DEMOPDB. Den Export las sie als "erst zeigen, dann auf OK warten",
legte einen Plan vor und startete ihn nicht. Nach Prompt 4 wechselte das Thema, **der Data-Pump-Export
ist nie gelaufen**. Die Policy `HMB_LOC_CLAUS_DATAPUMP` ist eingeschaltet, aber ungetestet.

## Teil 2 - Fehlerhaftes PL/SQL-Package für Martin

### Prompt 5 (Wortlaut)

```text
wir wollen ein fehlerhaftes PL/SQL package analisieren. erstell zuerst ein package für das scott oder hr schema
in der 26ai db (DEMOPDB) baue das falsch package mit sicherheitslücken und fehler. Martin soll es dann analisiere.
```

### Vorgehen der AI

1. SCOTT in DEMOPDB geprüft: OPEN, Rollen CONNECT und RESOURCE, 14 Zeilen in EMP, `SALGRADE` 1-5, kein
   Package vorhanden.
2. `SCOTT.HMB_EMP_API` gebaut, eine Mitarbeiter-API mit 8 Unterprogrammen, Logtabelle `SCOTT.HMB_API_LOG`
   und `GRANT EXECUTE ... TO PUBLIC`. Der Quelltext hat **keine Kommentare, die auf die Fehler hinweisen**.
   Die Befunde stehen nur im Lösungsschlüssel, der lokal bleibt.
3. Das Package kompiliert sauber (`VALID`, 0 Zeilen in `DBA_ERRORS`). So hat Martin etwas, das läuft, und
   nicht nur Compile-Fehler.
4. Smoke-Test nur mit lesenden Aufrufen. `raise_salary` und `delete_dept` blieben ungetestet, weil sie auf
   EMP und DEPT committen. Die SQL-Injection-Fälle blieben für Martin.
5. Eigener Fehler der AI: Der Puffer in `run_report` sollte von 20 auf 15 Zeichen schrumpfen, damit
   ORA-06502 sicher auftritt. `sed -i ''` (macOS-Syntax) scheiterte am GNU sed der Maschine. Der Smoke-Test
   lief, `run_report` ging ohne Fehler durch. Die AI sah das an der Ausgabe, korrigierte mit `sed -i`,
   kompilierte neu und testete erneut.
6. Die Logzeile aus dem Smoke-Test (Klartext-Passwort) hat die AI gelöscht, `HMB_API_LOG` ist leer.

### Resultate Smoke-Test

<!-- markdownlint-disable MD013 -->
| Aufruf | Ergebnis | Befund |
| --- | --- | --- |
| `find_emp('KING')` | 1 Zeile, KING | funktioniert, die Injection ist ungetestet |
| `salary_grade(1200)` / `(1300)` | `0` / `2` | Grenzwerte fehlen (B2) |
| `dept_headcount(10)` | `NULL` | Zähler nicht initialisiert (B3) |
| `login('hradmin', 'x')` | FALSE, Passwort im Log | Klartext-Passwort im Log (S2) |
| `login('hradmin', rpad('x', 4000, 'x'))` | **TRUE** | Fail-open über ORA-12899 im Log-Insert (S3, B6) |
| `run_report('deptno = 30')` | ORA-06502 bei der ersten Zeile | Puffer zu klein (B4) |
<!-- markdownlint-restore -->

### Lösungsschlüssel

Der Schlüssel ist unten im Anhang, für das Manuskript. Martin darf ihn vor der Analyse nicht sehen.

## Stand nach der Session

Lab-Stand am 2026-11-18 09:17, geprüft: In DEMOPDB existieren noch `CLAUS`, die drei `HMB_LOC_CLAUS_*`-
Policies und `SCOTT.HMB_EMP_API` mit `HMB_API_LOG`. Das Lab ist **noch nicht** zurückgesetzt.

- [ ] Martins Analyse von `SCOTT.HMB_EMP_API` festhalten (Prompt, Tool, Befunde gegen den Schlüssel)
- [ ] Data-Pump-Export als Claus testen oder im Manuskript als offen nennen
- [ ] Aufräumen: `09_noaudit_policies.sql`, `99_drop_user.sql`, `19_drop_package.sql`, oder einfach
  `make reset LAB=seclab` (zurück auf `LAB_BASELINE`)

## Verlauf Schritt für Schritt

Vollständige Chronologie: P = Prompt des Users, A = Antwort oder Rückfrage der AI an den User, sonst ein
Arbeitsschritt der AI mit Resultat. Die Zwischenmeldungen der AI sind sinngemäss wiedergegeben, die Prompts im
Wortlaut.

### P1 - Audit Policies für Claus

```text
Arbeite als DB Security spezialist und unterstütze mich beim erstellen von Oracle Unified audit policies für hoch
privilegierte User. Erstelle die Scripte für die 26ai Lab db. führe diese direkt aus und erstelle zudem auch gleich
die noaudit policies. der hoch priveligierte user heist Claus.
```

<!-- markdownlint-disable MD013 -->
| # | Schritt der AI | Resultat |
| --- | --- | --- |
| 1 | Skill `oracle-audit` geladen | Rolle Security Architect, Namenskonvention `<PREFIX>_<CON>_<WHAT>`, Hinweis 26ai: Policies greifen sofort |
| 2 | Repo gelesen: README, `tasks/state-2026-11-16.md`, `docs/prompts-stefan-rounds.md`, `docs/runbook-labs-talk-day.md` | Lab `seclab`, 26ai = `seclab-db26`, Port 1572 |
| 3 | `docker ps` | `seclab-db26` und `seclab-db19` healthy |
| 4 | SQL: Version, Audit-Modus, PDBs, CLAUS in `CDB_USERS`, Rollen, Privilegien, `V$PWFILE_USERS` | 23.26.3, Unified TRUE, PDBs LABPDB1 + DEMOPDB; **CLAUS: no rows selected** |
| 5 | A: Zwischenmeldung "CLAUS existiert nicht, ich prüfe die aktiven Policies" | - |
| 6 | SQL: aktive Policies je Container | 1. Abfrage ORA-00904 (Spalte `FAILURE` in `CDB_AUDIT_POLICIES`), 2. Abfrage 37 Zeilen: LABPDB1 mit `ORADBA_LOC_*`, DEMOPDB nur Defaults |
| 7 | `date`, Restore Points, `WALLET_ROOT` | 15:24, `LAB_BASELINE`, `WALLET_ROOT` leer - kein Privesc-Rest |
| 8 | A: Zwischenmeldung "Defaults: lokaler User CLAUS in DEMOPDB, Rolle DBA, Präfix `HMB_LOC_`" | Annahme ohne Rückfrage getroffen |
| 9 | SQL: Rechte der Rolle DBA mit AUDIT, vorhandene `HMB%`-Policies | **DBA hat `AUDIT ANY`, `AUDIT SYSTEM`**, `ADMINISTER FINE GRAINED AUDIT POLICY`; 0 HMB-Policies |
<!-- markdownlint-restore -->

### P2 - Testuser, Test- und Reporting-Script (kam während Schritt 9)

```text
erstell mir doch gleich einen test user in der pdb, mit eine test script und einem reporting script
```

<!-- markdownlint-disable MD013 -->
| # | Schritt der AI | Resultat |
| --- | --- | --- |
| 10 | A: "übernehme ich, Befund `AUDIT SYSTEM` kommt in die Policy-Abdeckung"; SQL: Service-Name, Tabellen in DEMOPDB | Service `demopdb.oradba.ch`; Tabellen `HMB_TDE.CUSTOMER_CARDS` (Runde 3, nicht anfassen), SCOTT, TVD_HR |
| 11 | 6 Scripts geschrieben: `00_create_user`, `01_audit_policies`, `02_test_claus`, `03_report`, `09_noaudit_policies`, `99_drop_user` | siehe Anhang |
| 12 | Passwort zufällig erzeugt (Datei 600), Scripts in den Container kopiert, `00` + `01` über stdin ausgeführt | User created 15:26:05, 3 × Audit policy created, 3 × Comment created, 3 × Audit succeeded |
| 13 | `02_test_claus.sql` als Claus, dann `03_report.sql` als SYSDBA | 21 Zeilen EMPLOYEES, 42 DBA_USERS, ORA-00942 wie geplant; Report 11 Aktionsgruppen, 16 Detailzeilen |
| 14 | Rollback-Test ungefragt: `09` und danach wieder `01` | Noaudit/Dropped je 3 ×, 0 übrig; danach wieder 3 Policies eingeschaltet |
| 15 | A: Zusammenfassung mit Risiken (AUDIT SYSTEM, BY USER statt BY GRANTED ROLE, DBA-Views ohne Systemprivileg, Data Pump ungetestet, DEMOPDB = Runde 3) | - |
<!-- markdownlint-restore -->

### P3 - Data Pump, erst die Statements

```text
Teste noch den Data Pump Export als Claus. aber zeige mir zuerst die create audit policy statements
```

<!-- markdownlint-disable MD013 -->
| # | Schritt der AI | Resultat |
| --- | --- | --- |
| 16 | CREATE-Statements aus `01_audit_policies.sql`, SQL: `AUDIT_UNIFIED_POLICIES`, `DATA_PUMP_DIR` | 22 Zeilen, alle `COMMON = NO`; `DATA_PUMP_DIR` = `/opt/oracle/admin/FREE/dpdump/602FE952E5A710ACE063020016AC7631` |
| 17 | A, **Rückfrage:** Plan (expdp `SCHEMAS=TVD_HR`, Parfile 600, Report mit `DP_*_PARAMETERS1`, Dump mit `UTL_FILE.FREMOVE` löschen) - "Soll ich den Export so starten?" | keine Antwort darauf |
<!-- markdownlint-restore -->

### P4 - Pfade

```text
absolute pfade zu den scripts
```

| # | Schritt der AI | Resultat |
| --- | --- | --- |
| 18 | A: Pfade lokal und im Container, Pfad der Passwortdatei | - |
| 19 | A, **Angebot:** Scripts ins Repo kopieren, ohne Commit; Hinweis "Export wartet auf OK" | keine Antwort darauf |

### P5 - Fehlerhaftes PL/SQL-Package

```text
wir wollen ein fehlerhaftes PL/SQL package analisieren. erstell zuerst ein package für das scott oder hr schema
in der 26ai db (DEMOPDB) baue das falsch package mit sicherheitslücken und fehler. Martin soll es dann analisiere.
```

<!-- markdownlint-disable MD013 -->
| # | Schritt der AI | Resultat |
| --- | --- | --- |
| 20 | SQL: SCOTT und TVD_HR, Packages, EMP, SALGRADE, Rechte | beide OPEN, kein Package, 14 EMP, Grades 1-5, SCOTT: CONNECT, RESOURCE, UNLIMITED TABLESPACE |
| 21 | Entscheid: SCOTT; `10_create_package.sql` und `19_drop_package.sql` geschrieben und ausgeführt | Table created, Package + Body created, Grant succeeded; `VALID`, 0 Compile-Fehler |
| 22 | Puffer in `run_report` verkleinern mit `sed -i ''`, Body neu kompiliert, `12_smoke_test.sql` | **sed scheiterte** ("can't read s/..."), der Body blieb bei 20 Zeichen; Smoke-Test: KING 1 Zeile, Grade 1200 → 0, Headcount NULL, Login falsch → FALSE, Login 4000 Zeichen → TRUE, `run_report` **ohne Fehler**; Log geleert (1 Zeile); `rm` im Container: Permission denied |
| 23 | Fehler an der Ausgabe erkannt, `sed -i` (GNU), neu kompiliert, `run_report` erneut, Temp-Datei als root gelöscht | ORA-06502 an Zeile 88, Body `VALID` |
| 24 | Lösungsschlüssel `18_findings_key.md` nur lokal geschrieben | 9 Sicherheitslücken, 7 Fehler, Spalte "Belegt" |
| 25 | A: Zusammenfassung, Abfrage auf `DBA_SOURCE` für Martin, Hinweis Reset | - |
<!-- markdownlint-restore -->

### P6 und P7 - Dokumentation

```text
session ist fertig. erstelle eine übersicht / dokumentation was wir hier gemacht haben, prompt, code, resultate etc.
als md file. Ziel ist, dass wir alles sammeln um anschliessend ein session manuskript zu generieren.
```

```text
also alle prompts, rückfragen, iterationen inkl resultate. so dass es nachvollziebar ist. melden wenn fertig und
wir hier schliessen können.
```

| # | Schritt der AI | Resultat |
| --- | --- | --- |
| 26 | Lab-Stand geprüft 2026-11-18 09:17 | CLAUS 1, Policies 22 Zeilen, Package 2 Objekte - noch nicht zurückgesetzt |
| 27 | Dokument zusammengebaut, Scripts im Anhang, markdownlint | 9 × MD013 in den Tabellen des Schlüssels, korrigiert |

### P8 bis P10 - Timings, Skills und Rules, Pakete (kamen während Schritt 27)

```text
hast du auch die timings aus der history? was was wann und wie lange und wie viele token?
```

```text
und was mit welchen skills, rules, commands?
```

```text
generierte files als packages zum abgeben
```

<!-- markdownlint-disable MD013 -->
| # | Schritt der AI | Resultat |
| --- | --- | --- |
| 28 | Session-Transcript ausgewertet (`~/.claude/projects/<projekt>/<session>.jsonl`, 286 Zeilen) | Zeitstempel, Token je API-Aufruf, Dauer je Tool-Aufruf |
| 29 | Abschnitte "Zeiten und Token" und "Skills, Rules, Commands" ergänzt | siehe unten |
| 30 | drei ZIP-Pakete gebaut (Abschnitt "Abgabe-Pakete") | Martins Paket ohne Schlüssel und Passwortdatei |
<!-- markdownlint-restore -->

## Zeiten und Token

Quelle: das Session-Transcript (siehe Schritt 28), Zeiten in Schweizer Zeit (UTC + 1 h). Die Token sind pro
API-Aufruf gezählt, auch wenn ein Aufruf im Transcript in mehreren Zeilen steht (Thinking, Text, Tool-Aufruf).

### Pro Prompt

<!-- markdownlint-disable MD013 -->
| Prompt | Start | Letzte Antwort | Dauer | API-Aufrufe | Output | Cache gelesen | Cache geschrieben | Input ohne Cache |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 + P2 Audit für Claus | 17.11. 15:22:17 | 15:26:38 | 4 min 21 s | 13 | 13'684 | 852'463 | 71'591 | 30 |
| P3 Statements zeigen | 15:27:55 | 15:28:17 | 22 s | 2 | 1'557 | 173'709 | 2'403 | 6 |
| P4 Pfade | 15:30:03 | 15:30:13 | 10 s | 1 | 1'030 | 89'975 | 14 | 4 |
| P5 PL/SQL-Package | 15:34:41 | 15:39:47 | 5 min 6 s | 6 | 10'852 | 569'251 | 11'104 | 14 |
| P6 bis P10 Dokumentation, bis Schritt 28 | 18.11. 09:17:26 | 09:19:48 | (läuft) | 5 | 14'720 | 487'331 | 115'395 | 14 |
| **Total bis 09:19:48** | | | | **27** | **41'843** | **2'172'729** | **200'507** | **68** |
<!-- markdownlint-restore -->

- Die AI arbeitete am 17.11. rund 9 min 50 s, verteilt über 17 min 30 s (15:22 bis 15:39). Die Lücken
  dazwischen sind die Zeit, in der Stefan las und den nächsten Prompt schrieb.
- Gross ist nur der Cache: Bei jedem Aufruf liest das Modell den ganzen Kontext neu (System-Prompt, Rules,
  Verlauf), meist aus dem Prompt Cache. Der Output, also der Text und Code, den die AI selbst erzeugt, beträgt
  rund 42'000 Token.
- Am 18.11. musste der Cache neu aufgebaut werden (100'220 Token geschrieben beim ersten Aufruf), weil der
  1-Stunden-Cache über Nacht verfallen war.
- Die Token der Schritte nach 09:19:48 (diese Abschnitte, die Pakete) sind nicht gezählt.

### Pro Tool-Aufruf

Die Dauer reicht vom Aufruf bis zum Resultat. Sie schliesst die Wartezeit auf Stefans Freigabe ein, wenn
Claude Code nachfragt. Beispiel: `00_create_user.sql` wurde um 15:25:33 aufgerufen, CLAUS ist laut DB um
15:26:05 erstellt. Rund 30 s davon war Warten auf die Freigabe.

<!-- markdownlint-disable MD013 -->
| Zeit | Dauer | Tool | Was |
| --- | --- | --- | --- |
| 15:22:27 | 0 s | Skill | `oracle-audit` |
| 15:22:27 | 2 s | Bash | Repo-Layout lesen |
| 15:22:33 | 1 s | Bash | README und State lesen |
| 15:22:38 | 0 s | Bash | Prompts, Runbook, env lesen |
| 15:22:44 | 11 s | Bash | `docker ps`, connect-Target |
| 15:23:01 | 49 s | Bash | DB inspizieren: Version, Modus, PDBs, CLAUS (erster `docker exec`, Freigabe) |
| 15:23:56 | 4 s | Bash | aktive Policies je Container |
| 15:24:06 | 2 s | Bash | Uhrzeit, Restore Point, `WALLET_ROOT` |
| 15:24:31 | 4 s | Bash | Rechte der Rolle DBA |
| 15:24:59 | 3 s | Bash | Service, Tabellen in DEMOPDB |
| 15:25:26 | 0 s | Bash | 6 Audit-Scripts schreiben |
| 15:25:33 | 32 s | Bash | User und Policies anlegen (Freigabe) |
| 15:25:35 | 33 s | Bash | Test als Claus und Report (parallel abgeschickt, wartete auf den vorigen) |
| 15:26:17 | 2 s | Bash | Rollback-Test |
| 15:28:06 | 3 s | Bash | CREATE-Statements und DB-Stand |
| 15:35:05 | 41 s | Bash | SCOTT inspizieren (Freigabe) |
| 15:36:04 | 122 s | Bash | Package schreiben und kompilieren (Freigabe) |
| 15:38:25 | 22 s | Bash | Smoke-Test, `sed` scheitert |
| 15:38:56 | 12 s | Bash | `sed` korrigiert, `run_report` erneut |
| 15:39:34 | 0 s | Write | `18_findings_key.md` |
| 09:17:38 | 2 s | Bash | Repo und Lab-Stand prüfen |
| 09:17:51 | 0 s | Bash | markdownlint-Konfiguration |
| 09:18:49 | 0 s | Write | Dokumentkopf |
| 09:19:28 | 0 s | Edit | Verlauf ergänzt |
| 09:19:34 | 1 s | Bash | Dokument zusammenbauen, lint |
| 09:19:48 | 0 s | Bash | Transcript auswerten |
<!-- markdownlint-restore -->

Die reine DB-Zeit war kurz: Jedes SQL*Plus-Script lief in 2 bis 4 s, wenn keine Freigabe anstand.

## Skills, Rules, Commands

### Skills und Commands

- **Skill `oracle-audit`** (`~/.claude/skills/oracle-audit`): einziger aufgerufener Skill, um 15:22:27 von
  der AI selbst geladen, nicht per Slash-Command. Daraus übernommen: die Rolle Security Architect, die
  Namenskonvention `<PREFIX>_<CON>_<WHAT>` (`HMB_LOC_CLAUS_*`), `COMMENT ON AUDIT POLICY` direkt nach dem
  CREATE, lokale statt Common Policies für PDB-User, der Hinweis "26ai: Policies greifen sofort" und die
  Markierungen `🔴 RISK` und `⚠️`. **Nicht** befolgt: das "Audit Mantra" (WHERE, HOW LONG, HOW) und die
  Phasen-Gates des Skills. Gefragt wurde nicht, die Fragen tauchen nur als Risiko auf.
- Den Skill `db` gab es auch, er wurde nicht geladen.
- **Slash-Commands:** keine. **Subagents:** keine. **Plan Mode:** nicht genutzt.
- **Tools:** Bash 23 ×, Write 2 ×, Edit 1 ×, Skill 1 × (Stand Schritt 28).

### Rules, die den Verlauf beeinflusst haben

Diese Rules sind global aktiv (`~/.claude/CLAUDE.md`, `~/.claude/rules/*.md`). Das Repo hat keine eigene
`CLAUDE.md`. Die Tabelle nennt nur Rules mit einer sichtbaren Wirkung oder Abweichung.

<!-- markdownlint-disable MD013 -->
| Rule | Inhalt | Im Verlauf |
| --- | --- | --- |
| `core-invariants.md` Oracle SQL | AUDIT immer mit NOAUDIT paaren | erfüllt, `09_noaudit_policies.sql` ausgeführt und getestet (auch im Prompt verlangt) |
| `core-invariants.md` Secrets | Secrets nur über `op read`, nie hartkodiert | Lab-Passwort zufällig, Datei 600, über stdin; `op` nicht genutzt. Das hartkodierte Passwort im Package ist Absicht (Befund S1) |
| `claude-code.md` Arbeitsmodus | alle klärenden Fragen vorab in einer Runde | **Abweichung:** keine Fragen, Defaults gewählt (CLAUS fehlte, PDB, Rolle) und in der Antwort genannt |
| `claude-code.md` Plan Mode | ab 3 Dateien Plan zeigen | **Abweichung:** 6 Scripts ohne Plan, weil "führe direkt aus" verlangt war |
| `claude-code.md` Filter, der still zurückhält | Übersprungenes benennen | Data Pump, `raise_salary`, `delete_dept`, Injection-Fälle als nicht ausgeführt genannt |
| `labs.md` geteilte Labs | `make reset` nur nach Absprache | Lab nicht zurückgesetzt, Reset nur vorgeschlagen |
| `git.md` | nie committen ohne ausdrückliche Anweisung | nichts committet |
| `markdown-lint.md` | Tabellen mit disable/restore, Code-Blöcke mit Sprache | dieses Dokument |
| `persona-core.md` | Schweizer "ss", knapp | Dokument und Antworten |
<!-- markdownlint-restore -->

Ebenfalls geladen, aber ohne Wirkung auf den Verlauf: `forge-conventions.md`, `api-patterns.md`,
`oci-naming.md`, `nda-meeting-notes.md`, die Memory "hmb SSH via home VPN". Als Kontext gelesen und genutzt,
aber keine Rules: `docs/runbook-labs-talk-day.md` (Lab, Ports, Talk-Zeitplan) und
`docs/prompts-stefan-rounds.md`.

## Abgabe-Pakete

Die Pakete liegen in `~/Downloads/hmb-session-2026-11-17/`, nicht im Repo:

<!-- markdownlint-disable MD013 -->
| Paket | Für | Inhalt |
| --- | --- | --- |
| `hmb-unified-audit-claus.zip` | Teilnehmende, Nachbereitung | `README.md`, `00`-`03`, `09`, `99` (ohne Passwortdatei) |
| `hmb-plsql-review-martin.zip` | Martin | `README.md`, `10_create_package.sql`, `12_smoke_test.sql`, `19_drop_package.sql` (ohne Lösungsschlüssel) |
| `hmb-session-manuskript-material.zip` | Stefan, Manuskript | dieses Dokument, `18_findings_key.md`, beide Pakete oben |
<!-- markdownlint-restore -->

## Beobachtungen für das Manuskript

Fakten aus dem Verlauf, sortiert nach dem, was auf der Bühne trägt:

- **Erst schauen, dann bauen:** Die AI fand, dass CLAUS nicht existiert, und wählte Defaults selbst
  (lokal, DEMOPDB, Rolle DBA), statt nachzufragen. Das ist schnell, aber eine Annahme. In der Antwort
  stand sie offen da.
- **Fachlicher Mehrwert:** Der Befund `AUDIT SYSTEM` in DBA, also dass der Auditierte sein Audit abschalten
  kann, war nicht verlangt. Ebenso die Lücke von `ONLY TOPLEVEL` bei dynamischem SQL, die im Trail belegt ist.
- **Verifikation am Ergebnis:** Rollback getestet, ohne dass es verlangt war. Den Fehler mit `sed` fand die
  AI selbst an der Ausgabe und nicht erst durch einen Hinweis.
- **Was nicht passiert ist:** Der Data-Pump-Export lief nie. Die AI wartete auf ein OK, das nicht kam. Die
  Policy ist damit ungetestet, das muss im Manuskript so stehen.
- **Kleine Fehler der AI:** ORA-00904 durch einen falschen Spaltennamen, die `sed`-Syntax für die falsche
  Plattform. Beides fiel innerhalb eines Schritts auf.
- **Umgang mit Secrets:** Lab-Passwörter kamen nie in den Chat oder auf die Befehlszeile.
- **Grenze bei Daten:** Commitende Prozeduren auf EMP und DEPT hat die AI im Smoke-Test bewusst nicht
  aufgerufen.

## Anhang - Code im Wortlaut

Stand der Dateien am Ende der Session.

### Unified Audit (`/tmp/audit-claus/`)

#### `00_create_user.sql`

```sql
-- 00_create_user.sql - local test user CLAUS (DBA) in DEMOPDB
-- run as SYSDBA in CDB$ROOT: @00_create_user.sql <password>
whenever sqlerror exit failure
alter session set container = DEMOPDB;
create user claus identified by "&1" default tablespace users quota 10m on users;
grant create session, dba to claus;
select username, account_status, created from dba_users where username = 'CLAUS';
```

#### `01_audit_policies.sql`

```sql
-- 01_audit_policies.sql - Unified Audit policies for highly privileged user CLAUS
-- local policies in DEMOPDB, 26ai: active immediately, also for open sessions
-- run as SYSDBA in CDB$ROOT; rollback: 09_noaudit_policies.sql
whenever sqlerror exit failure
alter session set container = DEMOPDB;

-- 1. every top-level statement (incl. LOGON/LOGOFF, SELECT, DDL, DCL, NOAUDIT/ALTER AUDIT POLICY)
create audit policy hmb_loc_claus_all_act
  actions all only toplevel;
comment on audit policy hmb_loc_claus_all_act is
  'All top-level actions of high-privileged user CLAUS. Rollback: 09_noaudit_policies.sql';

-- 2. use of critical system privileges, also inside PL/SQL (recursive, not top level)
create audit policy hmb_loc_claus_priv_use
  privileges select any table, insert any table, update any table, delete any table,
             select any dictionary, create any procedure, execute any procedure,
             create user, alter user, drop user, become user,
             grant any privilege, grant any role, grant any object privilege,
             alter system, alter database, audit system, audit any,
             exempt access policy, administer database trigger;
comment on audit policy hmb_loc_claus_priv_use is
  'Critical system privilege use by CLAUS, recursive included. Rollback: 09_noaudit_policies.sql';

-- 3. Data Pump is not part of ACTIONS ALL
create audit policy hmb_loc_claus_datapump
  actions component = datapump all;
comment on audit policy hmb_loc_claus_datapump is
  'Data Pump export/import by CLAUS. Rollback: 09_noaudit_policies.sql';

audit policy hmb_loc_claus_all_act  by claus;
audit policy hmb_loc_claus_priv_use by claus;
audit policy hmb_loc_claus_datapump by claus;

set lines 200 pages 100
col policy_name for a28
col entity_name for a12
select policy_name, enabled_option, entity_name, success, failure
  from audit_unified_enabled_policies where policy_name like 'HMB_LOC_CLAUS%' order by 1;
```

#### `02_test_claus.sql`

```sql
-- 02_test_claus.sql - generate audit events as CLAUS in DEMOPDB
-- run in sqlplus: @02_test_claus.sql <password>
whenever sqlerror continue
connect claus/"&1"@//localhost:1521/demopdb.oradba.ch
exec dbms_session.set_identifier('hmb-audit-test')
-- SELECT ANY TABLE on application data
select count(*) from tvd_hr.employees;
-- SELECT ANY DICTIONARY
select count(*) from dba_users;
-- DDL in own schema
create table claus_audit_test (id number);
insert into claus_audit_test values (1);
commit;
drop table claus_audit_test purge;
-- account management
create user claus_tmp identified by "Tmp_&1" ;
drop user claus_tmp;
-- failed action (ORA-00942) - recorded with return code
drop table does_not_exist;
-- recursive privilege use: dynamic SQL in an anonymous block
begin execute immediate 'select count(*) from scott.emp' ; end;
/
disconnect
```

#### `03_report.sql`

```sql
-- 03_report.sql - audit report for CLAUS in DEMOPDB (last 24 h)
-- run as SYSDBA in CDB$ROOT
alter session set container = DEMOPDB;
set lines 220 pages 200
col policy_name for a28
col entity_name for a12
col event_time for a19
col action_name for a22
col object for a32
col policies for a50
col client_id for a15
col sql_text for a60 trunc

prompt === enabled policies for CLAUS
select policy_name, enabled_option, entity_name, success, failure
  from audit_unified_enabled_policies where policy_name like 'HMB_LOC_CLAUS%' order by 1;

prompt === summary per action and result (last 24 h)
select action_name, return_code, count(*) cnt
  from unified_audit_trail
 where dbusername = 'CLAUS' and event_timestamp > systimestamp - interval '1' day
 group by action_name, return_code order by cnt desc, action_name;

prompt === details (last 40 events)
select to_char(event_timestamp, 'YYYY-MM-DD HH24:MI:SS') event_time, action_name, return_code rc,
       object_schema || nullif('.' || object_name, '.') object, system_privilege_used,
       unified_audit_policies policies, client_identifier client_id, sql_text
  from unified_audit_trail
 where dbusername = 'CLAUS' and event_timestamp > systimestamp - interval '1' day
 order by event_timestamp desc fetch first 40 rows only;

prompt === audit configuration changes on CLAUS policies (tamper check)
select to_char(event_timestamp, 'YYYY-MM-DD HH24:MI:SS') event_time, dbusername, action_name, sql_text
  from unified_audit_trail
 where action_name in ('AUDIT', 'NOAUDIT', 'ALTER AUDIT POLICY', 'DROP AUDIT POLICY')
   and upper(sql_text) like '%HMB_LOC_CLAUS%'
 order by event_timestamp desc fetch first 20 rows only;
```

#### `09_noaudit_policies.sql`

```sql
-- 09_noaudit_policies.sql - rollback of 01_audit_policies.sql
-- run as SYSDBA in CDB$ROOT
whenever sqlerror continue
alter session set container = DEMOPDB;
noaudit policy hmb_loc_claus_all_act  by claus;
noaudit policy hmb_loc_claus_priv_use by claus;
noaudit policy hmb_loc_claus_datapump by claus;
drop audit policy hmb_loc_claus_all_act;
drop audit policy hmb_loc_claus_priv_use;
drop audit policy hmb_loc_claus_datapump;
select count(*) remaining_policies from audit_unified_policies where policy_name like 'HMB_LOC_CLAUS%';
select count(*) remaining_enabled from audit_unified_enabled_policies where policy_name like 'HMB_LOC_CLAUS%';
```

#### `99_drop_user.sql`

```sql
-- 99_drop_user.sql - remove test user CLAUS (after 09_noaudit_policies.sql)
-- run as SYSDBA in CDB$ROOT; audit records of CLAUS stay in the trail
alter session set container = DEMOPDB;
drop user claus cascade;
```

### PL/SQL-Package (`/tmp/plsql-review/`)

#### `10_create_package.sql`

```sql
-- 10_create_package.sql - SCOTT.HMB_EMP_API, employee API for the HR frontend
-- run as SYSDBA in CDB$ROOT; rollback: 19_drop_package.sql
whenever sqlerror exit failure
alter session set container = DEMOPDB;

create table scott.hmb_api_log (
  log_time  date,
  username  varchar2(30),
  message   varchar2(4000)
);

create or replace package scott.hmb_emp_api as
  g_admin_user constant varchar2(30) := 'HRADMIN';
  g_admin_pwd  constant varchar2(30) := 'Welcome2026!';

  function  login (p_user varchar2, p_password varchar2) return boolean;
  function  find_emp (p_ename varchar2) return sys_refcursor;
  function  list_emps (p_deptno number, p_order_by varchar2 default 'ENAME') return sys_refcursor;
  function  salary_grade (p_sal number) return number;
  function  dept_headcount (p_deptno number) return number;
  procedure raise_salary (p_empno number, p_pct number);
  procedure delete_dept (p_deptno varchar2);
  procedure run_report (p_where varchar2);
end hmb_emp_api;
/

create or replace package body scott.hmb_emp_api as

  procedure log_msg (p_msg varchar2) is
    pragma autonomous_transaction;
  begin
    insert into hmb_api_log values (sysdate, user, p_msg);
    commit;
  end log_msg;

  function login (p_user varchar2, p_password varchar2) return boolean is
  begin
    log_msg('login ' || p_user || '/' || p_password);
    if upper(p_user) = g_admin_user and p_password = g_admin_pwd then
      return true;
    end if;
    return false;
  exception
    when others then
      return true;
  end login;

  function find_emp (p_ename varchar2) return sys_refcursor is
    l_cur sys_refcursor;
  begin
    open l_cur for
      'select empno, ename, job, sal, comm from emp where ename = ''' || upper(p_ename) || '''';
    return l_cur;
  end find_emp;

  function list_emps (p_deptno number, p_order_by varchar2 default 'ENAME') return sys_refcursor is
    l_cur sys_refcursor;
  begin
    open l_cur for
      'select empno, ename, job, sal from emp where deptno = :d order by ' || p_order_by
      using p_deptno;
    return l_cur;
  end list_emps;

  function salary_grade (p_sal number) return number is
    l_grade number;
  begin
    select grade into l_grade from salgrade where p_sal > losal and p_sal < hisal;
    return l_grade;
  exception
    when no_data_found then
      return 0;
  end salary_grade;

  function dept_headcount (p_deptno number) return number is
    l_cnt number;
  begin
    for r in (select empno from emp where deptno = p_deptno) loop
      l_cnt := l_cnt + 1;
    end loop;
    return l_cnt;
  end dept_headcount;

  procedure raise_salary (p_empno number, p_pct number) is
  begin
    update emp set sal = sal * p_pct / 100 where empno = p_empno;
    commit;
    log_msg('raise ' || p_empno || ' by ' || p_pct || '%');
  exception
    when others then
      null;
  end raise_salary;

  procedure delete_dept (p_deptno varchar2) is
  begin
    execute immediate 'delete from emp where deptno = ' || p_deptno;
    execute immediate 'delete from dept where deptno = ' || p_deptno;
    commit;
  exception
    when others then
      dbms_output.put_line('error: ' || sqlerrm);
  end delete_dept;

  procedure run_report (p_where varchar2) is
    type t_rec is record (ename varchar2(10), sal number);
    l_rec t_rec;
    l_cur sys_refcursor;
    l_line varchar2(15);
  begin
    open l_cur for 'select ename, sal from emp where ' || p_where;
    loop
      fetch l_cur into l_rec;
      exit when l_cur%notfound;
      l_line := l_rec.ename || ' earns ' || l_rec.sal;
      dbms_output.put_line(l_line);
    end loop;
  end run_report;

end hmb_emp_api;
/

grant execute on scott.hmb_emp_api to public;

set lines 200
col object_name for a20
select object_name, object_type, status from dba_objects
 where owner = 'SCOTT' and object_name in ('HMB_EMP_API', 'HMB_API_LOG') order by 2;
select count(*) compile_errors from dba_errors where owner = 'SCOTT' and name = 'HMB_EMP_API';
```

#### `12_smoke_test.sql`

```sql
-- 12_smoke_test.sql - read-only calls of SCOTT.HMB_EMP_API (no commits on EMP/DEPT)
-- run as SYSDBA in CDB$ROOT
alter session set container = DEMOPDB;
set serveroutput on lines 200 pages 100
var c refcursor
prompt === find_emp('KING')
exec :c := scott.hmb_emp_api.find_emp('KING')
print c
prompt === salary_grade(1200), salary_grade(1300)
select scott.hmb_emp_api.salary_grade(1200) g1200, scott.hmb_emp_api.salary_grade(1300) g1300 from dual;
prompt === dept_headcount(10)
select nvl(to_char(scott.hmb_emp_api.dept_headcount(10)), 'NULL') cnt10 from dual;
prompt === login wrong password / 4000-char password
begin
  dbms_output.put_line('wrong pwd: ' || case when scott.hmb_emp_api.login('hradmin', 'x') then 'TRUE' else 'FALSE' end);
  dbms_output.put_line('long pwd:  ' || case when scott.hmb_emp_api.login('hradmin', rpad('x', 4000, 'x')) then 'TRUE' else 'FALSE' end);
end;
/
prompt === run_report('deptno = 30')
exec scott.hmb_emp_api.run_report('deptno = 30')
```

#### `19_drop_package.sql`

```sql
-- 19_drop_package.sql - rollback of 10_create_package.sql
-- run as SYSDBA in CDB$ROOT
whenever sqlerror continue
alter session set container = DEMOPDB;
revoke execute on scott.hmb_emp_api from public;
drop package scott.hmb_emp_api;
drop table scott.hmb_api_log purge;
select count(*) remaining from dba_objects where owner = 'SCOTT' and object_name in ('HMB_EMP_API', 'HMB_API_LOG');
```

### Lösungsschlüssel (`18_findings_key.md`, nicht für Martin)

<!-- markdownlint-disable MD013 -->
Lab: `seclab-db26`, DEMOPDB. Belegt = im Smoke-Test 2026-11-17 reproduziert.

#### Sicherheitsluecken

| ID | Stelle | Befund | Belegt |
|---|---|---|---|
| S1 | Spec `g_admin_pwd` | Hartkodiertes Passwort als Konstante in der Spec - mit EXECUTE fuer PUBLIC liest es jeder User aus (`dbms_output.put_line(scott.hmb_emp_api.g_admin_pwd)`), zudem in `ALL_SOURCE` | nein |
| S2 | `login` | Passwort im Klartext in `HMB_API_LOG` | ja |
| S3 | `login` | `when others then return true` = fail-open: Passwort mit 4000 Zeichen -> Insert ins Log scheitert -> TRUE | ja |
| S4 | `find_emp` | SQL Injection ueber String-Verkettung (`x' or '1'='1`), `upper()` schuetzt nicht | nein |
| S5 | `list_emps` | ORDER-BY-Injection, `p_order_by` ungeprueft (Whitelist / `DBMS_ASSERT`) | nein |
| S6 | `delete_dept` | SQL Injection ueber VARCHAR2-Parameter: `10 or 1=1` loescht alle EMP- und DEPT-Zeilen | nein |
| S7 | `run_report` | Frei uebergebene WHERE-Klausel = Injection by design | nein |
| S8 | Grant / AUTHID | `GRANT EXECUTE ... TO PUBLIC` + Definer Rights (Default): jeder User aendert Saläre und loescht Abteilungen mit SCOTT-Rechten; `login` wird nirgends erzwungen | nein |
| S9 | `delete_dept` | `sqlerrm` per `dbms_output` an den Aufrufer (Information Disclosure), Fehler danach verschluckt | nein |

#### Fehler

| ID | Stelle | Befund | Belegt |
|---|---|---|---|
| B1 | `raise_salary` | `sal * p_pct / 100` setzt das Salaer **auf** p_pct Prozent statt um p_pct zu erhoehen; keine Pruefung auf NULL/negativ; unbekannte EMPNO still; `when others then null`; COMMIT im API bricht die Transaktion des Aufrufers | nein (committet) |
| B2 | `salary_grade` | `>` / `<` statt `between`: Grenzwerte (700, 1200, 1201, ...) liefern 0; 0 statt Fehler bei unbekanntem Salaer | ja (1200 -> 0) |
| B3 | `dept_headcount` | `l_cnt` nicht initialisiert -> NULL; Schleife statt `count(*)` | ja (10 -> NULL) |
| B4 | `run_report` | `l_line varchar2(15)` zu klein -> ORA-06502 bei der ersten Zeile; `ename varchar2(10)` statt `%type`; Cursor bei Fehler nicht geschlossen | ja |
| B5 | `delete_dept` | loescht still alle Mitarbeiter der Abteilung mit; implizite Konvertierung VARCHAR2 -> NUMBER; COMMIT im API | nein |
| B6 | `log_msg` | autonome Transaktion ohne Laengenbegrenzung -> ORA-12899 bei langen Meldungen (Ausloeser fuer S3) | ja |
| B7 | `find_emp` | keine Bind-Variable -> Hard Parse je Aufruf | nein |
<!-- markdownlint-restore -->
