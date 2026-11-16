# Runbook - labs for the talk (Stefan's rounds)

## Entry point

Two commands, both from the hold-my-beer checkout (`scripts/talk-start.sh`, `make help` section "Session"):

```bash
make talk-lab      # 11:45, after the privesc talk: stage.sh unweak, make reset, make verify (asks first)
make talk-start    # 14:30: check app + lab, set the three demo starting points, open deck/browser/terminals
```

<!-- markdownlint-disable MD013 MD060 -->
| Target | Does | Changes |
| --- | --- | --- |
| `make talk-check` | `host-check hmb`, `make verify LAB=seclab`, privesc leftovers (WALLET_ROOT, VICTIMPDB, sqlnet.ora), demo starting points, private deck present and newer than its sources | nothing |
| `make talk-lab` | switch from the privesc state (section "Switch") | the lab - asks first |
| `make talk-demos` | `setup.sql` of verifier, unified-audit, tde; refuses while privesc leftovers exist, skips a demo already set | the lab |
| `make talk-open` | private deck and `/screen` (new window) + `/admin` in Chrome, one Terminal window per round with `sqlplus / as sysdba` in the demo directory | nothing |
| `make talk-start` | `talk-check`, then `talk-demos`, then `talk-open` | the lab (demos) |
<!-- markdownlint-restore -->

`DRY_RUN=1` shows every changing step without running it (`make talk-lab DRY_RUN=1`). Logs:
`$TMPDIR/talk-start/`.

`make talk-lab` needs the privesc demo password: `DEMO_PWD` from the environment, else
`op read "op://secrets/privesc demo/password"` (override: `DEMO_PWD_OP`). The item does not exist yet - create it
once, the value only goes through stdin (bash builtin `printf`, `op item create -`):

```bash
read -rs -p "privesc demo password: " p; printf '{"title":"privesc demo","category":"PASSWORD","fields":[{"id":"password","type":"CONCEALED","purpose":"PASSWORD","value":"%s"}]}' "$p" | op item create --vault secrets -; unset p
```

After `make talk-start`: drag `/screen` to the projector and click "Ton aus" once, deck in its own window
(Speaker View with `S`), in each Terminal window `@check.sql` is the "before" picture of its round.

Stefan's three topics run on the oradba-labs lab `seclab`. The demos live there, not in this repo:

<!-- markdownlint-disable MD013 MD060 -->
| Round | Pool topic (A, Stefan) | Demo in oradba-labs | Database |
| --- | --- | --- | --- |
| 1 Warm-up | 10G-Passwort-Verifier finden und bereinigen | `demos/verifier/` | `seclab-db19` (19.27, port 1562) |
| 2 DBA-Alltag | Unified Audit Policy für privilegierte User inklusive NOAUDIT | `demos/unified-audit/` | `seclab-db19` (also runs on db26) |
| 3 Bruchstelle | TDE-Keystore mit WALLET_ROOT | `demos/tde/` | `seclab-db26` (26ai Free 23.26.3, port 1572) |
<!-- markdownlint-restore -->

Each demo has `setup.sql`, `check.sql`, `solution.sql` (the reference, never shown live) and `reset.sql`;
the details, timings and pitfalls are in its `README.md`. Martin's topics (B) run on his own lab.
The prompts Stefan types live: [`prompts-stefan-rounds.md`](prompts-stefan-rounds.md).

## Why a switch is needed

The privesc talk (Tue 2026-11-17 11:00) uses the same lab in a deliberately weak state
(`talks-privesc/talks/oracle-privesc/demos/stage.sh weak`, restore point `PRIVESC_WEAK`). That state
touches exactly what the hold-my-beer demos need untouched:

- m1 sets `SQLNET.ALLOWED_LOGON_VERSION_SERVER = 11` - the verifier demo brings its own copy of that setting
- m3 sets `WALLET_ROOT`, `TDE_CONFIGURATION` and keystore files - `tde/setup.sql` refuses to run while
  `WALLET_ROOT` is set, and round 3 is about building exactly that
- m6 adds `VICTIMPDB`

A flashback (`make reset LAB=seclab`) does not revert files or the spfile, so the order is fixed:
**`stage.sh unweak` first, then `make reset`**.

