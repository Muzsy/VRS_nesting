#!/usr/bin/env python3
"""SGH-Q71 - Anchor edge-lock and flush alignment benchmark."""
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
Q70_OUT = ROOT / "artifacts/benchmarks/sgh_q70/outputs/q70_A_corner_first_2sheet_sp5_output.json"
Q71 = ROOT / "artifacts" / "benchmarks" / "sgh_q71"
INPUTS = Q71 / "inputs"
OUTPUTS = Q71 / "outputs"
LOGS = Q71 / "logs"
RUN_ID = "q71_A_edge_lock_2sheet_sp5"

Q71_GATES = {
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


def q49_doc() -> dict[str, Any]:
    return json.loads(Q49_INPUT.read_text())


def q49_parts() -> list[dict[str, Any]]:
    parts = copy.deepcopy(q49_doc()["parts"])
    for part in parts:
        part.pop("allowed_rotations_deg", None)
        part.pop("rotation_policy", None)
    return parts


def polygon_area(part: dict[str, Any]) -> float:
    pts = part.get("outer_points") or []
    if pts:
        area = 0.0
        for idx, (x1, y1) in enumerate(pts):
            x2, y2 = pts[(idx + 1) % len(pts)]
            area += x1 * y2 - x2 * y1
        return abs(area) * 0.5
    return float(part.get("width", 0.0)) * float(part.get("height", 0.0))


def bbox_from_anchor(x: float, y: float, w: float, h: float, rot_deg: float) -> tuple[float, float, float, float]:
    angle = math.radians(rot_deg)
    c = math.cos(angle)
    s = math.sin(angle)
    xs: list[float] = []
    ys: list[float] = []
    for px, py in ((0.0, 0.0), (w, 0.0), (w, h), (0.0, h)):
        xs.append(x + px * c - py * s)
        ys.append(y + px * s + py * c)
    return min(xs), min(ys), max(xs), max(ys)


def edge_gap_summary(
    out: dict[str, Any],
    top_n_parts: int = 2,
    stock_width: float = 1500.0,
    stock_height: float = 3000.0,
) -> dict[str, Any]:
    doc = q49_doc()
    parts = {part["id"]: part for part in doc["parts"]}
    ranked = sorted(((polygon_area(part), part["id"]) for part in doc["parts"]), reverse=True)[:top_n_parts]
    focus_parts: list[dict[str, Any]] = []
    all_gaps: list[float] = []
    locked_count = 0
    total_count = 0
    for area_mm2, part_id in ranked:
        part = parts[part_id]
        placements = [pl for pl in out.get("placements", []) if pl.get("part_id") == part_id]
        placement_rows = []
        for pl in placements:
            mnx, mny, mxx, mxy = bbox_from_anchor(
                float(pl["x"]),
                float(pl["y"]),
                float(part["width"]),
                float(part["height"]),
                float(pl["rotation_deg"]),
            )
            gaps = {
                "left": abs(mnx - 0.0),
                "right": abs(stock_width - mxx),
                "bottom": abs(mny - 0.0),
                "top": abs(stock_height - mxy),
            }
            nearest_edge = min(gaps, key=gaps.get)
            min_gap = float(gaps[nearest_edge])
            all_gaps.append(min_gap)
            total_count += 1
            if min_gap <= 40.0:
                locked_count += 1
            placement_rows.append(
                {
                    "sheet_index": int(pl["sheet_index"]),
                    "rotation_deg": round(float(pl["rotation_deg"]), 3),
                    "nearest_edge": nearest_edge,
                    "min_edge_gap_mm": round(min_gap, 3),
                    "edge_gaps_mm": {k: round(v, 3) for k, v in gaps.items()},
                }
            )
        focus_parts.append(
            {
                "part_id": part_id,
                "area_mm2": round(area_mm2, 3),
                "placement_count": len(placement_rows),
                "avg_min_edge_gap_mm": round(
                    sum(row["min_edge_gap_mm"] for row in placement_rows) / len(placement_rows), 3
                )
                if placement_rows
                else None,
                "worst_min_edge_gap_mm": round(
                    max(row["min_edge_gap_mm"] for row in placement_rows), 3
                )
                if placement_rows
                else None,
                "placements": placement_rows,
            }
        )
    return {
        "focus_parts": focus_parts,
        "avg_min_edge_gap_mm": round(sum(all_gaps) / len(all_gaps), 3) if all_gaps else None,
        "worst_min_edge_gap_mm": round(max(all_gaps), 3) if all_gaps else None,
        "edge_locked_count": locked_count,
        "edge_locked_ratio": round(locked_count / total_count, 4) if total_count else None,
    }


def build_input(time_limit_s: int) -> Path:
    inp = {
        "contract_version": "v1",
        "project_name": "sgh_q71_anchor_edge_lock_and_flush_alignment",
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
    path = INPUTS / f"q71_full276_2x1500x3000_margin5_spacing5_continuous_{time_limit_s}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run(inp: Path, time_limit_s: int) -> dict[str, Any]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{RUN_ID}_output.json"
    env = dict(os.environ)
    env.pop("VRS_MULTISHEET_MODE", None)
    for key in list(Q71_GATES) + ["VRS_SHEET_BUILDER_STRICT_LATEST"]:
        env.pop(key, None)
    env.update(Q71_GATES)

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
        f"env={json.dumps(Q71_GATES, sort_keys=True)}\n"
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
    anchor_gaps = edge_gap_summary(out)
    return {
        "status": out.get("status"),
        "placed_count": metrics.get("placed_count"),
        "unplaced_count": metrics.get("unplaced_count"),
        "used_sheets": len({p.get("sheet_index", 0) for p in placements}),
        "utilization_pct": diag.get("sparrow_ms_utilization_pct"),
        "forced_latest_mode": bpp.get("bpp_q69_forced_latest_mode"),
        "seed_source": bpp.get("bpp_q69_seed_source"),
        "accepted_anchor_secondary_policy": bpp.get("bpp_q61_accepted_anchor_secondary_policy"),
        "anchor_selected_path": bpp.get("bpp_q68_anchor_selected_path"),
        "anchor_final_primary_gap_mm": bpp.get("bpp_q71_anchor_final_primary_gap_mm"),
        "anchor_final_secondary_gap_mm": bpp.get("bpp_q71_anchor_final_secondary_gap_mm"),
        "anchor_final_min_edge_gap_mm": bpp.get("bpp_q71_anchor_final_min_edge_gap_mm"),
        "anchor_final_rotation_drift_deg": bpp.get("bpp_q71_anchor_final_rotation_drift_deg"),
        "anchor_direct_fallback_blocked": bpp.get("bpp_q71_anchor_direct_fallback_blocked"),
        "non_orthogonal_rotation_count": count_non_orthogonal(placements),
        "forced_latest_locked": forced_locked,
        "wall_time_s": round(float(out.get("_wall", 0.0)), 1),
        "anchor_edge_gaps": anchor_gaps,
    }


def write_report(summary: dict[str, Any], input_rel: str) -> None:
    run = summary["run"]
    q70 = summary["comparisons"]["q70_baseline"]
    gap = run["anchor_edge_gaps"]
    lines = [
        "# SGH-Q71 Report - Anchor edge-lock and flush alignment",
        "",
        f"## Verdict: {summary['verdict']}",
        "",
        "## Run",
        "",
        "| run | status | placed | unplaced | used sheets | util % | non-orth rotations | wall s |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {RUN_ID} | {run['status']} | {run['placed_count']} | {run['unplaced_count']} | {run['used_sheets']} | {run['utilization_pct']} | {run['non_orthogonal_rotation_count']} | {run['wall_time_s']} |",
        "",
        "## Forced-latest anchor diagnostics",
        "",
        "| check | value |",
        "| --- | --- |",
        f"| forced latest lock active | {str(bool(run['forced_latest_locked'])).lower()} |",
        f"| accepted anchor secondary policy | {run['accepted_anchor_secondary_policy']} |",
        f"| selected anchor path | {run['anchor_selected_path']} |",
        f"| final primary gap mm | {run['anchor_final_primary_gap_mm']} |",
        f"| final secondary gap mm | {run['anchor_final_secondary_gap_mm']} |",
        f"| final min edge gap mm | {run['anchor_final_min_edge_gap_mm']} |",
        f"| final rotation drift deg | {run['anchor_final_rotation_drift_deg']} |",
        f"| direct fallback blocked | {str(bool(run['anchor_direct_fallback_blocked'])).lower()} |",
        "",
        "## Largest-part edge gaps",
        "",
        f"- Avg min edge gap across the 2 largest part families: `{gap['avg_min_edge_gap_mm']}` mm",
        f"- Worst min edge gap across the 2 largest part families: `{gap['worst_min_edge_gap_mm']}` mm",
        f"- Edge-locked placements (`<=40 mm`): `{gap['edge_locked_count']}`",
        "",
    ]
    for part in gap["focus_parts"]:
        lines.extend(
            [
                f"### {part['part_id']}",
                "",
                f"- area mm2: `{part['area_mm2']}`",
                f"- placement_count: `{part['placement_count']}`",
                f"- avg_min_edge_gap_mm: `{part['avg_min_edge_gap_mm']}`",
                f"- worst_min_edge_gap_mm: `{part['worst_min_edge_gap_mm']}`",
                "",
                "| sheet | rot deg | nearest edge | min edge gap mm | left | right | bottom | top |",
                "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in part["placements"]:
            gaps = row["edge_gaps_mm"]
            lines.append(
                f"| {row['sheet_index']} | {row['rotation_deg']} | {row['nearest_edge']} | {row['min_edge_gap_mm']} | {gaps['left']} | {gaps['right']} | {gaps['bottom']} | {gaps['top']} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Comparison vs Q70",
            "",
            "| metric | Q70 | Q71 |",
            "| --- | ---: | ---: |",
            f"| placed_count | {q70['placed_count']} | {run['placed_count']} |",
            f"| avg min edge gap (largest parts) | {q70['anchor_edge_gaps']['avg_min_edge_gap_mm']} | {gap['avg_min_edge_gap_mm']} |",
            f"| worst min edge gap (largest parts) | {q70['anchor_edge_gaps']['worst_min_edge_gap_mm']} | {gap['worst_min_edge_gap_mm']} |",
            f"| edge_locked_count | {q70['anchor_edge_gaps']['edge_locked_count']} | {gap['edge_locked_count']} |",
            "",
            "## Visual Proxy",
            "",
            f"- Render manifest: `artifacts/benchmarks/sgh_q71/renders/{RUN_ID}/render_manifest.json`",
            f"- Input: `{input_rel}`",
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
            "- summary: `artifacts/benchmarks/sgh_q71/q71_summary.json`",
            f"- output: `artifacts/benchmarks/sgh_q71/outputs/{RUN_ID}_output.json`",
            f"- log: `artifacts/benchmarks/sgh_q71/logs/{RUN_ID}.log`",
        ]
    )
    (Q71 / "q71_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=int, default=600)
    args = parser.parse_args()
    if not SOLVER_BIN.exists():
        raise SystemExit(f"ERROR: solver binary missing: {SOLVER_BIN}")

    inp = build_input(args.time_limit)
    input_rel = str(inp.relative_to(Q71))
    out = run(inp, args.time_limit)
    render_run(71, RUN_ID, input_rel, f"outputs/{RUN_ID}_output.json")
    render_manifest = json.loads((Q71 / "renders" / RUN_ID / "render_manifest.json").read_text())

    run_summary = summarize(out)
    q70_summary = summarize(json.loads(Q70_OUT.read_text()))
    summary = {
        "task": "sgh_q71_anchor_edge_lock_and_flush_alignment",
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
        "comparisons": {"q70_baseline": q70_summary},
        "per_sheet": render_manifest.get("per_sheet", []),
    }
    improves_avg_gap = (
        run_summary["anchor_edge_gaps"]["avg_min_edge_gap_mm"] is not None
        and q70_summary["anchor_edge_gaps"]["avg_min_edge_gap_mm"] is not None
        and run_summary["anchor_edge_gaps"]["avg_min_edge_gap_mm"]
        < q70_summary["anchor_edge_gaps"]["avg_min_edge_gap_mm"]
    )
    improves_locked = (
        run_summary["anchor_edge_gaps"]["edge_locked_count"]
        >= q70_summary["anchor_edge_gaps"]["edge_locked_count"]
    )
    acceptance = {
        "forced_latest_locked": bool(run_summary["forced_latest_locked"]),
        "improves_q70_anchor_avg_gap": bool(improves_avg_gap),
        "keeps_or_improves_q70_edge_locked_count": bool(improves_locked),
        "direct_fallback_blocked_or_unused": bool(run_summary["anchor_direct_fallback_blocked"])
        or run_summary["anchor_selected_path"] in {"catalog", "feature"},
    }
    summary["acceptance"] = acceptance
    if all(acceptance.values()):
        summary["verdict"] = "PASS"
        summary["finding"] = (
            "Q71 mar explicit edge-lock kriterium alapjan tartja bent a forced-latest Anchor placementeket, "
            "es az explicit fallback nem tudja csendben lerontani oket. A lenyegi meroszam itt az, hogy a "
            "legnagyobb darabok atlagos min-edge-gapje javuljon a Q70-hez kepest."
        )
    else:
        summary["verdict"] = "PARTIAL"
        summary["finding"] = (
            "Q71 mar edge-lock tudatosabb futast ad, de ha a legnagyobb darabok edge-gap summaryja vagy a "
            "render nem javul meggyozoen a Q70-hez kepest, akkor tovabbi solver-javitas kell."
        )
    (Q71 / "q71_summary.json").write_text(json.dumps(summary, indent=2))
    write_report(summary, input_rel)


if __name__ == "__main__":
    main()
