#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# OraDBA - Oracle Database Infrastructure and Security, 5630 Muri, Switzerland
# ------------------------------------------------------------------------------
# Name.......: hmb-host.sh
# Author.....: Stefan Oehrli (oes) stefan.oehrli@oradba.ch
# Editor.....: Stefan Oehrli
# Date.......: 2026-11-13
# Version....: 0.1.0
# Purpose....: App secrets in 1Password, app.env on the host, public checks for
#              a hold-my-beer voting host behind a Cloudflare Tunnel.
# Notes......: Secrets go through stdin (op <-> ssh), never onto a command line
#              or into a local file. Existing items and app.env are never
#              overwritten - the script says so and stops.
# Reference..: docs/runbook-terraform-host.md
# License....: Apache License Version 2.0, January 2004 as shown
#              at http://www.apache.org/licenses/
# ------------------------------------------------------------------------------
# CHANGE LOG:
# 2026-11-13  oes  Initial release                                    0.1.0
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Default Values
# ------------------------------------------------------------------------------
# APP_BASE and APP_PORT are expanded on the client side on purpose (ssh command strings)
# shellcheck disable=SC2029
set -euo pipefail
SCRIPT_NAME=$(basename "$0")
VERSION="0.1.0"
DRY_RUN=${DRY_RUN:-"FALSE"}
OP_VAULT=${OP_VAULT:-"secrets"}
OP_ITEM=${OP_ITEM:-""}     # override the item title, e.g. "hmb app production (hmb.oradba.ch)"
OP_TAGS=${OP_TAGS:-"DOAG,Hold my beer,hmb"}
ZONE=${ZONE:-"oradba.ch"}
APP_BASE=/opt/oracle-live-voting
APP_PORT=${APP_PORT:-8080}
POOL_FILE=${POOL_FILE:-"pool/doag-ak-2026.yaml"}
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=10)
CMD=""
HOST=""

# ------------------------------------------------------------------------------
# usage: show script usage
# ------------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS] <secrets|env|check> <host>

  App secrets in 1Password, app.env on the host, public checks.
  <host> is the SSH alias and the label below ${ZONE} (hmb2 -> https://hmb2.${ZONE}).

Commands:
  secrets   create the 1Password item "<host> app (<host>.${ZONE})" (SECRET_KEY, admin password)
  env       write ${APP_BASE}/shared/app.env on the host from that item (first deploy only)
  check     public checks against https://<host>.${ZONE} (runbook step 7) and service state

Options:
  -h, --help      Show this help and exit
  -d, --dry-run   Show what would be done, change nothing

Examples:
  ${SCRIPT_NAME} secrets hmb2
  ${SCRIPT_NAME} --dry-run env hmb2
  ${SCRIPT_NAME} check hmb

EOF
}

