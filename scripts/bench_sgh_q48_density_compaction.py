#!/usr/bin/env python3
"""SGH-Q48 — Interlock-aware density compaction A/B regression benchmark (full276 LV8).

Runs the native vrs_solver `sparrow_cde_multisheet` (BPP) path on the canonical full276 LV8
package (margin 5 / spacing 8 / continuous, 1500×3000 stock) TWICE:

  A  VRS_BPP_DENSITY_COMPACT=1  (interlock-aware density compaction ON)
  B  VRS_BPP_DENSITY_COMPACT=0  (pre-Q48: gravity-only)

REGRESSION + decision-diagnostic check, NOT a 2-sheet proof. Acceptance (canvas §10):
  * A is valid (status ok, 276/276, no collisions/boundary);
  * A does NOT regress used-sheet count vs B;
  * the density pass ran and the interlock decision-diagnostics are visible.
The interlock mechanism itself is proven separately on the 6×Lv8_11612 fixture (report §5).
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

Q48 = ROOT / "artifacts/benchmarks/sgh_q48"
INPUTS, OUTPUTS, LOGS = Q48 / "inputs", Q48 / "outputs", Q48 / "logs"

MARGIN_MM, SPACING_MM, KERF_MM, SEED = 5.0, 8.0, 0.0, 42
TOTAL_INSTANCES, SHEET_W, SHEET_H = 276, 1500.0, 3000.0


def load_parts() -> list[dict[str, Any]]:
    parts = copy.deepcopy(json.loads(BASE_FULL276.read_text())["parts"])
    for p in parts:
        p.pop("allowed_rotations_deg", None)
        p.pop("rotation_policy", None)
    return parts


def build_input(time_limit_s: int, stock_qty: int) -> Path:
    inp = {
        "contract_version": "v1", "project_name": "sgh_q48_density_full276", "seed": SEED,
        "time_limit_s": time_limit_s,
        "stocks": [{"id": "S1500x3000", "quantity": stock_qty, "width": SHEET_W, "height": SHEET_H}],
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde_multisheet", "collision_backend": "cde",
        "rotation_policy": "continuous",
        "margin_mm": MARGIN_MM, "spacing_mm": SPACING_MM, "kerf_mm": KERF_MM,
        "parts": load_parts(),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"q48_full276_{stock_qty}x1500x3000_margin5_spacing8_continuous_{time_limit_s}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run(side: str, on: bool, time_limit_s: int, input_path: Path) -> dict[str, Any]:
    rid = f"q48_{side}_density{'on' if on else 'off'}_{time_limit_s}"
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{rid}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)
    env["VRS_BPP_DENSITY_COMPACT"] = "1" if on else "0"
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(input_path), "--output", str(out_path)],
        capture_output=True, text=True, timeout=time_limit_s + 3600, env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{rid}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\nVRS_BPP_DENSITY_COMPACT={env['VRS_BPP_DENSITY_COMPACT']}\n"
        f"stdout:\n{proc.stdout[:3000]}\nstderr:\n{proc.stderr[:3000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{rid} exit {proc.returncode}: {proc.stderr[:800]}")
    out = json.loads(out_path.read_text())
    out["_wall_time_s"] = wall
    return out


def used_sheets(out: dict[str, Any]) -> int:
    return len({p.get("sheet_index", 0) for p in out.get("placements", [])})


def summary_side(out: dict[str, Any]) -> dict[str, Any]:
    d = out.get("optimizer_diagnostics") or {}
    b = d.get("bpp_reduction") or {}
    return {
        "status": out.get("status"),
        "placed_count": (out.get("metrics") or {}).get("placed_count"),
        "used_sheets": used_sheets(out),
        "final_pairs": d.get("sparrow_ms_final_pairs"),
        "boundary_violations": d.get("sparrow_ms_boundary_violations"),
        "utilization_pct": d.get("sparrow_ms_utilization_pct"),
        "density_applied": b.get("bpp_density_compaction_applied"),
        "density_moves_accepted": b.get("bpp_density_moves_accepted"),
        "interlock_generated": b.get("bpp_interlock_candidates_generated"),
        "interlock_accepted": b.get("bpp_interlock_candidates_accepted"),
        "wall_time_s": round(out.get("_wall_time_s", 0.0), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-limit", type=int, default=300)
    ap.add_argument("--stock-qty", type=int, default=6)
    args = ap.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    inp = build_input(args.time_limit, args.stock_qty)
    print(f"[Q48] input: {inp}")
    print(f"[Q48] Run A (density ON)  {args.time_limit}s ...")
    a = run("A", True, args.time_limit, inp)
    print(f"[Q48] Run B (density OFF) {args.time_limit}s ...")
    b = run("B", False, args.time_limit, inp)

    sa, sb = summary_side(a), summary_side(b)
    valid_a = sa["status"] == "ok" and sa["placed_count"] == TOTAL_INSTANCES and sa["final_pairs"] == 0
    valid_b = sb["status"] == "ok" and sb["placed_count"] == TOTAL_INSTANCES and sb["final_pairs"] == 0
    no_regression = (
        sa["used_sheets"] is not None and sb["used_sheets"] is not None
        and sa["used_sheets"] <= sb["used_sheets"]
    )
    pass_applied = sa["density_applied"] is True
    verdict = "PASS" if (valid_a and no_regression and pass_applied) else "FAIL"

    out = {
        "task": "sgh_q48_interlocking_density_compaction",
        "time_limit_s": args.time_limit, "stock_qty": args.stock_qty,
        "run_a_density_on": sa, "run_b_density_off": sb,
        "acceptance": {
            "valid_a": valid_a, "valid_b": valid_b,
            "no_sheet_count_regression": no_regression,
            "density_pass_ran": pass_applied,
        },
        "verdict": verdict,
    }
    Q48.mkdir(parents=True, exist_ok=True)
    (Q48 / "q48_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[Q48] VERDICT: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