Seen on 2026-11-16 in the weak state: `make verify LAB=seclab` fails on `seclab-db26` (container `unhealthy`,
SYSTEM login via the listener fails for every PDB). The switch must end with `make verify` fully green.

## Talk day timeline (Tue 2026-11-17)

| Time | Session | Lab state |
| --- | --- | --- |
| 08:30 | deep-data-security | `base26` - not affected |
| 11:00 | privesc | `seclab` weak (`PRIVESC_WEAK`) |
| **11:45-12:45** | **switch** (this runbook, section "Switch") | `seclab` -> baseline -> hmb starting points |
| 13:00 | Blind Spots | lab use not checked - if it uses `seclab`, the switch moves after 13:45 |
| 14:30 | hmb check (section "Before the session") | starting points in place |
| 15:00 | hold-my-beer | rounds 1-3 |
| after 15:45 | clean-up (section "After the session") | `seclab` baseline |

## Rehearse the switch today (Mon 2026-11-16)

The lab is in the privesc state now. Run the switch once end to end, time it, then put the privesc state
back for tomorrow morning:

1. Section "Switch" below, all steps - note the times in the table at the end
2. Each demo once: `@setup.sql`, `@check.sql`, `@solution.sql`, `@check.sql`, `@reset.sql`
3. Back to privesc: `cd ~/Repos/own/oehrlis/talks-privesc/talks/oracle-privesc/demos`, `export DEMO_PWD=...`,
   `./stage.sh weak` (about 80 s), `./stage.sh verify` - every row `PRESENT`

## Switch (privesc -> hold-my-beer)

`make talk-lab` runs these three steps and then checks for privesc leftovers. By hand:

```bash
# 1. undo the privesc state (OS files, spfile, VICTIMPDB) - DEMO_PWD as for the privesc talk
cd ~/Repos/own/oehrlis/talks-privesc/talks/oracle-privesc/demos
./stage.sh unweak

# 2. flash both databases back to the baseline (parallel)
cd ~/Repos/own/oehrlis/oradba-labs
make reset LAB=seclab

# 3. everything green, no WALLET_ROOT, no VICTIMPDB
make verify LAB=seclab
make status LAB=seclab
```

Check by hand after step 3 (`make connect LAB=seclab DB=db26`, then the same on db19):

```sql
show parameter wallet_root
select con_id, masterkey_activated from v$database_key_info;
host grep -i allowed_logon $ORACLE_HOME/network/admin/sqlnet.ora
```

Expected: `wallet_root` empty, `masterkey_activated` = `NO` in every container, no `ALLOWED_LOGON` line. If
`masterkey_activated` shows `YES` on db26: `make rebuild LAB=seclab` is the clean way (it takes about 15 min for
db19) - decide that in the rehearsal today, not tomorrow at noon.

If `make verify` is still red: do not improvise at 12:30. Fallback for the talk: round 1 and 2 run on db19 only,
round 3 is shown with `check.sql` and the solution steps (TDE README, "Restart plan").

## Before the session (14:30, about 5 min)

`make talk-start` does this section: starting points via `setup.sql`, one Terminal window per round. By hand,
three terminal tabs, one per round:

```bash
# tab 1 - round 1 verifier (db19)
docker exec -it -w /opt/oracle/demos/verifier seclab-db19 bash -c 'export ORAENV_ASK=NO; "${ORACLE_HOME}/bin/sqlplus" / as sysdba'

# tab 2 - round 2 unified audit (db19)
docker exec -it -w /opt/oracle/demos/unified-audit seclab-db19 bash -c 'export ORAENV_ASK=NO; "${ORACLE_HOME}/bin/sqlplus" / as sysdba'

# tab 3 - round 3 TDE (db26, -it is required: the keystore password is typed live)
docker exec -it -w /opt/oracle/demos/tde seclab-db26 bash -c 'export ORAENV_ASK=NO; "${ORACLE_HOME}/bin/sqlplus" / as sysdba'
```

In each tab:

```sql
@setup.sql
@check.sql
```

`check.sql` before the round is the "before" picture for the beamer (verifier: 10G accounts found; audit: the
traditional decoy looks configured; TDE: `grep` finds the marker in the datafile). Only the round that wins the
vote is played; the other two stay in their starting point.

