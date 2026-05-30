"""Database initialization and helpers for LLVM DiffTester."""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.path.join("instance", "llvm_tests.db")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at      TEXT,
                source_filename TEXT,
                seed_ir         TEXT,
                mutation_type   TEXT,
                mutated_ir      TEXT,
                valid           INTEGER,
                error_type      TEXT,
                error_detail    TEXT,
                o0_output       TEXT,
                o3_output       TEXT,
                o0_exit         INTEGER,
                o3_exit         INTEGER,
                diff_match      INTEGER,
                is_interesting  INTEGER
            )
            """
        )
        conn.commit()


def classify_error(stderr: str) -> str:
    text = (stderr or "").lower()
    if any(
        k in text
        for k in (
            "use before",
            "redefinition",
            "ssa",
            "already defined",
            "multiple definition",
        )
    ):
        return "SSA_VIOLATION"
    if any(
        k in text
        for k in (
            "type mismatch",
            "types must match",
            "operand type",
            "incompatible type",
        )
    ):
        return "TYPE_MISMATCH"
    if any(k in text for k in ("phi", "invalid phi", "predecessor")):
        return "INVALID_PHI"
    if any(
        k in text
        for k in ("dominance", "dominator", "not dominated", "dominated by")
    ):
        return "DOMINANCE_ERROR"
    if any(
        k in text
        for k in ("terminator", "no terminator", "missing terminator")
    ):
        return "MISSING_TERMINATOR"
    return "UNKNOWN_ERROR"


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def insert_run(data: dict) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO test_runs (
                created_at, source_filename, seed_ir, mutation_type,
                mutated_ir, valid, error_type, error_detail,
                o0_output, o3_output, o0_exit, o3_exit,
                diff_match, is_interesting
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("created_at")
                or datetime.now(timezone.utc).isoformat(),
                data.get("source_filename", ""),
                data.get("seed_ir", ""),
                data.get("mutation_type", ""),
                data.get("mutated_ir", ""),
                data.get("valid", 0),
                data.get("error_type"),
                data.get("error_detail"),
                data.get("o0_output"),
                data.get("o3_output"),
                data.get("o0_exit"),
                data.get("o3_exit"),
                data.get("diff_match"),
                data.get("is_interesting", 0),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_all_runs() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM test_runs ORDER BY id DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_run(run_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM test_runs WHERE id = ?", (run_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_analysis_stats() -> dict:
    runs = get_all_runs()
    total = len(runs)
    valid = sum(1 for r in runs if r.get("valid") == 1)
    invalid = total - valid
    match = sum(
        1 for r in runs if r.get("valid") == 1 and r.get("diff_match") == 1
    )
    mismatch = sum(
        1 for r in runs if r.get("valid") == 1 and r.get("diff_match") == 0
    )
    interesting = sum(1 for r in runs if r.get("is_interesting") == 1)

    by_mutation: dict[str, dict[str, int]] = {}
    by_error: dict[str, int] = {}
    timeline_map: dict[str, dict[str, int]] = {}

    for r in runs:
        mt = r.get("mutation_type") or "unknown"
        if mt not in by_mutation:
            by_mutation[mt] = {"valid": 0, "invalid": 0}
        if r.get("valid") == 1:
            by_mutation[mt]["valid"] += 1
        else:
            by_mutation[mt]["invalid"] += 1

        if r.get("valid") == 0 and r.get("error_type"):
            et = r["error_type"]
            by_error[et] = by_error.get(et, 0) + 1

        created = r.get("created_at") or ""
        date_key = created[:10] if len(created) >= 10 else "unknown"
        if date_key not in timeline_map:
            timeline_map[date_key] = {"valid": 0, "invalid": 0}
        if r.get("valid") == 1:
            timeline_map[date_key]["valid"] += 1
        else:
            timeline_map[date_key]["invalid"] += 1

    sorted_dates = sorted(
        d for d in timeline_map.keys() if d != "unknown"
    )
    if len(sorted_dates) > 14:
        sorted_dates = sorted_dates[-14:]

    timeline = [
        {
            "date": d,
            "valid": timeline_map[d]["valid"],
            "invalid": timeline_map[d]["invalid"],
        }
        for d in sorted_dates
    ]

    valid_pct = (valid / total * 100.0) if total else 0.0
    mismatch_pct = (mismatch / valid * 100.0) if valid else 0.0

    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "match": match,
        "mismatch": mismatch,
        "interesting": interesting,
        "by_mutation": by_mutation,
        "by_error": by_error,
        "timeline": timeline,
        "valid_pct": round(valid_pct, 1),
        "mismatch_pct": round(mismatch_pct, 1),
    }
