# Runbook - voting host with Terraform (OCI + Cloudflare Tunnel)

Builds a voting host of its own instead of the shared jump host: one small OCI instance, the app behind a
Cloudflare Tunnel, inbound only SSH from the admin IP. First target `hmb2.oradba.ch` as test and backup; the live
name `hmb.oradba.ch` stays on the current host until a rehearsal on `hmb2` has passed.

Manual setup and the reasons behind each setting: [`runbook-cloudflare-tunnel.md`](runbook-cloudflare-tunnel.md).
Terraform does the same steps 2-5 of that runbook; steps 6 (dashboard) and 7 (verify) still apply.

No OCID, IP, tunnel ID or token belongs in the repo - `terraform.tfvars` and the state are gitignored.

## What gets built

<!-- markdownlint-disable MD013 MD060 -->
| Resource | Name (oci-naming) | Note |
|----------|-------------------|------|
| VCN, IGW, route table | `vcn-zrh-lab-hmb-net-01`, `igw-...`, `rt-zrh-lab-hmb-public-01` | own network, `10.42.0.0/24` |
| Security list | `sl-zrh-lab-hmb-public-01` | in: TCP 22 from `admin_cidrs` + ICMP 3/4; out: all |
| Subnet | `subnet-zrh-lab-hmb-public-01` | public, the instance gets a public IP for SSH and egress |
| Instance | `vm-zrh-lab-hmb-app-01` | `VM.Standard.A1.Flex` 1 OCPU / 6 GB, OL 9 aarch64, 50 GB boot - inside Always Free |
| Tunnel | `hmb2` | locally managed (`config_src = local`), secret from `random_bytes` |
| DNS | `hmb2.oradba.ch` | proxied CNAME to `<TUNNEL-UUID>.cfargotunnel.com` |
<!-- markdownlint-restore -->

cloud-init installs `cloudflared` and `python3`, writes `/etc/cloudflared/config.yml` (`protocol: http2`, ingress
`http://127.0.0.1:8080`, catch-all 404) and the credentials file (600), starts `cloudflared` and creates
`/opt/oracle-live-voting/shared` for `opc`. The app comes afterwards with the usual `app/deploy-public.sh`.

## Prerequisites

- OCI profile `ACE` in `~/.oci/config`, compartment `cmp-oradba-labs-compute` (region `eu-zurich-1`)
- 1Password item `hmb terraform cloudflare` in vault `secrets`, field `credential`: Cloudflare API token with
  - Account - Cloudflare Tunnel - Edit
  - Zone - DNS - Edit and Zone - Zone - Read, zone `oradba.ch`

  The token in `AI-DevOps/Cloudflare API` can read the zone (enough for `tf-plan`) but gets "Authentication
  error" on tunnels - it cannot apply. The reference lives in `terraform/op.env`
- SSH key `~/.ssh/hmb.oradba.ch.pub` (private key in the 1Password SSH agent) - same key as `hmb`
- `terraform` >= 1.6, `op`, `jq`

## 1. Configure

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# compartment_ocid = OCID of cmp-oradba-labs-compute
# admin_cidrs      = ["<curl -s https://ifconfig.me>/32"]
make tf-init
make tf-plan          # 9 resources: network (5), instance, random secret, tunnel, DNS record
```

The admin IP changes with the network (home, hotel, conference). Add the new `/32` to `admin_cidrs`, then
`make tf-plan tf-apply` - this only updates the security list.

## 2. Build

```bash
make tf-apply
make tf-ssh-config    # writes ~/.ssh/config.d/31-hmb2.oradba.ch (Host hmb2 hmb2.oradba.ch -> public IP)
ssh hmb2 'cloud-init status --wait; systemctl is-active cloudflared'
```

`cloud-init status --wait` blocks until the first boot is done (a few minutes on A1). `cloudflared` is active
before the app runs; until the deploy, `https://hmb2.oradba.ch` answers 502.

A1 capacity in Zurich is sometimes short: "Out of host capacity" on apply - wait and repeat `tf-plan tf-apply`, or
`shape = "VM.Standard.E5.Flex"` with `memory_gb = 4` in `terraform.tfvars` (paid, a few CHF per month).

## 3. App: secrets, deploy, check

```bash
make host-up HOST=hmb2
```

Same as four steps:

<!-- markdownlint-disable MD013 MD060 -->
| Step | Target | Does |
|------|--------|------|
| 1 | `host-secrets` | creates the 1Password item `hmb2 app (hmb2.oradba.ch)` with generated `SECRET_KEY` and admin password - only if missing |
| 2 | `host-env` | writes `app.env` on the host from that item (127.0.0.1, ProxyFix 1 hop, secure cookie, `https://hmb2.oradba.ch`) - only if missing |
| 3 | `host-deploy` | `app/deploy-public.sh` with `PUBLIC_BASE_URL=https://hmb2.oradba.ch`, port 8080 |
| 4 | `host-check` | readyz, URL on the participant page, `qr.svg`, `no-store`, 404, both services, listen `127.0.0.1:8080` |
<!-- markdownlint-restore -->

Secrets go through stdin (`op read` -> `ssh` -> file with `umask 077`), never onto a command line. Admin password
for `/admin`: field `password` of the item.

Then runbook step 6 (dashboard settings apply zone-wide, nothing new) and step 7 with a phone on mobile data.

## Rehearsal against hmb2

```bash
make deck VOTING_URL=https://hmb2.oradba.ch     # deck QR and URL for the rehearsal - do not commit this build
```

Back to `make deck` (default `https://hmb.oradba.ch`) before committing.

## Later: hmb.oradba.ch onto the new host

Not before the talk on 2026-11-17 without a reason - the current host runs and is verified. When it is time:

1. Second root module or workspace with `hostname = "hmb"`, `instance_no = "02"` - the name `hmb` is taken by the
   manually created tunnel and the existing CNAME: delete both first (dashboard or `cloudflared tunnel delete hmb`
   with `cert.pem` from 1Password), or import them (`terraform import`)
2. `flask backup` on the old host, copy the backup over, restore (`app/README.md`, "Backup, Export, Restore")
3. `make host-up HOST=hmb`, `make host-check HOST=hmb`, phone test
4. Old host: `sudo systemctl disable --now cloudflared oracle-live-voting` - only after the colleague knows

## Secrets in this setup

- The tunnel secret is in the Terraform state and in the instance metadata (cloud-init `user_data`) - readable for
  anyone with read access on the instance in the `ACE` tenancy and from the instance metadata service on the host.
  Accepted for a lab host; the state stays local (`terraform/terraform.tfstate`, gitignored, not on OneDrive)
- Lost state: `make tf-destroy` is no longer possible - delete tunnel and CNAME in the Cloudflare dashboard and the
  OCI resources by tag `project = hold-my-beer`
- The Cloudflare token only comes in through `op run` for the duration of the command

## Teardown

```bash
make tf-destroy      # instance, network, tunnel, DNS record - asks for "yes"
op item delete "hmb2 app (hmb2.oradba.ch)" --vault secrets --archive
rm ~/.ssh/config.d/31-hmb2.oradba.ch
```
