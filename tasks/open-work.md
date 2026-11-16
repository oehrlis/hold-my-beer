# Open work

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
- [ ] Rehearsal against `hmb` (one round, window switch, Speaker View) [P1]
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
- [ ] "Gesamte Session zurücksetzen" in `/admin` on `hmb` - Stefan or Martin; rounds 2/3 change only then [P1]
- [ ] Lab (Martin's B topics): his own lab - CDB in ARCHIVELOG with local undo (3 B), RMAN target (2 B) [P1]
- [x] App: beer tube with carbonation and foam, burp cloud, burp sound on `/screen` (CC0, host-only file),
  static cache-busting; `hmb` full reset 2026-11-16 12:32, new topics 2 B / 3 B live (PR #12-#15)
- [ ] 1Password item `secrets/privesc demo` (field `password`) for `make talk-lab` - command in
  `docs/runbook-labs-talk-day.md` "Entry point" [P1] (due: 2026-11-16)
- [ ] Rehearse the lab switch privesc -> hmb on `seclab` once (`make talk-lab`, then `make talk-start`), fill in
  the times, then `stage.sh weak` again (`docs/runbook-labs-talk-day.md`) [P1] (due: 2026-11-16)
- [ ] `seclab-db26` unhealthy in the privesc state (SYSTEM login via listener fails) - must be green after the
  switch [P1] (due: 2026-11-16)

## App layout: switchable brand

- [x] Variant 1 Accenture, variant 2 Hold my Beer, admin default + local switch (PR #2, merged 2026-11-13)
- [ ] Admin page in the new layout checked in a logged-in browser [P2]

## CI

- [x] Phase 1: lint, tests 3.9/3.12, smoke, gitleaks (2026-11-13)
- [ ] Branch protection on `main` once the repo is public (Free plan: 403 while private) - command in
  `tasks/plan-ci.md` [P2]
- [ ] Phase 2: `make release` + `release.yml`, `iac.yml` - after the talk [P2]
