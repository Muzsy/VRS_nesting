#!/usr/bin/env python3
"""SGH-Q20R Sparrow search_position + coordinate descent smoke script.

Fixtures:
  1. Overlap reduction — search_position_calls > 0, placed_count > 0
  2. Boundary correction — items within sheet after search_position run
  3. Continuous rotation rescue — continuous places >= orthogonal
  4. CDE no bbox fallback — bbox_fallback_queries == 0, cde path used
  5. No primary LBF fallback — search_position_lbf_fallback_used == 0 in primary path
  6. Determinism — two runs with same seed produce identical output
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BINARY = Path(__file__).parent.parent / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
PROFILE = "jagua_optimizer_phase1_outer_only"

PASS_COUNT = 0
FAIL_COUNT = 0


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


def run_solver(input_dict: dict, timing: bool = False, seed: int = 0) -> dict:
    env = os.environ.copy()
    if timing:
        env["VRS_CDE_OBSERVABILITY_TIMING"] = "1"
    else:
        env.pop("VRS_CDE_OBSERVABILITY_TIMING", None)
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "in.json"
        out_path = Path(tmpdir) / "out.json"
        in_path.write_text(json.dumps(input_dict))
        result = subprocess.run(
            [str(BINARY), "--input", str(in_path), "--output", str(out_path),
             "--seed", str(seed), "--time-limit", "10"],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            print(f"  [ERROR] solver exited {result.returncode}: {result.stderr[:300]}")
            return {}
        return json.loads(out_path.read_text())


def base_input(pipeline: str | None = None, backend: str | None = None,
               rotation_policy: str | None = None,
               part_w: float = 30.0, part_h: float = 20.0,
               stock_w: float = 200.0, stock_h: float = 200.0,
               qty: int = 4) -> dict:
    inp: dict = {
        "contract_version": "v1",
        "project_name": "q20r_smoke",
        "seed": 0,
        "time_limit_s": 10,
        "solver_profile": PROFILE,
        "stocks": [{"id": "S", "quantity": 2, "width": stock_w, "height": stock_h}],
        "parts": [{"id": "P", "width": part_w, "height": part_h, "quantity": qty}],
    }
    if pipeline:
        inp["optimizer_pipeline"] = pipeline
    if backend:
        inp["collision_backend"] = backend
    if rotation_policy:
        inp["rotation_policy"] = rotation_policy
    return inp


# ---------------------------------------------------------------------------


def fixture1_overlap_reduction():
    # Use continuous policy so that Q20 rotation refinement creates overlaps that
    # search_position must resolve (search_position_calls > 0 is reliable here).
    print("\n=== Fixture 1: Overlap reduction via search_position (continuous policy) ===")
    out = run_solver(base_input(pipeline="phase_optimizer", rotation_policy="continuous",
                                part_w=60.0, part_h=20.0, stock_w=100.0, stock_h=100.0, qty=4))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    od = out.get("optimizer_diagnostics")
    check(od is not None, "optimizer_diagnostics present")
    if od:
        calls = od.get("search_position_calls", -1)
        check(calls > 0, f"search_position_calls > 0 (got {calls})")
        global_samp = od.get("search_position_global_samples_evaluated", -1)
        check(global_samp > 0, f"search_position_global_samples_evaluated > 0 (got {global_samp})")
        placed = out.get("metrics", {}).get("placed_count", 0)
        check(placed > 0, f"at least 1 part placed (got {placed})")
        _log("INFO", f"calls={calls} global_samp={global_samp} "
                     f"coord_steps={od.get('search_position_coord_descent_steps')} "
                     f"refined={od.get('search_position_refined_samples')} "
                     f"best_eval={od.get('search_position_best_eval')}")


def fixture2_boundary_correction():
    print("\n=== Fixture 2: Boundary correction — placements within sheet ===")
    out = run_solver(base_input(pipeline="phase_optimizer", rotation_policy="orthogonal",
                                part_w=40.0, part_h=25.0, stock_w=150.0, stock_h=150.0))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    placements = out.get("placements", [])
    check(len(placements) > 0, f"at least 1 placement returned ({len(placements)})")
    # All placements must have non-negative coordinates (basic boundary check)
    for p in placements:
        check(p.get("x", -1) >= 0, f"placement x >= 0 (x={p.get('x')})")
        check(p.get("y", -1) >= 0, f"placement y >= 0 (y={p.get('y')})")
    od = out.get("optimizer_diagnostics")
    if od:
        calls = od.get("search_position_calls", 0)
        _log("INFO", f"boundary check: placements={len(placements)} sp_calls={calls}")


def fixture3_continuous_rotation_rescue():
    print("\n=== Fixture 3: Continuous rotation rescue — continuous >= orthogonal ===")
    out_orth = run_solver(base_input(
        pipeline="phase_optimizer", rotation_policy="orthogonal",
        part_w=100.0, part_h=20.0, stock_w=90.0, stock_h=90.0, qty=2,
    ))
    out_cont = run_solver(base_input(
        pipeline="phase_optimizer", rotation_policy="continuous",
        part_w=100.0, part_h=20.0, stock_w=90.0, stock_h=90.0, qty=2,
    ))
    placed_orth = out_orth.get("metrics", {}).get("placed_count", 0)
    placed_cont = out_cont.get("metrics", {}).get("placed_count", 0)
    _log("INFO", f"orthogonal placed={placed_orth}, continuous placed={placed_cont}")
    check(placed_cont >= placed_orth,
          f"continuous >= orthogonal placed ({placed_cont} >= {placed_orth})")
    check(placed_cont >= 1, f"continuous places at least 1 part (placed={placed_cont})")
    od_cont = out_cont.get("optimizer_diagnostics")
    if od_cont:
        calls = od_cont.get("search_position_calls", 0)
        check(calls > 0, f"continuous run: search_position_calls > 0 (got {calls})")


def fixture4_cde_no_bbox_fallback():
    print("\n=== Fixture 4: CDE no bbox fallback — bbox_fallback_queries == 0 ===")
    out = run_solver(base_input(
        pipeline="phase_optimizer", backend="cde", rotation_policy="continuous"
    ))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    cbd = out.get("collision_backend_diagnostics")
    check(cbd is not None, "collision_backend_diagnostics present")
    if cbd:
        fallback = cbd.get("bbox_fallback_queries", -1)
        check(fallback == 0, f"bbox_fallback_queries == 0 (got {fallback})")
        total = cbd.get("cde_total_queries", 0)
        pair = cbd.get("cde_pair_queries", 0)
        boundary = cbd.get("cde_boundary_queries", 0)
        check(
            pair + boundary == total,
            f"CDE pair+boundary == total ({pair}+{boundary}=={total})"
        )
        _log("INFO", f"cde_total={total} pair={pair} boundary={boundary} fallback={fallback}")
    od = out.get("optimizer_diagnostics")
    if od:
        sp_calls = od.get("search_position_calls", 0)
        check(sp_calls > 0, f"search_position_calls > 0 under CDE (got {sp_calls})")


def fixture5_no_primary_lbf_fallback():
    # Use a large-sheet continuous fixture where parts have ample room on the sheet.
    # With plenty of valid positions, search_position always finds a candidate without
    # falling through to LBF. Q20 rotation refinement ensures search_position IS called.
    print("\n=== Fixture 5: No primary LBF fallback — lbf_fallback_used == 0 ===")
    out = run_solver(base_input(
        pipeline="phase_optimizer", rotation_policy="continuous",
        part_w=30.0, part_h=15.0, stock_w=200.0, stock_h=200.0, qty=6,
    ))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    od = out.get("optimizer_diagnostics")
    check(od is not None, "optimizer_diagnostics present")
    if od:
        sp_calls = od.get("search_position_calls", -1)
        lbf_fb = od.get("search_position_lbf_fallback_used", -1)
        check(sp_calls > 0, f"search_position_calls > 0 (got {sp_calls})")
        check(lbf_fb == 0,
              f"search_position_lbf_fallback_used == 0 (primary path, got {lbf_fb})")
        _log("INFO", f"sp_calls={sp_calls} lbf_fallback_used={lbf_fb}")


def fixture6_determinism():
    print("\n=== Fixture 6: Determinism — two runs produce identical output ===")
    inp = base_input(pipeline="phase_optimizer", rotation_policy="orthogonal",
                     part_w=35.0, part_h=20.0, qty=6)
    out1 = run_solver(inp, seed=42)
    out2 = run_solver(inp, seed=42)
    check(out1.get("status") == out2.get("status"),
          f"status identical ({out1.get('status')} == {out2.get('status')})")
    placed1 = out1.get("metrics", {}).get("placed_count", -1)
    placed2 = out2.get("metrics", {}).get("placed_count", -1)
    check(placed1 == placed2,
          f"placed_count identical ({placed1} == {placed2})")
    pl1 = sorted(out1.get("placements", []), key=lambda p: p.get("instance_id", ""))
    pl2 = sorted(out2.get("placements", []), key=lambda p: p.get("instance_id", ""))
    check(len(pl1) == len(pl2), f"placement list length identical ({len(pl1)}=={len(pl2)})")
    for i, (a, b) in enumerate(zip(pl1, pl2)):
        check(a.get("x") == b.get("x") and a.get("y") == b.get("y"),
              f"placement[{i}] x,y identical ({a.get('x')},{a.get('y')}) == ({b.get('x')},{b.get('y')})")
    od1 = out1.get("optimizer_diagnostics") or {}
    od2 = out2.get("optimizer_diagnostics") or {}
    check(
        od1.get("search_position_calls") == od2.get("search_position_calls"),
        f"search_position_calls identical ({od1.get('search_position_calls')} == {od2.get('search_position_calls')})"
    )


# ---------------------------------------------------------------------------


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)

    print(f"SGH-Q20R Sparrow search_position + coord descent smoke script")
    print(f"Binary: {BINARY}")

    fixture1_overlap_reduction()
    fixture2_boundary_correction()
    fixture3_continuous_rotation_rescue()
    fixture4_cde_no_bbox_fallback()
    fixture5_no_primary_lbf_fallback()
    fixture6_determinism()

    print()
    print("=" * 60)
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT > 0:
        print("SMOKE: FAIL")
        sys.exit(1)
    else:
        print("SMOKE: PASS")


if __name__ == "__main__":
    main()
