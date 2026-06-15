#!/usr/bin/env bash
# Deprecated: FastAPI already serves docs/ at http://127.0.0.1:8000/
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/run_all.sh" server "$@"
