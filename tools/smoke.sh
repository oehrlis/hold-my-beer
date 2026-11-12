#!/usr/bin/env bash
# Smoke-Test gegen die laufende lokale App: Seiten, QR, kompletter Voting-Ablauf.
# Nutzung: PORT=5000 ADMIN_PASSWORD=oracle-dev tools/smoke.sh   (setzt die Session am Ende NICHT zurueck)
set -euo pipefail
BASE="http://127.0.0.1:${PORT:-5000}"; PW="${ADMIN_PASSWORD:-oracle-dev}"
J="$(mktemp -d)"; trap 'rm -rf "$J"' EXIT
tok() { curl -s -b "$1" -c "$1" "$BASE/" | sed -n 's/.*name="csrf-token" content="\([^"]*\)".*/\1/p'; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
check() { [ "$2" = "$3" ] && echo "OK   $1 ($2)" || { echo "FAIL $1: erwartet $3, erhalten $2"; exit 1; }; }

check "GET /"        "$(code $BASE/)" 200
check "GET /screen"  "$(code $BASE/screen)" 200
check "GET /admin"   "$(code $BASE/admin)" 200
check "GET /healthz" "$(code $BASE/healthz)" 200
check "GET /readyz"  "$(code $BASE/readyz)" 200
check "GET /qr.svg (svg)" "$(curl -s $BASE/qr.svg | grep -c '<svg')" 1
check "Admin ohne Login" "$(code $BASE/admin/api/state)" 401

A="$J/admin"; T="$(tok $A)"
curl -s -b $A -c $A -o /dev/null -d "password=$PW&csrf_token=$T" $BASE/admin/login
T="$(curl -s -b $A -c $A $BASE/admin | sed -n 's/.*name="csrf-token" content="\([^"]*\)".*/\1/p')"
adm() { curl -s -b $A -c $A -H "X-CSRFToken: $T" -H 'Content-Type: application/json' -X POST -d "${2:-{\}}" "$BASE/admin/api/$1" -o /dev/null -w '%{http_code}'; }
check "Admin-Login/state" "$(code -b $A $BASE/admin/api/state)" 200
check "reset_round"       "$(adm reset_round '{"confirm":true}')" 200
check "open_voting"       "$(adm open_voting '{"duration":30}')" 200

P="$J/p1"; PT="$(tok $P)"
vote() { curl -s -b $P -c $P -H "X-CSRFToken: $PT" -H 'Content-Type: application/json' -X POST -d "{\"option\":\"$1\",\"request_id\":\"$2\"}" $BASE/api/vote -o /dev/null -w '%{http_code}'; }
curl -s -b $P -c $P $BASE/api/state >/dev/null
check "Stimme"          "$(vote B smoke-req-0001)" 200
check "Doppelstimme"    "$(vote A smoke-req-0002)" 409
check "Retry gleiche ID" "$(vote B smoke-req-0001)" 200
check "Zwischenstand verborgen" "$(curl -s -b $P $BASE/api/state | grep -c '"counts"')" 0
check "close_voting"    "$(adm close_voting)" 200
check "publish_result"  "$(adm publish_result)" 200
check "Ergebnis sichtbar" "$(curl -s $BASE/api/state | grep -c '"winner":"B"')" 1
check "start_challenge" "$(adm start_challenge)" 200
check "finish_challenge" "$(adm finish_challenge)" 200
check "save_scorecard"  "$(adm save_scorecard '{"ratings":["task_done"],"note":"smoke"}')" 200
echo "Smoke-Test erfolgreich. Zustand: scorecard_visible, Runde 1."
