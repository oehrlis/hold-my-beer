# Runbook - voting app behind a Cloudflare Tunnel

Publishes the voting app (`app/`) as `https://hmb.oradba.ch` through a Cloudflare Tunnel. The host keeps its public
IP, but no inbound port is needed for the app: `cloudflared` opens an outbound connection to Cloudflare and the
attendees' requests come back through it. HTTPS terminates at Cloudflare, no nginx, no certbot.

App-side background (why each setting): `app/README.md`, section "Betrieb hinter Cloudflare".
Handover app - slides: [`handover-app-slides.md`](handover-app-slides.md).
A new host with the same setup built by Terraform (`hmb2.oradba.ch`): [`runbook-terraform-host.md`](runbook-terraform-host.md).

No tunnel ID, credentials file, token or host IP belongs in this repo - it goes public after the talk.

## Prerequisites

- Cloudflare account with the zone `oradba.ch` (DNS on Cloudflare)
- Linux host (Oracle Linux 8/9 on OCI) with SSH access and sudo; the app deployed with `app/deploy-public.sh`
  (service `oracle-live-voting`, files under `/opt/oracle-live-voting/`)
- App port on the host, below `8080` (the port given to `deploy-public.sh`)
- 1Password for the tunnel credentials backup
- SSH alias on the Mac, e.g. `~/.ssh/config.d/30-hmb.oradba.ch` with `Host hmb hmb.oradba.ch`, `HostName <host-ip>`,
  `User opc`, `IdentityFile ~/.ssh/hmb.oradba.ch.pub` (1Password SSH agent), `IdentitiesOnly yes`. The DNS name
  `hmb.oradba.ch` points to Cloudflare, not to the host - SSH only works because the alias maps it to the IP.
  Plus `ControlMaster auto`, `ControlPath ~/.ssh/cm-%C`, `ControlPersist 10m`, `ServerAliveInterval 30`:
  `deploy-public.sh` opens 6-8 SSH connections in a row; on 2026-11-13 that ran into a block on the host
  (port 22 stopped answering, the tunnel kept running). With multiplexing a deploy uses one connection

Current live host (2026-11-13): the shared OCI jump host of a colleague (`vm-labs-ci-zrh-jump-pub`, OL 9.8, x86_64).
Other services run there - change only what belongs to `oracle-live-voting` and `cloudflared`.

## 1. App: listen locally, trust one proxy hop

On the host, edit `/opt/oracle-live-voting/shared/app.env`:

```bash
HOST=127.0.0.1
PORT=8080
PROXY_FIX_ENABLED=true
PROXY_FIX_X_FOR=1
SESSION_COOKIE_SECURE=true
PUBLIC_BASE_URL=https://hmb.oradba.ch
```

```bash
sudo systemctl restart oracle-live-voting
curl -s http://127.0.0.1:8080/readyz
ss -ltnp | grep ':8080 '   # must show 127.0.0.1:8080, not 0.0.0.0
```

**Redeploy keeps the URL only from 2026-11-13 on.** Up to then `deploy-public.sh` rewrote `PUBLIC_BASE_URL` on every
redeploy to `http://<SSH_HOST>:<PORT>` - with the alias `hmb` that was `http://hmb:8080`, and the live QR code
pointed nowhere (found 2026-11-13, an hour after the tunnel went live). Now an empty `PUBLIC_BASE_URL` keeps the
value in `app.env`. Deploy with the URL anyway, then nothing depends on the previous state:

```bash
make host-deploy HOST=hmb      # = PUBLIC_BASE_URL=https://hmb.oradba.ch app/deploy-public.sh 8080
make host-check HOST=hmb       # readyz, URL on the participant page, no-store, 404, services, 127.0.0.1:8080
```

`PROXY_FIX_X_FOR=1` is exactly one hop (cloudflared). A higher value makes `X-Forwarded-For` spoofable, a missing
ProxyFix puts all attendees and the admin into one login rate-limit bucket.

## 2. Install cloudflared

```bash
curl -fsSL https://pkg.cloudflare.com/cloudflared-ascii.repo | sudo tee /etc/yum.repos.d/cloudflared.repo
sudo dnf install -y cloudflared
cloudflared --version
```

