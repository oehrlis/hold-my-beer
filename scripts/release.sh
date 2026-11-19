#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# OraDBA - Oracle Database Infrastructure and Security, 5630 Muri, Switzerland
# ------------------------------------------------------------------------------
# Name.......: release.sh
# Author.....: Stefan Oehrli (oes) stefan.oehrli@oradba.ch
# Editor.....: Stefan Oehrli
# Date.......: 2026-11-19
# Version....: 0.1.0
# Purpose....: The one way to release hold-my-beer: gates, CHANGELOG rollover,
#              VERSION bump, annotated tag, push of branch AND tag, verify.
# Notes......: Called by 'make release VERSION=x.y.z'. DRY_RUN=TRUE|1|yes runs the
#              read-only gates and shows the writing steps without doing them.
#              The tag push starts .github/workflows/release.yml (assets, notes).
# Reference..: https://github.com/oehrlis/hold-my-beer
# License....: Apache License Version 2.0, January 2004 as shown
#              at http://www.apache.org/licenses/
# ------------------------------------------------------------------------------
# CHANGE LOG:
# 2026-11-19  oes  Initial release                                    0.1.0
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Default Values
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_NAME=$(basename "$0")
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NEW=${VERSION:-""}           # x.y.z, from 'make release VERSION=x.y.z'
DRY_RUN=${DRY_RUN:-"FALSE"}
REMOTE=${REMOTE:-"origin"}   # remote name or URL for fetch, push and verify
BRANCH="main"
TODAY="$(date +%Y-%m-%d)"

# ------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------
usage() {
    cat <<USAGE
Usage: VERSION=x.y.z ${SCRIPT_NAME} [-n|--dry-run] [-h|--help]   (make release VERSION=x.y.z [DRY_RUN=1])

  Gates (read only): x.y.z > VERSION, on ${BRANCH}, clean tree, not behind REMOTE, tag free locally and on
  REMOTE, CHANGELOG Unreleased not empty, ci.yml + secrets.yml green for HEAD, make lint app-test.
  Then: CHANGELOG rollover, VERSION + Makefile header, commit, annotated tag, push ${BRANCH} and the tag,
  verify both on REMOTE. The tag push starts release.yml.

Environment: VERSION (required), DRY_RUN=TRUE|1|yes (unknown values stop), REMOTE (default origin)
USAGE
}

