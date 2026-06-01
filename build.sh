#!/usr/bin/env bash
# LLVM DiffTester — install dependencies and initialize the database.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> LLVM DiffTester build"
echo "    Directory: $ROOT"

# --- Python ---
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install Python 3.10+."
  exit 1
fi
PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "    Python:    $PY_VER ($(command -v python3))"

# --- LLVM toolchain ---
MISSING=()
for tool in clang llvm-as opt lli; do
  if command -v "$tool" &>/dev/null; then
    echo "    $tool: $(command -v "$tool")"
  else
    MISSING+=("$tool")
  fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
  echo "ERROR: Missing LLVM tools: ${MISSING[*]}"
  echo "  Ubuntu: sudo apt install clang llvm"
  echo "  macOS:  brew install llvm  (add bin to PATH)"
  exit 1
fi

# --- Virtual environment ---
if [ ! -d "venv" ]; then
  echo "==> Creating virtual environment"
  python3 -m venv venv
fi
echo "==> Installing Python packages"
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt

# --- Directories ---
mkdir -p instance uploads uploads/test_cases

# --- Database ---
echo "==> Initializing SQLite database"
./venv/bin/python -c "from db import init_db; init_db(); print('    DB: instance/llvm_tests.db')"

echo ""
echo "Build complete. Next steps:"
echo "  ./run.sh              # start Flask web UI"
echo "  ./run.sh batch        # run all bundled test cases (needs GEMINI_API_KEY)"
echo "  See SCRIPTS.md for details."
