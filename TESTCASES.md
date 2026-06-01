# Test Cases

Bundled C programs live in:

```text
uploads/test_cases/
├── test1.c
├── test2.c
├── test3.c
├── test4.c
├── test5.c
└── test6.c
```

They are **educational-style** programs with deterministic `printf` output and no `scanf`, so `lli` comparisons at `-O0` vs `-O3` are stable for valid IR.

## Summary table

| File | Topic | Notable constructs |
|------|--------|-------------------|
| `test1.c` | Arithmetic | Variables, `printf`, simple `main` |
| `test2.c` | Factorial loop | `for`, accumulating product |
| `test3.c` | 1D array | Array init, sum, float average |
| `test4.c` | 2D matrix | Nested loops, 2D array indexing |
| `test5.c` | Grades / branches | Arrays, `if`/`else`, string literal |
| `test6.c` | Bubble sort | Nested loops, swaps, 10-element array |

## Per-file description

### `test1.c` — Basic arithmetic

- Adds two integers, prints `a`, `b`, and `sum`.
- Good **smoke test**: small IR, fast Gemini/LLVM turnaround.

### `test2.c` — Factorial loop

- Fixed `n = 5`, loop computes factorial with step prints.
- Exercises **loop PHI-friendly** seed IR for `insert_phi` mutations.

### `test3.c` — Array sum and average

- Five-element array, sum in loop, `float` average.
- Mix of **int** and **float** (`printf` with `%.2f`).

### `test4.c` — 2D matrix sum

- `matrix[2][2]`, nested loops for print and sum.
- Larger IR; stresses **control flow** mutations (`insert_branch`).

### `test5.c` — Conditional grading

- Marks array, total, average, `if (average >= 90)` for grade.
- Useful for **branch** and **icmp** mutation prompts.

### `test6.c` — Bubble sort

- Ten elements, O(n²) sort with swaps.
- Largest bundled case; more basic blocks and compares.

## How to run test cases

### 1. Automatic — all six files (recommended for regression)

```bash
./build.sh
export GEMINI_API_KEY=your_key
./run.sh batch
```

Runs **`automate_tests.py`** on every `uploads/test_cases/*.c` × **6 mutation types** each (36 Flask test records if all succeed).

### 2. Automatic — single file

```bash
# Terminal 1
./run.sh

# Terminal 2
./run.sh auto uploads/test_cases/test1.c
```

### 3. Manual — one file in Flask UI

```bash
./run.sh
```

1. Open http://localhost:5000  
2. Upload e.g. `uploads/test_cases/test1.c`  
3. Choose a mutation → Generate Prompt  
4. Paste mutated IR from your LLM  
5. Run Validation & Testing  
6. Repeat for other mutations or files  
7. Open **Analysis** to see aggregated results  

### 4. Manual — without upload path

You can also open `test1.c` in an editor, copy content into a new `.c` file, or use the file picker to select files under `uploads/test_cases/`.

## Expected outcomes

| Outcome | Meaning |
|---------|---------|
| **VALID + MATCH** | LLM IR verified; O0 and O3 agree — no differential bug signal |
| **VALID + MISMATCH** | “Interesting” — possible optimizer sensitivity (investigate) |
| **INVALID** | Verifier failed — check `error_type` on Analysis chart |

Invalid IR is **expected** for some LLM mutations; the goal is to measure validity rate per mutation type, not 100% success.

## Adding new test cases

1. Add `uploads/test_cases/my_test.c`  
2. Prefer deterministic output (no user input, avoid undefined behavior)  
3. Run:

   ```bash
   ./run.sh auto uploads/test_cases/my_test.c
   ```

4. Confirm `clang` can emit IR locally:

   ```bash
   clang -S -emit-llvm -O0 -o /tmp/x.ll uploads/test_cases/my_test.c
   ```

## Related docs

- [SCRIPTS.md](SCRIPTS.md) — `build.sh`, `run.sh`, `automate_tests.py`  
- [IMPLEMENTATION.md](IMPLEMENTATION.md) — LLVM verify and differential details  
- [DESIGN.md](DESIGN.md) — why differential testing on O0 vs O3  