log_info()  { echo "$(date '+%Y-%m-%d %H:%M:%S') INFO  $*"; }
log_warn()  { echo "$(date '+%Y-%m-%d %H:%M:%S') WARN  $*" >&2; }
log_error() { echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR $*" >&2; }

# ------------------------------------------------------------------------------
# Function: item_title
# Purpose.: 1Password item title for a host
# Args....: $1  host  SSH alias / host label
# Output..: title on stdout
# Example.: item_title hmb2   # -> hmb2 app (hmb2.oradba.ch)
# ------------------------------------------------------------------------------
item_title() { echo "${OP_ITEM:-$1 app ($1.${ZONE})}"; }

# ------------------------------------------------------------------------------
# Function: item_id
# Purpose.: ID of the host's 1Password item, empty if it does not exist
# Args....: $1  host  SSH alias / host label
# Output..: item ID on stdout (or nothing)
# Depends.: op, jq
# Example.: id=$(item_id hmb2)
# ------------------------------------------------------------------------------
item_id() {
    op item list --vault "${OP_VAULT}" --format json \
        | jq -r --arg t "$(item_title "$1")" '.[] | select(.title == $t) | .id' | head -1
}

# ------------------------------------------------------------------------------
# Function: cmd_secrets
# Purpose.: Create the app item (generated SECRET_KEY + admin password) once
# Args....: $1  host  SSH alias / host label
# Returns.: 0 created or already there (reported), 1 error
# Depends.: op, jq, python3
# Example.: cmd_secrets hmb2
# ------------------------------------------------------------------------------
cmd_secrets() {
    local host="$1" title id
    title="$(item_title "$host")"
    id="$(item_id "$host")"
    if [[ -n "$id" ]]; then
        log_info "1Password item exists, not touched: \"$title\" (vault ${OP_VAULT}, id $id)"
        return 0
    fi
    if [[ "${DRY_RUN}" == "TRUE" ]]; then
        log_info "DRY-RUN: would create \"$title\" in vault ${OP_VAULT} (tags ${OP_TAGS},$host.${ZONE})"
        return 0
    fi
    # generated values stay in the pipe: python -> jq -> op (stdin)
    python3 -c 'import secrets; print(secrets.token_urlsafe(48)); print(secrets.token_urlsafe(18))' \
        | jq -R -s --arg title "$title" --arg url "https://$host.${ZONE}" --arg tags "${OP_TAGS},$host.${ZONE}" '
            split("\n") as $v
            | {title: $title, category: "LOGIN", tags: ($tags | split(",")),
               fields: [
                 {id: "username", type: "STRING", purpose: "USERNAME", label: "username", value: "admin"},
                 {id: "password", type: "CONCEALED", purpose: "PASSWORD", label: "password", value: $v[1]},
                 {id: "secret_key", type: "CONCEALED", label: "SECRET_KEY", value: $v[0]},
                 {id: "public_base_url", type: "STRING", label: "PUBLIC_BASE_URL", value: $url},
                 {id: "notesPlain", type: "STRING", purpose: "NOTES", label: "notesPlain",
                  value: "hold-my-beer voting app: password = ADMIN_PASSWORD (/admin), SECRET_KEY = Flask. Written to app.env by scripts/hmb-host.sh env."}
               ]}' \
        | op item create --vault "${OP_VAULT}" - >/dev/null
    log_info "1Password item created: \"$title\" (vault ${OP_VAULT})"
}

# ------------------------------------------------------------------------------
# Function: cmd_env
# Purpose.: Write app.env on the host from the 1Password item (never overwrite)
# Args....: $1  host  SSH alias / host label
# Returns.: 0 written or already there (reported), 1 error
# Depends.: op, ssh
# Example.: cmd_env hmb2
# ------------------------------------------------------------------------------
cmd_env() {
    local host="$1" id
    id="$(item_id "$host")"
    [[ -n "$id" ]] || { log_error "no 1Password item \"$(item_title "$host")\" - new host: ${SCRIPT_NAME} secrets $host; other title: OP_ITEM=\"<title>\""; return 1; }
    if ssh "${SSH_OPTS[@]}" "$host" "test -e ${APP_BASE}/shared/app.env"; then
        log_warn "app.env exists on $host, not touched - edit it there or remove it first"
        return 0
    fi
    if [[ "${DRY_RUN}" == "TRUE" ]]; then
        log_info "DRY-RUN: would write ${APP_BASE}/shared/app.env on $host (URL https://$host.${ZONE}, port ${APP_PORT})"
        return 0
    fi
    if ! {
        echo "APP_ENV=production"
        echo "SECRET_KEY=$(op read "op://${OP_VAULT}/$id/SECRET_KEY")"
        echo "ADMIN_PASSWORD=$(op read "op://${OP_VAULT}/$id/password")"
        echo "DATABASE_URL=sqlite:///${APP_BASE}/shared/oracle-live-voting.db"
        echo "BACKUP_DIR=${APP_BASE}/shared/backups"
        echo "HOST=127.0.0.1"
        echo "PORT=${APP_PORT}"
        echo "PROXY_FIX_ENABLED=true"
        echo "PROXY_FIX_X_FOR=1"
        echo "SESSION_COOKIE_SECURE=true"
        echo "PUBLIC_BASE_URL=https://$host.${ZONE}"
        echo "POOL_FILE=${POOL_FILE}"
    } | ssh "${SSH_OPTS[@]}" "$host" "umask 077; set -o noclobber; mkdir -p ${APP_BASE}/shared && cat > ${APP_BASE}/shared/app.env"; then
        log_error "writing app.env on $host failed"
        return 1
    fi
    log_info "app.env written on $host (600, secrets from 1Password item $id)"
}

# ------------------------------------------------------------------------------
# Function: cmd_check
# Purpose.: Public checks (runbook step 7) plus service state on the host
# Args....: $1  host  SSH alias / host label
# Returns.: 0 all checks ok, 1 at least one failed
# Depends.: curl, ssh
# Example.: cmd_check hmb2
# ------------------------------------------------------------------------------
cmd_check() {
    local host="$1" url="https://$1.${ZONE}" fail=0 code body hdr state listen
    check() { if [[ "$2" == "$3" ]]; then log_info "OK   $1 = $2"; else log_error "FAIL $1 = $2 (expected $3)"; fail=1; fi; }

    code="$(curl -s -o /dev/null -w '%{http_code}' "$url/readyz")"; check "$url/readyz" "$code" 200
    body="$(curl -s "$url/" | grep -o -E "https?://${host}[^\"< ]*" | sort -u | head -1)"
    check "participant page URL" "$body" "$url/"
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url/qr.svg")"; check "$url/qr.svg" "$code" 200
    hdr="$(curl -sI "$url/api/state" | tr -d '\r' | grep -i -E '^cache-control:' | awk '{print $2}')"
    check "api/state cache-control" "$hdr" "no-store"
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url/does-not-exist")"; check "$url/does-not-exist" "$code" 404
    state="$(ssh "${SSH_OPTS[@]}" "$host" 'systemctl is-active cloudflared oracle-live-voting | paste -sd,')" || true
    check "services cloudflared,oracle-live-voting" "$state" "active,active"
    listen="$(ssh "${SSH_OPTS[@]}" "$host" "ss -ltn | awk '\$4 ~ /:${APP_PORT}\$/ {print \$4}' | head -1")" || true
    check "app listen" "$listen" "127.0.0.1:${APP_PORT}"
    return $fail
}

# ------------------------------------------------------------------------------
# Parse arguments
# ------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)    usage; exit 0 ;;
        -d|--dry-run) DRY_RUN="TRUE"; shift ;;
        secrets|env|check)
            CMD="$1"; HOST="${2:-}"; shift; [[ $# -gt 0 ]] && shift ;;
        *) log_error "Unknown option or command: $1"; usage; exit 1 ;;
    esac
done

# ------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------
main() {
    [[ -n "$CMD" && -n "$HOST" ]] || { usage; exit 1; }
    [[ "$HOST" =~ ^[a-z0-9-]+$ ]] || { log_error "host must be a plain label (e.g. hmb2), was: $HOST"; exit 1; }
    log_info "${SCRIPT_NAME} ${VERSION}: $CMD $HOST"
    "cmd_$CMD" "$HOST"
}

main "$@"
# --- EOF ----------------------------------------------------------------------
