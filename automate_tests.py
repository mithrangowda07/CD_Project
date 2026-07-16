#!/usr/bin/env python3
"""
Automate LLVM DiffTester runs against a running Flask app.

For one .c file, iterates all mutation types: generate prompt (Flask),
mutate IR (Gemini API), verify + differential test (Flask). Results land
in the same SQLite DB as the web UI (history + Analysis).

Usage:
  export GEMINI_API_KEY=your_key
  python app.py   # in another terminal
  python automate_tests.py path/to/program.c

Environment:
  GEMINI_API_KEY or GOOGLE_API_KEY  — required
  GEMINI_MODEL                      — default: gemini-2.5-flash
  DIFFTESTER_URL                    — default: http://127.0.0.1:5000
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

# Same mutation keys as the Flask app
MUTATION_TYPES = (
    "add_arithmetic",
    "change_types",
    "insert_branch",
    "insert_phi",
    "dead_code",
    "swap_operands",
)

DEFAULT_BASE_URL = "http://127.0.0.1:5000"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-001"
GEMINI_API_BASE = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit(
            "Error: set GEMINI_API_KEY or GOOGLE_API_KEY in the environment."
        )
    return key


def _request_json(
    method: str,
    url: str,
    payload: dict | None = None,
    timeout: float = 120,
) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {url}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot reach {url}: {e.reason}") from e


def check_flask_app(base_url: str) -> None:
    url = f"{base_url.rstrip('/')}/api/stats"
    try:
        data = _request_json("GET", url, timeout=10)
    except RuntimeError as e:
        sys.exit(
            f"Flask app not reachable at {base_url}.\n"
            f"  {e}\n"
            "Start it with: python app.py"
        )
    if not data.get("success"):
        sys.exit(f"Unexpected response from {url}: {data}")


def post_generate_ir(base_url: str, c_path: Path) -> dict:
    boundary = f"----DiffTester{uuid.uuid4().hex}"
    filename = c_path.name
    file_bytes = c_path.read_bytes()

    parts = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="c_file"; '
            f'filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8"),
        file_bytes,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)

    url = f"{base_url.rstrip('/')}/api/generate-ir"
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"generate-ir failed ({e.code}): {body_text}") from e


def post_get_prompt(base_url: str, ir: str, mutation_type: str) -> str:
    url = f"{base_url.rstrip('/')}/api/get-prompt"
    data = _request_json(
        "POST",
        url,
        {"ir": ir, "mutation_type": mutation_type},
    )
    if not data.get("success"):
        raise RuntimeError(
            data.get("error") or f"get-prompt failed for {mutation_type}"
        )
    return data["prompt"]


def call_gemini(prompt: str, model: str, api_key: str) -> str:
    url = (
        f"{GEMINI_API_BASE}/{model}:generateContent"
        f"?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API error ({e.code}): {err}") from e

    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(
            f"Unexpected Gemini response: {json.dumps(result)[:500]}"
        ) from e


def strip_ir_from_llm_response(text: str) -> str:
    """Remove markdown fences and leading commentary; keep raw IR."""
    text = text.strip()
    fence = re.match(
        r"^```(?:llvm|ll)?\s*\n?(.*?)\n?```\s*$",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if fence:
        text = fence.group(1).strip()
    else:
        text = re.sub(r"^```(?:llvm|ll)?\s*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```\s*$", "", text)
    # If model added prose before IR, try from first LLVM-ish line
    if not text.lstrip().startswith(";") and "define " not in text[:200]:
        for i, line in enumerate(text.splitlines()):
            if line.strip().startswith(";") or line.strip().startswith(
                "define "
            ):
                text = "\n".join(text.splitlines()[i:])
                break
    return text.strip()


def post_validate_and_test(
    base_url: str,
    *,
    mutated_ir: str,
    seed_ir: str,
    mutation_type: str,
    source_filename: str,
) -> dict:
    url = f"{base_url.rstrip('/')}/api/validate-and-test"
    return _request_json(
        "POST",
        url,
        {
            "mutated_ir": mutated_ir,
            "seed_ir": seed_ir,
            "mutation_type": mutation_type,
            "source_filename": source_filename,
        },
        timeout=120,
    )


def run_one_mutation(
    base_url: str,
    *,
    seed_ir: str,
    source_filename: str,
    mutation_type: str,
    gemini_model: str,
    api_key: str,
    delay_seconds: float,
) -> dict:
    print(f"\n--- {mutation_type} ---")
    print("  Generating prompt (Flask)...")
    prompt = post_get_prompt(base_url, seed_ir, mutation_type)

    if delay_seconds > 0:
        time.sleep(delay_seconds)

    print(f"  Calling Gemini ({gemini_model})...")
    raw = call_gemini(prompt, gemini_model, api_key)
    mutated_ir = strip_ir_from_llm_response(raw)
    if not mutated_ir:
        raise RuntimeError("Gemini returned empty IR")

    print("  Validate & differential test (Flask)...")
    result = post_validate_and_test(
        base_url,
        mutated_ir=mutated_ir,
        seed_ir=seed_ir,
        mutation_type=mutation_type,
        source_filename=source_filename,
    )
    if not result.get("success"):
        raise RuntimeError(
            result.get("error") or "validate-and-test failed"
        )
    return result


def print_summary(results: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for row in results:
        mt = row["mutation_type"]
        if row.get("error"):
            print(f"  {mt}: ERROR — {row['error']}")
            continue
        r = row["result"]
        run_id = r.get("run_id", "?")
        if r.get("valid"):
            match = r.get("diff_match")
            interesting = r.get("is_interesting")
            print(
                f"  {mt}: run #{run_id} VALID  "
                f"match={match}  interesting={interesting}"
            )
        else:
            print(
                f"  {mt}: run #{run_id} INVALID  "
                f"error_type={r.get('error_type')}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run all LLVM DiffTester mutation types for a .c file "
            "via Flask + Gemini."
        )
    )
    parser.add_argument(
        "c_file",
        type=Path,
        help="Path to the .c source file",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("DIFFTESTER_URL", DEFAULT_BASE_URL),
        help=f"Flask base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        help=f"Gemini model id (default: {DEFAULT_GEMINI_MODEL})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=float(os.environ.get("GEMINI_DELAY_SECONDS", "1.0")),
        help="Seconds to wait between Gemini calls (rate limits)",
    )
    parser.add_argument(
        "--mutations",
        nargs="*",
        choices=MUTATION_TYPES,
        default=None,
        help="Subset of mutation types (default: all six)",
    )
    args = parser.parse_args()

    c_path = args.c_file.resolve()
    if not c_path.is_file():
        sys.exit(f"File not found: {c_path}")
    if c_path.suffix.lower() != ".c":
        sys.exit("Input must be a .c file")

    base_url = args.url.rstrip("/")
    api_key = _api_key()
    mutations = args.mutations or list(MUTATION_TYPES)

    print(f"C file:    {c_path}")
    print(f"Flask:     {base_url}")
    print(f"Gemini:    {args.model}")
    print(f"Mutations: {', '.join(mutations)}")

    check_flask_app(base_url)

    print("\nUploading C file and generating seed IR (Flask)...")
    gen = post_generate_ir(base_url, c_path)
    if not gen.get("success"):
        sys.exit(f"generate-ir failed: {gen.get('error', gen)}")

    seed_ir = gen["ir"]
    source_filename = gen.get("source_filename") or c_path.name
    print(f"  Seed IR: {len(seed_ir)} bytes from {source_filename}")

    results: list[dict] = []
    for mutation_type in mutations:
        try:
            result = run_one_mutation(
                base_url,
                seed_ir=seed_ir,
                source_filename=source_filename,
                mutation_type=mutation_type,
                gemini_model=args.model,
                api_key=api_key,
                delay_seconds=args.delay,
            )
            results.append(
                {"mutation_type": mutation_type, "result": result, "error": None}
            )
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append(
                {"mutation_type": mutation_type, "result": None, "error": str(e)}
            )

    print_summary(results)

    try:
        stats = _request_json("GET", f"{base_url}/api/stats")
        if stats.get("success"):
            s = stats["stats"]
            print(
                f"\nDB totals: {s['total']} runs, "
                f"{s['valid']} valid, {s['interesting']} interesting"
            )
            print(f"View Analysis: {base_url}/analysis")
    except RuntimeError:
        pass

    failed = sum(1 for r in results if r.get("error"))
    sys.exit(1 if failed == len(results) else 0)


if __name__ == "__main__":
    main()
