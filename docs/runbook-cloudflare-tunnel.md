# Runbook - voting app behind a Cloudflare Tunnel

Publishes the voting app (`app/`) as `https://hmb.oradba.ch` through a Cloudflare Tunnel. The host keeps its public
IP, but no inbound port is needed for the app: `cloudflared` opens an outbound connection to Cloudflare and the
attendees' requests come back through it. HTTPS terminates at Cloudflare, no nginx, no certbot.

App-side background (why each setting): `app/README.md`, section "Betrieb hinter Cloudflare".
Handover app - slides: [`handover-app-slides.md`](handover-app-slides.md).

No tunnel ID, credentials file, token or host IP belongs in this repo - it goes public after the talk.

## Prerequisites

- Cloudflare account with the zone `oradba.ch` (DNS on Cloudflare)
- Linux host (Oracle Linux 8/9 on OCI) with SSH access and sudo; the app deployed with `app/deploy-public.sh`
  (service `oracle-live-voting`, files under `/opt/oracle-live-voting/`)
- App port on the host, below `8080` (the port given to `deploy-public.sh`)
- 1Password for the tunnel credentials backup

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

```bash
cloudflared tunnel login                 # prints a URL - open it in your local browser, pick the zone oradba.ch
cloudflared tunnel create hmb            # writes ~/.cloudflared/<TUNNEL-UUID>.json, prints the UUID
cloudflared tunnel route dns hmb hmb.oradba.ch   # creates the proxied CNAME hmb -> <TUNNEL-UUID>.cfargotunnel.com
```

Back up the credentials file to 1Password (path as argument, not the content):

```bash
op document create ~/.cloudflared/<TUNNEL-UUID>.json --title "hmb cloudflared tunnel credentials" --vault Private
```

## 4. Configure and run as a service

```bash
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/<TUNNEL-UUID>.json /etc/cloudflared/
sudo chmod 600 /etc/cloudflared/<TUNNEL-UUID>.json
sudo tee /etc/cloudflared/config.yml >/dev/null <<'EOF'
tunnel: <TUNNEL-UUID>
credentials-file: /etc/cloudflared/<TUNNEL-UUID>.json
ingress:
  - hostname: hmb.oradba.ch
    service: http://127.0.0.1:8080
  - service: http_status:404
EOF
sudo cloudflared tunnel ingress validate --config /etc/cloudflared/config.yml
sudo cloudflared service install
sudo systemctl enable --now cloudflared
systemctl status cloudflared --no-pager
```

The last ingress rule is required: anything that is not `hmb.oradba.ch` gets a 404 instead of reaching the app.

## 5. Close inbound ports

If the app port was opened for an earlier HTTP test, close it again - the tunnel does not need it:

```bash
sudo firewall-cmd --permanent --remove-port=8080/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

OCI: remove the ingress rule for the app port from the security list or NSG. Keep SSH only.

## 6. Cloudflare dashboard settings

| Setting | Value | Why |
|---------|-------|-----|
| SSL/TLS - Always Use HTTPS | on | QR code and slides point to HTTPS |
| Security - Bot Fight Mode | off for the event | 100-300 phones behind one NAT IP poll every 2 s; a JS challenge breaks the polling |
| Security - Under Attack Mode | off | same reason |
| WAF / managed challenge rules | none matching `hmb.oradba.ch` | same reason |
| Caching - Cache Rules | none matching `hmb.oradba.ch` (no "Cache Everything" on `*.oradba.ch`) | the app sends `no-store`; a cached `/api/state` freezes the vote |
| Rate limiting rules | none, or generous | a whole room shares one IP |

Bot Fight Mode is a zone-wide switch on the free plan and affects all of `oradba.ch`. If it is on for the blog,
test with real phones (step 7); if attendees get a challenge page, switch it off for the conference day.

## 7. Verify

```bash
curl -sI https://hmb.oradba.ch/readyz | head -1                       # HTTP/2 200
curl -s https://hmb.oradba.ch/readyz                                  # {"data":{"status":"ready"},"ok":true}
curl -sI https://hmb.oradba.ch/qr.svg | grep -i -E 'cross-origin-resource-policy|cache-control'
curl -sI https://hmb.oradba.ch/api/state | grep -i -E 'cache-control|cf-cache-status'   # no-store, not HIT
curl -s -o /dev/null -w '%{http_code}\n' https://hmb.oradba.ch/does-not-exist           # 404 from the app
```

- Phone on **mobile data** (not Wi-Fi): scan the QR on the deck's voting slide, the page loads, a vote counts
- Admin login from the laptop: `https://hmb.oradba.ch/admin` (password from `shared/initial-admin-password.txt`)
- Rebuild the deck with the same URL: `VOTING_URL=https://hmb.oradba.ch` (default in `slides/build.sh`) - the live QR
  now loads from the app instead of the build fallback
- Login rate limit sees real client IPs: `journalctl -u oracle-live-voting -n 50` after a test login shows the
  phone's or laptop's address, not `127.0.0.1`

## Talk day

- Before the talk: `systemctl is-active cloudflared oracle-live-voting`, `curl -s https://hmb.oradba.ch/readyz`,
  `flask backup` on the host (see `app/README.md`)
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
