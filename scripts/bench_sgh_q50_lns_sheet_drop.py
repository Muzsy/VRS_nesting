#!/usr/bin/env python3
"""SGH-Q50 — Density-guided LNS sheet-drop A/B benchmark (full276 LV8).

Isolates the LNS contribution on top of the Q49 density compaction:

  A  VRS_BPP_DENSITY_COMPACT=1 + VRS_BPP_LNS=1   (density + LNS sheet-drop)
  B  VRS_BPP_DENSITY_COMPACT=1 + VRS_BPP_LNS=0   (density only, Q49 baseline)

The real question: does the LNS drop the 3rd sheet (3 -> 2)? Acceptance (canvas §10): A valid (ok,
276/276, no collisions); A no sheet-count regression vs B; the LNS pass demonstrably attempts
elimination (attempts > 0). Sheet reduction to 2 is the stretch goal, not promised.
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
BASE = ROOT / "artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json"
Q50 = ROOT / "artifacts/benchmarks/sgh_q50"
INPUTS, OUTPUTS, LOGS = Q50 / "inputs", Q50 / "outputs", Q50 / "logs"
SEED, TOTAL = 42, 276


def load_parts() -> list[dict[str, Any]]:
    parts = copy.deepcopy(json.loads(BASE.read_text())["parts"])
    for p in parts:
        p.pop("allowed_rotations_deg", None)
        p.pop("rotation_policy", None)
    return parts


def build_input(t: int, qty: int) -> Path:
    inp = {
        "contract_version": "v1", "project_name": "sgh_q50_lns", "seed": SEED, "time_limit_s": t,
        "stocks": [{"id": "S1500x3000", "quantity": qty, "width": 1500.0, "height": 3000.0}],
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde_multisheet", "collision_backend": "cde",
        "rotation_policy": "continuous", "margin_mm": 5.0, "spacing_mm": 8.0, "kerf_mm": 0.0,
        "parts": load_parts(),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"q50_full276_{qty}x1500x3000_margin5_spacing8_continuous_{t}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run(side: str, lns: bool, t: int, inp: Path) -> dict[str, Any]:
    rid = f"q50_{side}_lns{'on' if lns else 'off'}_{t}"
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{rid}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)
    env["VRS_BPP_DENSITY_COMPACT"] = "1"
    env["VRS_BPP_LNS"] = "1" if lns else "0"
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(inp), "--output", str(out_path)],
        capture_output=True, text=True, timeout=t + 3600, env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{rid}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\nLNS={env['VRS_BPP_LNS']}\nstderr:\n{proc.stderr[:3000]}\n"
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
        "lns_applied": b.get("bpp_lns_applied"),
        "lns_attempts": b.get("bpp_lns_attempts"),
        "lns_sheets_dropped": b.get("bpp_lns_sheets_dropped"),
        "lns_parts_reinserted": b.get("bpp_lns_parts_reinserted"),
        "lns_restarts": b.get("bpp_lns_restarts"),
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
    print(f"[Q50] input: {inp}")
    print(f"[Q50] Run A (density + LNS) {args.time_limit}s ...")
    a = run("A", True, args.time_limit, inp)
    print(f"[Q50] Run B (density only) {args.time_limit}s ...")
    b = run("B", False, args.time_limit, inp)
    sa, sb = summ(a), summ(b)
    valid_a = sa["status"] == "ok" and sa["placed_count"] == TOTAL and sa["final_pairs"] == 0
    valid_b = sb["status"] == "ok" and sb["placed_count"] == TOTAL and sb["final_pairs"] == 0
    no_reg = sa["used_sheets"] is not None and sb["used_sheets"] is not None and sa["used_sheets"] <= sb["used_sheets"]
    attempted = (sa["lns_attempts"] or 0) > 0
    dropped = (sa["lns_sheets_dropped"] or 0) > 0
    verdict = "PASS" if (valid_a and no_reg and sa["lns_applied"] and attempted) else "FAIL"
    out = {
        "task": "sgh_q50_density_lns_sheet_drop",
        "time_limit_s": args.time_limit, "stock_qty": args.stock_qty,
        "run_a_density_plus_lns": sa, "run_b_density_only": sb,
        "lns_dropped_a_sheet": dropped,
        "acceptance": {
            "valid_a": valid_a, "valid_b": valid_b,
            "no_sheet_count_regression": no_reg,
            "lns_pass_ran": sa["lns_applied"],
            "lns_attempted_elimination": attempted,
            "STRETCH_lns_dropped_a_sheet": dropped,
        },
        "verdict": verdict,
    }
    Q50.mkdir(parents=True, exist_ok=True)
    (Q50 / "q50_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[Q50] VERDICT: {verdict}  (sheet dropped: {dropped})")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
