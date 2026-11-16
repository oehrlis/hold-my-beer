#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# OraDBA - Oracle Database Infrastructure and Security, 5630 Muri, Switzerland
# ------------------------------------------------------------------------------
# Name.......: talk-start.sh
# Author.....: Stefan Oehrli (oes) stefan.oehrli@oradba.ch
# Editor.....: Stefan Oehrli
# Date.......: 2026-11-16
# Version....: 0.1.1
# Purpose....: One entry point for the hold-my-beer session: check app and lab,
#              switch the seclab lab from the privesc state, set the demo
#              starting points, open deck, browser and terminals.
# Notes......: check and open change nothing. lab changes the lab (asks first,
#              --yes skips the question), demos runs setup.sql in the lab.
#              DEMO_PWD reaches stage.sh through the environment, never argv.
# Reference..: docs/runbook-labs-talk-day.md
# License....: Apache License Version 2.0, January 2004 as shown
#              at http://www.apache.org/licenses/
# ------------------------------------------------------------------------------
# CHANGE LOG:
# 2026-11-16  oes  Initial release                                    0.1.0
# 2026-11-16  oes  lab: name the step that failed and how to go on    0.1.1
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Default Values
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
VERSION="0.1.1"
DRY_RUN=${DRY_RUN:-"FALSE"}
ASSUME_YES=${ASSUME_YES:-"FALSE"}
REPOS_DIR=${REPOS_DIR:-"$HOME/Repos/own/oehrlis"}
LABS_DIR=${LABS_DIR:-"$REPOS_DIR/oradba-labs"}
PRIVESC_DIR=${PRIVESC_DIR:-"$REPOS_DIR/talks-privesc/talks/oracle-privesc/demos"}
LAB=${LAB:-"seclab"}
APP_HOST=${APP_HOST:-"hmb"}
APP_URL=${APP_URL:-"https://hmb.oradba.ch"}
DECK=${DECK:-""}
DEMO_PWD_OP=${DEMO_PWD_OP:-"op://secrets/privesc demo/password"}
BROWSER_APP=${BROWSER_APP:-"Google Chrome"}
LOG_DIR=${LOG_DIR:-"${TMPDIR:-/tmp}/talk-start"}
# demo | container | marker query (count > 0 = starting point already set) | terminal title
DEMOS=(
    "verifier|${LAB}-db19|select count(*) from cdb_users u join v\$pdbs p on p.con_id = u.con_id where p.name = 'DEMOPDB' and u.username = 'HMB_LEGACY'|R1 verifier (db19)"
    "unified-audit|${LAB}-db19|select count(*) from cdb_users u join v\$pdbs p on p.con_id = u.con_id where p.name = 'DEMOPDB' and u.username = 'HMB_DBA'|R2 unified audit (db19)"
    "tde|${LAB}-db26|select count(*) from cdb_tablespaces t join v\$pdbs p on p.con_id = t.con_id where p.name = 'DEMOPDB' and t.tablespace_name = 'HMB_PLAIN_TS'|R3 TDE (db26)"
)
CMD=""
FAILS=0

# ------------------------------------------------------------------------------
# usage: show script usage
# ------------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS] <check|lab|demos|open|start>

  One entry point for the hold-my-beer session (Stefan's rounds on the lab ${LAB}).

Commands:
  check   app (host-check ${APP_HOST}), lab (make verify), privesc state, demo starting points, deck - read only
  lab     switch ${LAB} from the privesc state: stage.sh unweak, make reset, make verify (asks first)
  demos   setup.sql of verifier, unified-audit, tde - skips a demo whose starting point is already set
  open    deck, ${APP_URL}/screen and /admin in ${BROWSER_APP}, one Terminal window per round with sqlplus
  start   check, demos, open - the entry point before the session

Options:
  -h, --help      Show this help and exit
  -d, --dry-run   Show what would be done, change nothing (check still runs, it is read only)
  -y, --yes       Do not ask before the lab switch

Environment:
  DECK            private deck (html), set by 'make talk-start' to PRIVATE_OUT
  DEMO_PWD        privesc demo password for stage.sh; unset: op read "${DEMO_PWD_OP}" (DEMO_PWD_OP)
  LABS_DIR        ${LABS_DIR}
  PRIVESC_DIR     ${PRIVESC_DIR}

Examples:
  ${SCRIPT_NAME} check
  ${SCRIPT_NAME} --dry-run lab
  ${SCRIPT_NAME} start

EOF
}

