# Plan: public gate for hold-my-beer

Prepared 2026-11-18 after the talk. Decision Stefan 2026-11-18: one repo at the end - the old private repo is
replaced by a new one built from the cleaned history, nothing is kept on GitHub besides it. The switch runs only
after Stefan's go.

## Why a new repo and not a force-push

GitHub keeps `refs/pull/<n>/head` of every PR (22 PRs) read-only. A force-push of a cleaned `main` would leave
the old commits - with the font and the host IP - reachable through those refs. Deleting the old repo and
pushing the cleaned history to a new one with the same name removes them.

## Scan result

- Before (old history, 2026-11-18): gitleaks 0 leaks (its rules only cover OCI and Cloudflare); pattern scan
  over `git log --all -p` found the findings B1-B3 below and nothing else secret - no OCIDs, PAR URLs, API key
  fingerprints, private keys, tunnel tokens, `.env`/tfvars/tfstate, `lab.env`, customer names
- Lab passwords from `oradba-labs/labs/seclab/lab.env`: 0 hits in the session protocols and the DOAG ZIP
- After the rewrite (checked on the rewritten repo, all commits, contents and metadata): host IP 0, SSH key
  name 0, `accenture.com` 0, private addresses 0, Graphik font files 0 (the word stays in this plan and the
  CHANGELOG), old photo 0 (name only in old slide markup); gitleaks 0 leaks

## Blockers - done in the rewrite (2026-11-18, `git filter-repo`, one pass on a fresh clone of `main`)

<!-- markdownlint-disable MD013 MD060 -->
| # | Finding | Done |
| --- | --- | --- |
| B1 | Licensed Accenture font (Graphik) embedded in full in `slides/doag-ak-2026/wissen-nicht-was-sie-tun.html`, all 64 versions | file removed from the whole history; the public deck is built with `DECK_THEME=oradba` (system fonts), `build.sh` 0.4.0 refuses the Accenture theme with an output inside the repo; `deck-private` stays Accenture, outside the repo |
| B2 | Public IP of the OCI host, `opc@` user and SSH key filename (history only) | replaced in every commit (`<host-ip>`, `<ssh-key>`) |
| B3 | Martin's private address as author | mailmap to his GitHub noreply address; on the slides LinkedIn instead (`in/martin-berger-ch`) |
| - | Stefan's employer address as author (49 commits) and on the slides | mailmap to `oehrlis@users.noreply.github.com`; slides show `stefan.oehrli@oradba.ch` and `in/stefanoehrli` |
| - | Old photo `slides/src/speaker-martin/martin-feuerwehr.jpg` (replaced 2026-11-16) | removed from the whole history |
<!-- markdownlint-restore -->

Commit references in the docs were mapped to the new SHAs (`.git/filter-repo/commit-map`); references to other
repos (oradba-labs, talks) are unchanged. Tags `v0.1.0` and `v0.2.0` are rewritten with the history.

## Accept as is

- `oracle-dev` as the local development admin password and the dev-only fallback `SECRET_KEY` in
  `app/votingapp/config.py` - only used when `ADMIN_PASSWORD` / `SECRET_KEY` are unset; the hosts set both
  (`app.env` from 1Password) - Martin's code, his call
- OraDBA script headers (`stefan.oehrli@oradba.ch`, Muri), employer names on the speaker slides, `hmb.oradba.ch`
- Internal CIDR `10.42.0.0/24`, OCI display names, SSH aliases `hmb` / `hmb2`, `op://` references (paths, no values)
- `Welcome2026!` in `docs/session-2026-11-17-claude-code-lab.md` is finding S1 of the faulty demo package, no
  real system

## Steps after the go

- [x] Backup of the old repo incl. PR refs: `git clone --mirror` -> `git bundle create --all` outside the repo
- [x] Token scope for the delete (Stefan, interactive): `gh auth refresh -h github.com -s delete_repo`
- [x] Delete `oehrlis/hold-my-beer` on GitHub (22 PRs, Actions history and release `v0.2.0` go with it)
- [x] `gh repo create oehrlis/hold-my-beer --private` with the same description and homepage, push `main` and
  the tags, release `v0.2.0` again with its notes
- [x] Public deck rebuilt in the new local checkout (`make deck`, oradba theme), check: no `Graphik` in the file
- [x] CI green on `main`, then `gh repo edit oehrlis/hold-my-beer --visibility public --accept-visibility-change-consequences`
- [x] Branch protection (command in [`plan-ci.md`](plan-ci.md)), `gh api .../branches/main/protection` shows the
  five checks
- [x] Invite Martin again (`gh api -X PUT repos/oehrlis/hold-my-beer/collaborators/martinberger-ch`); his old
  clone must be cloned fresh
- [x] Local checkout: old one moved aside, fresh clone at `~/Repos/own/oehrlis/hold-my-beer` (the talks
  recipe resolves it as a sibling)

Done 2026-11-18 15:00: backup `~/Downloads/hold-my-beer-pre-rewrite-2026-11-18.bundle` (all refs incl. 22 PR
refs), old repo deleted, new repo public, release `v0.2.0` again without the deck asset (it embedded the font),
public deck PR #1 (`89c990c`), branch protection with the five checks, Martin invited. Checked on an anonymous
clone of the public repo: host IP, key name, private addresses 0, gitleaks 0 leaks. Old local checkout kept at
`~/Repos/own/oehrlis/hold-my-beer.pre-rewrite-2026-11-18` - delete once nothing is missing. This checkout sets
`user.email` to the noreply address locally (the global one is the employer address).

Martin's OK for `app/` public under Apache 2.0: given implicitly (Stefan, 2026-11-18), not asked again.

## Message to Martin (draft, Stefan sends)

```text
Hoi Martin, danke für gestern - deine App hat 90 Geräte und 233 Stimmen gezählt.
Ich habe oehrlis/hold-my-beer für die Veröffentlichung neu aufgesetzt: History bereinigt (keine Host-IP, kein
lizenzierter Font, keine Mailadressen - deine steht jetzt als GitHub-noreply drin, auf den Folien LinkedIn).
Das Repo ist neu angelegt und öffentlich: bitte die Einladung annehmen, frisch klonen und den alten Clone
löschen (aus dem alten nichts mehr pushen, der enthält die alte History).
Für das Manuskript (DOAG-Portal) fehlt mir deine Runde 1 (Shell Health-Check): welches Werkzeug, der Prompt,
   was lief, was nicht - und ein Satz als dein Takeaway. Am einfachsten mit dem Prompt in
   docs/prompt-martin-session-protocol.md, den du in deinem AI-Tool laufen lässt.
Gruss Stefan
```
