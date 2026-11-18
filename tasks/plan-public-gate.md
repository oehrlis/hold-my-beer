# Plan: public gate for hold-my-beer

Prepared 2026-11-18 after the talk. The repo stays **private** until Stefan's go - nothing below switches it.
Order: decide the blockers, clear them, get Martin's OK, then switch and set branch protection.

## Scan result (2026-11-18, `docs/post-talk-2026-11-18`)

- gitleaks with `.gitleaks.toml` over the full history: 0 leaks (it reported 46 of 70 commits - the rules only
  cover OCI and Cloudflare, so a second scan by pattern ran over `git log --all -p`)
- Absent in history and HEAD: OCIDs, PAR URLs, API key fingerprints, private keys, tunnel tokens or credentials
  JSON, `.env`/tfvars/tfstate, `lab.env`, customer names, 172.16-31.x and 192.168.x
- Lab passwords from `oradba-labs/labs/seclab/lab.env`: 0 hits in the session protocols and the DOAG ZIP

## Blockers - decide before public

<!-- markdownlint-disable MD013 MD060 -->
| # | Finding | Where | Options |
| --- | --- | --- | --- |
| B1 | Licensed Accenture font (Graphik) embedded in full as base64 | `slides/doag-ak-2026/wissen-nicht-was-sie-tun.html` at HEAD and in history (8 `@font-face`) | build the public deck with the hmb skin / system font only, then rewrite history (`git filter-repo --path slides/doag-ak-2026/wissen-nicht-was-sie-tun.html --invert-paths`, rebuild) - or keep the deck out of the repo. Same case as the oradba-brand font-free rewrite |
| B2 | Public IP of the OCI host, `opc@` user and SSH key filename | history only: `cfd83e1`, `8c9ee75`, `3b7d072` (gone at HEAD) | accept (SSH only from the home IP, host is temporary) or rewrite history with `git filter-repo --replace-text` |
| B3 | Martin's private e-mail address as author/committer | commit metadata of `cfd83e1` (app import with history) | Martin decides: accept, or `git filter-repo --mailmap` to his noreply address |
<!-- markdownlint-restore -->

Any rewrite changes every SHA after the first touched commit: open PRs, the CHANGELOG references (`64254d0`)
and Martin's clone need to follow. Do all rewrites in one pass, in a fresh clone, then force-push once (main is
not protected yet - that is the only moment it is acceptable).

## Accept as is (state it, do not fix)

- `oracle-dev` as the local development admin password and the dev-only fallback `SECRET_KEY` in
  `app/votingapp/config.py` - only used when `ADMIN_PASSWORD` / `SECRET_KEY` are unset; check that the hosts
  always set both (`app.env` from 1Password) - Martin's code, his call
- OraDBA script headers (`stefan.oehrli@oradba.ch`, Muri), employer names on the speaker slides, `hmb.oradba.ch`
- Internal CIDR `10.42.0.0/24`, OCI display names, SSH aliases `hmb` / `hmb2`, `op://` references (paths, no values)
- `Welcome2026!` in `docs/session-2026-11-17-claude-code-lab.md` is finding S1 of the faulty demo package, no
  real system

## Steps after the go

- [ ] B1-B3 decided and done (fresh clone, one force-push)
- [ ] Martin's OK for `app/` (message below)
- [ ] `gh repo edit oehrlis/hold-my-beer --visibility public --accept-visibility-change-consequences`
- [ ] Branch protection (command in [`plan-ci.md`](plan-ci.md)), then `gh api repos/oehrlis/hold-my-beer/branches/main/protection`
  shows the five checks
- [ ] `secrets.yml` run on `main` green after the switch; README "Status" line updated

## Message to Martin (draft, Stefan sends)

```text
Hoi Martin, danke für gestern - deine App hat 90 Geräte und 233 Stimmen gezählt.
Ich möchte oehrlis/hold-my-beer öffentlich machen (Deck, Pool, Doku und deine App in app/). Bevor ich das
tue, brauche ich dein OK zu drei Punkten:
1. app/ öffentlich unter der Repo-Lizenz (Apache 2.0) - ok für dich?
2. Dein Import-Commit trägt deine private Mailadresse als Autor. Lassen, oder soll ich sie in der History
   auf eine noreply-Adresse umschreiben (dein Clone müsste dann neu)?
3. Für das Manuskript (DOAG-Portal) fehlt mir deine Runde 1 (Shell Health-Check): welches Werkzeug, der Prompt,
   was lief, was nicht - und ein Satz als dein Takeaway. Am einfachsten mit dem Prompt im Anhang, den du in
   deinem AI-Tool laufen lässt (docs/prompt-martin-session-protocol.md).
Gruss Stefan
```
