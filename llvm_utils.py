"""LLVM toolchain subprocess wrappers."""

import os
import subprocess
import tempfile


def _run_cmd(cmd: list[str], timeout: int = 30) -> dict:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stderr = result.stderr or ""
        stdout = result.stdout or ""
        if result.returncode != 0:
            return {
                "success": False,
                "output": stdout,
                "error": stderr or f"Command failed with exit code {result.returncode}",
                "exit_code": result.returncode,
            }
        return {
            "success": True,
            "output": stdout,
            "error": "",
            "exit_code": result.returncode,
        }
    except FileNotFoundError:
        tool = cmd[0] if cmd else "LLVM tool"
        return {
            "success": False,
            "output": "",
            "error": (
                f"{tool} not found. Install LLVM toolchain and ensure it is on PATH. "
                "Ubuntu: sudo apt install clang llvm | macOS: brew install llvm"
            ),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "TIMEOUT",
        }


def generate_ir(c_filepath: str) -> dict:
    tmp_ll = None
    try:
        fd, tmp_ll = tempfile.mkstemp(suffix=".ll")
        os.close(fd)
        cmd = [
            "clang",
            "-S",
            "-emit-llvm",
            "-O0",
            "-o",
            tmp_ll,
            c_filepath,
        ]
        result = _run_cmd(cmd)
        if not result["success"]:
            return result
        with open(tmp_ll, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "output": content, "error": ""}
    except OSError as e:
        return {"success": False, "output": "", "error": str(e)}
    finally:
        if tmp_ll and os.path.exists(tmp_ll):
            os.unlink(tmp_ll)


def verify_ir(ir_text: str) -> dict:
    tmp_ll = None
    try:
        fd, tmp_ll = tempfile.mkstemp(suffix=".ll")
        os.close(fd)
        with open(tmp_ll, "w", encoding="utf-8") as f:
            f.write(ir_text)

        errors = []
        llvm_as = _run_cmd(["llvm-as", tmp_ll, "-o", os.devnull])
        if not llvm_as["success"]:
            errors.append(llvm_as.get("error", ""))

        # Legacy: opt --verify (LLVM <= 16). New PM (LLVM 17+): -passes=verify
        opt_verify = _run_cmd(
            ["opt", "--verify", tmp_ll, "-o", os.devnull]
        )
        if not opt_verify["success"] and "new pass manager" in (
            opt_verify.get("error", "").lower()
        ):
            opt_verify = _run_cmd(
                ["opt", "-disable-output", "-passes=verify", tmp_ll]
            )
        if not opt_verify["success"]:
            errors.append(opt_verify.get("error", ""))

        if errors:
            combined = "\n".join(e for e in errors if e)
            return {"success": False, "output": "", "error": combined}
        return {"success": True, "output": "", "error": ""}
    except OSError as e:
        return {"success": False, "output": "", "error": str(e)}
    finally:
        if tmp_ll and os.path.exists(tmp_ll):
            os.unlink(tmp_ll)


def compile_and_run(ir_text: str, opt_level: str) -> dict:
    tmp_ll = None
    tmp_bc = None
    try:
        fd, tmp_ll = tempfile.mkstemp(suffix=".ll")
        os.close(fd)
        with open(tmp_ll, "w", encoding="utf-8") as f:
            f.write(ir_text)

        fd_bc, tmp_bc = tempfile.mkstemp(suffix=".bc")
        os.close(fd_bc)

        opt_result = _run_cmd(
            ["opt", opt_level, tmp_ll, "-o", tmp_bc], timeout=30
        )
        if not opt_result["success"]:
            return {
                "success": False,
                "output": "",
                "error": opt_result.get("error", "opt failed"),
                "exit_code": -1,
            }

        try:
            lli_result = subprocess.run(
                ["lli", tmp_bc],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "success": lli_result.returncode == 0,
                "output": lli_result.stdout or "",
                "error": lli_result.stderr or "",
                "exit_code": lli_result.returncode,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "error": (
                    "lli not found. Install LLVM toolchain and ensure it is on PATH."
                ),
                "exit_code": -1,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "TIMEOUT",
                "exit_code": -1,
            }
    except OSError as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "exit_code": -1,
        }
    finally:
        for path in (tmp_ll, tmp_bc):
            if path and os.path.exists(path):
                os.unlink(path)


def run_differential(ir_text: str) -> dict:
    o0 = compile_and_run(ir_text, "-O0")
    o3 = compile_and_run(ir_text, "-O3")

    if not o0["success"] and o0.get("error"):
        return {
            "o0_output": o0.get("output", "") or "",
            "o0_exit": o0.get("exit_code", -1),
            "o3_output": "",
            "o3_exit": -1,
            "match": False,
            "error": f"O0: {o0.get('error', '')}",
        }
    if not o3["success"] and o3.get("error"):
        return {
            "o0_output": o0.get("output", "") or "",
            "o0_exit": o0.get("exit_code", 0),
            "o3_output": o3.get("output", "") or "",
            "o3_exit": o3.get("exit_code", -1),
            "match": False,
            "error": f"O3: {o3.get('error', '')}",
        }

    o0_out = o0.get("output", "") or ""
    o3_out = o3.get("output", "") or ""
    o0_exit = o0.get("exit_code", 0)
    o3_exit = o3.get("exit_code", 0)
    match = o0_out == o3_out and o0_exit == o3_exit

    return {
        "o0_output": o0_out,
        "o0_exit": o0_exit,
        "o3_output": o3_out,
        "o3_exit": o3_exit,
        "match": match,
        "error": None,
    }
