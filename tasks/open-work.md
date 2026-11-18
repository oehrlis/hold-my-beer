# Open work

## After the talk (2026-11-18, branch `docs/post-talk-2026-11-18`)

- [x] Talk held 2026-11-17 15:00: 3 rounds, 90 devices, 233 votes (voting DB on `hmb`, read only)
- [x] Lab cleaned up 13:28: `reset.sql` verifier / unified-audit (db19) and tde (db26), `apex.sh down --purge`
  (ORDS container and config), `make reset LAB=seclab` (51 s), `make verify` green, APEX/CLAUS/HMB_EMP_API gone
  from DEMOPDB, `/tmp` leftovers in db26 removed (as root)
- [x] Kept on purpose for a later APEX demo: `~/oradba-labs-data/seclab/shared/apex-dl/` (1.5 GB), ORDS image,
  worktree `oradba-labs-apex` (`feat/demo-apex`, untracked `demos/apex/`), `$TMPDIR` files of that session
- [x] Manuscript, deck handout PDF (22 pages, last build step per slide) and material ZIP in
  `~/Downloads/hmb-doag-upload-2026-11-18/`; final score slide from the pool `result`
- [x] Blog kickoff prompt `~/notes/prompts/hmb-blogpost.md`
- [ ] DOAG portal: upload slides PDF, manuscript PDF and ZIP (Stefan) [P1] (due: 2026-11-18)
- [x] Martin's round 1 protocol in `docs/`, manuscript placeholders filled, slides / manuscript / ZIP rebuilt
  (2026-11-18)
- [x] Martin's open points settled 2026-11-18: no takeaway, round 1 tool as in the transcript (Claude Code,
  `claude-sonnet-5`), the PL/SQL package was not reviewed
- [x] Public gate B1-B3 fixed in a history rewrite (font file, host IP, addresses, old photo) -
  `tasks/plan-public-gate.md`
- [x] New public repo (old one deleted, one repo at the end) - `tasks/plan-public-gate.md` (2026-11-18)
- [ ] oradba-labs `demos/apex/apex.sh`: `DRY_RUN=1` is silently ignored (only `TRUE` counts) - the teardown on
  2026-11-18 ran for real although a dry run was meant; accept 1/true/yes or fail on unknown values [P2]
- [ ] APEX demo: build app 100 by click, export to `demos/apex/app/f100.sql`, README, PR in oradba-labs - or
  remove (`apex-dl/`, image, worktree) [P3]

## Cloudflare Tunnel hmb + Terraform hmb2 (2026-11-13, branch `feat/terraform-hmb2`)

- [x] Live config `hmb` checked: tunnel, ingress, `protocol: http2`, app on `127.0.0.1:8080`, 1Password backup
- [x] Live fix `hmb`: `PUBLIC_BASE_URL` was `http://hmb:8080` (overwritten by the redeploy) - now
  `https://hmb.oradba.ch`, QR decoded and verified
- [x] `remote-install.sh`: a redeploy without `PUBLIC_BASE_URL` keeps the value in `app.env`; a first deploy
  with an `https://` URL writes the tunnel settings (Martin to review)
- [x] Runbook: redeploy pitfall, port 8000 on the shared host, all 1Password items, SSH aliases
- [x] SSH: `hmb` / `hmb.oradba.ch` and `hmb2` / `hmb2.oradba.ch` in `~/.ssh/config.d/`
- [x] `terraform/`: OCI (VCN, public subnet, SSH from admin CIDR only, A1.Flex 1/6 free), Cloudflare tunnel
  `hmb2` + CNAME `hmb2.oradba.ch`, cloud-init (cloudflared, python3, app directories)
- [x] Makefile: `tf-*` via `op run`, `host-env` (app secrets from 1Password), `host-deploy`, `host-check`
- [x] Decision 2026-11-13: `terraform/` keeps the build in the repo; `hmb` stays on the shared host for the
  talk, `hmb2` is not applied for now
- [x] Decision 2026-11-16: no rehearsal with Martin, the talk is live; instead a 2 min tech check after
  `make talk-start` (`/screen` sound, `/admin` login, Speaker View, QR scan)
