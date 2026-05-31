#!/usr/bin/env python3
"""SGH-Q24R2 native Sparrow core port — small structural/functional smoke.

Per run.md this smoke is intentionally SMALL and structural. It confirms the new
native Sparrow lifecycle EXECUTES end-to-end on small fixed-sheet inputs via the
production `sparrow_cde` path (no legacy fallback). The native-lifecycle CODE
existence (separator strike loop, worker-master move_items_multi, worker
move_items over ALL colliding items, exploration pool + biased restore +
large-item disruption, compression restore/pressure/separate/accept) is proven by
the in-process Rust unit tests:

  optimizer::sparrow::tests::sparrow_q23r3_multi_target_and_incremental_graph_are_diagnosed
  optimizer::sparrow::tests::sparrow_q24r2_exploration_and_compression_lifecycle_are_diagnosed
  optimizer::sparrow::tests::sparrow_q24r2_exploration_pool_and_disruption_fire_on_infeasible

This is NOT an LV8 benchmark (LV8 convergence is explicitly not the Q24R2 gate).
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BINARY = Path(__file__).parent.parent / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
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


def run(inp, cap=60.0):
    with tempfile.TemporaryDirectory() as d:
        ip = Path(d) / "in.json"
        op = Path(d) / "out.json"
        ip.write_text(json.dumps(inp))
        t0 = time.perf_counter()
        try:
            r = subprocess.run([str(BINARY), "--input", str(ip), "--output", str(op)],
                               capture_output=True, text=True, timeout=cap)
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}, (time.perf_counter() - t0) * 1000.0
        if r.returncode != 0:
            return {"status": "error", "stderr": r.stderr[:200]}, (time.perf_counter() - t0) * 1000.0
        return json.loads(op.read_text()), (time.perf_counter() - t0) * 1000.0


def base(parts, stocks, seed=1, rot="orthogonal", tl=8, backend="cde", pipeline="sparrow_cde"):
    inp = {"contract_version": "v1", "project_name": "q24r2_smoke", "seed": seed,
           "time_limit_s": tl, "solver_profile": PROFILE, "rotation_policy": rot,
           "stocks": stocks, "parts": parts}
    if pipeline is not None:
        inp["optimizer_pipeline"] = pipeline
    if backend is not None:
        inp["collision_backend"] = backend
    return inp


def converge(name, parts, stocks, seed=1, rot="orthogonal"):
    print(f"\n=== {name} ===")
    out, ms = run(base(parts, stocks, seed=seed, rot=rot))
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(out.get("status") in ("ok", "partial"), f"status ok/partial ({out.get('status')}, {ms/1000:.1f}s)")
    check(od.get("pipeline_used") == "sparrow_cde", "pipeline_used==sparrow_cde (native lifecycle)")
    check(od.get("sparrow_converged") is True, f"converged ({od.get('sparrow_converged')})")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "no bbox fallback")
    check((od.get("search_position_lbf_fallback_used") or 0) == 0, "no LBF fallback")
    check(cbd.get("backend_used") == "cde_adapter", "CDE backend (no legacy fallback)")


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        sys.exit(1)
    print("SGH-Q24R2 native Sparrow core port smoke (small/structural)")

    # The native lifecycle must execute and converge these small CDE fixtures.
    converge("tiny_two_items_cde",
             [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 2}],
             [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}])
    converge("two_rect_overlap_cde",
             [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 2}],
             [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}], seed=2)

    # Medium (12 items) with the cheap bbox backend: the native lifecycle
    # (separator strike loop + worker-master + exploration + compression) must
    # execute and converge structurally. CDE convergence at this scale is the
    # deferred LV8-style perf gate, NOT a Q24R2 gate (run.md).
    # Same native lifecycle, cheap bbox backend (sparrow_cde forces CDE, so use
    # the sparrow_experimental pipeline which shares run_sparrow_pipeline).
    print("\n=== medium_10_to_20_items (sparrow_experimental + bbox, native lifecycle converges) ===")
    out, ms = run(base([{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
                       [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
                       seed=5, backend="bbox", pipeline="sparrow_experimental", tl=10))
    od = out.get("optimizer_diagnostics") or {}
    check(out.get("status") == "ok", f"medium bbox ok ({out.get('status')}, {ms/1000:.1f}s)")
    check((out.get("metrics") or {}).get("placed_count") == 12, "medium bbox 12/12")
    check(od.get("sparrow_converged") is True, "medium bbox converged via native lifecycle")

    # Medium CDE must EXECUTE within its time budget (no hang/overshoot), even if
    # it does not converge at this scale (deferred perf gate).
    print("\n=== medium_10_to_20_items (cde executes within budget) ===")
    out, ms = run(base([{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
                       [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
                       seed=5, backend="cde", tl=8), cap=30.0)
    check(out.get("status") != "timeout" and ms < 30_000,
          f"medium cde returns within budget (no hang): {out.get('status')}, {ms/1000:.1f}s")
    check(out.get("status") in ("ok", "partial", "unsupported"), "medium cde status well-defined")

    # Impossible fixture: the native lifecycle must run its exploration pool /
    # disruption attempts and then honestly return unsupported (no fallback).
    print("\n=== impossible_fixture_returns_unsupported_with_diagnostics ===")
    out, ms = run(base([{"id": "P", "width": 50.0, "height": 50.0, "quantity": 5}],
                        [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}], seed=9, tl=5))
    od = out.get("optimizer_diagnostics") or {}
    check(out.get("status") == "unsupported", f"impossible → unsupported ({out.get('status')})")
    check(od is not None and od.get("pipeline_used") == "sparrow_cde", "diagnostics preserved on failure")
    check(od.get("sparrow_converged") is False, "converged==false on failure")
    check((od.get("sparrow_iterations") or 0) > 0, "separator iterations recorded")

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        print("SMOKE: FAIL")
        sys.exit(1)
    print("SMOKE: PASS (native lifecycle executes; code existence proven by cargo unit tests)")


if __name__ == "__main__":
    main()
