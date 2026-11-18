# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- After the talk (2026-11-17): `docs/manuskript/manuskript-hold-my-beer-doag-2026.md` - session manuscript for
  the DOAG portal (entry, guardrails, prompts in the original wording, flow, results, share AI / prep / Stefan
  for round 2 counted afterwards from the protocol); the protocols `docs/session-2026-11-17-claude-code-lab.md`
  (Unified Audit for CLAUS, faulty PL/SQL package) and `docs/session-2026-11-18-apex-demopdb.md` (APEX + ORDS
  on DEMOPDB, app not built), transcript paths redacted; `docs/prompt-martin-session-protocol.md` (Martin
  collects his sessions in the same shape); `tasks/plan-public-gate.md` (scan result, blockers, steps, message
  to Martin)
- Pool: optional `result` per round (votes, played or winner, outcome) and per event (participation note).
  The final score slide shows them and drops the TODO once every round has one; the score tiles only appear
  with a counted scorecard. `pool/doag-ak-2026.yaml` carries the talk result from the voting DB (90 devices,
  233 votes)
- `scripts/talk-start.sh` 0.1.0 + `make talk-check | talk-lab | talk-demos | talk-open | talk-start`: one entry
  point for the session - read-only check (app, lab, privesc leftovers, demo starting points, stale deck), the lab
  switch from the privesc state (asks first, `DEMO_PWD` via environment or `op read`), demo `setup.sql`, and
  deck / `/screen` / `/admin` / one Terminal window per round; `DRY_RUN=1` changes nothing. 0.1.1: a failed
  lab step names where it stopped and how to go on (half switched, rerun is idempotent). 0.2.0: the sqlplus
  windows open with the Terminal profile `demo` (`TERMINAL_PROFILE`); `talk-check` reports a missing profile
- `docs/runbook-labs-talk-day.md`: Stefan's rounds on oradba-labs `seclab` - switch from the privesc weak state
  (`stage.sh unweak`, then `make reset`), starting points and before pictures, reset, and a step-based count of
  who did what (AI / preparation / Stefan in %); `docs/prompts-stefan-rounds.md`: the three live prompts
- CI phase 1: `.github/workflows/ci.yml` (`make lint`; `make app-test` on Python 3.9 in an `oraclelinux:9`
  container - the hosts' system python - and on 3.12; `make app-smoke` in OL9) and `secrets.yml` (gitleaks over
  the full history, weekly too, `.gitleaks.toml` with OCI OCID / PAR / API key fingerprint and Cloudflare tunnel
  rules). Branch protection is not available for a private repo on the Free plan (HTTP 403) - set it when the
  repo goes public (`tasks/plan-ci.md`)
- `make app-smoke`: app on a throwaway DB, `tools/smoke.sh`, 50-client load test, stop
- `host-check` (`scripts/hmb-host.sh` 0.3.0): vote POST with token through the tunnel must pass CSRF
  (`invalid_option`, nothing counted) - would have caught the v0.2.0 CSRF bug before the first login
- App: the voting countdown drains as a beer tube on the participant page and on `/screen`, as on the slide
  "Handys raus" (fill = `remaining / duration` from `/api/state`, no backend change; Accenture layout: solid accent)
- App: the beer tube has carbonation bubbles and a bubbly foam head over the rim; when the time runs out a
  "Rülps!" bubble pops up once - outside the views, so the switch to "closed" does not cut it off
- App: the burp bubble is a cloud; `/screen` can play a burp sound ("Ton aus/an", off by default - the click
  unlocks browser audio and plays a test burp). The file comes from `BURP_FILE` on the host via `/screen/burp`
  and is never in the repo; audio files are git-ignored. Live: CC0 burp from freesound.org (570266);
  `BURP_CREDIT` shows a credit on `/screen` for sounds that need one (hoerspielbox.de)

### Changed

