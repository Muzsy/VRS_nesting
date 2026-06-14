#!/usr/bin/env python3
"""SGH-Q42 - Full276 LV8 continuous rotation benchmark.

Run A: 1200 s. Run B: 2400 s only if Run A does not achieve a valid <=2 sheet
full276 layout. The input is derived from the canonical Q32 full276 fixture, but
part-level allowed_rotations_deg lists are removed so the global
rotation_policy="continuous" is the effective policy.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
BASE_FULL276 = ROOT / "artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json"

Q42 = ROOT / "artifacts/benchmarks/sgh_q42"
INPUTS = Q42 / "inputs"
OUTPUTS = Q42 / "outputs"
LOGS = Q42 / "logs"
RENDERS = Q42 / "renders"

MARGIN_MM = 5.0
SPACING_MM = 8.0
KERF_MM = 0.0
SEED = 42
TOTAL_INSTANCES = 276
TARGET_USED_SHEETS = 2
RUN_TIMES = [1200, 2400]
RUN_ID_PREFIX = "q42_full276_3x1500x3000_margin5_spacing8_continuous"

try:
    import cairosvg  # noqa: F401
    HAVE_CAIROSVG = True
except Exception:
    HAVE_CAIROSVG = False


def load_base() -> dict[str, Any]:
    return json.loads(BASE_FULL276.read_text())


def load_parts() -> list[dict[str, Any]]:
    parts = copy.deepcopy(load_base()["parts"])
    for part in parts:
        part.pop("allowed_rotations_deg", None)
        part.pop("rotation_policy", None)
    return parts


def base_part_lookup() -> dict[str, dict[str, Any]]:
    return {p["id"]: p for p in load_base()["parts"]}


def stocks() -> list[dict[str, Any]]:
    return [{"id": "S1500x3000", "quantity": 3, "width": 1500.0, "height": 3000.0}]


def build_input(time_limit_s: int) -> Path:
    doc = {
        "contract_version": "v1",
        "project_name": f"sgh_q42_full276_continuous_{time_limit_s}",
        "seed": SEED,
        "time_limit_s": time_limit_s,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": MARGIN_MM,
        "spacing_mm": SPACING_MM,
        "kerf_mm": KERF_MM,
        "rotation_policy": "continuous",
        "stocks": stocks(),
        "parts": load_parts(),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"{RUN_ID_PREFIX}_{time_limit_s}.json"
    path.write_text(json.dumps(doc, indent=2))
    return path


def run_id(time_limit_s: int) -> str:
    return f"{RUN_ID_PREFIX}_{time_limit_s}"


def output_path(time_limit_s: int) -> Path:
    return OUTPUTS / f"{RUN_ID_PREFIX}_{time_limit_s}_output.json"


def run_solver(time_limit_s: int, input_path: Path, reuse_existing: bool) -> dict[str, Any]:
    rid = run_id(time_limit_s)
    out_path = output_path(time_limit_s)
    if reuse_existing and out_path.exists():
        out = json.loads(out_path.read_text())
        out["_wall_time_s"] = None
        out["_time_limit_s"] = time_limit_s
        out["_reused_existing_output"] = True
        return out

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.pop("SGH_Q35_SPACING_VALIDATOR", None)
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(input_path), "--output", str(out_path)],
        capture_output=True,
        text=True,
        timeout=time_limit_s + 1200,
        env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{rid}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\ntime_limit_s={time_limit_s}\n"
        f"stdout:\n{proc.stdout[:4000]}\n"
        f"stderr:\n{proc.stderr[:4000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{rid} solver exit {proc.returncode}: {proc.stderr[:800]}")
    out = json.loads(out_path.read_text())
    out["_wall_time_s"] = wall
    out["_time_limit_s"] = time_limit_s
    out["_reused_existing_output"] = False
    return out


def expand_stock_sheets(stock_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for stock in stock_list:
        for _ in range(int(stock["quantity"])):
            out.append({"id": stock["id"], "width": float(stock["width"]), "height": float(stock["height"])})
    return out


def _part_outer(part: dict[str, Any]) -> list[tuple[float, float]]:
    raw = part.get("outer_points") or part.get("prepared_outer_points") or []
    pts = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            pts.append((float(item[0]), float(item[1])))
    if not pts:
        pts = [(0.0, 0.0), (float(part.get("width", 0.0)), 0.0),
               (float(part.get("width", 0.0)), float(part.get("height", 0.0))),
               (0.0, float(part.get("height", 0.0)))]
    return pts


def _transform(ring: list[tuple[float, float]], ax: float, ay: float, rot_deg: float) -> list[tuple[float, float]]:
    th = math.radians(rot_deg)
    c, s = math.cos(th), math.sin(th)
    return [(ax + x * c - y * s, ay + x * s + y * c) for x, y in ring]


def polygon_area(part: dict[str, Any]) -> float:
    pts = _part_outer(part)
    if len(pts) < 3:
        return 0.0
    return abs(0.5 * sum(
        pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
        for i in range(len(pts))
    ))


def render_sheet_svg(rid: str, sheet_index: int, sw: float, sh: float,
                     placements: list[dict[str, Any]], parts_by_id: dict[str, dict[str, Any]]) -> str:
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{sw:.2f}mm" height="{sh:.2f}mm" viewBox="0 0 {sw:.4f} {sh:.4f}">',
        f'  <!-- Q42 {rid} sheet {sheet_index} original contours, margin {MARGIN_MM:g}, spacing {SPACING_MM:g} -->',
        f'  <rect width="{sw:.4f}" height="{sh:.4f}" fill="#ffffff" stroke="#000000" stroke-width="2"/>',
        f'  <rect x="{MARGIN_MM:.4f}" y="{MARGIN_MM:.4f}" width="{sw - 2 * MARGIN_MM:.4f}" '
        f'height="{sh - 2 * MARGIN_MM:.4f}" fill="none" stroke="#cc0000" stroke-width="1.5" stroke-dasharray="8,6"/>',
    ]
    palette = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
               "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac", "#1f77b4", "#2ca02c"]
    count = 0
    for placement in placements:
        if placement.get("sheet_index") != sheet_index:
            continue
        part = parts_by_id.get(placement["part_id"])
        if not part:
            continue
        world = _transform(_part_outer(part), float(placement["x"]), float(placement["y"]),
                           float(placement.get("rotation_deg", 0.0)))
        d = " ".join(f"{'M' if idx == 0 else 'L'} {x:.3f} {sh - y:.3f}" for idx, (x, y) in enumerate(world)) + " Z"
        colour = palette[(hash(placement["part_id"]) & 0xFFFFFF) % len(palette)]
        lines.append(f'  <path d="{d}" fill="{colour}" fill-opacity="0.7" stroke="#222" stroke-width="0.5"/>')
        count += 1
    lines.append(f'  <text x="6" y="20" font-size="34" fill="#000">{rid} sheet {sheet_index} placed={count}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def render_overview_svg(rid: str, used: list[int], sheet_dims: dict[int, tuple[float, float]],
                        status: str, placed: int, total: int) -> str:
    if not used:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><text x="10" y="60">{rid}: no used sheets</text></svg>'
    target_h = 600.0
    gap = 40.0
    boxes = []
    x = gap
    max_h = 0.0
    for si in used:
        w, h = sheet_dims[si]
        scale = target_h / h
        bw, bh = w * scale, h * scale
        boxes.append((x, si, bw, bh))
        x += bw + gap
        max_h = max(max_h, bh)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{x:.0f}" height="{max_h + 80:.0f}" viewBox="0 0 {x:.0f} {max_h + 80:.0f}">',
        f'<rect width="{x:.0f}" height="{max_h + 80:.0f}" fill="#f7f7f7"/>',
        f'<text x="10" y="28" font-size="22" fill="#000">{rid} status={status} placed={placed}/{total} sheets={len(used)}</text>',
    ]
    for bx, si, bw, bh in boxes:
        lines.append(f'<rect x="{bx:.1f}" y="50" width="{bw:.1f}" height="{bh:.1f}" fill="#dfe7f0" stroke="#000" stroke-width="1.5"/>')
        lines.append(f'<text x="{bx + 4:.1f}" y="74" font-size="16" fill="#000">sheet {si}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def svg_to_png(svg_path: Path, png_path: Path) -> bool:
    if not HAVE_CAIROSVG:
        return False
    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1400)
        return True
    except Exception as exc:
        print(f"PNG conversion failed for {svg_path}: {exc}")
        return False


def render_run(time_limit_s: int, out: dict[str, Any]) -> dict[str, Any]:
    rid = run_id(time_limit_s)
    rdir = RENDERS / rid
    rdir.mkdir(parents=True, exist_ok=True)
    parts_by_id = base_part_lookup()
    expanded = expand_stock_sheets(stocks())
    sheet_dims = {i: (s["width"], s["height"]) for i, s in enumerate(expanded)}
    placements = out.get("placements", [])
    used = sorted({int(pl["sheet_index"]) for pl in placements})
    svg_count = 0
    png_count = 0
    per_sheet = []
    for render_idx, sheet_index in enumerate(used):
        sw, sh = sheet_dims[sheet_index]
        svg_path = rdir / f"sheet_{render_idx:02d}.svg"
        png_path = rdir / f"sheet_{render_idx:02d}.png"
        svg_path.write_text(render_sheet_svg(rid, sheet_index, sw, sh, placements, parts_by_id))
        svg_count += 1
        if svg_to_png(svg_path, png_path):
            png_count += 1
        placed_area = sum(
            polygon_area(parts_by_id.get(pl["part_id"], {}))
            for pl in placements if int(pl.get("sheet_index", -1)) == sheet_index
        )
        per_sheet.append({
            "sheet_index": sheet_index,
            "stock_id": expanded[sheet_index]["id"],
            "stock_width": sw,
            "stock_height": sh,
            "placed_count": sum(1 for pl in placements if int(pl.get("sheet_index", -1)) == sheet_index),
            "placed_part_area": round(placed_area, 2),
            "physical_utilization_pct": round(100.0 * placed_area / (sw * sh), 4),
            "usable_utilization_pct": round(100.0 * placed_area / ((sw - 2 * MARGIN_MM) * (sh - 2 * MARGIN_MM)), 4),
            "svg_path": str(svg_path.relative_to(ROOT)),
            "png_path": str(png_path.relative_to(ROOT)),
        })
    metrics = out.get("metrics", {})
    total = int(metrics.get("placed_count", 0)) + int(metrics.get("unplaced_count", 0))
    overview_svg = rdir / "overview.svg"
    overview_png = rdir / "overview.png"
    overview_svg.write_text(render_overview_svg(rid, used, sheet_dims, out.get("status", ""), int(metrics.get("placed_count", 0)), total))
    svg_count += 1
    if svg_to_png(overview_svg, overview_png):
        png_count += 1
    manifest = {
        "run_id": rid,
        "used_sheet_count": len(used),
        "used_sheet_indices": used,
        "render_source": "original_canonical_full276_contours",
        "svg_count": svg_count,
        "png_count": png_count,
        "have_cairosvg": HAVE_CAIROSVG,
        "per_sheet": per_sheet,
    }
    (rdir / "render_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def is_orthogonal(deg: float) -> bool:
    return any(abs((deg % 360.0) - target) <= 1e-6 for target in (0.0, 90.0, 180.0, 270.0))


def rotation_evidence(input_doc: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    rotations = [float(pl.get("rotation_deg", 0.0)) % 360.0 for pl in out.get("placements", [])]
    unique = sorted({round(r, 6) for r in rotations})
    non_orth = [r for r in rotations if not is_orthogonal(r)]
    examples = []
    for pl in out.get("placements", []):
        rot = float(pl.get("rotation_deg", 0.0)) % 360.0
        if not is_orthogonal(rot):
            examples.append({
                "instance_id": pl.get("instance_id"),
                "part_id": pl.get("part_id"),
                "sheet_index": pl.get("sheet_index"),
                "rotation_deg": round(rot, 6),
            })
        if len(examples) >= 10:
            break
    part_level_allowed_present = sum(1 for p in input_doc.get("parts", []) if "allowed_rotations_deg" in p)
    return {
        "rotation_policy_input": input_doc.get("rotation_policy"),
        "part_level_allowed_rotations_present_count": part_level_allowed_present,
        "part_level_allowed_rotations_handling": "removed_from_q42_generated_input",
        "unique_rotation_values_count": len(unique),
        "unique_rotation_values_deg": unique,
        "non_orthogonal_rotation_count": len(non_orth),
        "min_rotation_deg": min(rotations) if rotations else None,
        "max_rotation_deg": max(rotations) if rotations else None,
        "non_orthogonal_examples": examples,
        "continuous_rotation_proven_by_output": len(non_orth) > 0,
    }


def diagnostics(out: dict[str, Any]) -> dict[str, Any]:
    return out.get("optimizer_diagnostics") or {}


def run_summary(time_limit_s: int, input_path: Path, out: dict[str, Any], render_manifest: dict[str, Any]) -> dict[str, Any]:
    input_doc = json.loads(input_path.read_text())
    d = diagnostics(out)
    m = out.get("metrics", {})
    placements = out.get("placements", [])
    used = sorted({int(pl["sheet_index"]) for pl in placements})
    parts_by_id = base_part_lookup()
    placed_area = sum(polygon_area(parts_by_id.get(pl["part_id"], {})) for pl in placements)
    physical_used = len(used) * 1500.0 * 3000.0
    usable_used = len(used) * (1500.0 - 2 * MARGIN_MM) * (3000.0 - 2 * MARGIN_MM)
    margin_count = d.get("technology_margin_violation_count")
    spacing_count = d.get("technology_spacing_violation_count")
    row = {
        "run_id": run_id(time_limit_s),
        "time_limit_s": time_limit_s,
        "status": out.get("status"),
        "placed_count": int(m.get("placed_count", 0)),
        "unplaced_count": int(m.get("unplaced_count", 0)),
        "used_sheet_count": d.get("sparrow_ms_used_sheet_count", len(used)),
        "used_sheet_indices": d.get("sparrow_ms_used_sheet_indices", used),
        "available_sheet_count": d.get("sparrow_ms_available_sheet_count"),
        "physical_utilization_pct": round(100.0 * placed_area / physical_used, 4) if physical_used else 0.0,
        "usable_utilization_pct": round(100.0 * placed_area / usable_used, 4) if usable_used else 0.0,
        "final_pairs": d.get("sparrow_ms_final_pairs"),
        "boundary_violations": d.get("sparrow_ms_boundary_violations"),
        "technology_margin_violation_count": margin_count,
        "technology_spacing_violation_count": spacing_count,
        "margin_mm": d.get("technology_margin_mm"),
        "spacing_mm": d.get("technology_spacing_mm"),
        "kerf_mm": d.get("technology_kerf_mm"),
        "technology_sheet_margin_applied": margin_count is not None,
        "technology_part_spacing_applied": d.get("technology_spacing_geometry_applied") is True,
        "solver_reported_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "wall_time_s": round(out["_wall_time_s"], 3) if isinstance(out.get("_wall_time_s"), (int, float)) else None,
        "reused_existing_output": bool(out.get("_reused_existing_output")),
        "rotation_evidence": rotation_evidence(input_doc, out),
        "render_manifest": str((RENDERS / run_id(time_limit_s) / "render_manifest.json").relative_to(ROOT)),
        "render_svg_count": render_manifest.get("svg_count"),
        "render_png_count": render_manifest.get("png_count"),
    }
    row["acceptance_pass"] = (
        row["status"] == "ok"
        and row["placed_count"] == TOTAL_INSTANCES
        and row["unplaced_count"] == 0
        and int(row["used_sheet_count"] or 999) <= TARGET_USED_SHEETS
        and int(row["final_pairs"] or 0) == 0
        and int(row["boundary_violations"] or 0) == 0
        and int(row["technology_margin_violation_count"] or 0) == 0
        and int(row["technology_spacing_violation_count"] or 0) == 0
        and row["rotation_evidence"]["rotation_policy_input"] == "continuous"
        and row["rotation_evidence"]["part_level_allowed_rotations_present_count"] == 0
    )
    return row


def write_report(summary: dict[str, Any]) -> None:
    report = Q42 / "q42_report.md"
    rows = summary["runs"]
    best = summary["best_run"]
    verdict = "PASS" if summary["acceptance_achieved"] else "FAIL / NOT ACHIEVED"
    lines = [
        "# SGH-Q42 Report - Full276 LV8 continuous rotation benchmark",
        "",
        f"## Verdict: {verdict}",
        "",
        "## Goal",
        "",
        "- Full276 LV8 package, max 3 x 1500x3000 mm sheets.",
        "- Target: valid nesting on <= 2 sheets.",
        "- Technology: margin 5.0 mm, spacing 8.0 mm, kerf 0.0 mm.",
        "- Rotation: global `rotation_policy = continuous` with part-level legacy lists removed from Q42 input.",
        "",
        "## Runs",
        "",
        "| run | status | placed | unplaced | used sheets | used indices | util physical % | final pairs | boundary | margin viol | spacing viol | wall s | runtime ms | acceptance |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['run_id']} | {row['status']} | {row['placed_count']} | {row['unplaced_count']} | "
            f"{row['used_sheet_count']} | {row['used_sheet_indices']} | {row['physical_utilization_pct']} | "
            f"{row['final_pairs']} | {row['boundary_violations']} | "
            f"{row['technology_margin_violation_count']} | {row['technology_spacing_violation_count']} | "
            f"{row['wall_time_s']} | {row['solver_reported_runtime_ms']} | {'PASS' if row['acceptance_pass'] else 'FAIL'} |"
        )
    lines += [
        "",
        "## Continuous rotation evidence",
        "",
    ]
    for row in rows:
        ev = row["rotation_evidence"]
        lines += [
            f"### {row['run_id']}",
            "",
            f"- input `rotation_policy`: `{ev['rotation_policy_input']}`",
            f"- part-level `allowed_rotations_deg` count in generated input: `{ev['part_level_allowed_rotations_present_count']}`",
            f"- handling: `{ev['part_level_allowed_rotations_handling']}`",
            f"- unique rotation values count: `{ev['unique_rotation_values_count']}`",
            f"- non-orthogonal rotation count: `{ev['non_orthogonal_rotation_count']}`",
            f"- min/max rotation: `{ev['min_rotation_deg']}` / `{ev['max_rotation_deg']}`",
            f"- continuous proven by output: `{ev['continuous_rotation_proven_by_output']}`",
            f"- non-orthogonal examples: `{ev['non_orthogonal_examples']}`",
            "",
        ]
    lines += [
        "## Margin / spacing validation",
        "",
        "| run | margin | spacing | kerf | sheet margin applied | part spacing applied | margin violations | spacing violations |",
        "| --- | ---: | ---: | ---: | --- | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['run_id']} | {row['margin_mm']} | {row['spacing_mm']} | {row['kerf_mm']} | "
            f"{row['technology_sheet_margin_applied']} | {row['technology_part_spacing_applied']} | "
            f"{row['technology_margin_violation_count']} | {row['technology_spacing_violation_count']} |"
        )
    lines += [
        "",
        "## Best result",
        "",
        f"- Best run: `{best['run_id']}`",
        f"- Best valid sheet count: `{best.get('used_sheet_count')}`",
        f"- Acceptance achieved: `{summary['acceptance_achieved']}`",
        "",
        "## Render evidence",
        "",
    ]
    for row in rows:
        lines.append(f"- `{row['run_id']}`: `{row['render_manifest']}`")
    report.write_text("\n".join(lines) + "\n")


def write_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid_rows = [
        r for r in rows
        if r["status"] == "ok"
        and r["placed_count"] == TOTAL_INSTANCES
        and r["unplaced_count"] == 0
        and int(r["final_pairs"] or 0) == 0
        and int(r["boundary_violations"] or 0) == 0
        and int(r["technology_margin_violation_count"] or 0) == 0
        and int(r["technology_spacing_violation_count"] or 0) == 0
    ]
    if valid_rows:
        best = sorted(valid_rows, key=lambda r: (int(r["used_sheet_count"] or 999), r["time_limit_s"]))[0]
    else:
        best = sorted(rows, key=lambda r: (-r["placed_count"], int(r["used_sheet_count"] or 999), r["time_limit_s"]))[0]
    summary = {
        "task": "SGH-Q42",
        "acceptance_achieved": any(r["acceptance_pass"] for r in rows),
        "run_b_required": not rows[0]["acceptance_pass"],
        "best_run": best,
        "runs": rows,
    }
    (Q42 / "q42_summary.json").write_text(json.dumps(summary, indent=2))
    write_report(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()
    if not SOLVER_BIN.exists():
        raise SystemExit(f"missing solver binary: {SOLVER_BIN}")
    Q42.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, time_limit_s in enumerate(RUN_TIMES):
        input_path = build_input(time_limit_s)
        out = run_solver(time_limit_s, input_path, args.reuse_existing)
        render_manifest = render_run(time_limit_s, out)
        row = run_summary(time_limit_s, input_path, out, render_manifest)
        rows.append(row)
        print(f"{row['run_id']}: status={row['status']} placed={row['placed_count']} "
              f"unplaced={row['unplaced_count']} sheets={row['used_sheet_count']} "
              f"acceptance={row['acceptance_pass']}")
        if idx == 0 and row["acceptance_pass"]:
            break
    summary = write_summary(rows)
    print(f"Q42 acceptance_achieved={summary['acceptance_achieved']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
