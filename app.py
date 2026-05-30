"""Flask application for LLVM IR differential compiler testing."""

import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from db import (
    classify_error,
    get_all_runs,
    get_analysis_stats,
    get_run,
    init_db,
    insert_run,
)
from llvm_utils import generate_ir, run_differential, verify_ir
from mutation_prompts import MUTATION_TYPES, get_prompt

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("instance", exist_ok=True)


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/")
def index():
    return render_template(
        "index.html", mutation_types=MUTATION_TYPES
    )


@app.route("/analysis")
def analysis():
    return render_template("analysis.html")


@app.route("/research")
def research():
    return render_template("research.html")


@app.route("/mutation")
def mutation():
    return render_template("mutation.html")


@app.route("/api/generate-ir", methods=["POST"])
def api_generate_ir():
    if "c_file" not in request.files:
        return jsonify(
            {"success": False, "ir": "", "error": "No file uploaded"}
        ), 400

    f = request.files["c_file"]
    if not f.filename:
        return jsonify(
            {"success": False, "ir": "", "error": "Empty filename"}
        ), 400

    if not f.filename.lower().endswith(".c"):
        return jsonify(
            {
                "success": False,
                "ir": "",
                "error": "File must have .c extension",
            }
        ), 400

    uid = str(uuid.uuid4())
    filepath = os.path.join(UPLOAD_FOLDER, f"{uid}.c")
    f.save(filepath)

    result = generate_ir(filepath)
    if result["success"]:
        return jsonify(
            {
                "success": True,
                "ir": result["output"],
                "error": "",
                "source_filename": f.filename,
            }
        )
    return jsonify(
        {
            "success": False,
            "ir": "",
            "error": result.get("error", "IR generation failed"),
        }
    )


@app.route("/api/get-prompt", methods=["POST", "OPTIONS"])
def api_get_prompt():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    ir_text = data.get("ir", "")
    mutation_type = data.get("mutation_type", "")

    if not ir_text:
        return jsonify(
            {"success": False, "prompt": "", "error": "IR text required"}
        ), 400

    if mutation_type not in MUTATION_TYPES:
        return jsonify(
            {
                "success": False,
                "prompt": "",
                "error": f"Invalid mutation type: {mutation_type}",
            }
        ), 400

    try:
        prompt = get_prompt(mutation_type, ir_text)
        return jsonify({"success": True, "prompt": prompt, "error": ""})
    except ValueError as e:
        return jsonify(
            {"success": False, "prompt": "", "error": str(e)}
        ), 400


@app.route("/api/validate-and-test", methods=["POST", "OPTIONS"])
def api_validate_and_test():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    mutated_ir = data.get("mutated_ir", "")
    seed_ir = data.get("seed_ir", "")
    mutation_type = data.get("mutation_type", "")
    source_filename = data.get("source_filename", "unknown.c")

    if not mutated_ir.strip():
        return jsonify(
            {
                "success": False,
                "error": "Mutated IR is required",
            }
        ), 400

    verify_result = verify_ir(mutated_ir)
    created_at = datetime.now(timezone.utc).isoformat()

    if not verify_result["success"]:
        error_detail = verify_result.get("error", "")
        error_type = classify_error(error_detail)
        run_data = {
            "created_at": created_at,
            "source_filename": source_filename,
            "seed_ir": seed_ir,
            "mutation_type": mutation_type,
            "mutated_ir": mutated_ir,
            "valid": 0,
            "error_type": error_type,
            "error_detail": error_detail,
            "o0_output": None,
            "o3_output": None,
            "o0_exit": None,
            "o3_exit": None,
            "diff_match": None,
            "is_interesting": 0,
        }
        run_id = insert_run(run_data)
        return jsonify(
            {
                "success": True,
                "run_id": run_id,
                "valid": False,
                "error_type": error_type,
                "error_detail": error_detail,
                "diff_match": None,
                "is_interesting": False,
                "o0_output": "",
                "o3_output": "",
                "o0_exit": None,
                "o3_exit": None,
            }
        )

    diff = run_differential(mutated_ir)
    o0_output = diff.get("o0_output") or ""
    o3_output = diff.get("o3_output") or ""
    o0_exit = diff.get("o0_exit", 0)
    o3_exit = diff.get("o3_exit", 0)
    match = diff.get("match", False)
    is_interesting = 1 if not match else 0

    run_data = {
        "created_at": created_at,
        "source_filename": source_filename,
        "seed_ir": seed_ir,
        "mutation_type": mutation_type,
        "mutated_ir": mutated_ir,
        "valid": 1,
        "error_type": None,
        "error_detail": None,
        "o0_output": o0_output,
        "o3_output": o3_output,
        "o0_exit": o0_exit,
        "o3_exit": o3_exit,
        "diff_match": 1 if match else 0,
        "is_interesting": is_interesting,
    }
    run_id = insert_run(run_data)

    return jsonify(
        {
            "success": True,
            "run_id": run_id,
            "valid": True,
            "error_type": None,
            "error_detail": None,
            "diff_match": match,
            "is_interesting": bool(is_interesting),
            "o0_output": o0_output,
            "o3_output": o3_output,
            "o0_exit": o0_exit,
            "o3_exit": o3_exit,
            "diff_error": diff.get("error"),
        }
    )


@app.route("/api/runs", methods=["GET"])
def api_runs():
    runs = get_all_runs()
    return jsonify({"success": True, "runs": runs})


@app.route("/api/run/<int:run_id>", methods=["GET"])
def api_run(run_id: int):
    run = get_run(run_id)
    if not run:
        return jsonify(
            {"success": False, "error": "Run not found"}
        ), 404
    return jsonify({"success": True, "run": run})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    stats = get_analysis_stats()
    return jsonify({"success": True, "stats": stats})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
