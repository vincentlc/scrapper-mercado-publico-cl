#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
SETUP_STAMP=".setup.done"
REQ_STAMP=".requirements.sha256"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source ".venv/bin/activate"

CURRENT_REQ_HASH="$(sha256sum requirements.txt | awk '{print $1}')"
PREV_REQ_HASH=""
if [[ -f "$REQ_STAMP" ]]; then
  PREV_REQ_HASH="$(cat "$REQ_STAMP")"
fi

if [[ ! -f "$SETUP_STAMP" || "$CURRENT_REQ_HASH" != "$PREV_REQ_HASH" ]]; then
  echo "Running initial setup / dependency sync..."
  pip install -r requirements.txt
  echo "$CURRENT_REQ_HASH" > "$REQ_STAMP"
  touch "$SETUP_STAMP"
else
  echo "Setup already done. Skipping pip install."
fi

python -m scripts.update_offers

URL="http://127.0.0.1:8000"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi

exec uvicorn app.main:app --reload
