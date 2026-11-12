#!/usr/bin/env bash
# Erstellt dist/dswnwst-voting-<version>.tar.gz (ohne .git, .venv, DB, .env, Logs, Backups, Caches).
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
VERSION="$(cat VERSION)-$(date -u +%Y%m%d%H%M%S)"
NAME="dswnwst-voting-$VERSION"
mkdir -p dist
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
DEST="$STAGE/$NAME"; mkdir -p "$DEST"

cp -r votingapp migrations tools deploy "$DEST/"
cp wsgi.py gunicorn.conf.py VERSION README.md .env.example .gitignore \
   requirements.txt requirements-dev.txt requirements.lock start.sh stop.sh status.sh package.sh "$DEST/"
cp -r tests "$DEST/"
find "$DEST" \( -name __pycache__ -o -name '*.pyc' -o -name .pytest_cache -o -name '*.db*' -o -name '.env' \) -prune -exec rm -rf {} +

if grep -rIl "$HOME" "$DEST" >/dev/null 2>&1; then
  echo "FEHLER: Paket enthält Verweise auf $HOME:" >&2
  grep -rIl "$HOME" "$DEST" >&2; exit 1
fi
tar -C "$STAGE" -czf "dist/$NAME.tar.gz" "$NAME"
echo "dist/$NAME.tar.gz"
