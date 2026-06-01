# Design — LLVM DiffTester

## Problem statement

Compiler optimizers can change program behavior in subtle ways. Traditional fuzzing finds crashes; **differential testing** compares observable outputs across optimization levels (e.g. `-O0` vs `-O3`) on the **same** IR program. If outputs differ, that may indicate a miscompilation.

This project adds an **LLM-in-the-loop** step: a large language model mutates LLVM IR guided by structured prompts, so researchers can study how often LLM-produced IR is **verifier-valid** and whether it surfaces **optimization-sensitive** behavior.

## Goals

| Goal | Description |
|------|-------------|
| Reproducible pipeline | C → IR → prompt → mutated IR → verify → execute → compare |
| Human + machine paths | Web UI for exploration; script for batch runs |
| Persistent experiment log | SQLite stores every run for History and Analysis |
| No heavy frameworks | Flask + stdlib SQLite + subprocess LLVM tools |

## High-level architecture

```
┌─────────────┐     clang      ┌──────────┐
│  .c file    │ ─────────────► │ seed IR  │
└─────────────┘                └────┬─────┘
                                    │
                    mutation_prompts + LLM (manual or Gemini)
                                    ▼
                              ┌──────────┐
                              │mutated IR│
                              └────┬─────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        llvm-as + opt         opt -O0 → lli      opt -O3 → lli
         (verify)              (stdout/exit)      (stdout/exit)
              │                    └────────┬────────┘
              ▼                             ▼
         invalid →                    compare → match / mismatch
         error_type                   (interesting if mismatch)
              │                             │
              └─────────────┬───────────────┘
                            ▼
                   SQLite (test_runs)
                            ▼
              Flask UI: Test Lab + Analysis charts
```

## Core design decisions

### 1. Flask as single source of truth

All verification, differential execution, and database writes go through **Flask HTTP APIs** (`/api/validate-and-test`, etc.). The batch script (`automate_tests.py`) only adds **Gemini** for IR mutation; it does not reimplement LLVM logic. That keeps manual and automated runs comparable in the same database.

### 2. Prompt templates outside the LLM

Mutation instructions live in `mutation_prompts.py` as fixed templates with an `{ir}` placeholder. The app does not trust the model to invent the testing strategy—only to apply one of six named mutations.

### 3. Keyword-based error taxonomy

Verifier stderr is classified into categories (`SSA_VIOLATION`, `TYPE_MISMATCH`, …) via simple substring rules in `db.classify_error()`. This trades precision for transparency and zero ML dependency.

### 4. “Interesting” = output mismatch on valid IR

A run is flagged `is_interesting` when IR passes the verifier but `lli` results differ between `-O0` and `-O3` (stdout or exit code). Invalid IR is logged but not treated as a compiler bug signal.

### 5. Vanilla frontend

No React/Vue/Bootstrap: HTML templates + CSS + ES6 fetch. Chart.js loads from CDN for the Analysis page only.

## Approaches considered

### A. Monolithic CLI only (rejected as sole interface)

**Idea:** One Python script calls clang, Gemini, and opt directly.

**Pros:** Simple deployment, no server.

**Cons:** Duplicates logic; harder to demo; no live dashboard. **Chosen hybrid:** CLI for batch, Flask for everything LLVM-related.

### B. SQLAlchemy ORM (rejected)

**Idea:** Use Flask-SQLAlchemy models.

**Pros:** Migrations, relationships.

**Cons:** Extra dependency; spec required stdlib `sqlite3`. **Chosen:** thin helpers in `db.py`.

### C. Compile mutated IR to native binary (rejected)

**Idea:** `llc` + `gcc` instead of `lli`.

**Pros:** Closer to production execution.

**Cons:** Linking, libc, platform ABI; slower setup. **Chosen:** `lli` on bitcode for fast interpreter-style comparison.

### D. FuzzIR / custom mutator without LLM (alternative baseline)

**Idea:** Random LLVM pass pipelines or grammar-based IR mutators.

**Pros:** Higher throughput, no API cost.

**Cons:** Does not evaluate LLM usefulness. This project **complements** such work by measuring LLM validity rates per mutation type (Analysis chart E).

### E. Single optimization pair only (accepted)

**Idea:** Compare only `-O0` vs `-O3`.

**Pros:** Clear semantic gap; matches coursework spec.

**Cons:** Misses `-Os`, LTO, etc. Extending `llvm_utils.run_differential()` to more levels is straightforward.

## User workflows

### Manual (Flask web UI)

1. Upload `.c` → view seed IR  
2. Select mutation type → copy LLM prompt  
3. Paste mutated IR from Claude/GPT/Gemini  
4. Run validation & testing → read badges and diff  
5. Open **Analysis** for aggregate stats  

### Automated (script + Flask)

1. `./build.sh`  
2. `export GEMINI_API_KEY=...`  
3. `./run.sh batch` **or** `./run.sh` in one terminal and `./run.sh auto file.c` in another  

See [SCRIPTS.md](SCRIPTS.md) and [TESTCASES.md](TESTCASES.md).

## Security and operations notes

- Flask `secret_key` is random per process; no user auth (local research tool).
- Uploaded `.c` files land in `uploads/` with UUID names.
- Gemini API keys must not be committed; use `.env` (gitignored) or environment variables.
- Subprocess timeouts: 30s for most LLVM calls, 10s for `lli`.

## Related documents

| Document | Contents |
|----------|----------|
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | LLVM commands, verification, differential test |
| [SRC.md](SRC.md) | Source file map and module responsibilities |
| [SCRIPTS.md](SCRIPTS.md) | `build.sh`, `run.sh`, `automate_tests.py` |
| [TESTCASES.md](TESTCASES.md) | Bundled `.c` programs |
