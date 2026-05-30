#!/usr/bin/env python3
"""SGH-Q23 full Sparrow parity cutover smoke.

Exercises the *production* Sparrow path `optimizer_pipeline = "sparrow_cde"`,
which is CDE-first by contract (forces the CDE geometry backend, forbids
LBF/finite-candidate fallback, never falls back to a legacy solver).

Canvas-mandated fixtures:
  1.  tiny_cde_must_converge
  2.  overlap_two_rects_cde_must_separate
  3.  boundary_recovery_cde_must_recover
  4.  continuous_rotation_rescue_cde
  5.  medium_10_to_20_items_cde_must_not_timeout
  6.  medium_10_to_20_items_cde_must_converge_or_document_partial_by_contract
  7.  production_sparrow_uses_backend_oracle_evaluation
  8.  production_sparrow_no_legacy_fallback
  9.  production_sparrow_preserves_full_diagnostics_on_failure
  10. legacy_pipeline_requires_explicit_opt_in

Honesty contract (matches run.md / canvas):
  * No CDE failure is skipped. A fixture either asserts convergence, or is
    explicitly a "document partial / not timeout / diagnostics" gate.
  * "must_not_timeout" means the solver returns within a wall-clock bound — it
    is allowed to return `unsupported`/`partial`, it just may not hang.
  * The medium CDE convergence gap (Q22R1) is documented, not faked: fixture 6
    accepts a well-defined `unsupported` outcome ONLY if full diagnostics are
    preserved.
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BINARY = Path(__file__).parent.parent / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
PROFILE = "jagua_optimizer_phase1_outer_only"

PASS_COUNT = 0
FAIL_COUNT = 0
ROWS = []


def _log(label: str, msg: str):
    print(f"  [{label}] {msg}")


def check(cond: bool, msg: str):
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        _log("PASS", msg)
    else:
        FAIL_COUNT += 1
        _log("FAIL", msg)


def run_solver(input_dict: dict) -> tuple[dict, float]:
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "in.json"
        out_path = Path(tmpdir) / "out.json"
        in_path.write_text(json.dumps(input_dict))
        t0 = time.perf_counter()
        result = subprocess.run(
            [str(BINARY), "--input", str(in_path), "--output", str(out_path)],
            capture_output=True, text=True,
        )
        runtime_ms = (time.perf_counter() - t0) * 1000.0
        if result.returncode != 0:
            print(f"  [ERROR] solver exited {result.returncode}: {result.stderr[:300]}")
            return ({}, runtime_ms)
        return (json.loads(out_path.read_text()), runtime_ms)


def base_input(parts, stocks, pipeline="sparrow_cde", backend=None, seed=0,
               rotation="orthogonal", time_limit=5) -> dict:
    inp = {
        "contract_version": "v1",
        "project_name": "q23_sparrow_cutover_smoke",
        "seed": seed,
        "time_limit_s": time_limit,
        "solver_profile": PROFILE,
        "rotation_policy": rotation,
        "stocks": stocks,
        "parts": parts,
    }
    if pipeline is not None:
        inp["optimizer_pipeline"] = pipeline
    if backend:
        inp["collision_backend"] = backend
    return inp


def record(name: str, out: dict, runtime_ms: float):
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    init_raw = od.get("sparrow_initial_raw_loss")
    final_raw = od.get("sparrow_final_raw_loss")
    loss_red = "n/a"
    if init_raw and init_raw > 0:
        loss_red = f"{(init_raw - (final_raw or 0)) / init_raw * 100:.0f}%"
    ROWS.append({
        "fixture": name,
        "status": out.get("status", "?"),
        "runtime_ms": int(runtime_ms),
        "pipeline_used": od.get("pipeline_used"),
        "converged": od.get("sparrow_converged"),
        "iterations": od.get("sparrow_iterations"),
        "moves_attempted": od.get("sparrow_moves_attempted"),
        "moves_accepted": od.get("sparrow_moves_accepted"),
        "rollbacks": od.get("sparrow_rollbacks"),
        "pairs_init": od.get("sparrow_collision_graph_initial_pairs"),
        "pairs_final": od.get("sparrow_collision_graph_final_pairs"),
        "initial_raw": init_raw,
        "final_raw": final_raw,
        "loss_reduction": loss_red,
        "backend_used": cbd.get("backend_used"),
        "cde_total_queries": cbd.get("cde_total_queries"),
        "cde_engine_builds": cbd.get("cde_engine_builds"),
        "cde_broadphase_pruned": cbd.get("cde_broadphase_pruned"),
        "bbox_fallback_queries": cbd.get("bbox_fallback_queries"),
        "lbf_fallback_used": od.get("search_position_lbf_fallback_used"),
    })


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def f1_tiny_cde_must_converge():
    print("\n=== 1. tiny_cde_must_converge ===")
    stocks = [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}]
    parts = [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 2}]
    out, ms = run_solver(base_input(parts, stocks, seed=1, time_limit=5))
    record("tiny_cde_must_converge", out, ms)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    check(od.get("pipeline_used") == "sparrow_cde", f"pipeline_used==sparrow_cde (got {od.get('pipeline_used')})")
    check(od.get("sparrow_converged") is True, f"must converge (got {od.get('sparrow_converged')})")
    check(cbd.get("backend_used") == "cde_adapter", f"CDE backend (got {cbd.get('backend_used')})")
    check(cbd.get("bbox_fallback_queries") == 0, "no bbox fallback")


def f2_overlap_two_rects_cde_must_separate():
    print("\n=== 2. overlap_two_rects_cde_must_separate ===")
    stocks = [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}]
    parts = [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 2}]
    out, ms = run_solver(base_input(parts, stocks, seed=2, time_limit=5))
    record("overlap_two_rects_cde_must_separate", out, ms)
    od = out.get("optimizer_diagnostics") or {}
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    check(od.get("sparrow_converged") is True, f"two-rect overlap must separate (got {od.get('sparrow_converged')})")
    check((od.get("sparrow_collision_graph_final_pairs") or 0) == 0, "final colliding pairs == 0")


def f3_boundary_recovery_cde_must_recover():
    """The adapter seed places a single fitting item at (0,0), which is inside
    the boundary — so this exercises the already-feasible boundary path under
    CDE. True out-of-sheet recovery is unit-tested in
    `optimizer::sparrow::tests::sparrow_kernel_boundary_recovery`."""
    print("\n=== 3. boundary_recovery_cde_must_recover ===")
    stocks = [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}]
    parts = [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 1}]
    out, ms = run_solver(base_input(parts, stocks, seed=3, time_limit=5))
    record("boundary_recovery_cde_must_recover", out, ms)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    check(od.get("sparrow_converged") is True, "item must be within boundary (feasible)")
    check((od.get("sparrow_boundary_violations_final") or 0) == 0, "final boundary violations == 0")
    check(cbd.get("backend_used") == "cde_adapter", "boundary validity from CDE backend")


def f4_continuous_rotation_rescue_cde():
    print("\n=== 4. continuous_rotation_rescue_cde ===")
    stocks = [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}]
    parts = [{"id": "P", "width": 80.0, "height": 30.0, "quantity": 2}]
    out, ms = run_solver(base_input(parts, stocks, seed=4, rotation="continuous", time_limit=6))
    record("continuous_rotation_rescue_cde", out, ms)
    od = out.get("optimizer_diagnostics") or {}
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    check(od.get("sparrow_converged") is True,
          f"continuous rotation must rescue 2×80×30 on 100×100 under CDE (got {od.get('sparrow_converged')})")


def f5_medium_cde_must_not_timeout():
    """Wall-clock bound gate: the production path must always RETURN under the
    cap (no hang), even if the result is `unsupported`/`partial`. The kernel's
    time/iteration budgets guarantee termination; this verifies it empirically."""
    print("\n=== 5. medium_10_to_20_items_cde_must_not_timeout ===")
    wall_cap_s = 30.0
    stocks = [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}]
    parts = [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}]
    out, ms = run_solver(base_input(parts, stocks, seed=5, time_limit=8))
    record("medium_10_to_20_items_cde_must_not_timeout", out, ms)
    check(ms < wall_cap_s * 1000.0,
          f"production path returned under {wall_cap_s:.0f}s wall cap (got {ms/1000:.1f}s)")
    check(out.get("status") in ("ok", "partial", "unsupported"),
          f"status well-defined (got {out.get('status')})")


def f6_medium_cde_converge_or_document_partial():
    """Convergence OR a well-defined partial/unsupported by contract. If the
    medium CDE fixture cannot converge under the quick cap (documented Q22R1 /
    Q23 cutover gap), the `unsupported` output MUST preserve full diagnostics."""
    print("\n=== 6. medium_10_to_20_items_cde_must_converge_or_document_partial_by_contract ===")
    stocks = [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}]
    parts = [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}]
    out, ms = run_solver(base_input(parts, stocks, seed=6, time_limit=8))
    record("medium_cde_converge_or_document_partial", out, ms)
    status = out.get("status")
    od = out.get("optimizer_diagnostics")
    check(status in ("ok", "partial", "unsupported"), f"status well-defined (got {status})")
    if status == "ok":
        check((od or {}).get("sparrow_converged") is True, "ok implies converged")
    else:
        # documented partial / unsupported by contract: diagnostics MUST survive
        check(od is not None, "documented partial MUST preserve optimizer_diagnostics")
        if od:
            check(od.get("pipeline_used") == "sparrow_cde", "pipeline_used==sparrow_cde")
            check(od.get("sparrow_invoked") is True, "sparrow_invoked true")
            check((od.get("sparrow_iterations") or 0) > 0, "iterations > 0")
            check(od.get("sparrow_initial_raw_loss") is not None, "initial_raw_loss present")
            check(od.get("sparrow_best_infeasible_raw_loss") is not None, "best_infeasible_raw_loss present")


def f7_production_sparrow_uses_backend_oracle_evaluation():
    print("\n=== 7. production_sparrow_uses_backend_oracle_evaluation ===")
    stocks = [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}]
    parts = [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 2}]
    out, ms = run_solver(base_input(parts, stocks, seed=7, time_limit=5))
    record("production_sparrow_uses_backend_oracle_evaluation", out, ms)
    cbd = out.get("collision_backend_diagnostics") or {}
    check(cbd.get("backend_used") == "cde_adapter", f"oracle backend is CDE (got {cbd.get('backend_used')})")
    check((cbd.get("cde_total_queries") or 0) > 0,
          f"CDE oracle queries dispatched (got {cbd.get('cde_total_queries')})")
    # Q23 query-reduction evidence: broad-phase counter surfaced (>= 0).
    check(cbd.get("cde_broadphase_pruned") is not None, "broad-phase prune counter surfaced")


def f8_production_sparrow_no_legacy_fallback():
    print("\n=== 8. production_sparrow_no_legacy_fallback ===")
    stocks = [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}]
    parts = [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 2}]
    out, ms = run_solver(base_input(parts, stocks, seed=8, time_limit=5))
    record("production_sparrow_no_legacy_fallback", out, ms)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(od.get("pipeline_used") == "sparrow_cde", f"pipeline_used==sparrow_cde (got {od.get('pipeline_used')})")
    check(od.get("phase_optimizer_invoked") is False, "phase_optimizer must NOT be invoked")
    check((od.get("search_position_lbf_fallback_used") or 0) == 0, "no LBF/finite-candidate fallback")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "no bbox fallback")


def f9_production_sparrow_preserves_full_diagnostics_on_failure():
    print("\n=== 9. production_sparrow_preserves_full_diagnostics_on_failure ===")
    # 5×50×50 on a single 100×100 sheet: only 4 fit → never converges.
    stocks = [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}]
    parts = [{"id": "P", "width": 50.0, "height": 50.0, "quantity": 5}]
    out, ms = run_solver(base_input(parts, stocks, seed=9, time_limit=5))
    record("production_sparrow_preserves_full_diagnostics_on_failure", out, ms)
    check(out.get("status") == "unsupported", f"impossible fixture → unsupported (got {out.get('status')})")
    check(out.get("unsupported_reason") == "SPARROW_NO_FEASIBLE_LAYOUT",
          f"reason SPARROW_NO_FEASIBLE_LAYOUT (got {out.get('unsupported_reason')})")
    od = out.get("optimizer_diagnostics")
    cbd = out.get("collision_backend_diagnostics")
    check(od is not None, "optimizer_diagnostics preserved on failure")
    check(cbd is not None, "collision_backend_diagnostics preserved on failure")
    if od:
        check(od.get("pipeline_used") == "sparrow_cde", "pipeline_used==sparrow_cde on failure")
        check(od.get("sparrow_converged") is False, "converged==false on failure")
        check((od.get("sparrow_iterations") or 0) > 0, "iterations recorded on failure")
    if cbd:
        check(cbd.get("backend_used") == "cde_adapter", "CDE backend recorded on failure")


def f10_legacy_pipeline_requires_explicit_opt_in():
    print("\n=== 10. legacy_pipeline_requires_explicit_opt_in ===")
    stocks = [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}]
    parts = [{"id": "P", "width": 40.0, "height": 20.0, "quantity": 3}]
    # No optimizer_pipeline field → default must be legacy_multisheet (NOT sparrow).
    out_default, ms = run_solver(base_input(parts, stocks, pipeline=None, seed=10, time_limit=4))
    record("legacy_pipeline_default_is_legacy", out_default, ms)
    od_default = out_default.get("optimizer_diagnostics")
    # legacy_multisheet emits no optimizer_diagnostics (or not sparrow_cde).
    check(od_default is None or od_default.get("pipeline_used") != "sparrow_cde",
          "default pipeline is NOT sparrow_cde (legacy requires opt-in)")
    # Explicit phase_optimizer opt-in works and is labelled phase_optimizer.
    out_phase, ms2 = run_solver(base_input(parts, stocks, pipeline="phase_optimizer", seed=10, time_limit=4))
    record("legacy_phase_optimizer_explicit_opt_in", out_phase, ms2)
    od_phase = out_phase.get("optimizer_diagnostics") or {}
    check(od_phase.get("pipeline_used") == "phase_optimizer",
          f"phase_optimizer only when explicitly requested (got {od_phase.get('pipeline_used')})")


# ---------------------------------------------------------------------------


def print_table():
    print()
    print("=" * 100)
    print("Measurement table")
    print("=" * 100)
    cols = ["fixture", "status", "runtime_ms", "pipeline_used", "converged",
            "iterations", "moves_attempted", "moves_accepted", "pairs_init",
            "pairs_final", "loss_reduction", "backend_used", "cde_total_queries",
            "cde_engine_builds", "cde_broadphase_pruned", "bbox_fallback_queries"]
    for r in ROWS:
        print(f"\n  --- {r['fixture']} ---")
        for c in cols:
            if c == "fixture":
                continue
            v = r.get(c)
            v = "-" if v is None else v   # only None renders as '-'
            print(f"  {c:28s} = {v}")


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)
    print("SGH-Q23 full Sparrow parity cutover smoke")
    print(f"Binary: {BINARY}")

    f1_tiny_cde_must_converge()
    f2_overlap_two_rects_cde_must_separate()
    f3_boundary_recovery_cde_must_recover()
    f4_continuous_rotation_rescue_cde()
    f5_medium_cde_must_not_timeout()
    f6_medium_cde_converge_or_document_partial()
    f7_production_sparrow_uses_backend_oracle_evaluation()
    f8_production_sparrow_no_legacy_fallback()
    f9_production_sparrow_preserves_full_diagnostics_on_failure()
    f10_legacy_pipeline_requires_explicit_opt_in()

    print_table()
    print()
    print("=" * 60)
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT > 0:
        print("SMOKE: FAIL")
        sys.exit(1)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