- Pool: round 2 B (Martin) is now "RMAN: lokales CLI-Skript für ein Backup der DB", round 3 B "Refreshable PDB
  Clone" instead of the Data Guard switchover (no standby in the lab); AWR/ASH moves to the reserve (13 topics).
  `hmb` needs "Gesamte Session zurücksetzen" in `/admin` - the seed never changes existing rounds
- Slides: rules card "Wir auch" names ADB and the on-prem lab (Docker); prerequisites show the platform per
  person (Mac, Windows / WSL) and drop Data Guard; takeaways motto "AI ist kein Selbstläufer", draft TODO gone
  (it squeezed the cards, the image ran into the third one); new photo of Martin (head to hips, colleague in the background and number plate blurred)
- Slides: illustration next to the motto 330 -> 290 px, rules line shortened - in the Accenture layout the wider
  font made the cards taller and the "This is fine" image ran into the third card
- Speaker order Stefan, Martin, ACE program - in the talks repo recipe (`talks/wissen-nicht-was-sie-tun/talk.yaml`)

### Removed

- `slides/src/speaker-martin/martin-feuerwehr.jpg` (gear only), replaced by `martin-portrait.jpg`; last content
  in `64254d0`

### Fixed

- App: static URLs carry `?v=<content hash>` - with a 4 h cache an open projector browser kept the old JS after a
  deploy and the beer tube never showed
- CI: actions on Node 24 (`checkout` v7, `setup-node` v7, `setup-python` v7, `setup-terraform` v4) - the
  Node 20 versions raised a deprecation warning in every job
- `app/tools/loadtest.py`: "Verteilung stimmt" failed since rounds can have four options (`counts` has `"D": 0`)

## [0.2.0] - 2026-11-13

Voting app live behind the Cloudflare Tunnel as `https://hmb.oradba.ch`, own host as code (`hmb2`), switchable
layout. Before rehearsal, four days before the talk.

### Added

- `make host-backup HOST=...` / `scripts/hmb-host.sh backup` (0.2.0): SQLite online backup on the host with
  absolute paths, reports file and size - the hand-typed `cd current && . ../shared/app.env` failed, `current`
  is a symlink into `releases/`
- SSH multiplexing (`ControlMaster`/`ControlPersist`) in the generated SSH block and in the runbook: a deploy
  with 6-8 short connections ran into a block on the shared host (port 22 timed out, tunnel kept running)
- `terraform/`: own voting host on OCI (`VM.Standard.A1.Flex` 1 OCPU / 6 GB, Always Free, own VCN, inbound SSH from
  `admin_cidrs` only) plus Cloudflare tunnel and proxied CNAME, cloud-init for `cloudflared` and `python3`; first
  target `hmb2.oradba.ch` as test and backup. Cloudflare token via `op run` (`terraform/op.env`)
- `scripts/hmb-host.sh`: app secrets as 1Password item, `app.env` on the host from it (stdin only, never
  overwrites), public checks (readyz, QR URL, `no-store`, 404, services, listen address)
- Makefile: `tf-init|plan|apply|output|ssh-config|destroy`, `host-secrets|env|deploy|check|up`, `lint-terraform`
- `docs/runbook-terraform-host.md`; `tasks/open-work.md`; CI/release proposal `tasks/plan-ci.md`
- App layout Accenture (`acn`) / Hold my Beer (`hmb`) for participant, screen and admin: token-based `app.css`,
  `js/theme.js` (same codes and keys as the deck), Hold-my-Beer logo in the header. Default `APP_THEME`, the
  admin sets it for everyone (panel "Layout", migration `4e7a2c1b9d30` adds `session_state.theme`); each device
  can override locally (`?theme=`, key `t`, `ACN | HMB` switch; `Shift+T` follows the default again)

### Changed

- `.markdownlint.json`: `MD024` with `siblings_only` - Keep a Changelog repeats `Added` / `Fixed` per version

### Fixed

