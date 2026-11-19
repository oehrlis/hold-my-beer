# CI and release

Every CI job calls the same `make` target as on the Mac, so a green local run and a green CI run mean the same.
Linters run in pinned versions (CI installs them; `tflint` and `trivy` run as images pinned by digest).

## Workflows

<!-- markdownlint-disable MD013 MD060 -->
| Workflow | Trigger | Jobs | Make targets |
| --- | --- | --- | --- |
| `ci.yml` | push to `main`, PR, called by `release.yml` | `lint`, `test-ol9` (Python 3.9 in `oraclelinux:9`, the hosts' system python), `test-py312`, `smoke` | `lint`, `app-venv app-test`, `app-smoke` |
| `secrets.yml` | push to `main`, PR, weekly, manual, called by `release.yml` | `gitleaks` over the full history with `.gitleaks.toml` | - |
| `iac.yml` | push / PR touching `terraform/**`, called by `release.yml` | `terraform fmt -check` + `validate`, `tflint`, `trivy config` | `lint-terraform`, `lint-iac` |
| `release.yml` | push of a tag `v*` | guard, `ci` + `secrets` + `iac` again on the tag commit, `publish` | - |
<!-- markdownlint-restore -->

Branch protection on `main` requires `lint`, `test-ol9`, `test-py312`, `smoke` and `gitleaks`. `enforce_admins`
is off so that the release commit of `make release` can go to `main` directly.

## Release - one way only

Nobody tags by hand. The entry point is local, on the Mac:

```bash
make release VERSION=0.3.0 DRY_RUN=1   # gates for real, writing steps shown only
make release VERSION=0.3.0
```

`scripts/release.sh` stops with a message at the first failed gate - none is skipped:

1. `x.y.z` greater than `VERSION`, on `main`, tree clean, not behind the remote, tag `vX.Y.Z` neither local nor
   on the remote, `## [Unreleased]` in the CHANGELOG not empty, `ci.yml` and `secrets.yml` green for `HEAD`,
   `make lint app-test` green
2. CHANGELOG: `## [Unreleased]` becomes `## [x.y.z] - YYYY-MM-DD` under a new empty `[Unreleased]`; `VERSION`
   and the Makefile header to `x.y.z`; commit `chore(release): vX.Y.Z`; annotated tag with the CHANGELOG
   section as message
3. Push of `main` **and** of the tag - a tag that is not pushed does not exist
4. Verify on the remote: `main` and the tag point to the release commit

`release.yml` then checks that the tag equals `v$(cat VERSION)` and that its commit is on `main` (otherwise no
release for an orphaned or mistyped tag), runs `ci`, `secrets` and `iac` again on the tag commit, and creates
the GitHub release: notes from the CHANGELOG section, assets `dswnwst-voting-<app-version>-<stamp>.tar.gz`
(`app/package.sh`) with its `.sha256`, and the public deck HTML. A version with a suffix (`-rc.1`) becomes a
pre-release.

Versions: `VERSION` is the repo (deck, host tooling, docs); `app/VERSION` is Martin's app and has its own
cadence. The repo release does not bump it, the package name carries it.

Re-run after a failed `release.yml`: delete and push the tag again (`git push origin --delete vX.Y.Z`, then
`git push origin vX.Y.Z`) - never `--force`, a force-pushed tag does not trigger `push: tags`. If the GitHub
release was created already, delete it first (`gh release delete vX.Y.Z`).

Without SSH keys in the agent, push over HTTPS with the `gh` credentials:

```bash
REMOTE=https://github.com/oehrlis/hold-my-beer.git \
  GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0= \
  GIT_CONFIG_KEY_1=credential.helper GIT_CONFIG_VALUE_1='!gh auth git-credential' \
  make release VERSION=x.y.z
```

## Not in CI - decided

- Deploy: stays manual from the Mac (`make host-deploy host-check HOST=...`). The security list allows SSH only
  from the admin CIDR, GitHub runners have changing IPs, and the own host `hmb2` was dropped (2026-11-19)
- `terraform plan/apply`: needs the OCI API key and the Cloudflare token, the state is local - `make tf-*`
- Private deck (`make deck-private`): photos and the licensed font, only outside the repo