log_info()  { echo "$(date '+%H:%M:%S') INFO  $*"; }
log_ok()    { echo "$(date '+%H:%M:%S') OK    $*"; }
log_warn()  { echo "$(date '+%H:%M:%S') WARN  $*" >&2; }
log_error() { echo "$(date '+%H:%M:%S') ERROR $*" >&2; }
fail()      { log_error "$*"; FAILS=$((FAILS + 1)); }
die()       { log_error "$*"; exit 1; }

# ------------------------------------------------------------------------------
# Function: run
# Purpose.: Run a command, or print it in dry-run mode
# Args....: $@  command and arguments
# Returns.: exit code of the command (0 in dry-run mode)
# ------------------------------------------------------------------------------
run() {
    if [[ "$DRY_RUN" == "TRUE" ]]; then
        log_info "DRY-RUN: would run: $*"
        return 0
    fi
    "$@"
}

# ------------------------------------------------------------------------------
# Function: sql_value
# Purpose.: First value of a query as SYSDBA in a lab container (read only)
# Args....: $1  container, $2  query (single row, single column)
# Returns.: 0 and the value on stdout, 1 if sqlplus or the container fails
# ------------------------------------------------------------------------------
sql_value() {
    local container="$1" query="$2" out
    out="$(docker exec -i "$container" bash -c 'export ORAENV_ASK=NO; "${ORACLE_HOME}/bin/sqlplus" -s -L / as sysdba' <<SQL 2>&1
set heading off feedback off pagesize 0 verify off echo off trimout on
whenever sqlerror exit failure
${query};
exit
SQL
)" || return 1
    out="${out//[$'\t\r\n ']/}"
    echo "$out"
}

# ------------------------------------------------------------------------------
# Function: lab_state
# Purpose.: Report privesc leftovers that break the hmb demos (read only)
# Args....: none
# Returns.: 0 clean, 1 privesc state (or TDE demo not reset) found
# ------------------------------------------------------------------------------
lab_state() {
    local db wr victim alv rc=0 legacy
    for db in db19 db26; do
        wr="$(sql_value "${LAB}-${db}" "select value from v\$parameter where name = 'wallet_root'")" \
            || { fail "${LAB}-${db}: no SYSDBA connection"; rc=1; continue; }
        victim="$(sql_value "${LAB}-${db}" "select count(*) from v\$pdbs where name = 'VICTIMPDB'")" || victim="?"
        alv="$(docker exec "${LAB}-${db}" bash -c 'grep -i -E "^[[:space:]]*SQLNET.ALLOWED_LOGON_VERSION_SERVER" "${ORACLE_HOME}/network/admin/sqlnet.ora" 2>/dev/null' || true)"
        legacy="$(sql_value "${LAB}-${db}" "select count(*) from cdb_users where username = 'HMB_LEGACY'")" || legacy=0
        if [[ -n "$wr" ]]; then
            fail "${LAB}-${db}: WALLET_ROOT=${wr} - privesc state (m3) or TDE demo not reset - run: make talk-lab"
            rc=1
        fi
        if [[ "$victim" != "0" ]]; then
            fail "${LAB}-${db}: VICTIMPDB exists - privesc state (m6) - run: make talk-lab"
            rc=1
        fi
        if [[ -n "$alv" && "$legacy" == "0" ]]; then
            fail "${LAB}-${db}: sqlnet.ora has '${alv// /}' without the verifier demo - privesc state (m1) - run: make talk-lab"
            rc=1
        fi
        if [[ -z "$wr" && "$victim" == "0" && ( -z "$alv" || "$legacy" != "0" ) ]]; then
            log_ok "${LAB}-${db}: no privesc leftovers (WALLET_ROOT empty, no VICTIMPDB, sqlnet.ora as expected)"
        fi
    done
    return "$rc"
}

