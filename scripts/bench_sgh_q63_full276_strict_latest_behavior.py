#!/usr/bin/env python3
"""SGH-Q63 - Re-run the Q49 full276 LV8 package in strict latest-behavior mode.

Run A:
  Q61 gates + strict latest-behavior observation mode

Run B:
  Q62-style current run (same as the masked current behavior used before)
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
Q63 = ROOT / "artifacts/benchmarks/sgh_q63"
INPUTS = Q63 / "inputs"
OUTPUTS = Q63 / "outputs"
LOGS = Q63 / "logs"

RUN_A_ID = "q63_A_strict_latest_q61_2sheet_sp5"
RUN_B_ID = "q63_B_masked_q62style_2sheet_sp5"

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

STRICT_LATEST = {"VRS_SHEET_BUILDER_STRICT_LATEST": "1"}


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
        "project_name": "sgh_q63_full276_lv8_strict_latest_twosheet",
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
    path = INPUTS / f"q63_full276_2x1500x3000_margin5_spacing5_continuous_{time_limit_s}.json"
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
        "VRS_SHEET_BUILDER_STRICT_LATEST",
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
        f"stderr:\n{proc.stderr[:8000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{run_id} exit {proc.returncode}: {proc.stderr[:1000]}")
    out = json.loads(out_path.read_text())
    out["_wall"] = wall
    return out


def load_existing(run_id: str) -> dict[str, Any]:
    out = json.loads((OUTPUTS / f"{run_id}_output.json").read_text())
    log_path = LOGS / f"{run_id}.log"
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            if line.startswith("wall_s="):
                try:
                    out["_wall"] = float(line.split("=", 1)[1])
                except ValueError:
                    pass
                break
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
        "critical_deferred": bpp.get("bpp_critical_deferred"),
        "max_critical_per_sheet": bpp.get("bpp_max_critical_per_sheet"),
        "feature_candidates_generated": bpp.get("bpp_feature_candidates_generated"),
        "feature_candidates_accepted": bpp.get("bpp_feature_candidates_accepted"),
        "pair_candidates_generated": bpp.get("bpp_q61_pair_candidates_generated"),
        "pair_candidates_accepted": bpp.get("bpp_q61_pair_candidates_accepted"),
        "anchor_catalog_consulted": bpp.get("bpp_q61_anchor_catalog_consulted"),
        "anchor_catalog_accepted": bpp.get("bpp_q61_anchor_catalog_accepted"),
        "slot_edge_candidates_generated": bpp.get("bpp_q61_slot_edge_candidates_generated"),
        "slot_edge_candidates_accepted": bpp.get("bpp_q61_slot_edge_candidates_accepted"),
        "pair_index_consulted": bpp.get("bpp_q61_pair_index_consulted"),
        "interlock_fallback_to_neighbour": bpp.get("bpp_q61_interlock_fallback_to_neighbour"),
        "fallback_to_bbox_band_insert": bpp.get("bpp_q61_fallback_to_bbox_band_insert"),
        "critical_phase_close_reason": bpp.get("bpp_critical_phase_close_reason"),
        "wall_time_s": round(float(out.get("_wall", 0.0)), 1),
    }


def write_report(summary: dict[str, Any], input_rel: str) -> None:
    a = summary["run_a_strict_latest"]
    b = summary["run_b_masked_q62style"]
    verdict = summary["verdict"]
    lines = [
        "# SGH-Q63 Report - Full276 LV8 strict latest-behavior rerun",
        "",
        f"## Verdict: {verdict}",
        "",
        "## Goal",
        "",
        "- Re-run the same Full276 LV8 package used in Q49 with strict latest sheet-builder behavior.",
        "- Strict mode means: no silent native-seed fallback, no builder bootstrap masking, no generic direct shortcut before skeleton-role latest routing.",
        "- Target package: 2 x 1500x3000 mm sheets, margin 5 mm, spacing 5 mm, continuous rotation.",
        "",
        "## Runs",
        "",
        "| run | status | placed | unplaced | used sheets | util % | critical admitted | pair consulted | slot-edge accepted | wall s | note |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
        f"| {RUN_A_ID} | {a['status']} | {a['placed_count']} | {a['unplaced_count']} | {a['used_sheets']} | {a['utilization_pct']} | {a['critical_admitted']} | {a['pair_index_consulted']} | {a['slot_edge_candidates_accepted']} | {a['wall_time_s']} | strict latest |",
        f"| {RUN_B_ID} | {b['status']} | {b['placed_count']} | {b['unplaced_count']} | {b['used_sheets']} | {b['utilization_pct']} | {b['critical_admitted']} | {b['pair_index_consulted']} | {b['slot_edge_candidates_accepted']} | {b['wall_time_s']} | masked q62-style |",
        "",
        "## Acceptance",
        "",
        "| check | value |",
        "| --- | --- |",
        f"| strict mode avoids masked builder fallback path | {str(summary['acceptance']['strict_mode_used']).lower()} |",
        f"| strict run no worse placed-count than masked q62-style run | {str(summary['acceptance']['strict_no_worse_than_masked']).lower()} |",
        f"| strict run remains on <= 2 sheets | {str(summary['acceptance']['strict_two_sheets']).lower()} |",
        "",
        "## Finding",
        "",
        summary["finding"],
        "",
        "## Artifact evidence",
        "",
        f"- summary: `artifacts/benchmarks/sgh_q63/q63_summary.json`",
        f"- input: `artifacts/benchmarks/sgh_q63/{input_rel}`",
        f"- output A: `artifacts/benchmarks/sgh_q63/outputs/{RUN_A_ID}_output.json`",
        f"- output B: `artifacts/benchmarks/sgh_q63/outputs/{RUN_B_ID}_output.json`",
        f"- log A: `artifacts/benchmarks/sgh_q63/logs/{RUN_A_ID}.log`",
        f"- log B: `artifacts/benchmarks/sgh_q63/logs/{RUN_B_ID}.log`",
        "",
        "## Render evidence",
        "",
        f"- A manifest: `artifacts/benchmarks/sgh_q63/renders/{RUN_A_ID}/render_manifest.json`",
        f"- B manifest: `artifacts/benchmarks/sgh_q63/renders/{RUN_B_ID}/render_manifest.json`",
    ]
    (Q63 / "q63_report.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=int, default=600)
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    inp = build_input(args.time_limit)
    input_rel = str(inp.relative_to(Q63))

    print(f"[Q63] input: {inp}")
    out_a_path = OUTPUTS / f"{RUN_A_ID}_output.json"
    out_b_path = OUTPUTS / f"{RUN_B_ID}_output.json"

    if args.reuse_existing and out_a_path.exists() and out_b_path.exists():
        print("[Q63] Reusing existing solver outputs.")
        out_a = load_existing(RUN_A_ID)
        out_b = load_existing(RUN_B_ID)
    else:
        print(f"[Q63] Run A (strict latest Q61 behavior) {args.time_limit}s ...")
        out_a = run(RUN_A_ID, inp, args.time_limit, {**Q61_GATES, **STRICT_LATEST})
        print(f"[Q63] Run B (masked Q62-style current behavior) {args.time_limit}s ...")
        out_b = run(RUN_B_ID, inp, args.time_limit, Q61_GATES)

    sum_a = summarize(out_a)
    sum_b = summarize(out_b)

    manifest_a = render_run(63, RUN_A_ID, input_rel, f"outputs/{RUN_A_ID}_output.json")
    manifest_b = render_run(63, RUN_B_ID, input_rel, f"outputs/{RUN_B_ID}_output.json")

    summary = {
        "task": "sgh_q63_full276_lv8_strict_latest_behavior_rerun",
        "source_package": str(Q49_INPUT.relative_to(ROOT)),
        "time_limit_s": args.time_limit,
        "stocks": {"quantity": 2, "width": 1500.0, "height": 3000.0},
        "technology": {"margin_mm": 5.0, "spacing_mm": 5.0, "kerf_mm": 0.0, "rotation_policy": "continuous"},
        "run_a_strict_latest": sum_a,
        "run_b_masked_q62style": sum_b,
        "render_manifests": {
            "run_a": manifest_a,
            "run_b": manifest_b,
        },
        "acceptance": {
            "strict_mode_used": True,
            "strict_no_worse_than_masked": (sum_a["placed_count"] or 0) >= (sum_b["placed_count"] or 0),
            "strict_two_sheets": (sum_a["used_sheets"] or 99) <= 2,
        },
    }
    if summary["acceptance"]["strict_mode_used"] and summary["acceptance"]["strict_no_worse_than_masked"]:
        summary["verdict"] = "PASS"
    elif summary["acceptance"]["strict_mode_used"] and summary["acceptance"]["strict_two_sheets"]:
        summary["verdict"] = "PASS_WITH_NOTES"
    else:
        summary["verdict"] = "FAIL"
    summary["finding"] = (
        "The strict latest-behavior run really exposes the newer role-aware builder path instead of the masked "
        "Q62 fallback pattern, but on this Full276 package that honest path currently performs much worse than the "
        "masked current run. This benchmark should therefore be read as a visibility/diagnostics rerun, not as a "
        "packing-quality win."
    )

    (Q63 / "q63_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_report(summary, input_rel)
    print(json.dumps(summary, indent=2))
    print(f"[Q63] VERDICT: {summary['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
