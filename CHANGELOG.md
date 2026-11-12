# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
