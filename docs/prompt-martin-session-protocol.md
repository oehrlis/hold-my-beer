# Prompt for Martin: protocol of his sessions

Martin pastes the prompt below into the AI tool he used for the talk (Claude Code, Copilot, ChatGPT, ...),
ideally in the same session or project, so it can read its own history. The result has the same shape as
[`session-2026-11-17-claude-code-lab.md`](session-2026-11-17-claude-code-lab.md) and feeds the manuscript
(`manuskript/manuskript-hold-my-beer-doag-2026.md`, every "Input von Martin folgt").

What Stefan gets back: one Markdown protocol per session, one ZIP per reusable package, no secrets.

## Prompt

```text
Ich bin Martin Berger. Am 2026-11-17 haben Stefan Oehrli und ich an der DOAG Konferenz die Session
"Denn sie wissen nicht was sie tun - Oracle live mit Oehrli, Berger und KI" gehalten: Das Publikum stimmte
ab, wir lösten die Aufgabe live mit AI. Ich habe Runde 1 gespielt (Abstimmung 15:07, gespielt 15:11 bis 15:17
CET): "Shell Health-Check für Alert-Log und Listener". Dazu kommen weitere Arbeits-Sessions rund um den Talk
(z. B. Code-Review des fehlerhaften PL/SQL-Packages SCOTT.HMB_EMP_API, Voting-App, Vorbereitung).

Erstelle für Stefans Session-Manuskript ein Protokoll pro Session. Das Protokoll wertet nicht, es sammelt Fakten.
Erst klären, dann autonom.

Vorgehen:
1. Quellen suchen und mir zeigen, bevor du schreibst: deinen eigenen Verlauf dieser Session, Transcripts
   (Claude Code: ~/.claude/projects/<projekt>/<session>.jsonl, darin Zeitstempel und Token je Aufruf),
   Shell-History, Terminal-Logs, erzeugte Scripts, Git-Log. Was fehlt, sage ich dir oder wir rekonstruieren es.
   Rekonstruiertes markierst du als "rekonstruiert", nie als gemessen.
2. Klärende Fragen in EINER Runde: welche Sessions gehören dazu, welches Werkzeug und Modell, wo lief es
   (Lab, Host, OS), was darf ins öffentliche Material.
3. Dann je Session eine Markdown-Datei session-YYYY-MM-DD-<thema>-martin.md mit diesen Abschnitten:
   - Rahmen (Tabelle): Datum und Zeiten, Werkzeug + Modell, Skills/Plugins/Rules, Ausführung (wer führt aus:
     AI selbst oder ich nach Vorschlag), Umgebung (DB-Version, CDB/PDB, OS), Ausgangszustand
   - Ablauf in Kürze (Tabelle): # | Zeit | Prompt (Kurzform) | Was die AI tat | Ergebnis
   - Prompts im Wortlaut, Tippfehler belassen
   - Verlauf Schritt für Schritt: was die AI vor dem ersten Befehl tat, Design-Entscheide, Fehler der AI und
     wer sie gefunden hat (AI selbst an der Ausgabe oder ich), Rückfragen der AI
   - Resultate: Ausgaben, die das Ergebnis belegen (gekürzt), nicht die Aussage der AI
   - Wer hat was gemacht: jeden Schritt der Lösung mit genau einer Marke - P (Vorbereitung, vor der Runde
     da), A (AI korrekt, so übernommen), A~ (AI mit Korrektur durch mich, zählt halb/halb), S (ich selbst,
     AI lag falsch oder kam nicht drauf). Ein Fehler, den niemand korrigiert hat, bekommt keine Marke.
     Rechnung: AI = (A + 0,5 x A~) / Schritte, Martin = (S + 0,5 x A~) / Schritte, Vorbereitung = P / Schritte
   - Zeiten und Token, soweit messbar (sonst "nicht erfasst")
   - Was nicht passiert ist: was nie lief, nicht getestet ist, offen blieb - mit Namen
   - Stand nach der Session: was liegt wo (Lab-Objekte, Dateien, Container), was ist aufgeräumt
   - Beobachtungen für das Manuskript: 5-8 Fakten, sortiert nach dem, was auf der Bühne trägt
   - Mein Takeaway: ein Satz (frage mich danach, formuliere ihn nicht selbst)
   - Anhang: Code im Wortlaut (Stand am Ende)
4. Wiederverwendbares als ZIP hmb-<thema>-martin.zip: README.md (Zweck, Voraussetzungen, Aufruf, Rückweg)
   plus Scripts. Ohne Passwortdateien, ohne .env, ohne Keys.

Regeln:
- Keine Passwörter, Tokens, IPs, internen Hostnamen, SSH-Aliase, Kunden- oder Firmeninterna, keine
  E-Mail-Adressen - vor dem Abschluss alle Dateien danach durchsuchen und mir die Treffer zeigen
- Lab-Passwörter nie in den Chat oder auf die Befehlszeile
- Zeiten in CET, Format YYYY-MM-DD HH:MM
- Markdown: Code-Blöcke immer mit Sprache (bash, sql, text), Zeilen max. 120 Zeichen, " - " statt Gedankenstrich
- Deutsch, Schweizer Schreibweise (ss, nie ß)
- Nichts committen, nichts pushen, nichts versenden - ich schicke die Dateien selbst an Stefan

Am Ende: Liste der erzeugten Dateien mit Pfad, Ergebnis der Secret-Suche, offene Lücken.
```

## After Martin's delivery

- Check every file for secrets (`gitleaks dir`, plus a match against `lab.env`) before it goes anywhere
- Add the protocols to `docs/` (after a read), the ZIPs to the DOAG material ZIP, replace every
  "Input von Martin folgt" in the manuscript, then rebuild the PDF and upload it again
- Round 1 has no step table in `runbook-labs-talk-day.md` - take Martin's steps as the reference
