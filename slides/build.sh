#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# OraDBA - Oracle Database Infrastructure and Security, 5630 Muri, Switzerland
# ------------------------------------------------------------------------------
# Name.......: build.sh
# Author.....: Stefan Oehrli (oes) stefan.oehrli@oradba.ch
# Editor.....: Stefan Oehrli
# Date.......: 2026-11-12
# Version....: 0.3.0
# Purpose....: Build the hold-my-beer frame deck: generate the pool-driven atoms,
#              then assemble the standalone HTML with the talk CLI.
# Notes......: Needs uv and the talk CLI (ai-toolkit). VOTING_URL sets the QR target.
#              HMB_PRIVATE_DIR adds private photos - such a deck must never land in the repo.
# Reference..: https://github.com/oehrlis/hold-my-beer
# License....: Apache License Version 2.0, January 2004 as shown
#              at http://www.apache.org/licenses/
# ------------------------------------------------------------------------------
# CHANGE LOG:
# 2026-11-12  oes  Initial release                                    0.1.0
# 2026-11-12  oes  Default VOTING_URL https://hmb.oradba.ch            0.2.0
# 2026-11-12  oes  HMB_PRIVATE_DIR (private photos), OUT / -o, repo guard 0.3.0
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Default Values
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="0.3.0"
EVENT=${EVENT:-"doag-ak-2026"}
TALK_SLUG=${TALK_SLUG:-"wissen-nicht-was-sie-tun"}
TALKS_DIR=${TALKS_DIR:-"$(cd "${REPO_DIR}/.." && pwd)/talks"}
VOTING_URL=${VOTING_URL-"https://hmb.oradba.ch"}  # set but empty: placeholder + WARN
DRY_RUN=${DRY_RUN:-"FALSE"}
HMB_PRIVATE_DIR=${HMB_PRIVATE_DIR:-""}  # private photos replacing img/<stem>.svg (never into the repo)
OUT=${OUT:-""}  # output file; default slides/<EVENT>/<TALK_SLUG>.<format>
FORMAT="html"

# ------------------------------------------------------------------------------
# usage: show script usage
# ------------------------------------------------------------------------------
usage() {
    cat <<USAGE
Usage: ${SCRIPT_NAME} [OPTIONS]

  Build the frame deck into slides/${EVENT}/ (standalone HTML, optional PDF).

Options:
  -h, --help      Show this help and exit
  -d, --dry-run   Generate atoms, list the slide plan, write no deck
      --pdf       Build a PDF instead of HTML
  -o, --out FILE  Output file (default slides/${EVENT}/${TALK_SLUG}.html, or .pdf)

Environment:
  VOTING_URL      public base URL of the voting app (default ${VOTING_URL})
  TALKS_DIR       talks repo checkout with talks/${TALK_SLUG}/talk.yaml (default ${TALKS_DIR})
  EVENT           output folder below slides/ (default ${EVENT})
  OUT             output file, same as -o
  HMB_PRIVATE_DIR folder with private photos (<stem>.jpg|.png replaces img/<stem>.svg);
                  the deck then contains them, so the output must be outside the repo

Example:
  TALKS_DIR=~/Repos/own/oehrlis/talks ${SCRIPT_NAME}
  HMB_PRIVATE_DIR=<private media dir> ${SCRIPT_NAME} -o <dir outside the repo>/${TALK_SLUG}.html
USAGE
}

# ------------------------------------------------------------------------------
# die: print an error and exit
# ------------------------------------------------------------------------------
die() { echo "ERROR: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        -d|--dry-run) DRY_RUN="TRUE" ;;
        --pdf) FORMAT="pdf" ;;
        -o|--out) [[ $# -ge 2 ]] || die "$1 needs a file"; OUT="$2"; shift ;;
        *) usage >&2; die "unknown option: $1" ;;
    esac
    shift
done

command -v uv >/dev/null || die "uv not found"
command -v talk >/dev/null || die "talk CLI not found (ai-toolkit: make install-cli)"
TALK_YAML="${TALKS_DIR}/talks/${TALK_SLUG}/talk.yaml"
[[ -f "${TALK_YAML}" ]] || die "talk.yaml not found: ${TALK_YAML} (set TALKS_DIR)"

# talk.yaml reaches the sources via master/../../hold-my-beer - must be this checkout
LINKED="$(cd "${TALKS_DIR}/master-slides/../../hold-my-beer" 2>/dev/null && pwd -P || true)"
[[ "${LINKED}" == "$(cd "${REPO_DIR}" && pwd -P)" ]] \
    || die "talk.yaml resolves hold-my-beer to '${LINKED:-nothing}', not ${REPO_DIR} - check the sibling layout"

OUT=${OUT:-"${SCRIPT_DIR}/${EVENT}/${TALK_SLUG}.${FORMAT}"}
if [[ -n "${HMB_PRIVATE_DIR}" ]]; then
    [[ -d "${HMB_PRIVATE_DIR}" ]] || die "HMB_PRIVATE_DIR is not a directory: ${HMB_PRIVATE_DIR}"
    # resolve without creating anything: the guard runs before any file or folder is written
    OUT_ABS="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${OUT}")"
    REPO_ABS="$(cd "${REPO_DIR}" && pwd -P)"
    if [[ "${OUT_ABS}" == "${REPO_ABS}/"* ]]; then
        die "HMB_PRIVATE_DIR is set and the output is inside the repo: ${OUT_ABS}
       The deck would contain the private photos and the repo is public. Write it outside the repo, e.g.
       HMB_PRIVATE_DIR=\"${HMB_PRIVATE_DIR}\" ${SCRIPT_NAME} -o ~/Library/CloudStorage/OneDrive-Accenture/50_Community/Conferences/DOAG/2026-11-konferenz/Own/${TALK_SLUG}.${FORMAT}"
    fi
    mkdir -p "$(dirname "${OUT}")"
fi

# regenerate the public atoms on exit: slides/build/atoms must never keep a private photo
restore_public_atoms() {
    echo "INFO: regenerating the public atoms in slides/build/atoms (no private images)"
    VOTING_URL="${VOTING_URL}" HMB_PRIVATE_DIR="" uv run --quiet --with pyyaml --with qrcode python "${SCRIPT_DIR}/generate.py" \
        --pool "${REPO_DIR}/pool/${EVENT}.yaml" --out "${SCRIPT_DIR}/build/atoms" >/dev/null
}

echo "INFO: ${SCRIPT_NAME} ${VERSION} - talks ${TALKS_DIR}, voting url ${VOTING_URL}"
[[ -n "${HMB_PRIVATE_DIR}" ]] && { echo "INFO: private images from ${HMB_PRIVATE_DIR}, output ${OUT}"; trap restore_public_atoms EXIT; }
VOTING_URL="${VOTING_URL}" HMB_PRIVATE_DIR="${HMB_PRIVATE_DIR}" uv run --quiet --with pyyaml --with qrcode python \
    "${SCRIPT_DIR}/generate.py" --pool "${REPO_DIR}/pool/${EVENT}.yaml" --out "${SCRIPT_DIR}/build/atoms"

ARGS=(assemble --talk "${TALK_SLUG}" --format "${FORMAT}" -o "${OUT}")
[[ "${FORMAT}" == "html" ]] && ARGS+=(--standalone)
[[ "${DRY_RUN}" == "TRUE" ]] && ARGS+=(--dry-run)
TALKS_DIR="${TALKS_DIR}" talk "${ARGS[@]}"
