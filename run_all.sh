#!/usr/bin/env bash
# Local dev orchestrator: scrape Mercado Público + run API/frontend.
#
# Usage:
#   ./run_all.sh                 # scrape (local SQLite) + server
#   ./run_all.sh scrape          # only download/update offers
#   ./run_all.sh server          # only FastAPI + frontend
#   ./run_all.sh setup           # venv + dependencies
#
# Scrape options:
#   --local-only      SQLite only (default for local dev)
#   --with-sheets     Also write to Google Sheets (needs .env credentials)
#   --source auto|api|csv
#   --no-open         Do not open the browser
#
# Examples:
#   ./run_all.sh scrape --source csv
#   ./run_all.sh scrape --source api --local-only
#   ./run_all.sh scrape --with-sheets
#   ./run_all.sh server --port 8000

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

SETUP_STAMP=".setup.done"
REQ_STAMP=".requirements.sha256"
PORT=8000
OPEN_BROWSER=1
LOCAL_ONLY=1
WITH_SHEETS=0
SOURCE="auto"
CMD="all"

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

load_env() {
  local env_file="$ROOT_DIR/.env"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
    echo "[env] Loaded $env_file"
  else
    echo "[env] No .env file (OK for --local-only scrape)"
  fi
}

ensure_venv() {
  if [[ ! -d ".venv" ]]; then
    echo "[setup] Creating virtualenv..."
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source ".venv/bin/activate"

  local current_req_hash prev_req_hash=""
  current_req_hash="$(sha256sum requirements.txt | awk '{print $1}')"
  if [[ -f "$REQ_STAMP" ]]; then
    prev_req_hash="$(cat "$REQ_STAMP")"
  fi

  if [[ ! -f "$SETUP_STAMP" || "$current_req_hash" != "$prev_req_hash" ]]; then
    echo "[setup] Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo "$current_req_hash" > "$REQ_STAMP"
    touch "$SETUP_STAMP"
  else
    echo "[setup] Dependencies up to date"
  fi
}

run_scrape() {
  local args=()
  if [[ "$LOCAL_ONLY" -eq 1 ]]; then
    args+=(--local-only)
  fi
  if [[ "$SOURCE" != "auto" ]]; then
    args+=(--source "$SOURCE")
  fi

  echo "[scrape] python -m scripts.update_offers ${args[*]:-}"
  python -m scripts.update_offers "${args[@]}"
}

open_browser() {
  local url="http://127.0.0.1:${PORT}"
  if [[ "$OPEN_BROWSER" -eq 1 ]] && command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  fi
}

run_server() {
  local url="http://127.0.0.1:${PORT}"
  echo "[server] API + frontend at $url"
  echo "[server] Health check: curl $url/api/offers?page=1&page_size=5"
  exec python -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$PORT"
}

parse_args() {
  if [[ $# -gt 0 && "$1" != --* ]]; then
    CMD="$1"
    shift
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --local-only)
        LOCAL_ONLY=1
        WITH_SHEETS=0
        ;;
      --with-sheets)
        WITH_SHEETS=1
        LOCAL_ONLY=0
        ;;
      --source)
        shift
        SOURCE="${1:?--source requires auto, api, or csv}"
        ;;
      --no-open)
        OPEN_BROWSER=0
        ;;
      --port)
        shift
        PORT="${1:?--port requires a number}"
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 1
        ;;
    esac
    shift
  done
}

main() {
  parse_args "$@"
  load_env
  ensure_venv

  case "$CMD" in
    setup)
      echo "[done] Environment ready"
      ;;
    scrape)
      run_scrape
      ;;
    server)
      open_browser
      run_server
      ;;
    all)
      run_scrape
      open_browser
      run_server
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      echo "Unknown command: $CMD" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
