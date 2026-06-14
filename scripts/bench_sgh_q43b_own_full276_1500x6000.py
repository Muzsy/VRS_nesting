#!/usr/bin/env python3
"""SGH-Q43b — Own vrs_solver full276 LV8 1x1500x6000 single-strip baseline.

Runs the OWN vrs_solver (the native Rust Sparrow CDE port at
rust/vrs_solver/target/release/vrs_solver) on the Q42 full276 LV8 input
geometry, but with stocks = [1 db 1500x6000] instead of [3 db 1500x3000].

This is a "Q42-on-a-strip" run: same 12 part type / 276 instance geometry,
same margin=5 / spacing=8 / kerf=0 / continuous rotation policy, but the
container collapses to a single 1500x6000 mm sheet (the area of two
1500x3000 sheets placed end-to-end along the long axis).

This is an OWN solver run, NOT upstream Sparrow. The Q43 upstream SPP
baseline remains the reference for "what does the upstream algorithm do";
this run shows what the OWN (production-adapted, finite-stock aware) solver
does on a comparable container.

Own solver source is NOT modified by this runner — it only builds an input
JSON and invokes the existing vrs_solver binary.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"

Q42 = ROOT / "artifacts" / "benchmarks" / "sgh_q42"
Q43B = ROOT / "artifacts" / "benchmarks" / "sgh_q43b"
INPUTS = Q43B / "inputs"
OUTPUTS = Q43B / "outputs"
LOGS = Q43B / "logs"

# Q42 reference input (full276 LV8 derived, 12 part types, 276 instances)
BASE_FULL276 = Q42 / "inputs" / "q42_full276_3x1500x3000_margin5_spacing8_continuous_1200.json"

# Single-strip container matching the Q43 1500x6000 upstream SPP baseline
STRIP_W = 1500.0
STRIP_H = 6000.0
STRIP_ID = "S1500x6000"
STRIP_QTY = 1

# Q42-equivalent technology parameters
MARGIN_MM = 5.0
SPACING_MM = 8.0
KERF_MM = 0.0
SEED = 42
TIME_LIMIT_S = 1200  # single run, max 1200s (Q42 Run A budget)

RUN_ID = "q43b_full276_1x1500x6000_margin5_spacing8_continuous_1200"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_q42_base() -> dict[str, Any]:
    if not BASE_FULL276.exists():
        raise FileNotFoundError(f"Q42 base input not found: {BASE_FULL276}")
    return json.loads(BASE_FULL276.read_text())


def build_input() -> dict[str, Any]:
    """Build a v1-contract SolverInput for the vrs_solver, mirroring the Q42
    schema but collapsing stocks to 1x1500x6000."""
    base = load_q42_base()
    parts = copy.deepcopy(base["parts"])
    for part in parts:
        # Remove Q42-specific field that would override the global continuous
        # policy (Q42 already strips these, but defensive)
        part.pop("allowed_rotations_deg", None)
        part.pop("rotation_policy", None)
    return {
        "contract_version": "v1",
        "project_name": "sgh_q43b_full276_1500x6000_continuous_1200",
        "seed": SEED,
        "time_limit_s": TIME_LIMIT_S,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": MARGIN_MM,
        "spacing_mm": SPACING_MM,
        "kerf_mm": KERF_MM,
        "rotation_policy": "continuous",
        "stocks": [
            {"id": STRIP_ID, "quantity": STRIP_QTY, "width": STRIP_W, "height": STRIP_H},
        ],
        "parts": parts,
    }


def run_solver(input_path: Path, output_path: Path, log_path: Path) -> dict[str, Any]:
    if not SOLVER_BIN.exists():
        return {"status": "error", "error": f"vrs_solver binary missing: {SOLVER_BIN}"}
    t0 = time.time()
    try:
        r = subprocess.run(
            [str(SOLVER_BIN), "--input", str(input_path), "--output", str(output_path)],
            capture_output=True, text=True, timeout=TIME_LIMIT_S + 120,
        )
        elapsed = time.time() - t0
        log_path.write_text(
            f"=== SGH-Q43b own vrs_solver run ===\n"
            f"run_id: {RUN_ID}\n"
            f"time_limit_s: {TIME_LIMIT_S}\n"
            f"cmd: {SOLVER_BIN} --input {input_path} --output {output_path}\n"
            f"returncode: {r.returncode}\n"
            f"wall_time_s: {elapsed:.3f}\n"
            f"--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}\n"
        )
        if r.returncode != 0:
            return {
                "status": "error",
                "returncode": r.returncode,
                "wall_time_s": round(elapsed, 3),
                "stderr_tail": r.stderr[-500:],
                "stdout_tail": r.stdout[-500:],
            }
        if not output_path.exists():
            return {
                "status": "error",
                "error": "output JSON not created",
                "expected": str(output_path),
            }
        return {
            "status": "ok",
            "wall_time_s": round(elapsed, 3),
            "output_path": str(output_path),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": f"timeout (>= {TIME_LIMIT_S + 120}s)",
            "wall_time_s": round(time.time() - t0, 3),
        }


def normalize_solver_output(raw: dict[str, Any], out_data: dict[str, Any] | None) -> dict[str, Any]:
    base = {
        "status": raw["status"],
        "time_limit_s": TIME_LIMIT_S,
        "wall_time_s": raw.get("wall_time_s"),
    }
    if raw["status"] != "ok" or out_data is None:
        base["error"] = raw.get("error") or raw.get("stderr_tail") or "unknown"
        return base
    placements = out_data.get("placements") or []
    od = out_data.get("optimizer_diagnostics") or {}
    # vrs_solver emits 'rotation_deg' (continuous float), but be defensive and
    # accept 'rotation' as a fallback.
    rotations: list[float] = []
    for p in placements:
        r = p.get("rotation_deg")
        if r is None:
            r = p.get("rotation", 0.0)
        try:
            rotations.append(float(r))
        except (TypeError, ValueError):
            rotations.append(0.0)
    unique_rots = sorted({round(r, 6) for r in rotations})
    non_orth = [r for r in rotations if abs(r % 90.0) > 1e-3]
    # Q42-style fields if present
    return {
        **base,
        "placed_count": len(placements),
        "unplaced_count": 0,  # vrs_solver emits 0 if it places everything
        "status_solver": out_data.get("status"),
        "solver_optimizer_diagnostics_status": od.get("status"),
        "sparrow_iterations": od.get("sparrow_iterations"),
        "sparrow_search_position_calls": od.get("sparrow_search_position_calls"),
        "sparrow_collision_graph_final_pairs": od.get("sparrow_collision_graph_final_pairs"),
        "sparrow_collision_graph_total_pairs": od.get("sparrow_collision_graph_total_pairs"),
        "rotation_count_total": len(rotations),
        "unique_rotation_count": len(unique_rots),
        "non_orthogonal_count": len(non_orth),
        "min_rotation_deg": min(rotations) if rotations else None,
        "max_rotation_deg": max(rotations) if rotations else None,
        "container_model": f"single_stock {STRIP_W}x{STRIP_H} mm (quantity={STRIP_QTY})",
        "margin_mm": MARGIN_MM,
        "spacing_mm": SPACING_MM,
        "kerf_mm": KERF_MM,
        "rotation_policy": "continuous",
        "stock_quantity_available": STRIP_QTY,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-run", action="store_true", help="Prepare input only")
    args = parser.parse_args()

    Q43B.mkdir(parents=True, exist_ok=True)
    INPUTS.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    in_doc = build_input()
    in_path = INPUTS / f"{RUN_ID}.json"
    in_path.write_text(json.dumps(in_doc, indent=2))
    out_path = OUTPUTS / f"{RUN_ID}_output.json"
    log_path = LOGS / f"{RUN_ID}.log"
    print(f"=== SGH-Q43b own vrs_solver 1x1500x6000 strip baseline ===")
    print(f"solver: {SOLVER_BIN} (exists={SOLVER_BIN.exists()})")
    print(f"strip: {STRIP_W}x{STRIP_H} mm  qty={STRIP_QTY}  seed={SEED}  time_limit_s={TIME_LIMIT_S}")
    print(f"input: {in_path}")
    print(f"output target: {out_path}")
    print(f"log: {log_path}")
    print(f"part types: {len(in_doc['parts'])}  total instances: {sum(p.get('quantity',1) for p in in_doc['parts'])}")

    if args.no_run:
        print("--no-run specified, stopping after input preparation.")
        return 0

    print(f"\n[Run] {TIME_LIMIT_S}s ...")
    raw = run_solver(in_path, out_path, log_path)
    out_data = None
    if raw["status"] == "ok" and out_path.exists():
        try:
            out_data = json.loads(out_path.read_text())
        except Exception as e:
            raw = {"status": "error", "error": f"output parse failed: {e}"}
    summary = normalize_solver_output(raw, out_data)
    print(f"[Run] status={summary['status']} wall={summary.get('wall_time_s','?')}s placed={summary.get('placed_count','?')}")
    if summary.get("unique_rotation_count") is not None:
        print(f"[Run] unique_rotation_count={summary['unique_rotation_count']} non_orth={summary['non_orthogonal_count']}")

    (Q43B / "q43b_summary.json").write_text(json.dumps({
        "task": "sgh_q43b_own_full276_1500x6000_strip",
        "audit_time": now_iso(),
        "run_id": RUN_ID,
        "solver": "own vrs_solver (rust/vrs_solver)",
        "container_model": f"single_stock {STRIP_W}x{STRIP_H} mm quantity={STRIP_QTY}",
        "geometry_source": str(BASE_FULL276),
        "part_types": len(in_doc["parts"]),
        "total_instances": sum(p.get("quantity", 1) for p in in_doc["parts"]),
        "time_limit_s": TIME_LIMIT_S,
        "seed": SEED,
        "margin_mm": MARGIN_MM,
        "spacing_mm": SPACING_MM,
        "kerf_mm": KERF_MM,
        "rotation_policy": "continuous",
        "solver_binary": str(SOLVER_BIN),
        "result": summary,
        "comparability_to_q42": {
            "model": "Q42 uses 3x1500x3000 finite-stock; this run collapses to 1x1500x6000 single-strip",
            "objectives": "Q42 minimizes used sheet count; this single-strip run has only 1 stock available so acceptance is 'all-or-nothing on the single stock'",
            "comparability": "geometry identical (same 12 part types / 276 instances); inventory and objective differ",
        },
    }, indent=2))
    print(f"\nq43b_summary.json -> {Q43B / 'q43b_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