info() { printf 'INFO : %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# step: show a writing step; run it only without DRY_RUN
step() {
    if [[ "${DRY_RUN}" == "TRUE" ]]; then
        printf 'DRY_RUN: %s\n' "$*"
        return 0
    fi
    info "$*"
    "$@"
}

# changelog_section: body of '## [<version>]' in CHANGELOG.md (without the heading)
changelog_section() {
    python3 -I - "$1" "${REPO_DIR}/CHANGELOG.md" <<'PY'
import re, sys
ver, path = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
m = re.search(r"^## \[" + re.escape(ver) + r"\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.S | re.M)
print(m.group(1).strip() if m else "")
PY
}

# changelog_rollover: '## [Unreleased]' -> '## [x.y.z] - date', new empty Unreleased above
changelog_rollover() {
    python3 -I - "${NEW}" "${TODAY}" "${REPO_DIR}/CHANGELOG.md" <<'PY'
import sys
ver, day, path = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8").read()
head = "## [Unreleased]\n"
if text.count(head) != 1:
    sys.exit("CHANGELOG.md: exactly one '## [Unreleased]' heading expected")
text = text.replace(head, f"{head}\n## [{ver}] - {day}\n", 1)
open(path, "w", encoding="utf-8").write(text)
PY
}

# bump_files: VERSION and the Makefile header carry the release
bump_files() {
    printf '%s\n' "${NEW}" >"${REPO_DIR}/VERSION"
    sed -i.bak -e "s|^# Version\.\.\.\.: v.*|# Version....: v${NEW}|" \
        -e "s|^# Date\.\.\.\.\.\.\.: .*|# Date.......: $(date +%d.%m.%Y)|" "${REPO_DIR}/Makefile"
    rm -f "${REPO_DIR}/Makefile.bak"
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h | --help) usage; exit 0 ;;
            -n | --dry-run) DRY_RUN="TRUE" ;;
            *) usage >&2; die "unknown option: $1" ;;
        esac
        shift
    done
    case "$(printf '%s' "${DRY_RUN}" | tr '[:upper:]' '[:lower:]')" in
        true | 1 | yes) DRY_RUN="TRUE" ;;
        false | 0 | no | "") DRY_RUN="FALSE" ;;
        *) die "DRY_RUN='${DRY_RUN}' unknown - use TRUE or FALSE" ;;
    esac
    cd "${REPO_DIR}"
    CUR="$(cat VERSION)"
    TAG="v${NEW}"
    mode=""
    if [[ "${DRY_RUN}" == "TRUE" ]]; then mode=", DRY_RUN"; fi
    info "${SCRIPT_NAME}: ${CUR} -> ${NEW}, remote ${REMOTE}${mode}"

    # --- 1. gates (read only, every one stops with a message) ---------------------
    [[ "${NEW}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || die "VERSION='${NEW}' is not x.y.z[-rc.n]"
    [[ "$(printf '%s\n%s\n' "${CUR}" "${NEW}" | sort -V | tail -1)" == "${NEW}" && "${CUR}" != "${NEW}" ]] \
        || die "VERSION ${NEW} is not greater than the current ${CUR}"
    [[ "$(git rev-parse --abbrev-ref HEAD)" == "${BRANCH}" ]] || die "not on ${BRANCH} ($(git rev-parse --abbrev-ref HEAD))"
    [[ -z "$(git status --porcelain)" ]] || die "working tree not clean - commit or stash first (git status)"
    git fetch -q "${REMOTE}" "${BRANCH}" || die "git fetch ${REMOTE} ${BRANCH} failed"
    behind="$(git rev-list --count HEAD..FETCH_HEAD)"
    [[ "${behind}" == "0" ]] || die "${BRANCH} is ${behind} commit(s) behind ${REMOTE} - pull first"
    git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null && die "tag ${TAG} exists locally"
    [[ -z "$(git ls-remote --tags "${REMOTE}" "refs/tags/${TAG}")" ]] || die "tag ${TAG} exists on ${REMOTE}"
    [[ -n "$(changelog_section Unreleased)" ]] || die "CHANGELOG.md: '## [Unreleased]' is empty - nothing to release"
    command -v gh >/dev/null || die "gh not found - needed to check CI for HEAD"
    head_sha="$(git rev-parse HEAD)"
    for wf in ci.yml secrets.yml; do
        ok="$(gh run list --commit "${head_sha}" --workflow "${wf}" --json conclusion \
            --jq '[.[] | select(.conclusion == "success")] | length')"
        [[ "${ok:-0}" -gt 0 ]] || die "${wf} is not green for HEAD ${head_sha:0:7} (gh run list --commit ${head_sha:0:7})"
    done
    info "gates ok: version, branch, clean tree, up to date, tag free, CHANGELOG, CI green"
    make lint app-test >/dev/null || die "make lint app-test failed - run it to see why"
    info "make lint app-test green"

    # --- 2. CHANGELOG, VERSION, Makefile header, commit, annotated tag ------------
    step changelog_rollover
    step bump_files
    step git add CHANGELOG.md VERSION Makefile
    step git commit -q -m "chore(release): ${TAG}"
    notes="$(mktemp)"; trap 'rm -f "${notes}"' EXIT
    if [[ "${DRY_RUN}" == "TRUE" ]]; then
        changelog_section Unreleased >"${notes}"
    else
        changelog_section "${NEW}" >"${notes}"
    fi
    printf '%s\n\n%s\n' "${TAG}" "$(cat "${notes}")" >"${notes}.msg"
    step git tag -a "${TAG}" -F "${notes}.msg"
    rm -f "${notes}.msg"

    # --- 3. push branch AND tag - a tag that is not pushed does not exist ---------
    step git push -q "${REMOTE}" "${BRANCH}"
    step git push -q "${REMOTE}" "${TAG}"

    # --- 4. verify on the remote, not locally ------------------------------------
    if [[ "${DRY_RUN}" == "TRUE" ]]; then
        info "DRY_RUN: nothing written; the release notes would be:"
        sed 's/^/    /' "${notes}"
        exit 0
    fi
    release_sha="$(git rev-parse HEAD)"
    [[ "$(git ls-remote "${REMOTE}" "refs/heads/${BRANCH}" | cut -f1)" == "${release_sha}" ]] \
        || die "${REMOTE}/${BRANCH} is not ${release_sha:0:7} - push did not land"
    [[ "$(git ls-remote "${REMOTE}" "refs/tags/${TAG}^{}" | cut -f1)" == "${release_sha}" ]] \
        || die "tag ${TAG} on ${REMOTE} does not point to ${release_sha:0:7}"
    info "pushed: ${BRANCH} and ${TAG} at ${release_sha:0:7}"
    info "release workflow: gh run list --workflow release.yml --limit 1   (gh run watch to follow)"
}

main "$@"
# --- EOF ----------------------------------------------------------------------
