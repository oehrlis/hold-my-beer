# Themen-Pool - DOAG AK 2026

Entwurf zur Abstimmung mit Martin Berger (Stand 2026-11-03).
DOAG AK 2026, Nuernberg, Di 17.11., 15:00-15:45, Raum Istanbul, 45 min, DE.

## Format-Vorschlag

- **4 Runden statt 5**: Opening 5, Voting-Erklaerung 2, 4 Runden je 7 min = 28, Puffer 4, Closing 6.
  Eine fuenfte Runde nur, wenn der Puffer nach Runde 3 noch steht
- Jede Runde hat 3 Optionen: **eine von Stefan, eine von Martin, eine gemeinsam** - egal was gewinnt,
  beide sind gleich oft vorne
- Ablauf pro Runde: Voting 60 s, Auftrag vorlesen, 5 min hart, 1 min Scorecard
- Voting ueber eine eigene Mini-Web-App (QR-Code, kein Login): pro Runde **abstimmen** (3 Optionen) oder
  **Zufall** (Thema aus dem Pool ziehen), Ergebnis live auf dem Beamer
- Scorecard: AI richtig / AI halluziniert / falsches Problem geloest / DBA-Instinkt gewinnt

<!-- markdownlint-disable MD013 MD060 -->
## Runden

| Runde              | Stefan                                                     | Martin                                  | Gemeinsam / gegeneinander                                          |
| ------------------ | ---------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------ |
| 1 Warm-up (leicht) | 10G-Passwort-Verifier finden und bereinigen                | Shell Health-Check Alert-Log + Listener | Datapump Export/Import mit Remap                                   |
| 2 Alltag           | Unified Audit Policy fuer privilegierte User inkl. NOAUDIT | AWR/ASH: Slow Query analysieren         | Listener / sqlnet.ora Hardening                                    |
| 3 Automation       | Terraform: DB-System auf OCI                               | Ansible-Playbook Patching / Preinstall  | OEM: Metric Extension oder Incident Rule                           |
| 4 Bruchstelle      | TDE-Keystore mit WALLET_ROOT                               | Data Guard Switchover per DGMGRL        | AI-Code-Review: fehlerhaftes PL/SQL, Gegenpartei findet die Fehler |

## Reserve (Ersatz, falls ein Thema in der Probe nicht traegt)

| Thema                                       | Owner  | Hinweis                                      |
| ------------------------------------------- | ------ | -------------------------------------------- |
| Privilege Analysis (DBMS_PRIVILEGE_CAPTURE) | Stefan | Capture braucht Laufzeit - vorab aufzeichnen |
| Database Vault Realm fuer ein Schema        | Stefan | hohes Risiko, nur Wegwerf-DB                 |
| RMAN RECOVER TABLE / PDB-Restore            | Martin | nur Wegwerf-DB, Laufzeit pruefen             |
| ORA-Fehler aus dem Saal                     | beide  | Wildcard, falls das Publikum mitzieht        |
| SQL Firewall Allowlist bauen (26ai)         | Stefan | braucht 26ai                                 |
| Data Safe Assessment interpretieren         | Stefan | Report vorab erzeugen, nur Auswertung live   |
| OEM-Job per AI bauen                        | Martin | OEM-Instanz noetig                           |
| Backup-Strategie automatisieren             | Martin | nur Code + Review                            |
| Migrationsskript 19c nach 26ai              | beide  | nur Code + Review, kein Upgrade live         |

## Umgebung je Thema

| Bedarf                                     | Themen                                                                                   |
| ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Eine CDB/PDB reicht, Reset unter 2 min     | Verifier, Health-Check, Datapump, Unified Audit, AWR/ASH, sqlnet.ora, TDE, PL/SQL-Review |
| Kein DB-Zugriff noetig (nur Code + Review) | Terraform, Ansible, OEM                                                                  |
| Zweite DB / Wegwerf-Umgebung               | Data Guard, RMAN, Database Vault                                                         |
<!-- markdownlint-restore -->

## Fragen an Martin

1. Passt die Aufteilung - und welche deiner Themen fehlen (OEM, Ansible, OCI)?
2. Data Guard live: hast du ein Lab mit Primary + Standby, oder streichen wir es zugunsten der Reserve?
3. Umgebung: 19c, 26ai oder beides? Wer stellt sie, wie sieht der Reset aus?
4. Tools: welche hast du lizenziert (Codex, Copilot, ChatGPT, MS Copilot)? Fest pro Runde oder vom Publikum gewaehlt?
5. Voting-App: wer baut, wo laeuft sie, und welcher Modus pro Runde - Abstimmung, Zufall oder das Publikum entscheidet?
6. Probe: ein Durchlauf mit Zeitnahme vor dem 10.11. - welcher Termin?
