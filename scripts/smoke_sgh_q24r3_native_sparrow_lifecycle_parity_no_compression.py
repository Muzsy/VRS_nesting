#!/usr/bin/env python3
"""SGH-Q24R3 native Sparrow lifecycle parity smoke.

This is a hard smoke for the production `sparrow_cde` path after Q24R3.
It intentionally does NOT test compression quality. Default production Q24R3
must solve the medium CDE fixture through native Sparrow-style seed + exploration
+ separation + search + CDE tracker/loss, with compression disabled/gated or zero
passes by default.
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
PROFILE = "jagua_optimizer_phase1_outer_only"

PASS = 0
FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def run_solver(inp, cap=60.0):
    with tempfile.TemporaryDirectory() as tmp:
        ip = Path(tmp) / "input.json"
        op = Path(tmp) / "output.json"
        ip.write_text(json.dumps(inp), encoding="utf-8")
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(BINARY), "--input", str(ip), "--output", str(op)],
                capture_output=True,
                text=True,
                timeout=cap,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}, (time.perf_counter() - t0) * 1000.0
        ms = (time.perf_counter() - t0) * 1000.0
        if proc.returncode != 0:
            return {
                "status": "error",
                "returncode": proc.returncode,
                "stderr": proc.stderr[-2000:],
                "stdout": proc.stdout[-2000:],
            }, ms
        return json.loads(op.read_text(encoding="utf-8")), ms


def base(parts, stocks, seed=5, tl=20, rotation="orthogonal"):
    return {
        "contract_version": "v1",
        "project_name": "q24r3_native_sparrow_lifecycle_parity_no_compression",
        "seed": seed,
        "time_limit_s": tl,
        "solver_profile": PROFILE,
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "bbox",  # production sparrow_cde must force CDE anyway
        "rotation_policy": rotation,
        "stocks": stocks,
        "parts": parts,
    }


def medium_cde_hard_gate():
    print("\n=== medium_10_to_20_items / sparrow_cde / forced CDE [HARD] ===")
    inp = base(
        parts=[{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        stocks=[{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        seed=5,
        tl=20,
    )
    out, ms = run_solver(inp, cap=90.0)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    metrics = out.get("metrics") or {}

    check(out.get("status") == "ok", f"status ok, got {out.get('status')} ({ms/1000:.1f}s)")
    check(metrics.get("placed_count") == 12, f"placed 12/12, got {metrics.get('placed_count')}")
    check(od.get("pipeline_used") == "sparrow_cde", "pipeline_used == sparrow_cde")
    check(od.get("sparrow_converged") is True, "sparrow_converged == true")
    check(od.get("sparrow_collision_graph_final_pairs") == 0, "final collision pairs == 0")
    check(od.get("sparrow_boundary_violations_final") == 0, "final boundary violations == 0")
    check(cbd.get("backend_used") == "cde_adapter", "CDE backend used even when bbox requested")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "no bbox fallback queries")
    check((od.get("search_position_lbf_fallback_used") or od.get("sparrow_lbf_fallback_used") or 0) == 0, "no LBF fallback")
    check((od.get("sparrow_search_position_calls") or 0) > 0, "search_position calls > 0")
    check((od.get("sparrow_search_position_samples") or 0) > 0, "search_position samples > 0")

    # Q24R3 requirement: default production path must not rely on compression.
    # It may expose either a new explicit flag or the old pass count. Accept both
    # forms, but do not allow positive default compression passes.
    compression_disabled = od.get("sparrow_compression_disabled") is True
    compression_zero = (od.get("sparrow_compression_passes") or 0) == 0
    check(compression_disabled or compression_zero, "compression disabled/gated or zero default passes")


def impossible_honest_failure_gate():
    print("\n=== impossible_fixture / honest unsupported / no fallback ===")
    inp = base(
        parts=[{"id": "P", "width": 50.0, "height": 50.0, "quantity": 5}],
        stocks=[{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
        seed=9,
        tl=8,
    )
    out, ms = run_solver(inp, cap=60.0)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(out.get("status") == "unsupported", f"impossible returns unsupported, got {out.get('status')} ({ms/1000:.1f}s)")
    check(od.get("pipeline_used") == "sparrow_cde", "diagnostics preserved with sparrow_cde label")
    check(od.get("sparrow_converged") is False, "sparrow_converged == false on impossible input")
    check(cbd.get("backend_used") == "cde_adapter", "CDE diagnostics preserved on unsupported")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "no bbox fallback on unsupported")


def tiny_cde_regression_gate():
    print("\n=== tiny_two_items / sparrow_cde / CDE regression ===")
    inp = base(
        parts=[{"id": "P", "width": 40.0, "height": 30.0, "quantity": 2}],
        stocks=[{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}],
        seed=2,
        tl=10,
    )
    out, ms = run_solver(inp, cap=45.0)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(out.get("status") == "ok", f"tiny status ok, got {out.get('status')} ({ms/1000:.1f}s)")
    check(od.get("pipeline_used") == "sparrow_cde", "tiny pipeline sparrow_cde")
    check(od.get("sparrow_converged") is True, "tiny converged")
    check(cbd.get("backend_used") == "cde_adapter", "tiny CDE backend used")


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)

    print("SGH-Q24R3 native Sparrow lifecycle parity smoke — compression excluded")
    tiny_cde_regression_gate()
    medium_cde_hard_gate()
    impossible_honest_failure_gate()

    print("\n" + "=" * 72)
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL:
        print("SMOKE: FAIL")
        sys.exit(1)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
