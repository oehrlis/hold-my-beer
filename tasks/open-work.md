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
- [ ] Cloudflare token with `Account - Cloudflare Tunnel - Edit` + `Zone - DNS - Edit` (oradba.ch) [P1]
- [ ] `make tf-apply`, `make host-env host-deploy host-check HOST=hmb2` [P1]
- [ ] Rehearsal against `hmb2` (one round, window switch, Speaker View) [P1]
- [ ] Switch `hmb.oradba.ch` to the new instance - only after the rehearsal, not before the talk [P2]

## App layout: switchable brand

- [x] Variant 1 Accenture, variant 2 Hold my Beer, admin default + local switch (PR #2, merged 2026-11-13)
- [ ] Admin page in the new layout checked in a logged-in browser [P2]

## CI (proposal)

- [ ] Decide on `tasks/plan-ci.md` (phase 1: lint, tests, smoke, gitleaks before the repo goes public) [P2]
