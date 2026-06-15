#!/usr/bin/env python3
"""SGH-Q47 — Shape Profile Priority Layer A/B regression benchmark (full276 LV8).

Runs the native vrs_solver `sparrow_cde_multisheet` (BPP sheet-reduction) path on the canonical
full276 LV8 package with Q42 technology parameters (margin 5, spacing 8, kerf 0, continuous
rotation) on 1500×3000 finite stock, TWICE:

  A  VRS_SHAPE_PROFILE=1  (default; profile-aware ordering active)
  B  VRS_SHAPE_PROFILE=0  (pre-Q47 ordering)

This is a REGRESSION check, NOT a 2-sheet proof. Acceptance (canvas §10):
  * both runs produce a VALID layout (status ok, 276/276, no collisions/boundary);
  * profile (A) does NOT regress used-sheet count vs (B);
  * the priority change is visible in A's `shape_profiles` diagnostics
    (large/slender/concave types ranked before tiny fillers).

Writes artifacts under artifacts/benchmarks/sgh_q47/ and a q47_summary.json verdict.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
BASE_FULL276 = ROOT / "artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json"

Q47 = ROOT / "artifacts/benchmarks/sgh_q47"
INPUTS = Q47 / "inputs"
OUTPUTS = Q47 / "outputs"
LOGS = Q47 / "logs"

MARGIN_MM = 5.0
SPACING_MM = 8.0
KERF_MM = 0.0
SEED = 42
TOTAL_INSTANCES = 276
SHEET_W = 1500.0
SHEET_H = 3000.0


def load_base() -> dict[str, Any]:
    return json.loads(BASE_FULL276.read_text())


def load_parts() -> list[dict[str, Any]]:
    # Continuous rotation: strip per-part discrete rotation specs (Q42/Q45 convention).
    parts = copy.deepcopy(load_base()["parts"])
    for part in parts:
        part.pop("allowed_rotations_deg", None)
        part.pop("rotation_policy", None)
    return parts


def build_input(time_limit_s: int, stock_qty: int) -> Path:
    parts = load_parts()
    inp = {
        "contract_version": "v1",
        "project_name": "sgh_q47_shape_profile_full276",
        "seed": SEED,
        "time_limit_s": time_limit_s,
        "stocks": [
            {"id": "S1500x3000", "quantity": stock_qty, "width": SHEET_W, "height": SHEET_H}
        ],
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "rotation_policy": "continuous",
        "margin_mm": MARGIN_MM,
        "spacing_mm": SPACING_MM,
        "kerf_mm": KERF_MM,
        "parts": parts,
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"q47_full276_{stock_qty}x1500x3000_margin5_spacing8_continuous_{time_limit_s}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run_solver(side: str, profile_on: bool, time_limit_s: int, input_path: Path) -> dict[str, Any]:
    rid = f"q47_{side}_profile{'on' if profile_on else 'off'}_{time_limit_s}"
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{rid}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)  # ensure the BPP path (default) runs
    env["VRS_SHAPE_PROFILE"] = "1" if profile_on else "0"
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(input_path), "--output", str(out_path)],
        capture_output=True, text=True, timeout=time_limit_s + 1800, env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{rid}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\ntime_limit_s={time_limit_s}\n"
        f"VRS_SHAPE_PROFILE={env['VRS_SHAPE_PROFILE']}\n"
        f"stdout:\n{proc.stdout[:4000]}\nstderr:\n{proc.stderr[:4000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{rid} solver exit {proc.returncode}: {proc.stderr[:800]}")
    out = json.loads(out_path.read_text())
    out["_wall_time_s"] = wall
    return out


def used_sheet_count(out: dict[str, Any]) -> int:
    return len({p.get("sheet_index", 0) for p in out.get("placements", [])})


def summarize_side(out: dict[str, Any]) -> dict[str, Any]:
    diag = out.get("optimizer_diagnostics") or {}
    metrics = out.get("metrics") or {}
    return {
        "status": out.get("status"),
        "placed_count": metrics.get("placed_count"),
        "unplaced_count": len(out.get("unplaced", [])),
        "used_sheets": used_sheet_count(out),
        "final_pairs": diag.get("sparrow_ms_final_pairs"),
        "boundary_violations": diag.get("sparrow_ms_boundary_violations"),
        "utilization_pct": diag.get("sparrow_ms_utilization_pct"),
        "bpp_final_sheet_count": (diag.get("bpp_reduction") or {}).get("bpp_final_sheet_count"),
        "wall_time_s": round(out.get("_wall_time_s", 0.0), 1),
    }


def profile_evidence(out: dict[str, Any]) -> dict[str, Any]:
    """Extract the priority-ordering evidence from A's shape_profiles diagnostics."""
    diag = out.get("optimizer_diagnostics") or {}
    profiles = diag.get("shape_profiles") or []
    rows = sorted(profiles, key=lambda r: r.get("priority_rank", 0))
    top = [
        {
            "rank": r["priority_rank"],
            "part_id": r["part_id"],
            "priority_score": round(r["priority_score"], 4),
            "classes": r["classes"],
            "budget_mult": round(r["search_budget_multiplier"], 2),
            "placed": f'{r["placed_count"]}/{r["instance_count"]}',
        }
        for r in rows
    ]
    anchor_ranks = [r["priority_rank"] for r in rows if "large_anchor" in r.get("classes", [])]
    tiny_ranks = [r["priority_rank"] for r in rows if "tiny_filler" in r.get("classes", [])]
    anchors_before_fillers = (
        bool(anchor_ranks) and bool(tiny_ranks) and max(anchor_ranks) < min(tiny_ranks)
    )
    return {
        "type_count": len(rows),
        "ranked_types": top,
        "anchors_before_fillers": anchors_before_fillers,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-limit", type=int, default=600)
    ap.add_argument("--stock-qty", type=int, default=6)
    args = ap.parse_args()

    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    input_path = build_input(args.time_limit, args.stock_qty)
    print(f"[Q47] input: {input_path}")

    print(f"[Q47] Run A (VRS_SHAPE_PROFILE=1) time_limit={args.time_limit}s ...")
    a = run_solver("A", True, args.time_limit, input_path)
    print(f"[Q47] Run B (VRS_SHAPE_PROFILE=0) time_limit={args.time_limit}s ...")
    b = run_solver("B", False, args.time_limit, input_path)

    sa, sb = summarize_side(a), summarize_side(b)
    ev = profile_evidence(a)

    valid_a = sa["status"] == "ok" and sa["placed_count"] == TOTAL_INSTANCES and sa["final_pairs"] == 0
    valid_b = sb["status"] == "ok" and sb["placed_count"] == TOTAL_INSTANCES and sb["final_pairs"] == 0
    no_sheet_regression = (
        sa["used_sheets"] is not None
        and sb["used_sheets"] is not None
        and sa["used_sheets"] <= sb["used_sheets"]
    )
    priority_visible = ev["anchors_before_fillers"]
    verdict = "PASS" if (valid_a and no_sheet_regression and priority_visible) else "FAIL"

    summary = {
        "task": "sgh_q47_shape_profile_priority_layer",
        "time_limit_s": args.time_limit,
        "stock_qty": args.stock_qty,
        "run_a_profile_on": sa,
        "run_b_profile_off": sb,
        "profile_evidence_a": ev,
        "acceptance": {
            "valid_a": valid_a,
            "valid_b": valid_b,
            "no_sheet_count_regression": no_sheet_regression,
            "priority_change_visible": priority_visible,
        },
        "verdict": verdict,
    }
    Q47.mkdir(parents=True, exist_ok=True)
    (Q47 / "q47_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"[Q47] VERDICT: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
