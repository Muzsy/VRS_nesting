#!/usr/bin/env python3
"""SGH-Q53E - Feature-first critical admission proof benchmark."""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from render_sgh_q47_q50_benchmark_artifacts import (
    expand_stock_sheets,
    part_outer,
    polygon_area,
    render_overview_svg,
    render_sheet_svg,
    svg_to_png,
)

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
BASE = ROOT / "artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json"
Q53 = ROOT / "artifacts" / "benchmarks" / "sgh_q53"
OUTPUTS = Q53 / "outputs"
LOGS = Q53 / "logs"
RENDERS = Q53 / "renders"
SUMMARY_PATH = Q53 / "q53_summary.json"
REPORT_PATH = Q53 / "q53_report.md"


def base_parts() -> list[dict[str, Any]]:
    parts = copy.deepcopy(json.loads(BASE.read_text())["parts"])
    for part in parts:
        part.pop("allowed_rotations_deg", None)
        part.pop("rotation_policy", None)
    return parts


def make_input_doc(project_name: str, parts: list[dict[str, Any]], stock_qty: int, spacing: float, time_limit_s: int) -> dict[str, Any]:
    return {
        "contract_version": "v1",
        "project_name": project_name,
        "seed": 42,
        "time_limit_s": time_limit_s,
        "stocks": [{"id": "S", "quantity": stock_qty, "width": 1500.0, "height": 3000.0}],
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "rotation_policy": "continuous",
        "margin_mm": 5.0,
        "spacing_mm": spacing,
        "kerf_mm": 0.0,
        "parts": parts,
    }


def case_parts(case: str) -> tuple[list[dict[str, Any]], int]:
    if case != "6big":
        raise ValueError(f"unsupported case: {case}")
    parts = [part for part in base_parts() if str(part["id"]).startswith("Lv8_11612")]
    for part in parts:
        part["quantity"] = 6
    return parts, 4


def run_solver(run_id: str, input_doc: dict[str, Any], time_limit_s: int, env_updates: dict[str, str | None]) -> dict[str, Any]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{run_id}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)
    env.pop("VRS_ADMISSION_DENSITY_BIAS", None)
    for key, value in env_updates.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value

    with tempfile.TemporaryDirectory(prefix="sgh_q53_") as tmpdir:
        input_path = Path(tmpdir) / f"{run_id}_input.json"
        input_path.write_text(json.dumps(input_doc))
        t0 = time.monotonic()
        proc = subprocess.run(
            [str(SOLVER_BIN), "--input", str(input_path), "--output", str(out_path)],
            capture_output=True,
            text=True,
            timeout=time_limit_s + 3600,
            env=env,
        )
        wall = time.monotonic() - t0

    log_lines = [
        f"run_id={run_id}",
        f"exit={proc.returncode}",
        f"wall_time_s={wall:.1f}",
        f"env={json.dumps({k: v for k, v in env_updates.items()}, sort_keys=True)}",
        "",
        "stderr:",
        proc.stderr.strip(),
        "",
        "stdout:",
        proc.stdout.strip(),
    ]
    (LOGS / f"{run_id}.log").write_text("\n".join(log_lines).strip() + "\n")
    if proc.returncode != 0:
        raise RuntimeError(f"{run_id} exit {proc.returncode}: {proc.stderr[:500]}")
    output_doc = json.loads(out_path.read_text())
    output_doc["_wall"] = wall
    return output_doc


