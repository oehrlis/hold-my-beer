# Plan - CI for hold-my-beer (proposal, 2026-11-13)

Proposal only, nothing built yet. GitHub Actions (`oehrlis/hold-my-beer` is on GitHub, private now, public after
the talk). Every job calls a `make` target, so local and CI run the same commands.

## Today

- `make lint`: markdownlint, shellcheck, `py_compile`, `terraform fmt` + `validate`
- `make app-test`: 71 pytest tests, Python from the dev venv
- no workflow, no secret scan; the repo goes public after the talk - that makes the secret scan the first gate

## Proposal

<!-- markdownlint-disable MD013 MD060 -->
| Workflow | Trigger | Jobs | Secrets | Phase |
|----------|---------|------|---------|-------|
| `ci.yml` | push, PR | `lint` (make lint), `app-test` (matrix Python 3.9 = OL9 system python, 3.12), `smoke` (start app, `tools/smoke.sh`, `loadtest.py --clients 50`) | none | 1 - before the talk |
| `secrets.yml` | push, PR, weekly | gitleaks over the full history incl. OCI rules (OCID, PAR, tenancy), fails the PR | none | 1 - before public |
| `iac.yml` | PR on `terraform/**` | `terraform fmt -check`, `validate`, tflint (oci ruleset), trivy config (security list, IMDS v2) | none | 2 |
| `release.yml` | tag `v*` | `app/package.sh` -> release asset, CHANGELOG section as release notes, deck HTML as asset | `GITHUB_TOKEN` | 2 |
| `deck.yml` | PR on `slides/**`, `pool/**` | `generate.py` dry run against the pool (slide plan, no talk CLI) | none | 3 - needs the talks repo or a vendored recipe |
| `deploy.yml` | `workflow_dispatch` only, environment with approval | `make host-deploy host-check HOST=hmb2` | SSH key, 1Password service account | 3 - only after a decision, see below |
<!-- markdownlint-restore -->

## Tag and release - controlled, one way only

One entry point `make release VERSION=x.y.z`, one workflow that acts on the tag. Nobody tags by hand.

Versions: `VERSION` (repo, deck + host tooling, SemVer) and `app/VERSION` (Martin's app, own cadence). The repo
tag is `vX.Y.Z` from `VERSION`; `app/VERSION` goes into the release notes, it is not bumped by the repo release.

`make release VERSION=x.y.z` (local, Mac) - every gate stops with a message, none skips silently:

1. Gates: branch `main`, tree clean, `git fetch` and not behind `origin/main`, tag `vX.Y.Z` neither local nor on
   origin, `x.y.z` > current `VERSION`
2. `make lint app-test` green; `ci.yml` green for `HEAD` (`gh run list --commit HEAD --workflow ci.yml`)
3. CHANGELOG: `## [Unreleased]` not empty -> becomes `## [x.y.z] - YYYY-MM-DD`, new empty `[Unreleased]` above
4. `VERSION` and the Makefile header `Version....:` to `x.y.z`, commit `chore(release): vX.Y.Z`
5. Annotated tag `vX.Y.Z` (message = CHANGELOG section), then `git push origin main` **and**
   `git push origin vX.Y.Z` - a tag that is not pushed does not exist
6. Verify: `git ls-remote --tags origin vX.Y.Z` returns the commit, `git status -sb` shows `main` without `ahead`
7. Output: link to the running `release.yml`; `DRY_RUN=1` shows steps 1-6 without writing

`release.yml` (trigger: push of a tag `v*`, never `workflow_dispatch`):

- Guard: tag == `v$(cat VERSION)` and the tag commit is on `main` (`git branch -r --contains`) - otherwise fail,
  no release for an orphaned or mistyped tag
- Same jobs as `ci.yml` again on the tag commit (lint, tests, smoke, gitleaks) - the release does not trust an
  older run
- Build: `app/package.sh` -> `dist/dswnwst-voting-<app-version>-<stamp>.tar.gz` + `sha256sum`; public deck
  HTML (the committed build, no talk CLI in CI)
- `gh release create vX.Y.Z` with the CHANGELOG section as notes, assets + checksums; pre-release for `0.x` or `-rc`
- No deploy from the release workflow - deploy stays a separate, manual step against a named host

Re-run after a failed workflow: delete and push the tag again (`git push origin --delete vX.Y.Z`, then push),
never `--force` (a force-pushed tag does not trigger `push: tags`).

Deploy of a release (manual until the CI deploy decision): `git checkout vX.Y.Z`, `make host-deploy host-check
HOST=hmb2`, then `HOST=hmb`; the release ID on the host (`/opt/oracle-live-voting/current`) names the app version.

## Deploy from CI - recommendation: not before the talk

- The security list lets SSH in only from `admin_cidrs`; GitHub runners have changing IPs. Opening 22 to the
  GitHub ranges is the opposite of the design
- Clean ways when it is wanted: SSH through the tunnel (`ssh.hmb2.oradba.ch` with Cloudflare Access service token,
  `cloudflared access ssh` on the runner) and port 22 closed completely; or a self-hosted runner in the homelab
- Secrets then via a 1Password service account (`op` in the workflow, `1password/load-secrets-action`), no long-lived
  copies in GitHub secrets except the service account token
- Until then: deploy stays `make host-deploy` from the Mac, `make host-check` proves it

## Not in CI

- `terraform plan/apply`: needs OCI API key and Cloudflare token; the state is local. Stays manual (`make tf-*`)
- private deck (`make deck-private`): photos only on OneDrive

## Order

- [x] `ci.yml` + `secrets.yml` (lint, tests 3.9/3.12, smoke, gitleaks with `.gitleaks.toml`), branch protection on
  `main` with these checks required (2026-11-13)
- [x] `make app-smoke` (start on a throwaway DB, `tools/smoke.sh`, 50-client load test, stop)
- [ ] `iac.yml` with tflint + trivy [P2]
- [ ] `make release` with gates, CHANGELOG rollover, tag + push of branch and tag, `DRY_RUN=1` [P2]
- [ ] `release.yml` (tag guard, CI again on the tag, assets + checksums, notes from CHANGELOG) [P2]
- [ ] Decision deploy from CI (tunnel SSH vs self-hosted runner vs stay manual) [P3]

## Open questions

- Decided 2026-11-13: tests on 3.9 (OL9 container, `setup-python` has no 3.9 for Ubuntu 26.04) and 3.12;
  own `.gitleaks.toml` in the repo; CI blocks merges to `main`
