#!/usr/bin/env bash
# LLVM DiffTester — start the server or run automated test batches.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="./venv/bin/python"
PORT="${FLASK_PORT:-5000}"
BASE_URL="${DIFFTESTER_URL:-http://127.0.0.1:${PORT}}"
TEST_DIR="uploads/test_cases"
FLASK_PID=""

load_env() {
  if [ -f ".env" ]; then
    set -a
    # shellcheck source=/dev/null
    source ".env"
    set +a
    echo "    Loaded .env"
  fi
}

require_venv() {
  if [ ! -x "$PYTHON" ]; then
    echo "ERROR: venv not found. Run ./build.sh first."
    exit 1
  fi
}

require_gemini_key() {
  if [ -z "${GEMINI_API_KEY:-}" ] && [ -z "${GOOGLE_API_KEY:-}" ]; then
    echo "ERROR: Set GEMINI_API_KEY or GOOGLE_API_KEY (or add to .env)."
    exit 1
  fi
}

start_flask_background() {
  echo "==> Starting Flask on port ${PORT} (background)"
  "$PYTHON" -c "
from app import app, init_db
init_db()
app.run(host='127.0.0.1', port=${PORT}, debug=False, use_reloader=False)
" &
  FLASK_PID=$!
  sleep 2
  if ! kill -0 "$FLASK_PID" 2>/dev/null; then
    echo "ERROR: Flask failed to start."
    exit 1
  fi
  echo "    Flask PID: $FLASK_PID  URL: ${BASE_URL}"
}

stop_flask() {
  if [ -n "$FLASK_PID" ] && kill -0 "$FLASK_PID" 2>/dev/null; then
    echo "==> Stopping Flask (PID $FLASK_PID)"
    kill "$FLASK_PID" 2>/dev/null || true
    wait "$FLASK_PID" 2>/dev/null || true
  fi
}

trap stop_flask EXIT

run_server() {
  require_venv
  echo "==> Starting LLVM DiffTester (foreground)"
  echo "    Open: ${BASE_URL}"
  echo "    Press Ctrl+C to stop."
  export FLASK_RUN_PORT="$PORT"
  exec "$PYTHON" app.py
}

run_single_auto() {
  local c_file="$1"
  require_venv
  require_gemini_key
  load_env
  export DIFFTESTER_URL="$BASE_URL"
  echo "==> Automated run: $c_file"
  "$PYTHON" automate_tests.py "$c_file" --url "$BASE_URL" "$@"
}

run_batch() {
  require_venv
  require_gemini_key
  load_env

  start_flask_background

  shopt -s nullglob
  local files=( "$TEST_DIR"/*.c )
  if [ ${#files[@]} -eq 0 ]; then
    echo "ERROR: No .c files in ${TEST_DIR}/"
    exit 1
  fi

  echo "==> Batch: ${#files[@]} test case(s) in ${TEST_DIR}/"
  local failed=0
  for f in "${files[@]}"; do
    echo ""
    echo "########################################"
    echo "# $(basename "$f")"
    echo "########################################"
    if ! "$PYTHON" automate_tests.py "$f" --url "$BASE_URL"; then
      failed=$((failed + 1))
    fi
  done

  echo ""
  echo "==> Batch finished: ${#files[@]} file(s), ${failed} failure(s)"
  echo "    History & charts: ${BASE_URL}/  and  ${BASE_URL}/analysis"
  [ "$failed" -eq 0 ]
}

usage() {
  cat <<EOF
Usage: ./run.sh [COMMAND]

Commands:
  (none) | server     Start Flask web UI (manual testing)     [default]
  auto <file.c>       Run automate_tests.py for one .c file
                      (Flask must already be running, or use batch)
  batch               Start Flask, run ALL uploads/test_cases/*.c
                      through automate_tests.py, then stop Flask
  help                Show this message

Environment:
  FLASK_PORT / DIFFTESTER_URL   Flask port and base URL (default 5000)
  GEMINI_API_KEY / GOOGLE_API_KEY   Required for auto and batch
  GEMINI_MODEL                  Passed to automate_tests.py

Automatic test runner:  automate_tests.py  (see SCRIPTS.md)
Manual testing:        ./run.sh  →  browser at http://localhost:5000

EOF
}

# --- main ---
case "${1:-server}" in
  server|"")
    run_server
    ;;
  auto)
    shift
    [ $# -ge 1 ] || { echo "Usage: ./run.sh auto <file.c>"; exit 1; }
    CFILE="$1"
    shift
    run_single_auto "$CFILE" "$@"
    ;;
  batch)
    run_batch
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $1"
    usage
    exit 1
    ;;
esac
