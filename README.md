# LLVM DiffTester

A Flask web application for **LLVM IR differential compiler testing**. Upload C source, generate LLVM IR with `clang`, craft LLM mutation prompts, validate mutated IR with the LLVM verifier, and compare execution at `-O0` vs `-O3` using `lli`. All results are stored in SQLite and visualized on a live Analysis dashboard.

## Prerequisites

- **Python 3.10+** (tested with Python 3.11–3.14)
- **LLVM toolchain** on `PATH`:
  - `clang` — emit LLVM IR from `.c` files
  - `llvm-as` — assemble `.ll` to bitcode
  - `opt` — verify and optimize IR
  - `lli` — interpret bitcode

### Install LLVM

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install clang llvm
```

**macOS (Homebrew):**

```bash
brew install llvm
# Add to PATH, e.g. in ~/.zshrc:
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
```

**Verify:**

```bash
clang --version
llvm-as --version
opt --version
lli --version
```

> **Note (LLVM 17+):** The verifier uses `opt -passes=verify` when legacy `opt --verify` is unavailable (new pass manager). Behavior matches the original spec: IR must pass both `llvm-as` and `opt` verification.

## Install & Run

```bash
cd llvm_difftester
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000** in your browser.

If port 5000 is busy:

```bash
# Linux/macOS
FLASK_RUN_PORT=5001 python app.py
```

## Usage Flow

1. **Test Lab** — Upload a `.c` file (drag-and-drop or browse). The app runs `clang -S -emit-llvm -O0` and shows the generated IR.
2. Choose one of **six mutation types** (arithmetic, type change, branch, PHI loop, dead code, operand swap).
3. Click **Generate Prompt**, copy the prompt, and paste it into Claude, GPT-4, or another LLM.
4. Paste the **mutated IR** returned by the LLM into Step 4.
5. Click **Run Validation & Testing**:
   - Verifies IR (`llvm-as` + `opt` verify)
   - Runs differential test: `opt -O0` / `opt -O3` → `lli` (10s timeout each)
   - Compares stdout and exit codes
6. Review results (valid/invalid, error category, O0/O3 match, “interesting” mismatches).
7. Open **Analysis** for charts and KPIs built from the database (`instance/llvm_tests.db`).

## Project Layout

```
llvm_difftester/
├── app.py                 # Flask routes
├── db.py                  # SQLite schema & helpers
├── llvm_utils.py          # clang / llvm-as / opt / lli wrappers
├── mutation_prompts.py     # LLM prompt templates
├── requirements.txt
├── instance/llvm_tests.db # auto-created
├── uploads/               # temporary .c / .ll files
├── static/css/style.css
├── static/js/main.js
├── static/js/analysis.js
└── templates/
    ├── base.html
    ├── index.html
    └── analysis.html
```

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Test Lab UI |
| `GET` | `/analysis` | Analysis dashboard |
| `POST` | `/api/generate-ir` | Upload `.c`, return IR |
| `POST` | `/api/get-prompt` | JSON `{ ir, mutation_type }` → prompt |
| `POST` | `/api/validate-and-test` | Verify + differential test + DB insert |
| `GET` | `/api/runs` | All test runs |
| `GET` | `/api/run/<id>` | Single run |
| `GET` | `/api/stats` | Aggregated stats for charts |

## Error Categories

Invalid IR is classified from verifier stderr:

| Category | Typical cause |
|----------|----------------|
| `SSA_VIOLATION` | Use-before-def, redefined SSA name |
| `TYPE_MISMATCH` | Operand type mismatch |
| `INVALID_PHI` | PHI placement / predecessors |
| `DOMINANCE_ERROR` | Value used outside dominating block |
| `MISSING_TERMINATOR` | Block without terminator |
| `UNKNOWN_ERROR` | Other verifier failures |

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.10+, Flask 3.x, `sqlite3` (no ORM) |
| Frontend | Vanilla HTML/CSS/ES6+ |
| Charts | [Chart.js 4.x](https://www.chartjs.org/) (CDN) |
| Icons | [Feather Icons](https://feathericons.com/) (CDN) |

## Tested Versions

| Component | Version |
|-----------|---------|
| Python | 3.11 – 3.14 |
| Flask | 3.1.x |
| Chart.js | 4.4.7 (CDN) |
| LLVM / clang | 17 – 21 (Ubuntu 22.04/24.04) |

## Sample C Program

A minimal test file is included at `uploads/test_sample.c`:

```c
#include <stdio.h>
int main(void) {
  printf("42\n");
  return 0;
}
```

Upload it on the Test Lab page to try the full pipeline without writing C code first.

## Automated batch testing (Gemini + Flask)

`automate_tests.py` drives the **same Flask APIs** as the web UI. Verification, differential testing, SQLite history, and Analysis charts all use the running app — only IR mutation is done via the Gemini API.

**Prerequisites:**

1. Flask app running: `python app.py`
2. API key: `export GEMINI_API_KEY=your_key` (or `GOOGLE_API_KEY`)
3. Optional: `export GEMINI_MODEL=gemini-2.5-flash` (default)
4. Optional: `export DIFFTESTER_URL=http://127.0.0.1:5000` if not on default port

**Run all six mutation types for one C file:**

```bash
python automate_tests.py uploads/test_sample.c
```

**Options:**

```bash
python automate_tests.py program.c --url http://127.0.0.1:5001
python automate_tests.py program.c --model gemini-2.0-flash --delay 2
python automate_tests.py program.c --mutations add_arithmetic dead_code
```

**Flow per mutation:**

1. `POST /api/generate-ir` — once, from your `.c` file  
2. `POST /api/get-prompt` — prompt from Flask templates  
3. Gemini `generateContent` — mutated IR  
4. `POST /api/validate-and-test` — verifier + O0/O3 + DB insert  

Results appear on **Test Lab → History** and **Analysis** like manual runs.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `clang not found` | Install LLVM toolchain and ensure `PATH` includes its `bin` directory |
| `lli` timeout | IR may run indefinitely; simplify the program or increase timeout in `llvm_utils.py` |
| Verifier fails on valid-looking IR | LLM output may include markdown fences or commentary — paste **raw IR only** |
| Empty database on Analysis | Run at least one test on the Test Lab page |

## License

Provided as-is for LLVM IR fuzzing and differential testing research.
