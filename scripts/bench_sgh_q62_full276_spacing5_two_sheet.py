#!/usr/bin/env python3
"""SGH-Q62 - Re-run the Q49 full276 LV8 package on the current Q61 solver behavior.

Target configuration:
  - 276 parts
  - 2 x 1500x3000 mm sheets
  - margin 5 mm
  - spacing 5 mm
  - continuous rotation

Artifacts mirror the Q49 benchmark shape:
  - inputs/
  - outputs/
  - logs/
  - q62_summary.json
  - q62_report.md
  - renders/

Run A:
  current Q61 production-wiring gates enabled

Run B:
  builder-only baseline on the same 2-sheet / spacing-5 input
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

from render_sgh_q47_q50_benchmark_artifacts import render_run

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
Q49_INPUT = ROOT / "artifacts/benchmarks/sgh_q49/inputs/q49_full276_6x1500x3000_margin5_spacing8_continuous_300.json"
Q62 = ROOT / "artifacts/benchmarks/sgh_q62"
INPUTS = Q62 / "inputs"
OUTPUTS = Q62 / "outputs"
LOGS = Q62 / "logs"

RUN_A_ID = "q62_A_current_q61_2sheet_sp5"
RUN_B_ID = "q62_B_builderonly_2sheet_sp5"

Q61_GATES = {
    "VRS_SHEET_BUILDER": "1",
    "VRS_SHEET_BUILDER_SKELETON": "1",
    "VRS_FEATURE_CANDIDATES": "1",
    "VRS_PAIR_INDEX": "1",
    "VRS_INTERLOCK_PAIR": "1",
    "VRS_SHEET_FEASIBILITY_HINTS": "1",
    "VRS_BAND_INSERT_TRUE_EXTREME": "1",
    "VRS_SIMULTANEOUS_CRITICAL": "1",
    "VRS_ANCHOR_CATALOG": "1",
}


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
        "project_name": "sgh_q62_full276_lv8_spacing5_twosheet",
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
    path = INPUTS / f"q62_full276_2x1500x3000_margin5_spacing5_continuous_{time_limit_s}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run(run_id: str, inp: Path, time_limit_s: int, env_updates: dict[str, str]) -> dict[str, Any]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{run_id}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)
    for key in [
        "VRS_SHEET_BUILDER",
        "VRS_SHEET_BUILDER_SKELETON",
        "VRS_FEATURE_CANDIDATES",
        "VRS_PAIR_INDEX",
        "VRS_INTERLOCK_PAIR",
        "VRS_SHEET_FEASIBILITY_HINTS",
        "VRS_BAND_INSERT_TRUE_EXTREME",
        "VRS_SIMULTANEOUS_CRITICAL",
        "VRS_ANCHOR_CATALOG",
    ]:
        env.pop(key, None)
    env.update(env_updates)

    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(inp), "--output", str(out_path)],
        capture_output=True,
        text=True,
        timeout=time_limit_s + 3600,
        env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{run_id}.log").write_text(
        f"exit={proc.returncode}\n"
        f"wall_s={wall:.3f}\n"
        f"env={json.dumps(env_updates, sort_keys=True)}\n"
        f"stderr:\n{proc.stderr[:5000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{run_id} exit {proc.returncode}: {proc.stderr[:1000]}")
    out = json.loads(out_path.read_text())
    out["_wall"] = wall
    return out


def summarize(out: dict[str, Any]) -> dict[str, Any]:
    diag = out.get("optimizer_diagnostics") or {}
    bpp = diag.get("bpp_reduction") or {}
    metrics = out.get("metrics") or {}
    placements = out.get("placements") or []
    return {
        "status": out.get("status"),
        "placed_count": metrics.get("placed_count"),
        "unplaced_count": metrics.get("unplaced_count"),
        "used_sheets": len({p.get("sheet_index", 0) for p in placements}),
        "utilization_pct": diag.get("sparrow_ms_utilization_pct"),
        "final_pairs": diag.get("sparrow_ms_final_pairs"),
        "boundary_violations": diag.get("sparrow_ms_boundary_violations", diag.get("sparrow_boundary_violations_final")),
        "builder_applied": bpp.get("bpp_sheet_builder_applied"),
        "critical_admitted": bpp.get("bpp_critical_admitted"),
        "max_critical_per_sheet": bpp.get("bpp_max_critical_per_sheet"),
        "feature_candidates_generated": bpp.get("bpp_feature_candidates_generated"),
        "feature_candidates_accepted": bpp.get("bpp_feature_candidates_accepted"),
        "pair_candidates_generated": bpp.get("bpp_q61_pair_candidates_generated"),
        "pair_candidates_accepted": bpp.get("bpp_q61_pair_candidates_accepted"),
        "anchor_catalog_consulted": bpp.get("bpp_q61_anchor_catalog_consulted"),
        "best_partial_max_critical_count": bpp.get("bpp_q61_best_partial_max_critical_count"),
        "simultaneous_group_attempts": bpp.get("bpp_q61_simultaneous_group_attempts"),
        "pair_rejection_summary": bpp.get("bpp_q61_pair_rejection_summary"),
        "critical_phase_close_reason": bpp.get("bpp_critical_phase_close_reason"),
        "wall_time_s": round(float(out.get("_wall", 0.0)), 1),
    }


def write_report(summary: dict[str, Any], input_rel: str) -> None:
    a = summary["run_a_current_q61"]
    b = summary["run_b_builder_only"]
    verdict = summary["verdict"]
    lines = [
        "# SGH-Q62 Report - Full276 LV8 spacing-5 / 2-sheet rerun",
        "",
        f"## Verdict: {verdict}",
        "",
        "## Goal",
        "",
        "- Re-run the same Full276 LV8 package used in Q49 with the current Q61-wired solver behavior.",
        "- Target: place all 276 parts onto 2 x 1500x3000 mm sheets with margin 5 mm and spacing 5 mm.",
        "- Save Q49-shaped benchmark artifacts: input, raw outputs, logs, summary, report, and renders.",
        "",
        "## Runs",
        "",
        "| run | status | placed | unplaced | used sheets | util % | final pairs | max critical/sheet | feature accepted | pair generated | wall s | acceptance |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run_id, row in (
        (RUN_A_ID, a),
        (RUN_B_ID, b),
    ):
        accepted = "PASS" if row["status"] == "ok" and row["placed_count"] == 276 and row["used_sheets"] <= 2 and (row["final_pairs"] or 0) == 0 else "FAIL"
        lines.append(
            f"| {run_id} | {row['status']} | {row['placed_count']} | {row['unplaced_count']} | "
            f"{row['used_sheets']} | {row['utilization_pct']} | {row['final_pairs']} | "
            f"{row['max_critical_per_sheet']} | {row['feature_candidates_accepted']} | "
            f"{row['pair_candidates_generated']} | {row['wall_time_s']} | {accepted} |"
        )
    lines.extend(
        [
            "",
            "## Acceptance",
            "",
            "| check | value |",
            "| --- | --- |",
            f"| current solver full valid 276 | {str(summary['acceptance']['current_solver_valid_276']).lower()} |",
            f"| current solver reached <= 2 sheets | {str(summary['acceptance']['current_solver_two_sheets']).lower()} |",
            f"| baseline valid | {str(summary['acceptance']['baseline_valid']).lower()} |",
            f"| current solver no worse placed-count than baseline | {str(summary['acceptance']['no_worse_than_baseline_on_placed']).lower()} |",
            "",
            "## Finding",
            "",
            summary["finding"],
            "",
            "## Artifact evidence",
            "",
            f"- summary: `artifacts/benchmarks/sgh_q62/q62_summary.json`",
            f"- input: `artifacts/benchmarks/sgh_q62/{input_rel}`",
            f"- output A: `artifacts/benchmarks/sgh_q62/outputs/{RUN_A_ID}_output.json`",
            f"- output B: `artifacts/benchmarks/sgh_q62/outputs/{RUN_B_ID}_output.json`",
            f"- log A: `artifacts/benchmarks/sgh_q62/logs/{RUN_A_ID}.log`",
            f"- log B: `artifacts/benchmarks/sgh_q62/logs/{RUN_B_ID}.log`",
            "",
            "## Render evidence",
            "",
            f"- A manifest: `artifacts/benchmarks/sgh_q62/renders/{RUN_A_ID}/render_manifest.json`",
            f"- B manifest: `artifacts/benchmarks/sgh_q62/renders/{RUN_B_ID}/render_manifest.json`",
        ]
    )
    (Q62 / "q62_report.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=int, default=600)
    args = parser.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    inp = build_input(args.time_limit)
    input_rel = str(inp.relative_to(Q62))

    print(f"[Q62] input: {inp}")
    print(f"[Q62] Run A (current Q61 solver behavior) {args.time_limit}s ...")
    out_a = run(RUN_A_ID, inp, args.time_limit, Q61_GATES)
    print(f"[Q62] Run B (builder-only baseline) {args.time_limit}s ...")
    out_b = run(RUN_B_ID, inp, args.time_limit, {"VRS_SHEET_BUILDER": "1"})

    sum_a = summarize(out_a)
    sum_b = summarize(out_b)

    valid_a = sum_a["status"] == "ok" and sum_a["placed_count"] == 276 and (sum_a["final_pairs"] or 0) == 0 and (sum_a["boundary_violations"] or 0) == 0
    two_sheets_a = valid_a and sum_a["used_sheets"] <= 2
    valid_b = sum_b["status"] == "ok" and (sum_b["final_pairs"] or 0) == 0 and (sum_b["boundary_violations"] or 0) == 0
    no_worse = (sum_a["placed_count"] or 0) >= (sum_b["placed_count"] or 0)

    summary = {
        "task": "sgh_q62_full276_lv8_spacing5_two_sheet_rerun",
        "source_package": str(Q49_INPUT.relative_to(ROOT)),
        "time_limit_s": args.time_limit,
        "stocks": {"quantity": 2, "width": 1500.0, "height": 3000.0},
        "technology": {"margin_mm": 5.0, "spacing_mm": 5.0, "kerf_mm": 0.0, "rotation_policy": "continuous"},
        "run_a_current_q61": sum_a,
        "run_b_builder_only": sum_b,
        "acceptance": {
            "current_solver_valid_276": valid_a,
            "current_solver_two_sheets": two_sheets_a,
            "baseline_valid": valid_b,
            "no_worse_than_baseline_on_placed": no_worse,
        },
    }
    summary["verdict"] = "PASS" if two_sheets_a else "FAIL"
    if summary["verdict"] == "PASS":
        summary["finding"] = (
            "The current Q61-wired solver reached a full valid 276-part layout within 2 sheets at "
            "spacing 5 / margin 5 on the Q49 full276 LV8 package."
        )
    else:
        summary["finding"] = (
            "The current Q61-wired solver did not reach the requested 2-sheet full-valid target on "
            "the Q49 full276 LV8 package at spacing 5 / margin 5. The saved diagnostics capture the "
            "actual placed-count, used-sheet count, and Q61 critical-admission counters."
        )

    Q62.mkdir(parents=True, exist_ok=True)
    (Q62 / "q62_summary.json").write_text(json.dumps(summary, indent=2))

    manifest_a = render_run(62, RUN_A_ID, input_rel, f"outputs/{RUN_A_ID}_output.json")
    manifest_b = render_run(62, RUN_B_ID, input_rel, f"outputs/{RUN_B_ID}_output.json")
    if not all(m["png_count"] == m["svg_count"] for m in (manifest_a, manifest_b)):
        raise SystemExit("not all SVG renders have matching PNG outputs")

    write_report(summary, input_rel)

    print(json.dumps(summary, indent=2))
    print(f"[Q62] VERDICT: {summary['verdict']}")
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
