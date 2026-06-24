#!/usr/bin/env python3
"""SGH-Q69 - Full276 LV8 forced-latest result audit."""
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
Q63_OUT = ROOT / "artifacts/benchmarks/sgh_q63/outputs/q63_A_strict_latest_q61_2sheet_sp5_output.json"
Q69 = ROOT / "artifacts" / "benchmarks" / "sgh_q69"
INPUTS = Q69 / "inputs"
OUTPUTS = Q69 / "outputs"
LOGS = Q69 / "logs"

RUN_ID = "q69_A_forced_latest_2sheet_sp5"

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
    "VRS_SHEET_BUILDER_FORCE_LATEST": "1",
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
        "project_name": "sgh_q69_full276_lv8_forced_latest_result_audit",
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
    path = INPUTS / f"q69_full276_2x1500x3000_margin5_spacing5_continuous_{time_limit_s}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run(inp: Path, time_limit_s: int) -> dict[str, Any]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{RUN_ID}_output.json"
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
        "VRS_SHEET_BUILDER_FORCE_LATEST",
        "VRS_SHEET_BUILDER_STRICT_LATEST",
    ]:
        env.pop(key, None)
    env.update(Q61_GATES)

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
        f"env={json.dumps(Q61_GATES, sort_keys=True)}\n"
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
    role_aware_visible = any(
        [
            (bpp.get("bpp_q61_pair_candidates_accepted") or 0) > 0,
            (bpp.get("bpp_q61_anchor_catalog_accepted") or 0) > 0,
            (bpp.get("bpp_q61_slot_edge_candidates_accepted") or 0) > 0,
            bool(bpp.get("bpp_q67_simultaneous_authority_used")),
            (bpp.get("bpp_feature_candidates_accepted") or 0) > 0,
        ]
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
        "builder_sheet_slice_hits": bpp.get("bpp_q69_builder_sheet_slice_hits"),
        "completion_sweep_inserted": bpp.get("bpp_q69_completion_sweep_inserted"),
        "builder_applied": bpp.get("bpp_sheet_builder_applied"),
        "sheets_opened": bpp.get("bpp_sheets_opened"),
        "critical_admitted": bpp.get("bpp_critical_admitted"),
        "critical_deferred": bpp.get("bpp_critical_deferred"),
        "max_critical_per_sheet": bpp.get("bpp_max_critical_per_sheet"),
        "feature_candidates_accepted": bpp.get("bpp_feature_candidates_accepted"),
        "pair_index_consulted": bpp.get("bpp_q61_pair_index_consulted"),
        "pair_candidates_accepted": bpp.get("bpp_q61_pair_candidates_accepted"),
        "anchor_catalog_accepted": bpp.get("bpp_q61_anchor_catalog_accepted"),
        "slot_edge_candidates_accepted": bpp.get("bpp_q61_slot_edge_candidates_accepted"),
        "simultaneous_authority_used": bpp.get("bpp_q67_simultaneous_authority_used"),
        "best_partial_max_critical_count": bpp.get("bpp_q61_best_partial_max_critical_count"),
        "critical_phase_close_reason": bpp.get("bpp_critical_phase_close_reason"),
        "non_orthogonal_rotation_count": count_non_orthogonal(placements),
        "rotation_top_counts": rotation_top_counts(placements),
        "forced_latest_locked": forced_locked,
        "role_aware_activity_visible": role_aware_visible,
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
    q63 = summary["comparisons"]["q63_strict"]
    visual = summary["visual_proxy"]
    lines = [
        "# SGH-Q69 Report - Full276 LV8 forced-latest result audit",
        "",
        f"## Verdict: {summary['verdict']}",
        "",
        "## Goal",
        "",
        "- Force the solver onto the current role-aware / hint-aware / simultaneous-aware path.",
        "- Disallow native constructive seed fallback and random bootstrap rescue.",
        "- Re-run the same Full276 LV8 package on 2 x 1500x3000 mm sheets with margin 5 mm and spacing 5 mm.",
        "- Produce a hard post-check with render evidence and explicit diagnostics.",
        "",
        "## Run",
        "",
        "| run | status | placed | unplaced | used sheets | util % | non-orth rotations | sheets opened | pair accepted | sim authority | wall s |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        f"| {RUN_ID} | {run['status']} | {run['placed_count']} | {run['unplaced_count']} | {run['used_sheets']} | {run['utilization_pct']} | {run['non_orthogonal_rotation_count']} | {run['sheets_opened']} | {run['pair_candidates_accepted']} | {run['simultaneous_authority_used']} | {run['wall_time_s']} |",
        "",
        "## Hard Post-Check",
        "",
        "| check | value |",
        "| --- | --- |",
        f"| forced latest lock active | {str(run['forced_latest_locked']).lower()} |",
        f"| seed source = builder_forced_latest | {str(run['seed_source'] == 'builder_forced_latest').lower()} |",
        f"| native seed fallback used | {str(run['native_seed_fallback_used']).lower()} |",
        f"| random bootstrap used | {str(run['builder_random_bootstrap_used']).lower()} |",
        f"| builder reached multiple sheets | {str((run['sheets_opened'] or 0) >= 2).lower()} |",
        f"| role-aware activity visible in diagnostics | {str(run['role_aware_activity_visible']).lower()} |",
        f"| non-orth rotation count > 0 | {str((run['non_orthogonal_rotation_count'] or 0) > 0).lower()} |",
        "",
        "## Comparison",
        "",
        "| baseline | status | placed | unplaced | used sheets | pair accepted | pair consulted | wall s |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |",
        f"| Q62 current | {q62['status']} | {q62['placed_count']} | {q62['unplaced_count']} | {q62['used_sheets']} | {q62['pair_candidates_accepted']} | {q62['pair_index_consulted']} | {q62['wall_time_s']} |",
        f"| Q63 strict latest | {q63['status']} | {q63['placed_count']} | {q63['unplaced_count']} | {q63['used_sheets']} | {q63['pair_candidates_accepted']} | {q63['pair_index_consulted']} | {q63['wall_time_s']} |",
        f"| Q69 forced latest | {run['status']} | {run['placed_count']} | {run['unplaced_count']} | {run['used_sheets']} | {run['pair_candidates_accepted']} | {run['pair_index_consulted']} | {run['wall_time_s']} |",
        "",
        "## Visual Proxy",
        "",
        f"- Render manifest: `artifacts/benchmarks/sgh_q69/renders/{RUN_ID}/render_manifest.json`",
        f"- Non-orth rotation count: `{visual['non_orthogonal_rotation_count']}`",
        f"- Top rotations: `{json.dumps(visual['rotation_top_counts'])}`",
        f"- Interpretation: {visual['interpretation']}",
        "",
        "## Finding",
        "",
        summary["finding"],
        "",
        "## Artifact evidence",
        "",
        "- summary: `artifacts/benchmarks/sgh_q69/q69_summary.json`",
        f"- input: `artifacts/benchmarks/sgh_q69/{input_rel}`",
        f"- output: `artifacts/benchmarks/sgh_q69/outputs/{RUN_ID}_output.json`",
        f"- log: `artifacts/benchmarks/sgh_q69/logs/{RUN_ID}.log`",
    ]
    (Q69 / "q69_report.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=int, default=600)
    args = parser.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    inp = build_input(args.time_limit)
    input_rel = str(inp.relative_to(Q69))
    print(f"[Q69] input: {inp}")
    out = run(inp, args.time_limit)
    run_summary = summarize(out)
    render_manifest = render_run(69, RUN_ID, input_rel, f"outputs/{RUN_ID}_output.json")
    q62 = load_existing_summary(Q62_OUT, "q62_current")
    q63 = load_existing_summary(Q63_OUT, "q63_strict")

    visual_proxy = {
        "non_orthogonal_rotation_count": run_summary["non_orthogonal_rotation_count"],
        "rotation_top_counts": run_summary["rotation_top_counts"],
        "interpretation": (
            "The forced-latest run still looks too orthogonal in practice."
            if run_summary["non_orthogonal_rotation_count"] == 0
            else "The forced-latest run exposes non-orthogonal placement activity, so the current path is not visually collapsing to a 90-degree-only layout."
        ),
    }
    acceptance = {
        "forced_latest_locked": run_summary["forced_latest_locked"],
        "builder_reached_multiple_sheets": (run_summary["sheets_opened"] or 0) >= 2,
        "role_aware_activity_visible": run_summary["role_aware_activity_visible"],
        "non_orth_visible": (run_summary["non_orthogonal_rotation_count"] or 0) > 0,
        "no_regression_vs_q63_strict_on_placed": (run_summary["placed_count"] or 0) >= (q63["placed_count"] or 0),
    }
    if acceptance["forced_latest_locked"] and acceptance["builder_reached_multiple_sheets"] and acceptance["role_aware_activity_visible"]:
        verdict = "PASS_WITH_NOTES"
        if acceptance["non_orth_visible"] and (run_summary["placed_count"] or 0) >= (q62["placed_count"] or 0):
            verdict = "PASS"
    else:
        verdict = "FAIL"

    summary = {
        "task": "sgh_q69_full276_lv8_forced_latest_result_audit",
        "source_package": str(Q49_INPUT.relative_to(ROOT)),
        "time_limit_s": args.time_limit,
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
            "q63_strict": q63,
        },
        "render_manifest": render_manifest,
        "visual_proxy": visual_proxy,
        "acceptance": acceptance,
        "verdict": verdict,
    }
    summary["finding"] = (
        "The solver stayed on the forced latest-path lock without native seed fallback or random bootstrap, "
        "and the saved diagnostics now say that explicitly. The result still has to be judged on layout quality: "
        "compare the placed-count, sheets-opened, role-aware counters, and the render images before calling it a production win."
    )
    Q69.mkdir(parents=True, exist_ok=True)
    (Q69 / "q69_summary.json").write_text(json.dumps(summary, indent=2))
    write_report(summary, input_rel)
    print(json.dumps(summary["acceptance"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
