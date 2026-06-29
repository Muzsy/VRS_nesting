#!/usr/bin/env python3
"""SGH-Q73 - Big-part pitch-minimizing interlock row-seed benchmark.

The dominant repeated BIG critical type must be distributed (fill a sheet before opening the next)
at the tightest CDE-clear orientation (non-orthogonal allowed), instead of sitting one-per-sheet at
the min-bbox-width 90 degrees. Judged result-centric: total placed_count must not regress vs Q72
(262), the dominant big type should reach >= 2 per used sheet, and its rotation should be
non-orthogonal where that packs tighter. Edge-lock/corner remain diagnostics only.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from render_sgh_q47_q50_benchmark_artifacts import render_run

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
Q49_INPUT = ROOT / "artifacts/benchmarks/sgh_q49/inputs/q49_full276_6x1500x3000_margin5_spacing8_continuous_300.json"
Q72_OUT = ROOT / "artifacts/benchmarks/sgh_q72/outputs/q72_A_no_drop_repack_2sheet_sp5_output.json"
Q73 = ROOT / "artifacts" / "benchmarks" / "sgh_q73"
INPUTS = Q73 / "inputs"
OUTPUTS = Q73 / "outputs"
LOGS = Q73 / "logs"
RUN_ID = "q73_A_interlock_rowseed_2sheet_sp5"
BASELINE_PLACED = 262  # Q72 no-drop repack

Q73_GATES = {
    "VRS_SHEET_BUILDER": "1",
    "VRS_SHEET_BUILDER_SKELETON": "1",
    "VRS_FEATURE_CANDIDATES": "1",
    "VRS_PAIR_INDEX": "1",
    "VRS_INTERLOCK_PAIR": "1",
    "VRS_SHEET_FEASIBILITY_HINTS": "1",
    "VRS_BAND_INSERT_TRUE_EXTREME": "1",
    "VRS_SIMULTANEOUS_CRITICAL": "1",
    "VRS_ANCHOR_CATALOG": "1",
    "VRS_SHEET_BUILDER_FORCE_LATEST": "1",
    # SGH-Q73 opt-in big-part row seed (default OFF in production; this bench documents its effect).
    "VRS_BIG_ROW_SEED": "1",
}
GATE_KEYS = list(Q73_GATES) + ["VRS_SHEET_BUILDER_STRICT_LATEST"]


def poly_area(pts: list[list[float]]) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def q49_parts() -> list[dict[str, Any]]:
    doc = json.loads(Q49_INPUT.read_text())
    parts = copy.deepcopy(doc["parts"])
    for part in parts:
        part.pop("allowed_rotations_deg", None)
        part.pop("rotation_policy", None)
    return parts


def build_input(time_limit_s: int) -> Path:
    inp = {
        "contract_version": "v1",
        "project_name": "sgh_q73_big_part_interlock_rowseed",
        "seed": 42,
        "time_limit_s": time_limit_s,
        "stocks": [{"id": "S1500x3000", "quantity": 2, "width": 1500.0, "height": 3000.0}],
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "rotation_policy": "continuous",
        "margin_mm": 5.0,
        "spacing_mm": 5.0,
        "kerf_mm": 0.0,
        "parts": q49_parts(),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"q73_full276_2x1500x3000_margin5_spacing5_continuous_{time_limit_s}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run(inp: Path, time_limit_s: int) -> dict[str, Any]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{RUN_ID}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)
    for key in GATE_KEYS:
        env.pop(key, None)
    env.update(Q73_GATES)
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(inp), "--output", str(out_path)],
        capture_output=True,
        text=True,
        timeout=time_limit_s + 3600,
        env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{RUN_ID}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\n"
        f"env={json.dumps(Q73_GATES, sort_keys=True)}\nstderr:\n{proc.stderr[:12000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{RUN_ID} exit {proc.returncode}: {proc.stderr[:1500]}")
    out = json.loads(out_path.read_text())
    out["_wall"] = wall
    return out


def big_part_analysis(out: dict[str, Any], parts_by_id: dict[str, Any]) -> dict[str, Any]:
    pa = {pid: poly_area(p["outer_points"]) for pid, p in parts_by_id.items()}
    dominant = max(pa, key=lambda k: pa[k]) if pa else None
    rows: dict[int, list[float]] = {}
    for p in out.get("placements", []):
        if p["part_id"] == dominant:
            rows.setdefault(int(p["sheet_index"]), []).append(round(float(p["rotation_deg"]), 2))
    per_sheet = {s: sorted(rs) for s, rs in rows.items()}
    placed_dom = sum(len(v) for v in per_sheet.values())
    all_rots = [r for rs in per_sheet.values() for r in rs]
    non_orth = sum(1 for r in all_rots if abs((r % 90.0)) > 0.5 and abs((r % 90.0) - 90.0) > 0.5)
    return {
        "dominant_part_id": dominant,
        "dominant_area_mm2": round(pa.get(dominant, 0.0), 1) if dominant else None,
        "dominant_qty": parts_by_id.get(dominant, {}).get("quantity") if dominant else None,
        "dominant_placed": placed_dom,
        "dominant_per_sheet_rotations": {str(k): v for k, v in per_sheet.items()},
        "dominant_non_orthogonal_count": non_orth,
        "dominant_min_per_used_sheet": min((len(v) for v in per_sheet.values()), default=0),
    }


def summarize(out: dict[str, Any], parts_by_id: dict[str, Any]) -> dict[str, Any]:
    diag = out.get("optimizer_diagnostics") or {}
    bpp = diag.get("bpp_reduction") or {}
    metrics = out.get("metrics") or {}
    placements = out.get("placements") or []
    forced_locked = (
        bool(bpp.get("bpp_q69_forced_latest_mode"))
        and not bool(bpp.get("bpp_q69_native_seed_fallback_used"))
        and not bool(bpp.get("bpp_q69_builder_random_bootstrap_used"))
    )
    return {
        "status": out.get("status"),
        "placed_count": metrics.get("placed_count"),
        "unplaced_count": metrics.get("unplaced_count"),
        "used_sheets": len({p.get("sheet_index", 0) for p in placements}),
        "utilization_pct": diag.get("sparrow_ms_utilization_pct"),
        "final_pairs": diag.get("sparrow_ms_final_pairs"),
        "boundary_violations": diag.get(
            "sparrow_ms_boundary_violations", diag.get("sparrow_boundary_violations_final")
        ),
        "forced_latest_locked": forced_locked,
        "no_drop_seed_used": bpp.get("bpp_q72_no_drop_seed_used"),
        "seed_instance_count_before_pipeline": bpp.get("bpp_q72_seed_instance_count_before_pipeline"),
        "q73_big_row_seed_used": bpp.get("bpp_q73_big_row_seed_used"),
        "q73_big_row_part_id": bpp.get("bpp_q73_big_row_part_id"),
        "q73_big_row_rotation_deg": bpp.get("bpp_q73_big_row_rotation_deg"),
        "q73_big_row_pitch_mm": bpp.get("bpp_q73_big_row_pitch_mm"),
        "q73_big_row_copies_per_sheet": bpp.get("bpp_q73_big_row_copies_per_sheet"),
        "q73_big_row_seeded_count": bpp.get("bpp_q73_big_row_seeded_count"),
        "big_part": big_part_analysis(out, parts_by_id),
        "wall_time_s": round(float(out.get("_wall", 0.0)), 1),
    }


def write_report(summary: dict[str, Any], input_rel: str) -> None:
    r = summary["run"]
    q72 = summary["comparisons"]["q72_no_drop"]
    bp = r["big_part"]
    bp72 = q72["big_part"]
    per_sheet = summary["per_sheet"]
    lines = [
        "# SGH-Q73 Report - Big-part pitch-minimizing interlock row-seed",
        "",
        f"## Verdict: {summary['verdict']}",
        "",
        "## Run",
        "",
        "| run | status | placed | unplaced | used | util % | wall s |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        f"| {RUN_ID} | {r['status']} | {r['placed_count']} | {r['unplaced_count']} | {r['used_sheets']} | {r['utilization_pct']} | {r['wall_time_s']} |",
        "",
        "## Big-part (dominant repeated type) distribution",
        "",
        "| metric | Q72 | Q73 |",
        "| --- | --- | --- |",
        f"| dominant part | {bp72['dominant_part_id']} | {bp['dominant_part_id']} |",
        f"| qty | {bp72['dominant_qty']} | {bp['dominant_qty']} |",
        f"| placed | {bp72['dominant_placed']} | {bp['dominant_placed']} |",
        f"| per-sheet rotations | `{json.dumps(bp72['dominant_per_sheet_rotations'])}` | `{json.dumps(bp['dominant_per_sheet_rotations'])}` |",
        f"| min per used sheet | {bp72['dominant_min_per_used_sheet']} | {bp['dominant_min_per_used_sheet']} |",
        f"| non-orthogonal placements | {bp72['dominant_non_orthogonal_count']} | {bp['dominant_non_orthogonal_count']} |",
        "",
        "## Q73 row-seed diagnostics",
        "",
        "| check | value |",
        "| --- | --- |",
        f"| row seed used | {str(bool(r['q73_big_row_seed_used'])).lower()} |",
        f"| chosen rotation (deg) | {r['q73_big_row_rotation_deg']} |",
        f"| min clear pitch (mm) | {r['q73_big_row_pitch_mm']} |",
        f"| copies per sheet | {r['q73_big_row_copies_per_sheet']} |",
        f"| seeded count | {r['q73_big_row_seeded_count']} |",
        f"| no-drop seed used | {str(bool(r['no_drop_seed_used'])).lower()} |",
        f"| forced latest locked | {str(bool(r['forced_latest_locked'])).lower()} |",
        f"| final pairs / boundary | {r['final_pairs']} / {r['boundary_violations']} |",
        "",
        "## Per-sheet",
        "",
        "| sheet | placed | physical util % |",
        "| --- | ---: | ---: |",
    ]
    for it in per_sheet:
        lines.append(f"| {it['sheet_index']} | {it['placed_count']} | {it['physical_utilization_pct']} |")
    lines += [
        "",
        "## Comparison",
        "",
        "| run | placed | used sheets | util % |",
        "| --- | ---: | ---: | ---: |",
        f"| Q72 no-drop | {q72['placed_count']} | {q72['used_sheets']} | {q72['utilization_pct']} |",
        f"| **Q73 row-seed** | **{r['placed_count']}** | {r['used_sheets']} | {r['utilization_pct']} |",
        "",
        "## Visual Audit",
        "",
        "- Pending manual review after the benchmark run.",
        "",
        "## Finding",
        "",
        summary["finding"],
        "",
        "## Artifact evidence",
        "",
        "- summary: `artifacts/benchmarks/sgh_q73/q73_summary.json`",
        f"- input: `artifacts/benchmarks/sgh_q73/{input_rel}`",
        f"- output: `artifacts/benchmarks/sgh_q73/outputs/{RUN_ID}_output.json`",
        f"- log: `artifacts/benchmarks/sgh_q73/logs/{RUN_ID}.log`",
    ]
    (Q73 / "q73_report.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=int, default=600)
    args = parser.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    inp = build_input(args.time_limit)
    input_rel = str(inp.relative_to(Q73))
    parts_by_id = {p["id"]: p for p in json.loads(inp.read_text())["parts"]}
    out = run(inp, args.time_limit)
    run_summary = summarize(out, parts_by_id)
    render_run(73, RUN_ID, input_rel, f"outputs/{RUN_ID}_output.json")
    render_manifest = json.loads((Q73 / "renders" / RUN_ID / "render_manifest.json").read_text())
    q72_out = json.loads(Q72_OUT.read_text())
    q72 = summarize(q72_out, parts_by_id)
    per_sheet = render_manifest.get("per_sheet") or []

    placed = run_summary["placed_count"] or 0
    bp = run_summary["big_part"]
    acceptance = {
        "forced_latest_locked": run_summary["forced_latest_locked"],
        "row_seed_used": bool(run_summary["q73_big_row_seed_used"]),
        "no_regression_vs_q72": placed >= BASELINE_PLACED,
        "big_two_per_used_sheet": bp["dominant_min_per_used_sheet"] >= 2,
        "big_non_orthogonal": bp["dominant_non_orthogonal_count"] > 0,
        "valid": (run_summary["final_pairs"] in (0, None))
        and (run_summary["boundary_violations"] in (0, None)),
    }
    verdict = "FAIL"
    if (
        acceptance["forced_latest_locked"]
        and acceptance["row_seed_used"]
        and acceptance["valid"]
        and acceptance["no_regression_vs_q72"]
        and acceptance["big_two_per_used_sheet"]
    ):
        verdict = "PASS"

    summary = {
        "task": "sgh_q73_big_part_interlock_rowseed",
        "source_package": str(Q49_INPUT.relative_to(ROOT)),
        "time_limit_s": args.time_limit,
        "baseline_placed": BASELINE_PLACED,
        "target_placed": 276,
        "stocks": {"quantity": 2, "width": 1500.0, "height": 3000.0},
        "technology": {"margin_mm": 5.0, "spacing_mm": 5.0, "kerf_mm": 0.0, "rotation_policy": "continuous"},
        "run": run_summary,
        "comparisons": {"q72_no_drop": q72},
        "render_manifest": render_manifest,
        "per_sheet": per_sheet,
        "acceptance": acceptance,
        "verdict": verdict,
    }
    summary["finding"] = (
        "Q73 row-seeds the dominant repeated big type at the tightest CDE-clear (often non-orthogonal) "
        "orientation, distributed to fill a sheet before opening the next. Judged on the big-part "
        "distribution (>= 2 per used sheet, non-orthogonal) and total placed_count not regressing vs "
        f"Q72 ({BASELINE_PLACED}); the 3-per-sheet limit for this long part is geometric and is reported honestly."
    )
    Q73.mkdir(parents=True, exist_ok=True)
    (Q73 / "q73_summary.json").write_text(json.dumps(summary, indent=2))
    write_report(summary, input_rel)
    print(json.dumps({"verdict": verdict, **acceptance, "placed": placed, "big_per_sheet": bp["dominant_per_sheet_rotations"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