Check the repo URL against the current Cloudflare docs ("Downloads" in the Cloudflare Tunnel documentation) before
running it.

## 3. Create the tunnel (locally managed)

Locally managed keeps the ingress in a file on the host and needs no token on a command line.

Run as root: `cloudflared` writes to the `~/.cloudflared/` of the user that runs it, so everything below lands in
`/root/.cloudflared/` (`cert.pem` from the login, `<TUNNEL-UUID>.json` from the create).

```bash
sudo cloudflared tunnel login                 # prints a URL - open it in your local browser, pick the zone oradba.ch
sudo cloudflared tunnel create hmb            # writes /root/.cloudflared/<TUNNEL-UUID>.json, prints the UUID
sudo cloudflared tunnel route dns hmb hmb.oradba.ch   # proxied CNAME hmb -> <TUNNEL-UUID>.cfargotunnel.com
```

Back up both files to 1Password, vault `secrets`, tags `DOAG`, `Hold my beer`, `hmb`, `hmb.oradba.ch`. `op` runs on
the Mac and the files are root-only, so pipe them over ssh - the content goes through stdin, never onto a command
line or into a local file:

```bash
ssh <host> 'sudo -n cat /root/.cloudflared/<TUNNEL-UUID>.json' | op document create - --file-name <TUNNEL-UUID>.json --title "hmb cloudflared tunnel credentials" --vault secrets --tags "DOAG,Hold my beer,hmb,hmb.oradba.ch"
ssh <host> 'sudo -n cat /root/.cloudflared/cert.pem' | op document create - --file-name cert.pem --title "hmb cloudflared cert.pem" --vault secrets --tags "DOAG,Hold my beer,hmb,hmb.oradba.ch"
```

`sudo -n` needs passwordless sudo and fails cleanly otherwise (`ssh -t` with a password prompt would write the prompt
into the item). Check the copy with `sha256sum` on the host against `op document get "<title>" --vault secrets |
shasum -a 256`. Only the credentials file is needed to run the tunnel; `cert.pem` is for `tunnel create` and
`route dns`.

Items in vault `secrets` for `hmb` (as of 2026-11-13):

<!-- markdownlint-disable MD013 MD060 -->
| Item | Content |
|------|---------|
| `hmb cloudflared tunnel credentials` | `<TUNNEL-UUID>.json` - enough to run the tunnel on any host |
| `hmb cloudflared cert.pem` | account cert for `tunnel create` / `route dns` / `tunnel delete` |
| `hmb cloudflared config.yml` | `/etc/cloudflared/config.yml` from step 4 |
| `hmb app production (hmb.oradba.ch)` | `SECRET_KEY`, admin password (`ADMIN_PASSWORD`), `PUBLIC_BASE_URL` |
<!-- markdownlint-restore -->

## 4. Configure and run as a service

```bash
sudo mkdir -p /etc/cloudflared
sudo install -m 600 -o root -g root /root/.cloudflared/<TUNNEL-UUID>.json /etc/cloudflared/
sudo tee /etc/cloudflared/config.yml >/dev/null <<'EOF'
tunnel: <TUNNEL-UUID>
credentials-file: /etc/cloudflared/<TUNNEL-UUID>.json
ingress:
  - hostname: hmb.oradba.ch
    service: http://127.0.0.1:8080
  - service: http_status:404
protocol: http2
EOF
sudo cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
sudo cloudflared tunnel --config /etc/cloudflared/config.yml ingress rule https://hmb.oradba.ch
sudo cloudflared service install
sudo systemctl enable --now cloudflared
systemctl status cloudflared --no-pager
```

The last ingress rule is required: anything that is not `hmb.oradba.ch` gets a 404 instead of reaching the app.
`--config` is a flag of `tunnel`, not of `ingress validate` - after the subcommand it fails with "flag provided but
not defined". `validate` prints `OK`, `rule` must show the `http://127.0.0.1:8080` rule.
`protocol: http2` keeps the tunnel on TCP 443. Without it `cloudflared` starts with QUIC (UDP 7844); where egress
allows only TCP (OCI security list) every dial ends in "failed to dial to edge with quic: timeout", the precheck says
`suggested_protocol=http2`, and `service install` fails with "a timeout was exceeded" because the unit waits for the
first connection.

