# Prompts - Stefans Runden (live getippt)

Ein Prompt pro Runde, zum Kopieren in das AI-Tool der Runde. Er enthält, was ein DBA ohnehin weiss (Release,
CDB/PDB, Werkzeug) und den Auftrag - **keine Lösung und keinen Hinweis auf die Fallen** aus dem Pool. Die
Fallen sind der Inhalt der Runde. Labs, Ablauf und die %-Erfassung: [`runbook-labs-talk-day.md`](runbook-labs-talk-day.md).

Regeln für alle drei:

- Der Prompt wird vorgelesen, während er getippt oder eingefügt wird
- Die AI schreibt, Stefan führt aus - jedes Statement vor dem Ausführen laut lesen
- Nachschub nur, wenn die AI danebenliegt; jeder Nachschub wird in der Erfassung zu `A~` oder `S`
- Keine Secrets im Prompt: Lab-Passwörter tippt Stefan in SQL*Plus, nicht in die AI

## Runde 1 - 10G-Passwort-Verifier finden und bereinigen

Lab: `seclab-db19`, Tab 1 (`demos/verifier`), Startpunkt mit `@setup.sql` gesetzt.

```text
Ich bin DBA einer Oracle Database 19c (19.27, Enterprise Edition, Multitenant). In der PDB DEMOPDB haben
einige Accounts noch 10G-Passwort-Verifier. Ich arbeite in SQL*Plus als SYSDBA direkt auf dem Server und
darf die sqlnet.ora des Servers ändern.

Auftrag:
1. Finde alle Accounts in DEMOPDB mit einem 10G-Verifier.
2. Sag mir, wer nach der Bereinigung nicht mehr einloggen kann, bevor wir etwas ändern.
3. Bereinige die Verifier und sorge dafür, dass die Datenbank keine neuen 10G-Verifier mehr erzeugt.
4. Zeig mir, wie ich das Ergebnis prüfe.

Gib mir die SQL-Statements Schritt für Schritt, jeweils mit einem Satz, was sie tun. Es ist ein Lab, die
Passwörter kenne ich nicht alle.
```

Nachschub, falls nötig:

- "Woher weisst du, wer ausgesperrt wird? Prüf das vor der Änderung, nicht danach."
- "Gilt die Änderung an der sqlnet.ora für meine aktuelle Session?"
- "Ich kenne das Passwort von HMB_APP_OLD nicht. Geht die Bereinigung trotzdem?"

## Runde 2 - Unified Audit Policy für privilegierte User inklusive NOAUDIT

Lab: `seclab-db19`, Tab 2 (`demos/unified-audit`), Startpunkt mit `@setup.sql` gesetzt.

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

Nachschub, falls nötig:

- "Wir sind im Pure Mode. Schreibt dieses Statement überhaupt einen Audit-Record?"
- "Wird HMB_APP damit nicht auch auditiert?"
- "Gilt die Policy für die Session, die schon offen ist?"

## Runde 3 - TDE-Keystore mit WALLET_ROOT

Lab: `seclab-db26`, Tab 3 (`demos/tde`), Startpunkt mit `@setup.sql` gesetzt. Der Restart gehört zur Runde -
ankündigen, Martin überbrückt die etwa 5 s.

```text
Ich bin DBA einer Oracle AI Database 26ai (23.26.3, Free, Single Instance, CDB FREE). In der PDB DEMOPDB
liegen Kartennummern im Klartext im Tablespace HMB_PLAIN_TS - man findet sie mit grep im Datafile. Es gibt
noch keinen TDE-Keystore. Ich arbeite in SQL*Plus als SYSDBA, ein Restart der Datenbank ist erlaubt.

Auftrag:
1. Richte einen TDE-Software-Keystore auf die aktuelle Art ein.
2. Erzeuge die Master Keys.
3. Verschlüssle den Tablespace HMB_PLAIN_TS, ohne dass die Applikation etwas merkt.
4. Zeig mir, wie ich prüfe: Daten lesbar, Datafile nicht mehr.

Gib mir die Schritte in der richtigen Reihenfolge, jeweils mit einem Satz, was sie tun. Sag mir vorher,
wenn ein Schritt einen Restart braucht.
```

Nachschub, falls nötig:

- "Das ist 26ai. Gibt es ENCRYPTION_WALLET_LOCATION in der sqlnet.ora dort noch?"
- "Gilt der Key auch für die PDB?"
- "Ist der Klartext von vorher jetzt wirklich weg - auch aus Redo und Flashback Logs?"
