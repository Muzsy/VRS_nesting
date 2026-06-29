#!/usr/bin/env python3
"""SGH-Q70 - Corner-first residual-space recovery benchmark."""
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
Q69_OUT = ROOT / "artifacts/benchmarks/sgh_q69/outputs/q69_A_forced_latest_2sheet_sp5_output.json"
Q70 = ROOT / "artifacts" / "benchmarks" / "sgh_q70"
INPUTS = Q70 / "inputs"
OUTPUTS = Q70 / "outputs"
LOGS = Q70 / "logs"
RUN_ID = "q70_A_corner_first_2sheet_sp5"

Q70_GATES = {
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
        "project_name": "sgh_q70_corner_first_residual_space_recovery",
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
    path = INPUTS / f"q70_full276_2x1500x3000_margin5_spacing5_continuous_{time_limit_s}.json"
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
    env.update(Q70_GATES)

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
        f"env={json.dumps(Q70_GATES, sort_keys=True)}\n"
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
        "builder_sheet_slice_hits": bpp.get("bpp_q69_builder_sheet_slice_hits"),
        "completion_sweep_inserted": bpp.get("bpp_q69_completion_sweep_inserted"),
        "sheets_opened": bpp.get("bpp_sheets_opened"),
        "critical_admitted": bpp.get("bpp_critical_admitted"),
        "critical_deferred": bpp.get("bpp_critical_deferred"),
        "accepted_anchor_secondary_policy": bpp.get("bpp_q61_accepted_anchor_secondary_policy"),
        "anchor_best_corner_score": bpp.get("bpp_q70_anchor_best_corner_score"),
        "anchor_best_center_score": bpp.get("bpp_q70_anchor_best_center_score"),
        "anchor_center_blocked_by_policy": bpp.get("bpp_q70_anchor_center_blocked_by_policy"),
        "anchor_center_override_used": bpp.get("bpp_q70_anchor_center_override_used"),
        "anchor_center_only_path": bpp.get("bpp_q70_anchor_center_only_path"),
        "sheet_fill_recovery_inserted": bpp.get("bpp_q70_sheet_fill_recovery_inserted"),
        "underfilled_sheet_recovery_used": bpp.get("bpp_q70_underfilled_sheet_recovery_used"),
        "completion_fill_first_applied": bpp.get("bpp_q70_completion_fill_first_applied"),
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
    q69 = summary["comparisons"]["q69_forced_latest"]
    per_sheet = summary["per_sheet"]
    lines = [
        "# SGH-Q70 Report - Corner-first residual-space recovery",
        "",
        f"## Verdict: {summary['verdict']}",
        "",
        "## Goal",
        "",
        "- Keep the solver on the forced latest-path.",
        "- Strengthen corner-first / residual-space authority for critical anchor decisions.",
        "- Recover obvious filler opportunities on underfilled sheets before calling the run acceptable.",
        "",
        "## Run",
        "",
        "| run | status | placed | unplaced | used sheets | util % | non-orth rotations | wall s |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {RUN_ID} | {run['status']} | {run['placed_count']} | {run['unplaced_count']} | {run['used_sheets']} | {run['utilization_pct']} | {run['non_orthogonal_rotation_count']} | {run['wall_time_s']} |",
        "",
        "## Q70 Diagnostics",
        "",
        "| check | value |",
        "| --- | --- |",
        f"| forced latest lock active | {str(run['forced_latest_locked']).lower()} |",
        f"| accepted anchor secondary policy | {run['accepted_anchor_secondary_policy']} |",
        f"| best corner score | {run['anchor_best_corner_score']} |",
        f"| best center score | {run['anchor_best_center_score']} |",
        f"| center blocked by policy | {str(bool(run['anchor_center_blocked_by_policy'])).lower()} |",
        f"| center override used | {str(bool(run['anchor_center_override_used'])).lower()} |",
        f"| center-only path | {str(bool(run['anchor_center_only_path'])).lower()} |",
        f"| sheet fill recovery inserted | {run['sheet_fill_recovery_inserted']} |",
        f"| underfilled sheet recovery used | {str(bool(run['underfilled_sheet_recovery_used'])).lower()} |",
        f"| completion fill-first applied | {str(bool(run['completion_fill_first_applied'])).lower()} |",
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
            "## Comparison",
            "",
            "| baseline | placed | unplaced | used sheets | util % |",
            "| --- | ---: | ---: | ---: | ---: |",
            f"| Q62 current | {q62['placed_count']} | {q62['unplaced_count']} | {q62['used_sheets']} | {q62['utilization_pct']} |",
            f"| Q69 forced latest | {q69['placed_count']} | {q69['unplaced_count']} | {q69['used_sheets']} | {q69['utilization_pct']} |",
            f"| Q70 recovery | {run['placed_count']} | {run['unplaced_count']} | {run['used_sheets']} | {run['utilization_pct']} |",
            "",
            "## Visual Proxy",
            "",
            f"- Render manifest: `artifacts/benchmarks/sgh_q70/renders/{RUN_ID}/render_manifest.json`",
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
            "- summary: `artifacts/benchmarks/sgh_q70/q70_summary.json`",
            f"- input: `artifacts/benchmarks/sgh_q70/{input_rel}`",
            f"- output: `artifacts/benchmarks/sgh_q70/outputs/{RUN_ID}_output.json`",
            f"- log: `artifacts/benchmarks/sgh_q70/logs/{RUN_ID}.log`",
        ]
    )
    (Q70 / "q70_report.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=int, default=600)
    args = parser.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    inp = build_input(args.time_limit)
    input_rel = str(inp.relative_to(Q70))
    out = run(inp, args.time_limit)
    run_summary = summarize(out)
    render_run(70, RUN_ID, input_rel, f"outputs/{RUN_ID}_output.json")
    render_manifest = json.loads(
        (Q70 / "renders" / RUN_ID / "render_manifest.json").read_text()
    )
    q62 = load_existing_summary(Q62_OUT, "q62_current")
    q69 = load_existing_summary(Q69_OUT, "q69_forced_latest")
    per_sheet = render_manifest.get("per_sheet") or []

    sheet0_util = per_sheet[0]["physical_utilization_pct"] if per_sheet else 0.0
    acceptance = {
        "forced_latest_locked": run_summary["forced_latest_locked"],
        "improves_q69_placed_count": (run_summary["placed_count"] or 0) >= (q69["placed_count"] or 0),
        "improves_q69_sheet0_util": sheet0_util >= 45.0,
        "center_not_silent": (
            run_summary["accepted_anchor_secondary_policy"] is None
            or "center" not in str(run_summary["accepted_anchor_secondary_policy"])
            or bool(run_summary["anchor_center_override_used"])
            or bool(run_summary["anchor_center_only_path"])
        ),
        "fill_recovery_visible": (run_summary["sheet_fill_recovery_inserted"] or 0) > 0
        or bool(run_summary["completion_fill_first_applied"]),
    }
    verdict = "FAIL"
    if (
        acceptance["forced_latest_locked"]
        and acceptance["center_not_silent"]
        and acceptance["fill_recovery_visible"]
    ):
        verdict = "PASS_WITH_NOTES"
        if acceptance["improves_q69_placed_count"] and acceptance["improves_q69_sheet0_util"]:
            verdict = "PASS"

    summary = {
        "task": "sgh_q70_corner_first_residual_space_recovery",
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
            "q69_forced_latest": q69,
        },
        "render_manifest": render_manifest,
        "per_sheet": per_sheet,
        "acceptance": acceptance,
        "verdict": verdict,
    }
    summary["finding"] = (
        "Q70 keeps the solver on the forced latest-path and records whether center seating was blocked, "
        "explicitly overridden, or used only as a last resort. The benchmark still has to be judged on "
        "what happened to sheet-0 utilization, total placed-count, and the rendered board plans."
    )
    Q70.mkdir(parents=True, exist_ok=True)
    (Q70 / "q70_summary.json").write_text(json.dumps(summary, indent=2))
    write_report(summary, input_rel)
    print(json.dumps(summary["acceptance"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
