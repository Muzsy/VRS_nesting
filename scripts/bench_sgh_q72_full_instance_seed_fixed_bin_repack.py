#!/usr/bin/env python3
"""SGH-Q72 - Full-instance seed + fixed-bin global repack benchmark.

The forced-latest path must retain EVERY instance in the seed (no-drop) and then let the real
exploration SA + redistribute pipeline pack them on the fixed 2 sheets. Success is judged ONLY on
placed_count: the run must beat the Q62 native+full-pipeline baseline (259). Edge-lock / corner /
residual metrics are diagnostics, never acceptance gates.
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
Q62_OUT = ROOT / "artifacts/benchmarks/sgh_q62/outputs/q62_A_current_q61_2sheet_sp5_output.json"
Q70_OUT = ROOT / "artifacts/benchmarks/sgh_q70/outputs/q70_A_corner_first_2sheet_sp5_output.json"
Q71_OUT = ROOT / "artifacts/benchmarks/sgh_q71/outputs/q71_A_edge_lock_2sheet_sp5_output.json"
Q72 = ROOT / "artifacts" / "benchmarks" / "sgh_q72"
INPUTS = Q72 / "inputs"
OUTPUTS = Q72 / "outputs"
LOGS = Q72 / "logs"
RUN_ID = "q72_A_no_drop_repack_2sheet_sp5"

# The baseline the forced-latest path currently regresses against. Q72 must beat it.
BASELINE_PLACED = 259

Q72_GATES = {
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
}

GATE_KEYS = list(Q72_GATES) + ["VRS_SHEET_BUILDER_STRICT_LATEST"]


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
        "project_name": "sgh_q72_full_instance_seed_fixed_bin_repack",
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
    path = INPUTS / f"q72_full276_2x1500x3000_margin5_spacing5_continuous_{time_limit_s}.json"
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
    env.update(Q72_GATES)

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
        f"exit={proc.returncode}\n"
        f"wall_s={wall:.3f}\n"
        f"env={json.dumps(Q72_GATES, sort_keys=True)}\n"
        f"stderr:\n{proc.stderr[:12000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{RUN_ID} exit {proc.returncode}: {proc.stderr[:1500]}")
    out = json.loads(out_path.read_text())
    out["_wall"] = wall
    return out


def count_non_orthogonal(placements: list[dict[str, Any]]) -> int:
    count = 0
    for placement in placements:
        rot = float(placement.get("rotation_deg", 0.0)) % 90.0
        if rot > 1e-3 and abs(rot - 90.0) > 1e-3:
            count += 1
    return count


def rotation_top_counts(placements: list[dict[str, Any]], top_n: int = 12) -> list[dict[str, Any]]:
    buckets: dict[float, int] = {}
    for placement in placements:
        rot = round(float(placement.get("rotation_deg", 0.0)), 3)
        buckets[rot] = buckets.get(rot, 0) + 1
    top = sorted(buckets.items(), key=lambda item: (-item[1], item[0]))[:top_n]
    return [{"rotation_deg": rot, "count": count} for rot, count in top]


def summarize(out: dict[str, Any]) -> dict[str, Any]:
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
            "sparrow_ms_boundary_violations",
            diag.get("sparrow_boundary_violations_final"),
        ),
        "forced_latest_mode": bpp.get("bpp_q69_forced_latest_mode"),
        "seed_source": bpp.get("bpp_q69_seed_source"),
        "native_seed_fallback_used": bpp.get("bpp_q69_native_seed_fallback_used"),
        "builder_random_bootstrap_used": bpp.get("bpp_q69_builder_random_bootstrap_used"),
        # Q72 no-drop / global repack diagnostics
        "no_drop_seed_used": bpp.get("bpp_q72_no_drop_seed_used"),
        "seed_instance_count_before_pipeline": bpp.get("bpp_q72_seed_instance_count_before_pipeline"),
        "seed_builder_placed_before_completion": bpp.get("bpp_q72_seed_builder_placed_before_completion"),
        "global_repack_reinserted_count": bpp.get("bpp_q72_global_repack_reinserted_count"),
        "sheets_opened": bpp.get("bpp_sheets_opened"),
        "critical_admitted": bpp.get("bpp_critical_admitted"),
        "critical_deferred": bpp.get("bpp_critical_deferred"),
        "accepted_anchor_secondary_policy": bpp.get("bpp_q61_accepted_anchor_secondary_policy"),
        "non_orthogonal_rotation_count": count_non_orthogonal(placements),
        "rotation_top_counts": rotation_top_counts(placements),
        "forced_latest_locked": forced_locked,
        "wall_time_s": round(float(out.get("_wall", 0.0)), 1),
    }


def load_existing_summary(path: Path, label: str) -> dict[str, Any]:
    out = json.loads(path.read_text())
    summary = summarize(out)
    summary["label"] = label
    return summary


def write_report(summary: dict[str, Any], input_rel: str) -> None:
    run = summary["run"]
    q62 = summary["comparisons"]["q62_current"]
    q70 = summary["comparisons"]["q70_corner_first"]
    q71 = summary["comparisons"]["q71_edge_lock"]
    per_sheet = summary["per_sheet"]
    lines = [
        "# SGH-Q72 Report - Full-instance seed + fixed-bin global repack",
        "",
        f"## Verdict: {summary['verdict']}",
        "",
        "## Goal",
        "",
        "- Keep the solver on the forced latest-path with NO part dropped before the optimizer.",
        "- The seed must retain all instances; the real exploration SA + redistribute pipeline packs",
        "  them on the fixed 2 sheets.",
        f"- Success is judged ONLY on placed_count vs the Q62 baseline ({BASELINE_PLACED}).",
        "",
        "## Run",
        "",
        "| run | status | placed | unplaced | used sheets | util % | non-orth rot | wall s |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {RUN_ID} | {run['status']} | {run['placed_count']} | {run['unplaced_count']} | {run['used_sheets']} | {run['utilization_pct']} | {run['non_orthogonal_rotation_count']} | {run['wall_time_s']} |",
        "",
        "## Q72 No-drop / global-repack diagnostics",
        "",
        "| check | value |",
        "| --- | --- |",
        f"| forced latest lock active | {str(run['forced_latest_locked']).lower()} |",
        f"| no-drop seed used | {str(bool(run['no_drop_seed_used'])).lower()} |",
        f"| seed instance count before pipeline | {run['seed_instance_count_before_pipeline']} |",
        f"| builder placed before completion | {run['seed_builder_placed_before_completion']} |",
        f"| global repack re-inserted count | {run['global_repack_reinserted_count']} |",
        f"| native seed fallback used | {str(bool(run['native_seed_fallback_used'])).lower()} |",
        f"| seed source | {run['seed_source']} |",
        "",
        "## Per-sheet",
        "",
        "| sheet | placed | physical util % |",
        "| --- | ---: | ---: |",
    ]
    for item in per_sheet:
        lines.append(
            f"| {item['sheet_index']} | {item['placed_count']} | {item['physical_utilization_pct']} |"
        )
    lines.extend(
        [
            "",
            "## Comparison (placed_count is the only acceptance metric)",
            "",
            "| run | placed | unplaced | used sheets | util % |",
            "| --- | ---: | ---: | ---: | ---: |",
            f"| Q62 current (baseline) | {q62['placed_count']} | {q62['unplaced_count']} | {q62['used_sheets']} | {q62['utilization_pct']} |",
            f"| Q70 corner-first | {q70['placed_count']} | {q70['unplaced_count']} | {q70['used_sheets']} | {q70['utilization_pct']} |",
            f"| Q71 edge-lock | {q71['placed_count']} | {q71['unplaced_count']} | {q71['used_sheets']} | {q71['utilization_pct']} |",
            f"| **Q72 no-drop repack** | **{run['placed_count']}** | {run['unplaced_count']} | {run['used_sheets']} | {run['utilization_pct']} |",
            "",
            f"- Target: 276 / 2 sheets. Baseline to beat: {BASELINE_PLACED} (Q62).",
            "",
            "## Visual Proxy",
            "",
            f"- Render manifest: `artifacts/benchmarks/sgh_q72/renders/{RUN_ID}/render_manifest.json`",
            f"- Top rotations: `{json.dumps(run['rotation_top_counts'])}`",
            f"- Sheet 0 physical utilization: `{per_sheet[0]['physical_utilization_pct'] if per_sheet else 'n/a'}`",
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
            "- summary: `artifacts/benchmarks/sgh_q72/q72_summary.json`",
            f"- input: `artifacts/benchmarks/sgh_q72/{input_rel}`",
            f"- output: `artifacts/benchmarks/sgh_q72/outputs/{RUN_ID}_output.json`",
            f"- log: `artifacts/benchmarks/sgh_q72/logs/{RUN_ID}.log`",
        ]
    )
    (Q72 / "q72_report.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=int, default=600)
    args = parser.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    inp = build_input(args.time_limit)
    input_rel = str(inp.relative_to(Q72))
    out = run(inp, args.time_limit)
    run_summary = summarize(out)
    render_run(72, RUN_ID, input_rel, f"outputs/{RUN_ID}_output.json")
    render_manifest = json.loads(
        (Q72 / "renders" / RUN_ID / "render_manifest.json").read_text()
    )
    q62 = load_existing_summary(Q62_OUT, "q62_current")
    q70 = load_existing_summary(Q70_OUT, "q70_corner_first")
    q71 = load_existing_summary(Q71_OUT, "q71_edge_lock")
    per_sheet = render_manifest.get("per_sheet") or []

    placed = run_summary["placed_count"] or 0
    acceptance = {
        "forced_latest_locked": run_summary["forced_latest_locked"],
        "no_drop_seed_used": bool(run_summary["no_drop_seed_used"]),
        "seed_retains_all_instances": (
            (run_summary["seed_instance_count_before_pipeline"] or 0) >= 276
        ),
        "beats_q62_baseline": placed > BASELINE_PLACED,
        "beats_q70": placed > (q70["placed_count"] or 0),
        "beats_q71": placed > (q71["placed_count"] or 0),
    }
    # Honest verdict: PASS only if the forced-latest no-drop path actually BEATS the baseline it
    # currently regresses. No proxy-based PASS.
    verdict = "FAIL"
    if (
        acceptance["forced_latest_locked"]
        and acceptance["no_drop_seed_used"]
        and acceptance["seed_retains_all_instances"]
        and acceptance["beats_q62_baseline"]
    ):
        verdict = "PASS"

    summary = {
        "task": "sgh_q72_full_instance_seed_fixed_bin_repack",
        "source_package": str(Q49_INPUT.relative_to(ROOT)),
        "time_limit_s": args.time_limit,
        "baseline_placed": BASELINE_PLACED,
        "target_placed": 276,
        "stocks": {"quantity": 2, "width": 1500.0, "height": 3000.0},
        "technology": {
            "margin_mm": 5.0,
            "spacing_mm": 5.0,
            "kerf_mm": 0.0,
            "rotation_policy": "continuous",
        },
        "run": run_summary,
        "comparisons": {
            "q62_current": q62,
            "q70_corner_first": q70,
            "q71_edge_lock": q71,
        },
        "render_manifest": render_manifest,
        "per_sheet": per_sheet,
        "acceptance": acceptance,
        "verdict": verdict,
    }
    summary["finding"] = (
        "Q72 completes the forced-latest seed to a no-drop full-instance seed (builder critical/anchor "
        "placements kept, remainder re-inserted) and hands it to the real exploration SA + redistribute "
        "pipeline on the fixed 2 sheets. The only acceptance metric is placed_count vs the Q62 baseline "
        f"({BASELINE_PLACED}); edge-lock/corner/residual are diagnostics only."
    )
    Q72.mkdir(parents=True, exist_ok=True)
    (Q72 / "q72_summary.json").write_text(json.dumps(summary, indent=2))
    write_report(summary, input_rel)
    print(json.dumps({"verdict": verdict, **acceptance, "placed": placed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