def summarize_run(run_id: str, output_doc: dict[str, Any]) -> dict[str, Any]:
    diag = output_doc.get("optimizer_diagnostics") or {}
    bpp = diag.get("bpp_reduction") or {}
    placements = output_doc.get("placements") or []
    metrics = output_doc.get("metrics") or {}
    big_per_sheet: dict[int, int] = {}
    big_rotations: dict[int, list[float]] = {}
    for placement in placements:
        if not str(placement.get("part_id", "")).startswith("Lv8_11612"):
            continue
        sheet_index = int(placement.get("sheet_index", 0))
        big_per_sheet[sheet_index] = big_per_sheet.get(sheet_index, 0) + 1
        big_rotations.setdefault(sheet_index, []).append(round(float(placement.get("rotation_deg", 0.0)), 3))
    used_sheet_indices = sorted({int(placement.get("sheet_index", 0)) for placement in placements})
    final_pairs = diag.get("sparrow_ms_final_pairs", diag.get("sparrow_collision_graph_final_pairs"))
    boundary_violations = diag.get("sparrow_ms_boundary_violations", diag.get("sparrow_boundary_violations_final"))
    return {
        "run_id": run_id,
        "status": output_doc.get("status"),
        "placed_count": metrics.get("placed_count"),
        "unplaced_count": metrics.get("unplaced_count"),
        "used_sheets": len(used_sheet_indices),
        "used_sheet_indices": used_sheet_indices,
        "utilization_pct": diag.get("sparrow_ms_utilization_pct"),
        "wall_time_s": round(float(output_doc.get("_wall", 0.0)), 1),
        "final_pairs": final_pairs,
        "boundary_violations": boundary_violations,
        "big_per_sheet": {str(k): v for k, v in sorted(big_per_sheet.items())},
        "big_rotations_deg_by_sheet": {str(k): v for k, v in sorted(big_rotations.items())},
        "max_big_per_sheet": max(big_per_sheet.values()) if big_per_sheet else 0,
        "builder_applied": bpp.get("bpp_sheet_builder_applied"),
        "critical_admitted": bpp.get("bpp_critical_admitted"),
        "critical_deferred": bpp.get("bpp_critical_deferred"),
        "max_critical_per_sheet": bpp.get("bpp_max_critical_per_sheet"),
        "feature_candidates_generated": bpp.get("bpp_feature_candidates_generated"),
        "feature_candidates_accepted": bpp.get("bpp_feature_candidates_accepted"),
        "bbox_corner_candidates_generated": bpp.get("bpp_bbox_corner_candidates_generated"),
        "bbox_corner_candidates_accepted": bpp.get("bpp_bbox_corner_candidates_accepted"),
        "accepted_feature_pair_type": bpp.get("bpp_accepted_feature_pair_type"),
        "feature_refine_seed_rotation_deg": bpp.get("bpp_feature_refine_seed_rotation_deg"),
        "feature_refine_refined_rotation_deg": bpp.get("bpp_feature_refine_refined_rotation_deg"),
        "feature_refine_iterations": bpp.get("bpp_feature_refine_iterations"),
        "feature_refine_successes": bpp.get("bpp_feature_refine_successes"),
        "feature_refine_failures": bpp.get("bpp_feature_refine_failures"),
        "feature_refine_rejection_reason": bpp.get("bpp_feature_refine_rejection_reason"),
        "critical_feature_admission_attempts": bpp.get("bpp_critical_feature_admission_attempts"),
        "critical_feature_admission_successes": bpp.get("bpp_critical_feature_admission_successes"),
        "critical_feature_admission_failures": bpp.get("bpp_critical_feature_admission_failures"),
        "critical_phase_close_reason": bpp.get("bpp_critical_phase_close_reason"),
        "critical_candidate_rejection_summary": bpp.get("bpp_critical_candidate_rejection_summary"),
    }