- [x] Session on `hmb` reset (14:47, checked in the DB: `waiting`, round 1, 0 votes); `make deck-private` built,
  voting URL and both QR codes decoded to `https://hmb.oradba.ch/`
- [x] `/admin` during the talk: Martin
- [ ] Later, if `hmb2` is wanted: Cloudflare token (`Account - Cloudflare Tunnel - Edit` + `Zone - DNS - Edit`
  for oradba.ch) in `secrets/hmb terraform cloudflare`, then `make tf-apply` and `make host-up HOST=hmb2` [P3]

## Feedback deck + app (2026-11-16, before the talk 2026-11-17 15:00)

- [x] Slide 2 `spielregeln`, card "Wir auch": ADB and the on-prem lab (Docker) [P1]
- [x] Slide 3 `voraussetzungen`: platform per person (Stefan Mac, Martin Windows/WSL); drop Data Guard from the
  environment card [P1]
- [x] Slides 5/6: Martin before ACE - order in `talks/talks/wissen-nicht-was-sie-tun/talk.yaml` (talks `de1993d`)
- [x] Round 2 B (Martin): RMAN backup via a local CLI script instead of AWR/ASH; AWR/ASH moves to the reserve
- [x] Round 3 B (Martin): refreshable PDB clone instead of Data Guard (not available in the lab) [P1]
- [x] Slide 16 `fazit`: "AI ist kein Selbstlaeufer", image no longer overlaps the block, TODO note gone [P1]
- [x] App: voting countdown as draining beer (as on slide 7), participant page + `/screen`
- [x] Slide 5: new photo of Martin (cropped, no EXIF), source in the Trash
- [x] Deployed to `hmb` 09:34 over the VPN (backup `voting-20261116-083343.db`), `host-check` green, beer markup
  served, `PUBLIC_BASE_URL` unchanged; `make deck-private` built, QR on slides 7/10/12/14 decoded to `https://hmb.oradba.ch/`
- [x] Full session reset on `hmb` 2026-11-16 12:32 (host-side, same service function as `/admin`): rounds 2 B / 3 B
  are RMAN CLI / Refreshable PDB Clone, state `waiting`, 0 votes
- [x] App: beer tube with carbonation and foam, burp cloud, burp sound on `/screen` (CC0, host-only file),
  static cache-busting; `hmb` full reset 2026-11-16 12:32, new topics 2 B / 3 B live (PR #12-#15)
- [x] 1Password item `secrets/privesc demo` (field `password`) for `make talk-lab` - created and readable
- [x] Lab switch rehearsed: `make talk-lab` 3 min 20 s after a db19 restart (Java pool, ORA-04031 in privesc m4b
  unweak; floor 64M in oradba-labs `4431cfe`), `make talk-start` and each demo once - times in the runbook
- [x] seclab back to the privesc weak state - privesc entry point (`~/notes/prompts/privesc-talk-start.md`)
  [P1] (due: 2026-11-16)
- [x] Tue 11:45 `make talk-lab`, 14:00 `make talk-start` + tech check, after the talk `@reset.sql` in the three
  windows and `make reset LAB=seclab` (`docs/runbook-labs-talk-day.md`) [P1] (due: 2026-11-17)
- [x] `seclab-db26` unhealthy only in the privesc state - fully green after the switch

## App layout: switchable brand

- [x] Variant 1 Accenture, variant 2 Hold my Beer, admin default + local switch (PR #2, merged 2026-11-13)
- [x] Admin page in the new layout checked in a logged-in browser - part of the tech check Tue 14:00 [P2]

## CI

- [x] Phase 1: lint, tests 3.9/3.12, smoke, gitleaks (2026-11-13)
- [x] Branch protection on `main` once the repo is public (Free plan: 403 while private) - command in
  `tasks/plan-ci.md`, order in `tasks/plan-public-gate.md` [P2]
- [ ] Phase 2: `make release` + `release.yml`, `iac.yml` - after the talk [P2]
