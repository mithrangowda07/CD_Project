# Implementation — LLVM Details

This document describes how LLVM tools are invoked, how IR is verified, and how differential results are produced. Implementation code lives primarily in `llvm_utils.py` and `db.py`.

## Toolchain requirements

| Binary | Role |
|--------|------|
| `clang` | Emit LLVM IR (`.ll`) from C at `-O0` |
| `llvm-as` | Parse/assemble `.ll` to bitcode (verification) |
| `opt` | IR verification pass and optimization to bitcode |
| `lli` | Execute bitcode interpreter |

All invocations use:

```python
subprocess.run(..., capture_output=True, text=True, timeout=30)
```

(`lli` uses a **10 second** timeout in `compile_and_run`.)

Missing binaries return a clear `FileNotFoundError` message pointing to OS install instructions.

## Stage 1 — Generate seed IR (`generate_ir`)

**Command:**

```bash
clang -S -emit-llvm -O0 -o <tmp.ll> <c_filepath>
```

**Behavior:**

- Writes IR to a temporary `.ll` file, reads content into memory, deletes the temp file in a `finally` block.
- Returns `{ "success", "output", "error" }` where `output` is the full IR text.

**Why `-O0`:** Seed IR should reflect a direct translation before aggressive opts, so LLM mutations start from a predictable baseline.

## Stage 2 — Verify mutated IR (`verify_ir`)

**Steps:**

1. Write `ir_text` to a temporary `.ll` file.
2. Run **llvm-as**:

   ```bash
   llvm-as <tmp.ll> -o /dev/null
   ```

3. Run **opt verify**:

   ```bash
   opt --verify <tmp.ll> -o /dev/null
   ```

   On **LLVM 17+** (new pass manager), legacy `--verify` may fail with a “new pass manager” error. The code then retries:

   ```bash
   opt -disable-output -passes=verify <tmp.ll>
   ```

4. If either step fails, combine stderr into `error` and set `success=False`.

**Rationale:** `llvm-as` catches syntax/structural issues; `opt -passes=verify` runs IR-level verification passes.

## Stage 3 — Compile and run (`compile_and_run`)

**Parameters:** `opt_level` is `"-O0"` or `"-O3"`.

**Pipeline:**

```bash
opt <opt_level> <tmp.ll> -o <tmp.bc>
lli <tmp.bc>
```

**Returns:**

- `output` — stdout from `lli`
- `exit_code` — process return code
- `error` — stderr or `TIMEOUT` if `lli` exceeds 10s

Temp `.ll` and `.bc` files are always removed in `finally`.

## Stage 4 — Differential test (`run_differential`)

Calls `compile_and_run` twice on the **same** mutated IR:

| Run | opt flag | Keys in result |
|-----|----------|----------------|
| Baseline | `-O0` | `o0_output`, `o0_exit` |
| Optimized | `-O3` | `o3_output`, `o3_exit` |

**Match condition:**

```text
o0_output == o3_output  AND  o0_exit == o3_exit
```

If `opt`/`lli` fails for one side, `match=False` and `error` describes which side failed.

**Note:** Programs that print to stderr only, or depend on undefined behavior, may produce flaky comparisons—test cases are chosen to be deterministic with `printf` and fixed inputs.

## Error classification (`classify_error`)

Verifier stderr is lowercased and matched with keyword heuristics:

| Category | Example keywords |
|----------|------------------|
| `SSA_VIOLATION` | `use before`, `redefinition`, `ssa`, `already defined` |
| `TYPE_MISMATCH` | `type mismatch`, `operand type`, `incompatible type` |
| `INVALID_PHI` | `phi`, `predecessor` |
| `DOMINANCE_ERROR` | `dominance`, `dominator`, `not dominated` |
| `MISSING_TERMINATOR` | `terminator`, `no terminator` |
| `UNKNOWN_ERROR` | default |

Stored in SQLite when `valid=0`.

## Database mapping

After validation/testing, `app.py` builds a row for `test_runs`:

| Field | Valid IR | Invalid IR |
|-------|----------|------------|
| `valid` | 1 | 0 |
| `error_type` / `error_detail` | NULL | set |
| `o0_*`, `o3_*`, `diff_match` | set | NULL |
| `is_interesting` | 1 if mismatch | 0 |

## API flow (`/api/validate-and-test`)

1. `verify_ir(mutated_ir)`  
2. If invalid → `classify_error` → `insert_run` → JSON with `valid: false`  
3. If valid → `run_differential` → `insert_run` → JSON with `diff_match`, outputs, `run_id`  

The client (browser or `automate_tests.py`) never runs LLVM directly for this step.

## Mutation prompts (non-LLVM)

`mutation_prompts.py` defines six templates. Each instructs the LLM to return **raw IR only** (no markdown). The batch script strips ``` fences if the model disobeys.

Mutation types and typical LLVM features exercised:

| Key | LLVM concepts stressed |
|-----|-------------------------|
| `add_arithmetic` | New SSA defs, `add`/`mul`, typed operands |
| `change_types` | `i32`/`i64`, `sext`/`zext`/`trunc` |
| `insert_branch` | `icmp`, `br`, `phi`, block terminators |
| `insert_phi` | Loop header, PHI incoming edges |
| `dead_code` | Unreachable blocks or unused defs |
| `swap_operands` | Commutative ops, constant operands |

## Frontend LLVM display

- Seed and mutated IR shown in `<pre>` blocks (monospace).
- Invalid runs: collapsible verifier stderr in `<details>`.
- Mismatch: side-by-side O0 (blue label) vs O3 (coral label); empty stdout shows *No output*.

## Version notes

| LLVM era | Verification |
|----------|----------------|
| ≤ 16 | `opt --verify` works |
| 17+ | Fallback to `opt -passes=verify` |

`opt -O0` / `opt -O3` remain valid on tested clang **17–21**.

## Extension points

- Add `-O2` or LTO: extend `run_differential()` and DB columns.
- Use `lit` or FileCheck: optional second validation layer (not in current scope).
- Replace keyword classifier with LLVM error code parsing if available in stderr.

See [SRC.md](SRC.md) for file-level map.