- App behind the tunnel rejected every POST with "Sicherheitstoken ungültig oder abgelaufen" (admin login and
  votes): over HTTPS Flask-WTF requires a same-origin Referer, the app sends `Referrer-Policy: no-referrer`.
  `WTF_CSRF_SSL_STRICT = False`; the session-bound token stays mandatory (`tests/test_https_csrf.py`). Over plain
  HTTP before the tunnel the check never ran - found on 2026-11-13 at the first admin login via
  `https://hmb.oradba.ch`
- `app/deploy-public.sh`, `app/deploy/remote-install.sh`: a redeploy without `PUBLIC_BASE_URL` rewrote it to
  `http://<SSH_HOST>:<PORT>` - on the live host `http://hmb:8080`, so the QR code pointed nowhere. Now an empty
  value keeps `app.env`; a first deploy with an `https://` URL writes the tunnel settings (127.0.0.1, ProxyFix one
  hop, secure cookie). Live host corrected by hand on 2026-11-13, QR decoded to `https://hmb.oradba.ch/`
- `docs/runbook-cloudflare-tunnel.md`, found during the real setup on 2026-11-13:
  - redeploy pitfall above, `make host-deploy` / `make host-check`, QR content check, all four 1Password items,
    SSH alias `hmb hmb.oradba.ch` (DNS points to Cloudflare), shared host: port 8000 is not ours
  - `cloudflared` runs as root and writes to `/root/.cloudflared/`; `sudo cp ~/.cloudflared/...` expanded `~` to
    the login user before `sudo` and found nothing - now `sudo install -m 600` from `/root/.cloudflared/`
  - `--config` belongs to `tunnel`, not to `ingress validate` ("flag provided but not defined") - order fixed,
    plus `ingress rule` as a check
  - `protocol: http2` in `config.yml`: QUIC (UDP 7844) timed out on the OCI host, the unit never became ready and
    `service install` failed with "a timeout was exceeded"
  - 1Password backup: vault `secrets` with tags instead of `Private`, piped over ssh from the Mac (the files are
    root-only and `op` is not on the host), `cert.pem` included, check by `sha256sum`

## [0.1.0] - 2026-11-12

First complete state for DOAG AK 2026 ("Denn sie wissen nicht was sie tun", 2026-11-17), before rehearsal.

### Added

- `app/`: voting app by Martin Berger, imported from `dswnwst` (commit `cfd83e1`) with its history
- `pool/doag-ak-2026.yaml`: topic pool as single source for app seed and round slides (3 rounds, 12 reserve
  topics, optional English fields)
- `docs/handover-app-slides.md`: contract between app and slides (QR from the app, window switch, fallback)
- `docs/runbook-cloudflare-tunnel.md`: app behind a Cloudflare Tunnel as `hmb.oradba.ch`
- `slides/`: frame deck (22 slides) built with the talk CLI - generator for pool-driven slides, bilingual DE/EN
  switch (key `L`), theme switch Accenture / Hold my Beer (key `T`), own illustrations in `slides/img/`,
  private photos via `HMB_PRIVATE_DIR` with a guard against building them into the repo
- `Makefile`: `deck`, `deck-private`, `deck-pdf`, `app-test`, `app-run`, `lint`, `status`
- `CHANGELOG.md`, `VERSION`

### Changed

- `app/`: seed from the pool file (strict validation, no built-in fallback), `/qr.svg` embeddable in the slides
  (CORP), `no-store` for HTML, configurable proxy hops (`PROXY_FIX_X_FOR`) and `SHARE_URL`, macOS fallbacks in
  the start/stop/status scripts, Swiss "ss" in the README
- `app/deploy`: no hardcoded host, user or SSH key; package ships the pool file

### Fixed

- `app/deploy/remote-install.sh`: post-deploy check looped over paths with trailing commas
- `app/tests`: flaky request IDs in `conftest.py`; `tools/smoke.sh` with auto-published results

### Security

- Removed host IP, SSH user and key name from the app code. They remain in the imported history (`cfd83e1`);
  Martin Berger accepted that on 2026-11-12, no history rewrite before the repo goes public