## 5. Close inbound ports

If the app port was opened for an earlier HTTP test, close it again - the tunnel does not need it.
Check first what is open and who listens - on a shared host not every port is yours:

```bash
sudo firewall-cmd --list-ports
sudo ss -ltnp | grep -v 127.0.0.1
```

On the current live host `8000/tcp` is open and a `python3` (started at boot, not ours) listens on `0.0.0.0:8000` -
leave it to its owner. Only the app port goes:

```bash
sudo firewall-cmd --permanent --remove-port=8080/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

OCI: remove the ingress rule for the app port from the security list or NSG. Keep SSH only.

## 6. Cloudflare dashboard settings

<!-- markdownlint-disable MD013 MD060 -->
| Setting | Value | Why |
|---------|-------|-----|
| SSL/TLS - Always Use HTTPS | on | QR code and slides point to HTTPS |
| Security - Bot Fight Mode | off for the event | 100-300 phones behind one NAT IP poll every 2 s; a JS challenge breaks the polling |
| Security - Under Attack Mode | off | same reason |
| WAF / managed challenge rules | none matching `hmb.oradba.ch` | same reason |
| Caching - Cache Rules | none matching `hmb.oradba.ch` (no "Cache Everything" on `*.oradba.ch`) | the app sends `no-store`; a cached `/api/state` freezes the vote |
| Rate limiting rules | none, or generous | a whole room shares one IP |
<!-- markdownlint-restore -->

Bot Fight Mode is a zone-wide switch on the free plan and affects all of `oradba.ch`. If it is on for the blog,
test with real phones (step 7); if attendees get a challenge page, switch it off for the conference day.

## 7. Verify

`make host-check HOST=hmb` runs the curl checks below plus service state and listen address in one go.

```bash
curl -sI https://hmb.oradba.ch/readyz | head -1                       # HTTP/2 200
curl -s https://hmb.oradba.ch/readyz                                  # {"data":{"status":"ready"},"ok":true}
curl -sI https://hmb.oradba.ch/qr.svg | grep -i -E 'cross-origin-resource-policy|cache-control'
curl -sI https://hmb.oradba.ch/api/state | grep -i -E 'cache-control|cf-cache-status'   # no-store, not HIT
curl -s -o /dev/null -w '%{http_code}\n' https://hmb.oradba.ch/does-not-exist           # 404 from the app
```

- Phone on **mobile data** (not Wi-Fi): scan the QR on the deck's voting slide, the page loads, a vote counts
- Admin login from the laptop: `https://hmb.oradba.ch/admin` (password: 1Password item
  `hmb app production (hmb.oradba.ch)`, on the host `shared/initial-admin-password.txt`)
- Rebuild the deck with the same URL: `VOTING_URL=https://hmb.oradba.ch` (default in `slides/build.sh`) - the live QR
  now loads from the app instead of the build fallback
- QR content: the image must decode to `https://hmb.oradba.ch/` (phone camera, or on the Mac
  `rsvg-convert -b white qr.svg -o qr.png` and any QR reader) - `PUBLIC_BASE_URL` decides it, not the tunnel
- Login rate limit sees real client IPs: `journalctl -u oracle-live-voting -n 50` after a test login shows the
  phone's or laptop's address, not `127.0.0.1`

## Talk day

- Before the talk: `make host-check HOST=hmb` and `make host-backup HOST=hmb` (SQLite online backup into
  `shared/backups/`, see `app/README.md`)
- Tunnel down: `sudo systemctl restart cloudflared`; the app state is in SQLite and survives
- App down: `sudo systemctl restart oracle-live-voting`
- Both down or no network: show of hands on the round slide (fallback in `handover-app-slides.md`)

## After the talk

- Export results first: `flask export-json` (see `app/README.md`)
- Keep the tunnel for the next event, or tear it down - delete the CNAME `hmb` in the Cloudflare dashboard (DNS),
  then on the host:

```bash
sudo systemctl disable --now cloudflared
cloudflared tunnel delete hmb
sudo rm -f /etc/cloudflared/<TUNNEL-UUID>.json
```