Also before the session: voting app (`make host-check HOST=hmb`, `/screen` sound on), see
[`runbook-cloudflare-tunnel.md`](runbook-cloudflare-tunnel.md) "Talk day".

## During a round

- The AI writes, Stefan types the task (prompt) and runs what the AI suggests in the round's tab
- Before running anything the AI suggests: read it aloud, one sentence on what it does - that is the review
- `check.sql` at the end, on the beamer - it is the proof, not the AI's claim
- Record the share (section "Who did what") while it happens - Martin or a second screen ticks the steps

## After the session

```sql
-- in each tab that ran setup.sql
@reset.sql
```

Then `make reset LAB=seclab` and `make verify LAB=seclab`. The TDE `reset.sql` restarts db26 (about 6 s).
`reset.sql` of the verifier restores `sqlnet.ora`, which the flashback does not.

## Who did what - AI, preparation, Stefan in %

Per round, the demo README lists the steps of the expected solution. Each step gets exactly one mark while the
round runs. The marks are counted against the steps, not lines or minutes - a step is one decision a DBA has to
get right.

| Mark | Meaning |
| --- | --- |
| `P` | Preparation: in place before the round (lab, `setup.sql`, context in the prompt template) |
| `A` | AI: suggestion used as is and correct |
| `A~` | AI with correction: AI suggested it, Stefan had to fix or complete it (counts half AI, half Stefan) |
| `S` | Stefan: AI did not get it or got it wrong, Stefan did it |

Share: AI = (`A` + 0.5 x `A~`) / steps, Stefan = (`S` + 0.5 x `A~`) / steps, preparation = `P` / steps.
A step the AI got wrong and Stefan did not catch is not a mark - it shows up in `check.sql` and gets the
scorecard rating "AI halluziniert".

Steps per round (from the demo READMEs) - copy one table per played round:

<!-- markdownlint-disable MD013 MD060 -->
| # | Round 1 verifier | Round 2 unified audit | Round 3 TDE | Mark |
| --- | --- | --- | --- | --- |
| 0 | lab + starting point (`setup.sql`) | lab + starting point (`setup.sql`) | lab + starting point (`setup.sql`) | P |
| 1 | find 10G accounts (`PASSWORD_VERSIONS` as a list) | local policy `ACTIONS ALL ONLY TOPLEVEL` | `WALLET_ROOT` in the spfile + directory | |
| 2 | lock-out pre-check (`HMB_LEGACY`) | enable `BY USERS WITH GRANTED ROLES dba` | restart (planned, announced) | |
| 3 | `ALLOWED_LOGON_VERSION_SERVER` 12/12a + reconnect | (bonus) critical privilege policy | `TDE_CONFIGURATION` after the restart | |
| 4 | strip old verifiers (`IDENTIFIED BY VALUES 'T:...'`) | verify `AUDIT_UNIFIED_ENABLED_POLICIES` | create + open keystore `CONTAINER = ALL` | |
| 5 | 10G-only account: new password + expire | `NOAUDIT` with the same BY clause + `DROP` | master keys `WITH BACKUP`, `CONTAINER = ALL` | |
| 6 | `check.sql` green | `check.sql`: trail shows `HMB_DBA`, not `HMB_APP` | local auto-login keystore | |
| 7 | | | `ENCRYPTION ONLINE` of the tablespace | |
| 8 | | | `check.sql`: encrypted, scan 0, rows readable | |
<!-- markdownlint-restore -->

Example round 2 with 7 steps (0-6): `P` 1, `A` 3, `A~` 2, `S` 1 -> AI 4/7 = 57 %, Stefan 2/7 = 29 %,
preparation 1/7 = 14 %. On the final score slide: one line per played round plus the sum over all rounds.

## Times (fill in during today's rehearsal)

| Step | Expected | Measured 2026-11-16 |
| --- | --- | --- |
| `stage.sh unweak` | ? | |
| `make reset LAB=seclab` | ? | |
| `make verify LAB=seclab` | under 1 min | |
| three `setup.sql` + `check.sql` | about 2 min | |
| `stage.sh weak` (back to privesc) | about 80 s | |
