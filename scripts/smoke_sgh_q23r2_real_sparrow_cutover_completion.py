#!/usr/bin/env python3
"""SGH-Q23R2 real Sparrow cutover completion smoke.

Exercises the production `sparrow_cde` path with the SGH-Q23R2 single-engine
multi-hazard candidate session (one CDEngine holds the sheet Exterior + all
same-sheet fixed items as Hole hazards; the candidate is queried once + a cheap
CDE-truth separation probe). This replaces N pairwise CDEngine builds.

HARD gates (fatal):
  tiny / two_rect / boundary / continuous converge under CDE
  backend oracle, no legacy/bbox/LBF fallback, full diagnostics on failure
  batch session metrics present and active (cde_batch_engine_builds > 0)
  engine-build reduction vs Q23 baseline 7650 meets the >=80% target
    (total builds = legacy cde_engine_builds + cde_batch_engine_builds)
  medium_10_to_20_items must converge 12/12, final pairs 0  [run.md §G]

Per run.md §G the medium convergence gate is HARD: this smoke exits non-zero if
medium does not converge. (Current honest status: NOT converged — see report.)
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BINARY = Path(__file__).parent.parent / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
PROFILE = "jagua_optimizer_phase1_outer_only"
Q23_ENGINE_BUILD_BASELINE = 7650

PASS_COUNT = 0
FAIL_COUNT = 0
ROWS = []


def _log(label, msg):
    print(f"  [{label}] {msg}")


def check(cond, msg):
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        _log("PASS", msg)
    else:
        FAIL_COUNT += 1
        _log("FAIL", msg)


def run_solver(input_dict, hard_timeout_s=40.0):
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "in.json"
        out_path = Path(tmpdir) / "out.json"
        in_path.write_text(json.dumps(input_dict))
        t0 = time.perf_counter()
        try:
            r = subprocess.run(
                [str(BINARY), "--input", str(in_path), "--output", str(out_path)],
                capture_output=True, text=True, timeout=hard_timeout_s,
            )
        except subprocess.TimeoutExpired:
            return ({"status": "timeout"}, (time.perf_counter() - t0) * 1000.0)
        ms = (time.perf_counter() - t0) * 1000.0
        if r.returncode != 0:
            print(f"  [ERROR] solver exit {r.returncode}: {r.stderr[:300]}")
            return ({"status": "error"}, ms)
        return (json.loads(out_path.read_text()), ms)


def base_input(parts, stocks, pipeline="sparrow_cde", backend=None, seed=0,
               rotation="orthogonal", time_limit=5):
    inp = {
        "contract_version": "v1", "project_name": "q23r2_smoke", "seed": seed,
        "time_limit_s": time_limit, "solver_profile": PROFILE,
        "rotation_policy": rotation, "stocks": stocks, "parts": parts,
    }
    if pipeline is not None:
        inp["optimizer_pipeline"] = pipeline
    if backend:
        inp["collision_backend"] = backend
    return inp


def total_engine_builds(cbd):
    return (cbd.get("cde_engine_builds") or 0) + (cbd.get("cde_batch_engine_builds") or 0)


def record(name, out, ms):
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    ROWS.append({
        "fixture": name, "status": out.get("status"), "runtime_ms": int(ms),
        "converged": od.get("sparrow_converged"), "iters": od.get("sparrow_iterations"),
        "pairs": f"{od.get('sparrow_collision_graph_initial_pairs')}->{od.get('sparrow_collision_graph_final_pairs')}",
        "legacy_engine_builds": cbd.get("cde_engine_builds"),
        "batch_engine_builds": cbd.get("cde_batch_engine_builds"),
        "total_engine_builds": total_engine_builds(cbd),
        "batch_candidate_queries": cbd.get("cde_batch_candidate_queries"),
        "batch_hazards_registered": cbd.get("cde_batch_hazards_registered"),
        "pairwise_fallback": cbd.get("cde_pairwise_fallback_queries"),
        "bbox_fb": cbd.get("bbox_fallback_queries"),
        "lbf_fb": od.get("search_position_lbf_fallback_used"),
    })


def converge_fixture(name, parts, stocks, seed, rotation="orthogonal", tl=6):
    print(f"\n=== {name} ===")
    out, ms = run_solver(base_input(parts, stocks, seed=seed, rotation=rotation, time_limit=tl))
    record(name, out, ms)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    check(od.get("pipeline_used") == "sparrow_cde", "pipeline_used==sparrow_cde")
    check(od.get("sparrow_converged") is True, f"must converge (got {od.get('sparrow_converged')})")
    check(cbd.get("backend_used") == "cde_adapter", "CDE backend")
    check(cbd.get("bbox_fallback_queries") == 0, "no bbox fallback")
    check((cbd.get("cde_batch_engine_builds") or 0) > 0, "batch session active (batch builds > 0)")


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        sys.exit(1)
    print("SGH-Q23R2 real Sparrow cutover completion smoke")
    print(f"Binary: {BINARY}")

    converge_fixture("tiny_cde_must_converge",
                     [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 2}],
                     [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}], seed=1)
    converge_fixture("two_rect_overlap_cde_must_separate",
                     [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 2}],
                     [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}], seed=2)
    converge_fixture("boundary_recovery_cde_must_recover",
                     [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 1}],
                     [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}], seed=3)
    converge_fixture("continuous_rotation_rescue_cde",
                     [{"id": "P", "width": 80.0, "height": 30.0, "quantity": 2}],
                     [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
                     seed=4, rotation="continuous")

    # oracle / no fallback / batch metrics
    print("\n=== production_sparrow_uses_backend_oracle_evaluation + batch metrics ===")
    out, ms = run_solver(base_input(
        [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 2}],
        [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}], seed=7))
    record("backend_oracle_and_batch_metrics", out, ms)
    cbd = out.get("collision_backend_diagnostics") or {}
    od = out.get("optimizer_diagnostics") or {}
    check(cbd.get("backend_used") == "cde_adapter", "oracle backend is CDE")
    check(od.get("phase_optimizer_invoked") is False, "phase_optimizer NOT invoked")
    check((od.get("search_position_lbf_fallback_used") or 0) == 0, "no LBF fallback")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "no bbox fallback")
    check(cbd.get("cde_batch_engine_builds") is not None
          and cbd.get("cde_batch_candidate_queries") is not None
          and cbd.get("cde_batch_hazards_registered") is not None,
          "single-engine batch metrics surfaced")
    check((cbd.get("cde_pairwise_fallback_queries") or 0) == 0, "no pairwise fallback")

    # diagnostics preserved on failure
    print("\n=== production_sparrow_preserves_full_diagnostics_on_failure ===")
    out, ms = run_solver(base_input(
        [{"id": "P", "width": 50.0, "height": 50.0, "quantity": 5}],
        [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}], seed=9))
    record("preserves_full_diagnostics_on_failure", out, ms)
    check(out.get("status") == "unsupported", f"impossible → unsupported (got {out.get('status')})")
    od = out.get("optimizer_diagnostics"); cbd = out.get("collision_backend_diagnostics")
    check(od is not None and od.get("pipeline_used") == "sparrow_cde", "optimizer_diagnostics preserved")
    check(cbd is not None and cbd.get("backend_used") == "cde_adapter", "backend diagnostics preserved")

    # ── MEDIUM HARD GATE (run.md §G) ─────────────────────────────────────────
    print("\n=== medium_10_to_20_items_cde_must_converge [HARD GATE] ===")
    out, ms = run_solver(base_input(
        [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}], seed=5, time_limit=8),
        hard_timeout_s=40.0)
    record("medium_10_to_20_items", out, ms)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    placed = out.get("metrics", {}).get("placed_count")
    req = (out.get("metrics", {}).get("placed_count") or 0) + (out.get("metrics", {}).get("unplaced_count") or 0)
    # engine-build reduction gate (>=80% vs 7650) — MET via batch path
    tb = total_engine_builds(cbd)
    if tb:
        red = (Q23_ENGINE_BUILD_BASELINE - tb) / Q23_ENGINE_BUILD_BASELINE * 100
        _log("INFO", f"total engine builds {tb} (legacy {cbd.get('cde_engine_builds')} + batch "
                     f"{cbd.get('cde_batch_engine_builds')}); reduction vs Q23 {red:.0f}%")
    check(tb > 0 and tb <= 1530,
          f"engine builds <= 1530 (>=80% reduction vs 7650); got {tb}")
    check(out.get("status") != "timeout" and ms < 40_000, f"no timeout (got {ms/1000:.1f}s)")
    # HARD convergence gate
    check(out.get("status") == "ok", f"medium status must be ok (got {out.get('status')})")
    check(placed == req and req == 12, f"medium must place 12/12 (got {placed}/{req})")
    check(od.get("sparrow_converged") is True, f"medium sparrow_converged (got {od.get('sparrow_converged')})")
    check((od.get("sparrow_collision_graph_final_pairs") or 1) == 0,
          f"medium final collision pairs == 0 (got {od.get('sparrow_collision_graph_final_pairs')})")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "medium no bbox fallback")

    # ── table ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    for r in ROWS:
        print(f"\n  --- {r['fixture']} ---")
        for k, v in r.items():
            if k == "fixture":
                continue
            print(f"  {k:26s} = {'-' if v is None else v}")

    print("\n" + "=" * 60)
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT > 0:
        print("SMOKE: FAIL (medium convergence is a hard gate per run.md §G)")
        sys.exit(1)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
