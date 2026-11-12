#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# OraDBA - Oracle Database Infrastructure and Security, 5630 Muri, Switzerland
# ------------------------------------------------------------------------------
# Name.......: build.sh
# Author.....: Stefan Oehrli (oes) stefan.oehrli@oradba.ch
# Editor.....: Stefan Oehrli
# Date.......: 2026-11-12
# Version....: 0.2.0
# Purpose....: Build the hold-my-beer frame deck: generate the pool-driven atoms,
#              then assemble the standalone HTML with the talk CLI.
# Notes......: Needs uv and the talk CLI (ai-toolkit). VOTING_URL sets the QR target.
# Reference..: https://github.com/oehrlis/hold-my-beer
# License....: Apache License Version 2.0, January 2004 as shown
#              at http://www.apache.org/licenses/
# ------------------------------------------------------------------------------
# CHANGE LOG:
# 2026-11-12  oes  Initial release                                    0.1.0
# 2026-11-12  oes  Default VOTING_URL https://hmb.oradba.ch            0.2.0
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Default Values
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="0.2.0"
EVENT=${EVENT:-"doag-ak-2026"}
TALK_SLUG=${TALK_SLUG:-"wissen-nicht-was-sie-tun"}
TALKS_DIR=${TALKS_DIR:-"$(cd "${REPO_DIR}/.." && pwd)/talks"}
VOTING_URL=${VOTING_URL-"https://hmb.oradba.ch"}  # set but empty: placeholder + WARN
DRY_RUN=${DRY_RUN:-"FALSE"}
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

Environment:
  VOTING_URL      public base URL of the voting app (default ${VOTING_URL})
  TALKS_DIR       talks repo checkout with talks/${TALK_SLUG}/talk.yaml (default ${TALKS_DIR})
  EVENT           output folder below slides/ (default ${EVENT})

Example:
  TALKS_DIR=~/Repos/own/oehrlis/talks ${SCRIPT_NAME}
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

echo "INFO: ${SCRIPT_NAME} ${VERSION} - talks ${TALKS_DIR}, voting url ${VOTING_URL}"
VOTING_URL="${VOTING_URL}" uv run --quiet --with pyyaml --with qrcode python "${SCRIPT_DIR}/generate.py" \
    --pool "${REPO_DIR}/pool/${EVENT}.yaml" --out "${SCRIPT_DIR}/build/atoms"

OUT="${SCRIPT_DIR}/${EVENT}/${TALK_SLUG}.${FORMAT}"
ARGS=(assemble --talk "${TALK_SLUG}" --format "${FORMAT}" -o "${OUT}")
[[ "${FORMAT}" == "html" ]] && ARGS+=(--standalone)
[[ "${DRY_RUN}" == "TRUE" ]] && ARGS+=(--dry-run)
TALKS_DIR="${TALKS_DIR}" talk "${ARGS[@]}"
