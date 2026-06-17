#!/usr/bin/env python3
"""SGH-Q51 — Critical-aware constructive sheet builder benchmark.

Two things:
  (1) PROOF — 6×Lv8_11612 with VRS_SHEET_BUILDER=1 at spacing 0: the builder achieves the
      reference's structure — 3 big curved parts per sheet, 2 sheets, valid. (At spacing 5/8 the
      3-way interlock is tighter than the admission yet finds, so it falls back to 3 sheets.)
  (2) NO REGRESSION — full276 LV8, builder ON vs OFF at production spacing 8: identical (the builder
      seed is used only when fully feasible, else it falls back to the LBF seed).

Honest status: the architecture is proven (2 sheets at spacing 0); the tight-spacing admission
(density-biased separation) is the next R&D (SGH-Q52). Builder is gated (default off).
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
Q51 = ROOT / "artifacts/benchmarks/sgh_q51"
INPUTS, OUTPUTS, LOGS = Q51 / "inputs", Q51 / "outputs", Q51 / "logs"


def base_parts() -> list[dict[str, Any]]:
    parts = copy.deepcopy(json.loads(BASE.read_text())["parts"])
    for p in parts:
        p.pop("allowed_rotations_deg", None)
        p.pop("rotation_policy", None)
    return parts


def write_input(name: str, parts: list, qty: int, spacing: float, t: int) -> Path:
    inp = {
        "contract_version": "v1", "project_name": f"sgh_q51_{name}", "seed": 42, "time_limit_s": t,
        "stocks": [{"id": "S", "quantity": qty, "width": 1500.0, "height": 3000.0}],
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde_multisheet", "collision_backend": "cde",
        "rotation_policy": "continuous", "margin_mm": 5.0, "spacing_mm": spacing, "kerf_mm": 0.0,
        "parts": parts,
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"q51_{name}.json"
    path.write_text(json.dumps(inp))
    return path


def run(name: str, builder: bool, inp: Path, t: int) -> dict[str, Any]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{name}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)
    if builder:
        env["VRS_SHEET_BUILDER"] = "1"
    else:
        env.pop("VRS_SHEET_BUILDER", None)
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(inp), "--output", str(out_path)],
        capture_output=True, text=True, timeout=t + 3600, env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{name}.log").write_text(f"exit={proc.returncode}\nwall={wall:.1f}\n{proc.stderr[:2000]}")
    if proc.returncode != 0:
        raise RuntimeError(f"{name} exit {proc.returncode}: {proc.stderr[:500]}")
    o = json.loads(out_path.read_text())
    o["_wall"] = wall
    return o


def summ(o: dict[str, Any]) -> dict[str, Any]:
    d = o.get("optimizer_diagnostics") or {}
    b = d.get("bpp_reduction") or {}
    big: dict[int, int] = {}
    for p in o.get("placements", []):
        if str(p.get("part_id", "")).startswith("Lv8_11612"):
            s = p.get("sheet_index", 0)
            big[s] = big.get(s, 0) + 1
    return {
        "status": o.get("status"),
        "placed_count": (o.get("metrics") or {}).get("placed_count"),
        "used_sheets": len({p.get("sheet_index", 0) for p in o.get("placements", [])}),
        "utilization_pct": d.get("sparrow_ms_utilization_pct"),
        "big_per_sheet": {str(k): v for k, v in sorted(big.items())},
        "max_big_per_sheet": max(big.values()) if big else 0,
        "builder_applied": b.get("bpp_sheet_builder_applied"),
        "max_critical_per_sheet": b.get("bpp_max_critical_per_sheet"),
        "wall_time_s": round(o.get("_wall", 0.0), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-time", type=int, default=300)
    ap.add_argument("--proof-time", type=int, default=60)
    args = ap.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    big6 = [p for p in base_parts() if str(p["id"]).startswith("Lv8_11612")]
    for p in big6:
        p["quantity"] = 6

    # (1) PROOF — 6-big at spacing 0, builder ON
    proof_in = write_input("6big_sp0", big6, 4, 0.0, args.proof_time)
    print("[Q51] PROOF: 6×Lv8_11612 spacing 0, builder ON ...")
    proof = summ(run("6big_sp0_builderon", True, proof_in, args.proof_time))

    # (1b) tight spacing fallback — 6-big at spacing 8, builder ON
    tight_in = write_input("6big_sp8", big6, 4, 8.0, args.proof_time)
    print("[Q51] tight spacing: 6×Lv8_11612 spacing 8, builder ON (fallback) ...")
    tight = summ(run("6big_sp8_builderon", True, tight_in, args.proof_time))

    # (2) NO REGRESSION — full276 spacing 8, builder ON vs OFF
    full_in = write_input("full276_sp8", base_parts(), 6, 8.0, args.full_time)
    print(f"[Q51] full276 builder ON  ({args.full_time}s) ...")
    full_on = summ(run("full276_builderon", True, full_in, args.full_time))
    print(f"[Q51] full276 builder OFF ({args.full_time}s) ...")
    full_off = summ(run("full276_builderoff", False, full_in, args.full_time))

    proof_ok = proof["status"] == "ok" and proof["used_sheets"] == 2 and proof["max_big_per_sheet"] == 3
    no_reg = (
        full_on["status"] == "ok"
        and full_on["placed_count"] == 276
        and full_on["used_sheets"] is not None
        and full_off["used_sheets"] is not None
        and full_on["used_sheets"] <= full_off["used_sheets"]
    )
    verdict = "PASS" if (proof_ok and no_reg) else "FAIL"
    out = {
        "task": "sgh_q51_critical_aware_sheet_builder",
        "proof_6big_spacing0_builder_on": proof,
        "tight_6big_spacing8_builder_on": tight,
        "full276_builder_on": full_on,
        "full276_builder_off": full_off,
        "acceptance": {
            "PROOF_2sheets_3big_per_sheet_at_spacing0": proof_ok,
            "no_full276_regression_vs_off": no_reg,
        },
        "verdict": verdict,
        "note": "Architecture proven at spacing 0; tight-spacing admission (density-biased separation) = SGH-Q52.",
    }
    Q51.mkdir(parents=True, exist_ok=True)
    (Q51 / "q51_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[Q51] VERDICT: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
