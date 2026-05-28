#!/usr/bin/env python3
"""SGH-Q20 continuous rotation refinement smoke script.

Fixtures:
  1. Continuous + phase_optimizer — refinement_enabled=true, attempts>0
  2. Orthogonal + phase_optimizer — refinement_enabled=false, attempts=0
  3. Continuous + CDE + phase_optimizer — bbox_fallback_queries==0, refinement_enabled
  4. Linspace coarse coverage — 100x20 part fits in 90x90 sheet under Continuous
  5. Default output has no timing fields (regression guard)
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


def run_solver(input_dict: dict, timing: bool = False) -> dict:
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
             "--seed", "0", "--time-limit", "10"],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            print(f"  [ERROR] solver exited {result.returncode}: {result.stderr[:300]}")
            return {}
        return json.loads(out_path.read_text())


def base_input(pipeline: str | None = None, backend: str | None = None,
               rotation_policy: str | None = None,
               part_w: float = 30.0, part_h: float = 20.0,
               stock_w: float = 200.0, stock_h: float = 200.0) -> dict:
    inp: dict = {
        "contract_version": "v1",
        "project_name": "q20_smoke",
        "seed": 0,
        "time_limit_s": 10,
        "solver_profile": PROFILE,
        "stocks": [{"id": "S", "quantity": 1, "width": stock_w, "height": stock_h}],
        "parts": [{"id": "P", "width": part_w, "height": part_h, "quantity": 2}],
    }
    if pipeline:
        inp["optimizer_pipeline"] = pipeline
    if backend:
        inp["collision_backend"] = backend
    if rotation_policy:
        inp["rotation_policy"] = rotation_policy
    return inp


# ---------------------------------------------------------------------------


def fixture1_continuous_refinement_enabled():
    print("\n=== Fixture 1: Continuous + phase_optimizer → refinement_enabled ===")
    out = run_solver(base_input(
        pipeline="phase_optimizer",
        rotation_policy="continuous",
    ))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    od = out.get("optimizer_diagnostics")
    check(od is not None, "optimizer_diagnostics present")
    if od:
        check(od.get("rotation_refinement_enabled") is True,
              f"rotation_refinement_enabled=true (got {od.get('rotation_refinement_enabled')})")
        attempts = od.get("rotation_refinement_attempts", -1)
        check(attempts > 0, f"rotation_refinement_attempts>0 (got {attempts})")
        accepts = od.get("rotation_refinement_accepts", -1)
        rejections = od.get("rotation_refinement_rejections", -1)
        check(accepts >= 0, f"rotation_refinement_accepts>=0 (got {accepts})")
        check(rejections >= 0, f"rotation_refinement_rejections>=0 (got {rejections})")
        check(accepts + rejections == attempts,
              f"accepts+rejections==attempts ({accepts}+{rejections}=={attempts})")
        _log("INFO", f"attempts={attempts} accepts={accepts} rejections={rejections} "
                     f"best_delta={od.get('rotation_refinement_best_delta', 'n/a')}")


def fixture2_orthogonal_no_refinement():
    print("\n=== Fixture 2: Orthogonal + phase_optimizer → no refinement ===")
    out = run_solver(base_input(
        pipeline="phase_optimizer",
        rotation_policy="orthogonal",
    ))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    od = out.get("optimizer_diagnostics")
    check(od is not None, "optimizer_diagnostics present")
    if od:
        check(od.get("rotation_refinement_enabled") is False,
              f"rotation_refinement_enabled=false for Orthogonal (got {od.get('rotation_refinement_enabled')})")
        attempts = od.get("rotation_refinement_attempts", -1)
        check(attempts == 0, f"rotation_refinement_attempts==0 for Orthogonal (got {attempts})")


def fixture3_continuous_cde_bbox_fallback_zero():
    print("\n=== Fixture 3: Continuous + CDE + phase_optimizer → bbox_fallback_queries==0 ===")
    out = run_solver(base_input(
        pipeline="phase_optimizer",
        backend="cde",
        rotation_policy="continuous",
    ))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    cbd = out.get("collision_backend_diagnostics")
    check(cbd is not None, "collision_backend_diagnostics present")
    if cbd:
        fallback = cbd.get("bbox_fallback_queries", -1)
        check(fallback == 0, f"bbox_fallback_queries==0 (got {fallback})")
        check(cbd.get("backend_used") == "cde_adapter",
              f"backend_used=cde_adapter (got {cbd.get('backend_used')})")
    od = out.get("optimizer_diagnostics")
    if od:
        check(od.get("rotation_refinement_enabled") is True,
              f"rotation_refinement_enabled=true under CDE (got {od.get('rotation_refinement_enabled')})")
        _log("INFO", f"cde_total_queries={cbd.get('cde_total_queries') if cbd else 'n/a'} "
                     f"refinement_attempts={od.get('rotation_refinement_attempts')}")


def fixture4_linspace_fit_rescue():
    print("\n=== Fixture 4: Linspace fit-rescue — 100x20 fits in 90x90 at diagonal angle ===")
    # Under Orthogonal (0°/90°): bbox 100x20 doesn't fit in 90x90 sheet
    # Under Continuous (linspace n=16 → includes 45°): bbox ≈ 84.85x84.85 fits
    out_orth = run_solver(base_input(
        pipeline="phase_optimizer",
        rotation_policy="orthogonal",
        part_w=100.0, part_h=20.0,
        stock_w=90.0, stock_h=90.0,
    ))
    out_cont = run_solver(base_input(
        pipeline="phase_optimizer",
        rotation_policy="continuous",
        part_w=100.0, part_h=20.0,
        stock_w=90.0, stock_h=90.0,
    ))
    placed_orth = out_orth.get("metrics", {}).get("placed_count", 0)
    placed_cont = out_cont.get("metrics", {}).get("placed_count", 0)
    unplaced_orth = out_orth.get("metrics", {}).get("unplaced_count", 0)
    unplaced_cont = out_cont.get("metrics", {}).get("unplaced_count", 0)
    _log("INFO", f"orthogonal: placed={placed_orth} unplaced={unplaced_orth}")
    _log("INFO", f"continuous: placed={placed_cont} unplaced={unplaced_cont}")
    check(unplaced_orth > 0 or placed_orth < 2,
          f"orthogonal cannot fit all 100x20 parts in 90x90 (unplaced={unplaced_orth})")
    check(placed_cont >= placed_orth,
          f"continuous >= orthogonal placed count ({placed_cont}>={placed_orth})")
    # The key quality check: continuous should place at least 1 part via diagonal rotation
    check(placed_cont >= 1, f"continuous must place at least 1 part (placed={placed_cont})")


def fixture5_default_no_timing_fields():
    print("\n=== Fixture 5: Default output has no wall-clock timing fields ===")
    out = run_solver(base_input(pipeline="phase_optimizer", rotation_policy="continuous"))
    od = out.get("optimizer_diagnostics", {})
    cbd = out.get("collision_backend_diagnostics", {}) or {}
    timing_fields = [
        "phase_optimizer_exploration_ms", "phase_optimizer_compression_ms",
        "phase_optimizer_bpp_ms", "phase_optimizer_final_commit_ms",
        "final_commit_validation_ms",
    ]
    for field in timing_fields:
        val_od = od.get(field) if od else None
        val_cbd = cbd.get(field)
        check(val_od is None and val_cbd is None,
              f"{field} must be absent from default output (od={val_od}, cbd={val_cbd})")


# ---------------------------------------------------------------------------


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)

    print(f"SGH-Q20 continuous rotation refinement smoke script")
    print(f"Binary: {BINARY}")

    fixture1_continuous_refinement_enabled()
    fixture2_orthogonal_no_refinement()
    fixture3_continuous_cde_bbox_fallback_zero()
    fixture4_linspace_fit_rescue()
    fixture5_default_no_timing_fields()

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
