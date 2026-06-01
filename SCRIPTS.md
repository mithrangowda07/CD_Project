# Scripts — How to Run the System

## Overview

| Script / file | Purpose |
|---------------|---------|
| **`./build.sh`** | One-time setup: venv, `pip install`, check LLVM, init database |
| **`./run.sh`** | Start Flask **or** run automated batch tests |
| **`automate_tests.py`** | **Automatic test runner** for one `.c` file (all mutation types) |
| **`app.py`** | Flask application (started by `./run.sh` or `python app.py`) |

## Quick start

```bash
cd llvm_difftester
chmod +x build.sh run.sh
./build.sh
export GEMINI_API_KEY=your_key_here   # required for automation only
./run.sh                            # manual web UI
```

Open **http://localhost:5000** in a browser.

---

## `./build.sh`

**What it does:**

1. Checks `python3` and LLVM tools (`clang`, `llvm-as`, `opt`, `lli`)
2. Creates `venv/` if missing
3. Installs `requirements.txt` (Flask)
4. Creates `instance/`, `uploads/`, `uploads/test_cases/`
5. Runs `init_db()` → `instance/llvm_tests.db`

**Run:**

```bash
./build.sh
```

Re-run safely after pulling code changes (reinstalls pip deps, ensures DB exists).

---

## `./run.sh`

**What it does:** Wrapper with subcommands for server vs automation.

### Manual testing (Flask web UI) — default

```bash
./run.sh
# same as:
./run.sh server
```

- Starts **`app.py`** in the **foreground**
- URL: `http://127.0.0.1:5000` (override with `FLASK_PORT=5001 ./run.sh`)
- Use the **Test Lab** page step-by-step (upload C, pick mutation, paste LLM IR, run test)
- View **Analysis** for charts from the database

**This is the only way to run tests fully manually** (you paste LLM output yourself).

### Automatic tests — one C file

**Requires Flask already running** in another terminal:

```bash
# Terminal 1
./run.sh

# Terminal 2
./run.sh auto uploads/test_cases/test1.c
```

Equivalent to:

```bash
./venv/bin/python automate_tests.py uploads/test_cases/test1.c
```

Optional flags are passed through, e.g.:

```bash
./run.sh auto program.c --mutations add_arithmetic dead_code --delay 2
```

### Automatic tests — all bundled test cases

```bash
./run.sh batch
```

**What happens:**

1. Loads `.env` if present (for `GEMINI_API_KEY`)
2. Starts Flask in the **background**
3. For each `uploads/test_cases/*.c`, runs **`automate_tests.py`**
4. Stops Flask on exit
5. Results are in the same SQLite DB as manual runs

**Requires:** `GEMINI_API_KEY` or `GOOGLE_API_KEY`

---

## `automate_tests.py` — automatic test runner

This is the file that **runs test cases automatically** (with Gemini mutating IR).

**It does:**

| Step | Via |
|------|-----|
| Generate seed IR | Flask `POST /api/generate-ir` |
| Build prompt per mutation | Flask `POST /api/get-prompt` |
| Mutate IR | **Gemini API** (only step outside Flask) |
| Verify + O0/O3 + save | Flask `POST /api/validate-and-test` |

**It does not:** bypass Flask for LLVM or database operations.

**Direct usage:**

```bash
# Flask must be running unless you use ./run.sh batch
export GEMINI_API_KEY=...
./venv/bin/python automate_tests.py path/to/file.c
./venv/bin/python automate_tests.py uploads/test_cases/test3.c --url http://127.0.0.1:5000
```

**Environment:**

| Variable | Default | Meaning |
|----------|---------|---------|
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | — | Required |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model id |
| `DIFFTESTER_URL` | `http://127.0.0.1:5000` | Flask base URL |
| `GEMINI_DELAY_SECONDS` | `1.0` | Pause between API calls |

---

## Manual vs automatic — comparison

| Aspect | Manual (Flask UI) | Automatic (`automate_tests.py`) |
|--------|-------------------|----------------------------------|
| Start server | `./run.sh` | `./run.sh` or `./run.sh batch` |
| Generate IR | Upload in browser | Flask API |
| Get prompt | Click “Generate Prompt” | Flask API |
| Mutate IR | You paste from ChatGPT/Claude/Gemini | **Gemini API in script** |
| Verify + diff test | “Run Validation & Testing” | Flask API |
| History / Analysis | Same DB | Same DB |
| LLM choice | Any | Gemini (configured model) |

---

## `app.py` (without shell scripts)

```bash
source venv/bin/activate
python app.py
```

Same as `./run.sh server`. Initializes DB on startup.

---

## Optional `.env`

Create `llvm_difftester/.env`:

```bash
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
FLASK_PORT=5000
```

`./run.sh batch` and `./run.sh auto` load this file automatically.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `venv not found` | Run `./build.sh` |
| `Flask app not reachable` | Start `./run.sh` before `auto` |
| `GEMINI_API_KEY` missing | Export key or use `.env` |
| Port in use | `FLASK_PORT=5001 ./run.sh` and `DIFFTESTER_URL=http://127.0.0.1:5001` for auto |
| Batch slow / rate limits | Increase `--delay` on `automate_tests.py` |

See also [TESTCASES.md](TESTCASES.md) and [README.md](README.md).
