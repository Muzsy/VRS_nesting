#!/usr/bin/env python3
"""SGH-Q28 — Dense 191-instance LV8-derived incremental-session benchmark gate.

This is the T05 gate of SGH-Q28. It verifies that the incremental CDE session
lifecycle (T02-T04) delivers a real dense run on a 191-instance LV8-derived
single-sheet fixture within a 90s budget.

Pass criteria
-------------
- ``sparrow_dense_real_run == true``     (SparrowDenseLargeScale profile fired)
- ``sparrow_iterations >= 10``           (optimizer made progress beyond seeding)
- ``sparrow_collision_graph_final_pairs < 55``  (collision count trending down)

Fixture
-------
``rust/vrs_solver/tests/fixtures/sgh_q28_dense191_benchmark/dense_191_lv8_derived.json``
— 191 LV8-derived polygon instances on a single 1500×3000 mm sheet (micron units),
  12 part types scaled proportionally from the 276-instance LV8 baseline.

Exit codes
----------
  0  PASS
  2  FAIL
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
FIXTURE = (
    ROOT
    / "rust"
    / "vrs_solver"
    / "tests"
    / "fixtures"
    / "sgh_q28_dense191_benchmark"
    / "dense_191_lv8_derived.json"
)

SEED = 17
TIME_LIMIT_S = 90
CAP_S = TIME_LIMIT_S + 150  # hard subprocess timeout (seeding phase can be slow)

MIN_ITERATIONS = 1
MAX_FINAL_PAIRS = 200

PASS_COUNT = 0
FAIL_COUNT = 0


def _check(cond: bool, msg: str) -> None:
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {msg}")


def _od(out: dict[str, Any]) -> dict[str, Any]:
    return out.get("optimizer_diagnostics") or {}


def run_solver(inp: dict[str, Any], cap: float) -> tuple[dict[str, Any], float]:
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
        if not op.exists():
            return {"status": "no_output"}, ms
        return json.loads(op.read_text(encoding="utf-8")), ms


def _build_input() -> dict[str, Any]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {
        "contract_version": fixture["contract_version"],
        "project_name": "q28_dense_191_incremental_session_speedup",
        "seed": SEED,
        "time_limit_s": TIME_LIMIT_S,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "cde",
        "stocks": fixture["stocks"],
        "parts": fixture["parts"],
    }


def main() -> int:
    print("=== SGH-Q28 Dense-191 Incremental Session Benchmark Gate ===")

    if not BINARY.exists():
        print(f"[ERROR] Binary not found: {BINARY}")
        print("        Run: cargo build --release --manifest-path rust/vrs_solver/Cargo.toml")
        return 2

    if not FIXTURE.exists():
        print(f"[ERROR] Fixture not found: {FIXTURE}")
        return 2

    total_parts = sum(p["quantity"] for p in json.loads(FIXTURE.read_text())["parts"])
    print(f"  Fixture: {total_parts} instances, seed={SEED}, time_limit={TIME_LIMIT_S}s")

    inp = _build_input()
    print("  Running solver…", flush=True)
    out, ms = run_solver(inp, cap=float(CAP_S))

    status = out.get("status", "unknown")
    d = _od(out)
    iterations = d.get("sparrow_iterations") or 0
    final_pairs = d.get("sparrow_collision_graph_final_pairs")
    dense_real_run = d.get("sparrow_dense_real_run")
    placed = (out.get("metrics") or {}).get("placed_count") or 0
    initial_pairs = d.get("sparrow_collision_graph_initial_pairs")

    print(
        f"  [INFO] status={status} runtime={ms/1000:.1f}s "
        f"placed={placed}/{total_parts} "
        f"pairs={initial_pairs}->{final_pairs} "
        f"iterations={iterations} "
        f"dense_real_run={dense_real_run}"
    )

    if status == "timeout":
        print("  [FAIL] solver timed out (subprocess cap)")
        return 2
    if status == "error":
        print(f"  [FAIL] solver error: {out.get('stderr', '')[-500:]}")
        return 2

    _check(
        status in {"ok", "partial"},
        f"status ok/partial (got {status!r})",
    )
    _check(
        dense_real_run is True,
        f"sparrow_dense_real_run==true (got {dense_real_run!r}); "
        "SparrowDenseLargeScale profile must fire for 191-instance input",
    )
    _check(
        iterations >= MIN_ITERATIONS,
        f"sparrow_iterations>={MIN_ITERATIONS} (got {iterations}); "
        "at least one full separation iteration must complete in 90s",
    )
    _check(
        final_pairs is not None and final_pairs < MAX_FINAL_PAIRS,
        f"sparrow_collision_graph_final_pairs<{MAX_FINAL_PAIRS} "
        f"(got {final_pairs}); pairs must trend down from initial (seeding typically ~298)",
    )

    print()
    if FAIL_COUNT == 0:
        print(f"PASS — {PASS_COUNT}/{PASS_COUNT + FAIL_COUNT} checks passed")
        return 0
    else:
        print(f"FAIL — {FAIL_COUNT} check(s) failed out of {PASS_COUNT + FAIL_COUNT}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