# ------------------------------------------------------------------------------
# Function: cmd_check
# Purpose.: Read-only checks of app, lab, privesc state, demos and deck
# Returns.: 0 all green, 1 at least one FAIL
# ------------------------------------------------------------------------------
cmd_check() {
    local entry name container marker title n newer
    log_info "== app: ${APP_URL} (host-check ${APP_HOST}; the SSH part needs the VPN)"
    if "${SCRIPT_DIR}/hmb-host.sh" check "${APP_HOST}" >"${LOG_DIR}/host-check.log" 2>&1; then
        log_ok "host-check ${APP_HOST}: all checks green"
    else
        grep -E 'FAIL' "${LOG_DIR}/host-check.log" >&2 || true
        fail "host-check ${APP_HOST} failed (log: ${LOG_DIR}/host-check.log) - SSH timeouts: VPN up?"
    fi

    log_info "== lab: make verify LAB=${LAB}"
    if make -s -C "${LABS_DIR}" verify LAB="${LAB}" >"${LOG_DIR}/lab-verify.log" 2>&1; then
        log_ok "make verify LAB=${LAB}: all checks green"
    else
        grep -E 'FAIL' "${LOG_DIR}/lab-verify.log" >&2 || true
        fail "make verify LAB=${LAB} failed (log: ${LOG_DIR}/lab-verify.log)"
    fi

    log_info "== privesc state on ${LAB}"
    lab_state || true

    log_info "== demo starting points"
    for entry in "${DEMOS[@]}"; do
        IFS='|' read -r name container marker title <<<"$entry"
        n="$(sql_value "$container" "$marker")" || { fail "${name}: no connection to ${container}"; continue; }
        if [[ "$n" != "0" ]]; then log_ok "${name}: starting point set (${container})"
        else log_warn "${name}: starting point not set - run: make talk-demos (or make talk-start)"; fi
    done

    log_info "== deck"
    if [[ -z "$DECK" ]]; then log_warn "DECK not set - run through 'make talk-check' to check the private deck"
    elif [[ -f "$DECK" ]]; then
        log_ok "deck: ${DECK} ($(date -r "$DECK" '+%Y-%m-%d %H:%M'))"
        # -print -quit instead of '| head': no SIGPIPE under pipefail
        newer="$(find "${SCRIPT_DIR}/../slides/src" "${SCRIPT_DIR}/../slides/deck.css" "${SCRIPT_DIR}/../pool" \
            -type f -newer "$DECK" -print -quit 2>/dev/null || true)"
        if [[ -n "$newer" ]]; then log_warn "deck is older than its sources (e.g. ${newer}) - run: make deck-private"; fi
    else fail "deck not found: ${DECK} - run: make deck-private"; fi

    if [[ "$FAILS" -gt 0 ]]; then
        log_error "check: ${FAILS} FAIL(s) - see above"
        return 1
    fi
    log_ok "check: everything green"
}

# ------------------------------------------------------------------------------
# Function: cmd_lab
# Purpose.: Switch the lab from the privesc state: unweak, flashback, verify
# Returns.: 0 lab clean and verified, 1 otherwise
# ------------------------------------------------------------------------------
cmd_lab() {
    local answer pwd
    [[ -x "${PRIVESC_DIR}/stage.sh" ]] || die "stage.sh not found: ${PRIVESC_DIR}/stage.sh (PRIVESC_DIR)"
    log_info "lab switch on ${LAB}: ${PRIVESC_DIR}/stage.sh unweak, make reset LAB=${LAB}, make verify LAB=${LAB}"
    log_info "this removes the privesc weak state - the privesc talk needs 'stage.sh weak' again afterwards"
    if [[ "$DRY_RUN" != "TRUE" && "$ASSUME_YES" != "TRUE" ]]; then
        read -r -p "Switch ${LAB} now? [y/N] " answer
        [[ "$answer" =~ ^[yYjJ]$ ]] || die "stopped, nothing changed"
    fi
    if [[ "$DRY_RUN" == "TRUE" ]]; then
        log_info "DRY-RUN: would read DEMO_PWD (environment, else op read \"${DEMO_PWD_OP}\")"
        run "${PRIVESC_DIR}/stage.sh" unweak
    else
        pwd="${DEMO_PWD:-}"
        if [[ -z "$pwd" ]]; then
            pwd="$(op read "${DEMO_PWD_OP}")" \
                || die "no DEMO_PWD: export DEMO_PWD=... or create the 1Password item (${DEMO_PWD_OP}), see the runbook"
        fi
        (cd "${PRIVESC_DIR}" && DEMO_PWD="$pwd" ./stage.sh unweak) \
            || die "stage.sh unweak failed - lab half switched (modules up to the error undone). Fix the cause above,
       then make talk-lab again (unweak is idempotent). ORA-04031 java pool: runbook section 'Switch'"
    fi
    run make -C "${LABS_DIR}" reset LAB="${LAB}" \
        || die "make reset LAB=${LAB} failed - privesc state is undone, flashback not done: check make status LAB=${LAB}"
    run make -C "${LABS_DIR}" verify LAB="${LAB}" || die "make verify LAB=${LAB} failed after the switch - see FAIL lines above"
    [[ "$DRY_RUN" == "TRUE" ]] && return 0
    lab_state || die "lab still shows privesc leftovers - see above, runbook section 'Switch'"
    log_ok "lab ${LAB}: switched, verified, no privesc leftovers"
}

