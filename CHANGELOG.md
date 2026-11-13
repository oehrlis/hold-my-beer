# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- App layout Accenture (`acn`) / Hold my Beer (`hmb`) for participant, screen and admin: token-based `app.css`,
  `js/theme.js` (same codes and keys as the deck), Hold-my-Beer logo in the header. Default `APP_THEME`, the
  admin sets it for everyone (panel "Layout", migration `4e7a2c1b9d30` adds `session_state.theme`); each device
  can override locally (`?theme=`, key `t`, `ACN | HMB` switch; `Shift+T` follows the default again)

### Fixed

- `docs/runbook-cloudflare-tunnel.md`, found during the real setup on 2026-11-13:
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