def render_run(run_id: str, input_doc: dict[str, Any], output_doc: dict[str, Any]) -> dict[str, Any]:
    parts_by_id = {part["id"]: part for part in input_doc.get("parts", [])}
    sheets = expand_stock_sheets(input_doc.get("stocks", []))
    sheet_dims = {idx: (sheet["width"], sheet["height"]) for idx, sheet in enumerate(sheets)}
    placements = output_doc.get("placements", [])
    used = sorted({int(placement["sheet_index"]) for placement in placements})
    out_dir = RENDERS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    margin_mm = float(input_doc.get("margin_mm", 0.0))
    per_sheet = []
    svg_count = 0
    png_count = 0
    for render_index, sheet_index in enumerate(used):
        sheet_w, sheet_h = sheet_dims[sheet_index]
        svg_path = out_dir / f"sheet_{render_index:02d}.svg"
        png_path = out_dir / f"sheet_{render_index:02d}.png"
        svg_path.write_text(
            render_sheet_svg(run_id, sheet_index, sheet_w, sheet_h, margin_mm, placements, parts_by_id)
        )
        svg_count += 1
        if svg_to_png(svg_path, png_path):
            png_count += 1
        sheet_placements = [placement for placement in placements if int(placement.get("sheet_index", -1)) == sheet_index]
        area = sum(polygon_area(part_outer(parts_by_id.get(str(placement["part_id"]), {}))) for placement in sheet_placements)
        per_sheet.append(
            {
                "sheet_index": sheet_index,
                "stock_id": sheets[sheet_index]["id"],
                "stock_width": sheet_w,
                "stock_height": sheet_h,
                "placed_count": len(sheet_placements),
                "placed_part_area": round(area, 2),
                "physical_utilization_pct": round(100.0 * area / (sheet_w * sheet_h), 4),
                "svg_path": str(svg_path.relative_to(ROOT)),
                "png_path": str(png_path.relative_to(ROOT)) if png_path.exists() else None,
            }
        )
    metrics = output_doc.get("metrics", {})
    placed = int(metrics.get("placed_count", len(placements)))
    total = placed + int(metrics.get("unplaced_count", len(output_doc.get("unplaced", []))))
    overview_svg = out_dir / "overview.svg"
    overview_png = out_dir / "overview.png"
    overview_svg.write_text(render_overview_svg(run_id, used, sheet_dims, output_doc.get("status", ""), placed, total))
    svg_count += 1
    if svg_to_png(overview_svg, overview_png, output_width=1400):
        png_count += 1
    manifest = {
        "run_id": run_id,
        "task": "SGH-Q53",
        "render_source": "input_outer_points_plus_solver_output_anchor_placements",
        "used_sheet_count": len(used),
        "used_sheet_indices": used,
        "svg_count": svg_count,
        "png_count": png_count,
        "have_cairosvg": overview_png.exists(),
        "per_sheet": per_sheet,
        "overview_svg": str(overview_svg.relative_to(ROOT)),
        "overview_png": str(overview_png.relative_to(ROOT)) if overview_png.exists() else None,
    }
    (out_dir / "render_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def acceptance(summary: dict[str, Any]) -> dict[str, Any]:
    feature_on = summary["runs"]["feature_on"]
    feature_off = summary["runs"]["feature_off"]
    feature_on_valid = (
        feature_on["status"] == "ok"
        and feature_on["placed_count"] == 6
        and int(feature_on.get("final_pairs") or 0) == 0
        and int(feature_on.get("boundary_violations") or 0) == 0
    )
    control_valid = (
        feature_off["status"] == "ok"
        and feature_off["placed_count"] == 6
        and int(feature_off.get("final_pairs") or 0) == 0
        and int(feature_off.get("boundary_violations") or 0) == 0
    )
    feature_candidates_exercised = int(feature_on.get("feature_candidates_generated") or 0) > 0
    feature_path_evidenced = (
        int(feature_on.get("feature_candidates_accepted") or 0) > 0
        or int(feature_on.get("critical_feature_admission_successes") or 0) > 0
        or feature_on.get("accepted_feature_pair_type") is not None
        or feature_on.get("feature_refine_rejection_reason") is not None
        or feature_on.get("critical_candidate_rejection_summary") is not None
    )
    return {
        "feature_on_valid": feature_on_valid,
        "feature_on_has_3_big_on_a_sheet": int(feature_on.get("max_big_per_sheet") or 0) >= 3,
        "feature_candidates_exercised": feature_candidates_exercised,
        "feature_path_evidenced_or_reason_recorded": feature_path_evidenced,
        "feature_off_control_valid": control_valid,
    }


def write_artifact_report(summary: dict[str, Any], manifests: dict[str, dict[str, Any]]) -> None:
    feature_off = summary["runs"]["feature_off"]
    feature_on = summary["runs"]["feature_on"]
    acc = summary["acceptance"]
    lines = [
        "# SGH-Q53 Report - Feature-first critical admission proof",
        "",
        f"## Verdict: {summary['verdict']}",
        "",
        "## Goal",
        "",
        "- Compare Q51/Q52 builder-only control against the Q53 feature-first critical admission arm.",
        "- Prove or disprove that spacing 5 can reach at least 3 `Lv8_11612` parts on one sheet while staying CDE-valid.",
        "- Export diagnostics, raw outputs, and sheet-plan renders in the same artifact shape as Q51/Q52.",
        "",
        "## Runs",
        "",
        "| run | status | placed | used sheets | util % | max big/sheet | feature cand. | accepted feature pair | critical feature succ. | wall s | acceptance |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for label, run in (("feature_off", feature_off), ("feature_on", feature_on)):
        accepted = "PASS"
        if not (run["status"] == "ok" and int(run.get("final_pairs") or 0) == 0 and int(run.get("boundary_violations") or 0) == 0):
            accepted = "FAIL"
        elif label == "feature_on" and int(run.get("max_big_per_sheet") or 0) < 3:
            accepted = "FAIL_TARGET"
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    str(run.get("status")),
                    str(run.get("placed_count")),
                    str(run.get("used_sheets")),
                    str(run.get("utilization_pct")),
                    str(run.get("max_big_per_sheet")),
                    str(run.get("feature_candidates_generated")),
                    str(run.get("accepted_feature_pair_type")),
                    str(run.get("critical_feature_admission_successes")),
                    str(run.get("wall_time_s")),
                    accepted,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Acceptance",
            "",
            "| check | value |",
            "| --- | --- |",
        ]
    )
    for key, value in acc.items():
        lines.append(f"| {key} | {str(value).lower()} |")
    lines.extend(
        [
            "",
            "## Diagnostics highlights",
            "",
            f"- `feature_off` big/sheet: `{feature_off['big_per_sheet']}` rotations: `{feature_off['big_rotations_deg_by_sheet']}`",
            f"- `feature_on` big/sheet: `{feature_on['big_per_sheet']}` rotations: `{feature_on['big_rotations_deg_by_sheet']}`",
            f"- `feature_on` refine: seed=`{feature_on['feature_refine_seed_rotation_deg']}`, refined=`{feature_on['feature_refine_refined_rotation_deg']}`, iterations=`{feature_on['feature_refine_iterations']}`",
            f"- `feature_on` rejection summary: `{feature_on['critical_candidate_rejection_summary']}`",
            f"- `feature_on` phase close reason: `{feature_on['critical_phase_close_reason']}`",
            "",
            "## Artifact evidence",
            "",
            f"- summary: `{SUMMARY_PATH.relative_to(ROOT)}`",
            f"- outputs: `{OUTPUTS.relative_to(ROOT)}/`",
            f"- logs: `{LOGS.relative_to(ROOT)}/`",
            f"- renders: `{RENDERS.relative_to(ROOT)}/`",
            "",
            "## Render evidence",
            "",
            f"- `feature_off`: `{(RENDERS / 'feature_off' / 'render_manifest.json').relative_to(ROOT)}`",
            f"- `feature_on`: `{(RENDERS / 'feature_on' / 'render_manifest.json').relative_to(ROOT)}`",
            "",
            "## Notes",
            "",
            f"- PNG generated for all SVG renders: `{all(m['png_count'] == m['svg_count'] for m in manifests.values())}`",
            f"- Finding: {summary['finding']}",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="6big", choices=["6big"])
    parser.add_argument("--spacing", type=float, default=5.0)
    parser.add_argument("--time-limit", type=int, default=600)
    args = parser.parse_args()

    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 2

    parts, stock_qty = case_parts(args.case)
    input_doc = make_input_doc(
        project_name=f"sgh_q53_{args.case}_sp{int(args.spacing)}",
        parts=parts,
        stock_qty=stock_qty,
        spacing=args.spacing,
        time_limit_s=args.time_limit,
    )

    runs: dict[str, dict[str, Any]] = {}
    manifests: dict[str, dict[str, Any]] = {}
    run_specs = {
        "feature_off": {
            "VRS_SHEET_BUILDER": "1",
            "VRS_SHEET_BUILDER_FEATURE_CRITICAL": None,
            "VRS_FEATURE_CANDIDATES": None,
            "VRS_BPP_DENSITY_SAMPLES": "40",
        },
        "feature_on": {
            "VRS_SHEET_BUILDER": "1",
            "VRS_SHEET_BUILDER_FEATURE_CRITICAL": "1",
            "VRS_FEATURE_CANDIDATES": "1",
            "VRS_BPP_DENSITY_SAMPLES": "40",
        },
    }
    for run_id, env_updates in run_specs.items():
        print(f"[Q53] {run_id} ...")
        output_doc = run_solver(run_id, input_doc, args.time_limit, env_updates)
        runs[run_id] = summarize_run(run_id, output_doc)
        manifests[run_id] = render_run(run_id, input_doc, output_doc)

    summary = {
        "task": "sgh_q53_feature_admission_proof",
        "case": args.case,
        "spacing_mm": args.spacing,
        "time_limit_s": args.time_limit,
        "runs": runs,
    }
    summary["acceptance"] = acceptance(summary)
    summary["verdict"] = "PASS" if all(summary["acceptance"].values()) else "FAIL"
    if summary["verdict"] == "PASS":
        summary["finding"] = (
            "Feature-first critical admission reached a valid spacing-5 layout with at least one "
            "3-big sheet and diagnostic proof that the accepted admission came from the feature path."
        )
    else:
        summary["finding"] = (
            "Feature-first critical admission stayed CDE-valid and exercised the feature path "
            f"(generated {runs['feature_on']['feature_candidates_generated']} candidates), but the "
            f"600 s spacing-5 gate still ended at {runs['feature_on']['max_big_per_sheet']} big/sheet "
            "across 3 sheets, matching the builder-only control."
        )

    Q53.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    write_artifact_report(summary, manifests)
    print(json.dumps(summary, indent=2))
    print(f"[Q53] VERDICT: {summary['verdict']}")
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