# ------------------------------------------------------------------------------
# Function: cmd_demos
# Purpose.: Set the starting point of each demo (setup.sql), skip set ones
# Returns.: 0 all set, 1 a setup.sql failed
# ------------------------------------------------------------------------------
cmd_demos() {
    local entry name container marker title n log
    lab_state || die "lab is not clean - run: make talk-lab"
    for entry in "${DEMOS[@]}"; do
        IFS='|' read -r name container marker title <<<"$entry"
        n="$(sql_value "$container" "$marker")" || die "${name}: no connection to ${container}"
        if [[ "$n" != "0" ]]; then
            log_info "SKIP ${name}: starting point already set on ${container} (new start: @reset.sql in its tab)"
            continue
        fi
        log="${LOG_DIR}/${name}-setup.log"
        if [[ "$DRY_RUN" == "TRUE" ]]; then
            log_info "DRY-RUN: would run @setup.sql in /opt/oracle/demos/${name} on ${container}"
            continue
        fi
        if docker exec -i -w "/opt/oracle/demos/${name}" "$container" \
            bash -c 'export ORAENV_ASK=NO; "${ORACLE_HOME}/bin/sqlplus" -s -L / as sysdba @setup.sql' \
            </dev/null >"$log" 2>&1; then
            log_ok "${name}: setup.sql done on ${container} (log: ${log})"
        else
            tail -n 15 "$log" >&2
            fail "${name}: setup.sql failed on ${container} (log: ${log})"
        fi
    done
    [[ "$FAILS" -eq 0 ]] || return 1
}

# ------------------------------------------------------------------------------
# Function: open_terminal
# Purpose.: New Terminal window with a command and a title
# Args....: $1  title, $2  shell command
# Returns.: exit code of osascript
# ------------------------------------------------------------------------------
open_terminal() {
    local title="$1" cmd="$2"
    local script
    cmd="${cmd//\\/\\\\}"; cmd="${cmd//\"/\\\"}"
    script="tell application \"Terminal\"
activate
set t to do script \"${cmd}\"
set custom title of t to \"${title}\"
end tell"
    if [[ "$DRY_RUN" == "TRUE" ]]; then
        log_info "DRY-RUN: would open a Terminal window '${title}': ${cmd}"
        return 0
    fi
    osascript -e "$script" >/dev/null
}

# ------------------------------------------------------------------------------
# Function: cmd_open
# Purpose.: Deck, voting app and one sqlplus window per round
# Returns.: 0
# ------------------------------------------------------------------------------
cmd_open() {
    local entry name container marker title
    if [[ -n "$DECK" && -f "$DECK" ]]; then
        run open -a "${BROWSER_APP}" "$DECK"
        log_ok "deck opened - present it in its own window, Speaker View with S"
    else
        log_warn "deck not opened: '${DECK}' not found - run: make deck-private"
    fi
    run open -na "${BROWSER_APP}" --args --new-window "${APP_URL}/screen"
    run open -a "${BROWSER_APP}" "${APP_URL}/admin"
    log_ok "voting app: /screen in a new window (drag it to the projector, click 'Ton aus' once), /admin as a tab"
    for entry in "${DEMOS[@]}"; do
        IFS='|' read -r name container marker title <<<"$entry"
        open_terminal "$title" "docker exec -it -w /opt/oracle/demos/${name} ${container} bash -c 'export ORAENV_ASK=NO; \"\${ORACLE_HOME}/bin/sqlplus\" / as sysdba'"
    done
    log_ok "Terminal: one window per round (sqlplus / as sysdba in the demo directory) - @check.sql is the before picture"
}

# ------------------------------------------------------------------------------
# Parse arguments
# ------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)    usage; exit 0 ;;
        -d|--dry-run) DRY_RUN="TRUE"; shift ;;
        -y|--yes)     ASSUME_YES="TRUE"; shift ;;
        check|lab|demos|open|start) CMD="$1"; shift ;;
        *) log_error "Unknown option or command: $1"; usage; exit 1 ;;
    esac
done

# ------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------
main() {
    [[ -n "$CMD" ]] || { usage; exit 1; }
    mkdir -p "${LOG_DIR}"
    log_info "${SCRIPT_NAME} ${VERSION}: ${CMD}$([[ "$DRY_RUN" == "TRUE" ]] && echo " (dry-run)")"
    case "$CMD" in
        check) cmd_check ;;
        lab)   cmd_lab ;;
        demos) cmd_demos ;;
        open)  cmd_open ;;
        start)
            cmd_check || log_warn "check had FAILs - fix them before the session (see above); going on with demos and open"
            FAILS=0
            cmd_demos
            cmd_open ;;
    esac
}

main "$@"
# --- EOF ----------------------------------------------------------------------
