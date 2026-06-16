#!/usr/bin/env python3
"""SGH-Q49 — Density-pass budget-allocation A/B benchmark (full276 LV8).

Re-runs the full276 LV8 BPP path with the interlock-aware density compaction, now with the Q49
budget reservation (VRS_BPP_DENSITY_BUDGET_FRAC) + per-part efficiency (incremental tracker,
multi-sweep). Measures whether the density pass now acts on (most/all of) the 276 parts within the
reserved budget — vs the Q48 budget-starved result (20 interlock generated / 2 accepted).

  A  VRS_BPP_DENSITY_COMPACT=1  (density on, reserved budget)
  B  VRS_BPP_DENSITY_COMPACT=0  (off; reduction deadline unchanged)

REGRESSION + decision-diagnostic check, NOT a 2-sheet proof. Acceptance:
  * A valid (ok, 276/276, no collisions); A no sheet-count regression vs B;
  * the density pass runs across the parts (parts_processed, sweeps, density_time_ms visible).
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
Q49 = ROOT / "artifacts/benchmarks/sgh_q49"
INPUTS, OUTPUTS, LOGS = Q49 / "inputs", Q49 / "outputs", Q49 / "logs"
SEED, TOTAL = 42, 276


def load_parts() -> list[dict[str, Any]]:
    parts = copy.deepcopy(json.loads(BASE_FULL276.read_text())["parts"])
    for p in parts:
        p.pop("allowed_rotations_deg", None)
        p.pop("rotation_policy", None)
    return parts


def build_input(t: int, qty: int) -> Path:
    inp = {
        "contract_version": "v1", "project_name": "sgh_q49_density_budget", "seed": SEED,
        "time_limit_s": t,
        "stocks": [{"id": "S1500x3000", "quantity": qty, "width": 1500.0, "height": 3000.0}],
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde_multisheet", "collision_backend": "cde",
        "rotation_policy": "continuous", "margin_mm": 5.0, "spacing_mm": 8.0, "kerf_mm": 0.0,
        "parts": load_parts(),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"q49_full276_{qty}x1500x3000_margin5_spacing8_continuous_{t}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run(side: str, on: bool, t: int, inp: Path) -> dict[str, Any]:
    rid = f"q49_{side}_density{'on' if on else 'off'}_{t}"
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{rid}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)
    env["VRS_BPP_DENSITY_COMPACT"] = "1" if on else "0"
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(inp), "--output", str(out_path)],
        capture_output=True, text=True, timeout=t + 3600, env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{rid}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\nVRS_BPP_DENSITY_COMPACT={env['VRS_BPP_DENSITY_COMPACT']}\n"
        f"stderr:\n{proc.stderr[:3000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{rid} exit {proc.returncode}: {proc.stderr[:800]}")
    o = json.loads(out_path.read_text())
    o["_wall"] = wall
    return o


def summ(o: dict[str, Any]) -> dict[str, Any]:
    d = o.get("optimizer_diagnostics") or {}
    b = d.get("bpp_reduction") or {}
    return {
        "status": o.get("status"),
        "placed_count": (o.get("metrics") or {}).get("placed_count"),
        "used_sheets": len({p.get("sheet_index", 0) for p in o.get("placements", [])}),
        "final_pairs": d.get("sparrow_ms_final_pairs"),
        "utilization_pct": d.get("sparrow_ms_utilization_pct"),
        "density_applied": b.get("bpp_density_compaction_applied"),
        "density_sweeps": b.get("bpp_density_sweeps"),
        "density_parts_processed": b.get("bpp_density_parts_processed"),
        "density_moves_accepted": b.get("bpp_density_moves_accepted"),
        "interlock_generated": b.get("bpp_interlock_candidates_generated"),
        "interlock_accepted": b.get("bpp_interlock_candidates_accepted"),
        "reduction_time_ms": round(b.get("bpp_reduction_time_ms") or 0.0, 0),
        "density_time_ms": round(b.get("bpp_density_time_ms") or 0.0, 0),
        "wall_time_s": round(o.get("_wall", 0.0), 1),
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
    print(f"[Q49] input: {inp}")
    print(f"[Q49] Run A (density ON, reserved budget) {args.time_limit}s ...")
    a = run("A", True, args.time_limit, inp)
    print(f"[Q49] Run B (density OFF) {args.time_limit}s ...")
    b = run("B", False, args.time_limit, inp)
    sa, sb = summ(a), summ(b)
    valid_a = sa["status"] == "ok" and sa["placed_count"] == TOTAL and sa["final_pairs"] == 0
    valid_b = sb["status"] == "ok" and sb["placed_count"] == TOTAL and sb["final_pairs"] == 0
    no_reg = sa["used_sheets"] is not None and sb["used_sheets"] is not None and sa["used_sheets"] <= sb["used_sheets"]
    ran = sa["density_applied"] is True and (sa["density_parts_processed"] or 0) >= TOTAL
    verdict = "PASS" if (valid_a and no_reg and sa["density_applied"]) else "FAIL"
    out = {
        "task": "sgh_q49_density_budget_allocation",
        "time_limit_s": args.time_limit, "stock_qty": args.stock_qty,
        "run_a_density_on": sa, "run_b_density_off": sb,
        "q48_starved_reference": {"interlock_generated": 20, "interlock_accepted": 2},
        "acceptance": {
            "valid_a": valid_a, "valid_b": valid_b,
            "no_sheet_count_regression": no_reg,
            "density_pass_ran": sa["density_applied"],
            "density_processed_all_276": ran,
        },
        "verdict": verdict,
    }
    Q49.mkdir(parents=True, exist_ok=True)
    (Q49 / "q49_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[Q49] VERDICT: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
