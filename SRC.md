# Source Layout

Project root: `llvm_difftester/`. All paths below are relative to that directory.

## Directory tree

```
llvm_difftester/
├── app.py                 # Flask app, routes, orchestration
├── db.py                  # SQLite schema, stats, error classification
├── llvm_utils.py          # clang / llvm-as / opt / lli wrappers
├── mutation_prompts.py    # Six LLM prompt templates
├── automate_tests.py      # Batch runner (Flask APIs + Gemini)
├── requirements.txt       # Python: flask>=3.0.0
├── build.sh               # Install venv, deps, init DB
├── run.sh                 # Start server or batch tests
├── README.md              # Quick start and overview
├── DESIGN.md              # Architecture and alternatives
├── IMPLEMENTATION.md      # LLVM pipeline details
├── SCRIPTS.md             # How to run build/run/automation
├── TESTCASES.md           # Bundled C programs
├── instance/
│   └── llvm_tests.db      # SQLite (created by init_db)
├── uploads/               # Uploaded / generated .c files
│   └── test_cases/        # Sample programs test1.c … test6.c
├── static/
│   ├── css/style.css
│   └── js/
│       ├── main.js        # Test Lab UI logic
│       └── analysis.js    # Charts + KPIs
└── templates/
    ├── base.html          # Sidebar layout
    ├── index.html         # Test Lab (6 steps)
    ├── analysis.html      # Dashboard
    ├── research.html      # Extra research page (if linked)
    └── mutation.html      # Extra mutation page (if linked)
```

## Core Python modules

### `app.py`

| Responsibility | Details |
|----------------|---------|
| HTTP routes | `/`, `/analysis`, REST `/api/*` |
| Upload handling | Saves `uploads/<uuid>.c`, calls `generate_ir` |
| Test pipeline | `verify_ir` → `run_differential` → `insert_run` |
| CORS | `Access-Control-Allow-Origin: *` for local dev |
| Entry | `init_db()` then `app.run()`; port from `FLASK_PORT` (default 5000) |

### `db.py`

| Function | Purpose |
|----------|---------|
| `init_db()` | `CREATE TABLE IF NOT EXISTS test_runs` |
| `insert_run(data)` | Insert row, return `id` |
| `get_all_runs()` / `get_run(id)` | History and modal |
| `get_analysis_stats()` | Aggregates for charts |
| `classify_error(stderr)` | Map verifier text → category |

### `llvm_utils.py`

| Function | Purpose |
|----------|---------|
| `generate_ir(path)` | `clang -emit-llvm` |
| `verify_ir(text)` | `llvm-as` + `opt` verify |
| `compile_and_run(text, level)` | `opt` + `lli` |
| `run_differential(text)` | O0 vs O3 comparison |

### `mutation_prompts.py`

| Symbol | Purpose |
|--------|---------|
| `MUTATION_TYPES` | Dict of 6 keys → `label`, `description`, `prompt_template` |
| `get_prompt(type, ir)` | `.format(ir=...)` on template |

### `automate_tests.py`

| Responsibility | Details |
|----------------|---------|
| CLI | `python automate_tests.py <file.c>` |
| Flask client | `urllib` → `/api/generate-ir`, `/api/get-prompt`, `/api/validate-and-test` |
| Gemini | REST `generateContent`; strips markdown from response |
| Not duplicated | No local verify/opt/lli — always via Flask |

## Frontend

| File | Role |
|------|------|
| `static/js/main.js` | Upload, mutation cards, prompt, validate, history table, modal |
| `static/js/analysis.js` | Fetch `/api/stats`, Chart.js doughnut/bar/line charts |
| `static/css/style.css` | Layout, steps, badges, diff view, responsive sidebar |

## Data flow (manual)

```
index.html  →  main.js  →  POST /api/generate-ir
                         →  POST /api/get-prompt
                    (user + external LLM)
                         →  POST /api/validate-and-test
                         →  GET  /api/runs

analysis.html  →  analysis.js  →  GET /api/stats
```

## Data flow (automated)

```
automate_tests.py  →  POST /api/generate-ir
                   →  for each mutation:
                         POST /api/get-prompt
                         Gemini API
                         POST /api/validate-and-test
```

## Configuration files

| File | Use |
|------|-----|
| `.env` | Optional `GEMINI_API_KEY`, `FLASK_PORT` (not committed) |
| `.gitignore` | `venv/`, `instance/*.db`, `.env`, uploads noise |

## What is not in `src/`

This project uses a **flat layout** (modules at repo root), not a `src/` package. The “source” is the Python modules and `static/` / `templates/` listed above.

See [SCRIPTS.md](SCRIPTS.md) for execution entry points.
