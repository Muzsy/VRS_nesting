#!/usr/bin/env python3
"""SGH-Q39 — Full LV8 production benchmark with strict regression gates + SVG/PNG renders.

Runs the mandatory baseline + spacing/margin production matrix at FULL time limits (NO cap on
mandatory runs), renders every used sheet of every run to SVG + PNG (ORIGINAL contours, not
spacing-expanded), emits diagnostic tables + machine-readable regression gates, and exits
non-zero if any mandatory baseline regresses.

Datasets (committed canonical inputs; no hand-invented parts):
  - dense191: artifacts/benchmarks/sgh_q31/inputs/dense191.json  (12 parts, 191 instances)
  - full276:  artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json (12 parts, 276)

Usage:
  python3 scripts/bench_sgh_q39_full_lv8_visuals.py --tier mandatory
  python3 scripts/bench_sgh_q39_full_lv8_visuals.py --tier extended
  python3 scripts/bench_sgh_q39_full_lv8_visuals.py --only dense191_baseline|full276_baselines|spacing_runs|render_check
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
BASE_FULL276 = ROOT / "artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json"
BASE_DENSE191 = ROOT / "artifacts/benchmarks/sgh_q31/inputs/dense191.json"

Q39 = ROOT / "artifacts/benchmarks/sgh_q39"
INPUTS = Q39 / "inputs"
OUTPUTS = Q39 / "outputs"
TABLES = Q39 / "tables"
LOGS = Q39 / "logs"
RENDERS = Q39 / "renders"

try:
    import cairosvg  # noqa
    HAVE_CAIROSVG = True
except Exception:
    HAVE_CAIROSVG = False


def sheets(spec: str) -> list[dict]:
    if spec == "1x1500x3000":
        return [{"id": "LV8_SHEET", "quantity": 1, "width": 1500.0, "height": 3000.0}]
    if spec == "2x1500x3000":
        return [{"id": "LV8_SHEET", "quantity": 2, "width": 1500.0, "height": 3000.0}]
    if spec == "3x1500x3000":
        return [{"id": "LV8_SHEET", "quantity": 3, "width": 1500.0, "height": 3000.0}]
    if spec == "mixed":
        return [
            {"id": "LV8_BIG", "quantity": 1, "width": 1500.0, "height": 3000.0},
            {"id": "LV8_SMALL", "quantity": 2, "width": 1000.0, "height": 2000.0},
        ]
    raise ValueError(spec)


# (run_id, tier, dataset, sheet_spec, margin, spacing, time_limit, baseline)
SCENARIOS = [
    ("B0", "mandatory", "dense191", "1x1500x3000", 0.0, 0.0, 600, None),
    ("B1", "mandatory", "full276", "2x1500x3000", 0.0, 0.0, 1200, None),
    ("B2", "mandatory", "full276", "3x1500x3000", 0.0, 0.0, 1200, None),
    ("B3", "mandatory", "full276", "mixed", 0.0, 0.0, 1200, None),
    ("S0", "mandatory", "dense191", "1x1500x3000", 0.0, 2.0, 600, "B0"),
    ("S1", "mandatory", "dense191", "1x1500x3000", 5.0, 2.0, 600, "B0"),
    ("S2", "mandatory", "full276", "2x1500x3000", 0.0, 2.0, 1200, "B1"),
    ("S3", "mandatory", "full276", "2x1500x3000", 5.0, 2.0, 1200, "B1"),
    ("S4", "mandatory", "full276", "3x1500x3000", 0.0, 2.0, 1200, "B2"),
    ("S5", "mandatory", "full276", "mixed", 0.0, 2.0, 1200, "B3"),
    ("E0", "extended", "dense191", "1x1500x3000", 0.0, 5.0, 600, "B0"),
    ("E1", "extended", "full276", "2x1500x3000", 0.0, 5.0, 1200, "B1"),
    ("E2", "extended", "full276", "2x1500x3000", 5.0, 5.0, 1200, "B1"),
    ("E3", "extended", "full276", "3x1500x3000", 0.0, 2.0, 1200, "B2"),
    ("E4", "extended", "full276", "mixed", 5.0, 2.0, 1200, "B3"),
]

MANDATORY = [s for s in SCENARIOS if s[1] == "mandatory"]


def scn_by_id(run_id: str):
    for s in SCENARIOS:
        if s[0] == run_id:
            return s
    return None


# ── inputs ────────────────────────────────────────────────────────────────────

def load_parts(dataset: str) -> list[dict]:
    base = BASE_DENSE191 if dataset == "dense191" else BASE_FULL276
    return copy.deepcopy(json.loads(base.read_text())["parts"])


def part_lookup(dataset: str) -> dict[str, dict]:
    return {p["id"]: p for p in load_parts(dataset)}


def build_input(scn) -> Path:
    run_id, tier, dataset, sheet_spec, margin, spacing, tl, _b = scn
    doc = {
        "contract_version": "v1",
        "project_name": f"sgh_q39_{run_id}_{dataset}",
        "seed": 42,
        "time_limit_s": tl,  # FULL time limit; no cap for mandatory runs.
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": margin,
        "spacing_mm": spacing,
        "kerf_mm": 0.0,
        "stocks": sheets(sheet_spec),
        "parts": load_parts(dataset),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"{run_id}_{dataset}_{sheet_spec}_m{margin:g}_s{spacing:g}.json"
    path.write_text(json.dumps(doc, indent=2))
    return path


def expand_stock_sheets(stock_list: list[dict]) -> list[dict]:
    """Expanded per-sheet stock dims, matching the solver's expand_sheets order."""
    out = []
    for st in stock_list:
        for _ in range(int(st["quantity"])):
            out.append({"id": st["id"], "width": float(st["width"]), "height": float(st["height"])})
    return out


# ── solver ──────────────────────────────────────────────────────────────────

def run_solver(scn, input_path: Path) -> dict[str, Any]:
    run_id = scn[0]
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{run_id}_output.json"
    tl = scn[6]
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(input_path), "--output", str(out_path)],
        capture_output=True, text=True, timeout=tl + 900,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{run_id}.log").write_text(f"exit={proc.returncode}\nwall_s={wall:.3f}\nstderr:\n{proc.stderr[:2000]}\n")
    if proc.returncode != 0:
        raise RuntimeError(f"{run_id} solver exit {proc.returncode}: {proc.stderr[:400]}")
    out = json.loads(out_path.read_text())
    out["_wall_time_s"] = wall
    out["_time_limit_s"] = tl
    return out


# ── rendering (ORIGINAL contours, anchor transform) ───────────────────────────

_PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
            "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac", "#1f77b4", "#2ca02c"]


def _colour(part_id: str) -> str:
    return _PALETTE[(hash(part_id) & 0xFFFFFF) % len(_PALETTE)]


def _part_outer(part: dict) -> list[tuple[float, float]]:
    raw = part.get("outer_points") or part.get("prepared_outer_points") or []
    pts = []
    for pr in raw:
        if isinstance(pr, (list, tuple)) and len(pr) >= 2:
            pts.append((float(pr[0]), float(pr[1])))
    if not pts:
        w = float(part.get("width", 0)); h = float(part.get("height", 0))
        pts = [(0, 0), (w, 0), (w, h), (0, h)]
    return pts


def _transform(ring, ax, ay, rot_deg):
    th = math.radians(rot_deg)
    c, s = math.cos(th), math.sin(th)
    return [(ax + x * c - y * s, ay + x * s + y * c) for x, y in ring]


def render_sheet_svg(run_id, sheet_index, sw, sh, margin, placements, parts_by_id) -> str:
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{sw:.2f}mm" height="{sh:.2f}mm" viewBox="0 0 {sw:.4f} {sh:.4f}">',
        f'  <!-- Q39 {run_id} sheet {sheet_index} ORIGINAL contours -->',
        f'  <rect width="{sw:.4f}" height="{sh:.4f}" fill="#ffffff" stroke="#000000" stroke-width="2"/>',
    ]
    if margin > 0:
        lines.append(
            f'  <rect x="{margin:.4f}" y="{margin:.4f}" width="{sw - 2 * margin:.4f}" '
            f'height="{sh - 2 * margin:.4f}" fill="none" stroke="#cc0000" '
            f'stroke-width="1.5" stroke-dasharray="8,6"/>'
        )
    n = 0
    for pl in placements:
        if pl.get("sheet_index") != sheet_index:
            continue
        part = parts_by_id.get(pl["part_id"])
        if part is None:
            continue
        world = _transform(_part_outer(part), pl["x"], pl["y"], pl.get("rotation_deg", 0.0))
        d = " ".join(f"{'M' if i == 0 else 'L'} {x:.3f} {sh - y:.3f}" for i, (x, y) in enumerate(world)) + " Z"
        lines.append(f'  <path d="{d}" fill="{_colour(pl["part_id"])}" fill-opacity="0.7" stroke="#222" stroke-width="0.5"/>')
        n += 1
    lines.append(f'  <text x="6" y="20" font-size="34" fill="#000">{run_id} sheet {sheet_index}  placed={n}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def render_overview_svg(run_id, used, sheet_dims, status, placed, total) -> str:
    # Lay used sheets in a row, scaled to a common height.
    if not used:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120">'
                f'<rect width="400" height="120" fill="#fff" stroke="#000"/>'
                f'<text x="10" y="60" font-size="16">{run_id}: no used sheets (status {status}, {placed}/{total})</text></svg>')
    target_h = 600.0
    gap = 40.0
    boxes = []
    x = gap
    maxh = 0.0
    for si in used:
        w, h = sheet_dims[si]
        scale = target_h / h
        bw, bh = w * scale, h * scale
        boxes.append((x, si, bw, bh))
        x += bw + gap
        maxh = max(maxh, bh)
    total_w = x
    total_hh = maxh + 80
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w:.0f}" height="{total_hh:.0f}" viewBox="0 0 {total_w:.0f} {total_hh:.0f}">',
             f'<rect width="{total_w:.0f}" height="{total_hh:.0f}" fill="#f7f7f7"/>',
             f'<text x="10" y="28" font-size="22" fill="#000">{run_id}  status={status}  placed={placed}/{total}  sheets={len(used)}</text>']
    for (bx, si, bw, bh) in boxes:
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
    except Exception as e:
        print(f"    PNG conversion failed for {svg_path.name}: {e}")
        return False


def render_run(scn, out: dict) -> dict:
    run_id, _, dataset, sheet_spec, margin, spacing, _tl, _b = scn
    rdir = RENDERS / run_id
    rdir.mkdir(parents=True, exist_ok=True)
    parts_by_id = part_lookup(dataset)
    expanded = expand_stock_sheets(sheets(sheet_spec))
    sheet_dims = {i: (s["width"], s["height"]) for i, s in enumerate(expanded)}
    placements = out.get("placements", [])
    used = sorted({pl["sheet_index"] for pl in placements})
    t0 = time.monotonic()
    svg_t = png_t = 0.0
    svg_count = png_count = 0
    per_sheet = []
    # Render each USED sheet (sequential render index 00,01,... per spec path scheme).
    for render_idx, si in enumerate(used):
        sw, sh = sheet_dims.get(si, (1500.0, 3000.0))
        svg = render_sheet_svg(run_id, si, sw, sh, margin, placements, parts_by_id)
        svg_path = rdir / f"sheet_{render_idx:02d}.svg"
        ts = time.monotonic(); svg_path.write_text(svg); svg_t += time.monotonic() - ts
        svg_count += 1
        png_path = rdir / f"sheet_{render_idx:02d}.png"
        tp = time.monotonic()
        if svg_to_png(svg_path, png_path):
            png_count += 1
        png_t += time.monotonic() - tp
        placed_on = sum(1 for pl in placements if pl["sheet_index"] == si)
        placed_area = sum(part_polygon_area(parts_by_id.get(pl["part_id"], {}))
                          for pl in placements if pl["sheet_index"] == si)
        phys = sw * sh
        usable = (sw - 2 * margin) * (sh - 2 * margin) if margin > 0 else phys
        per_sheet.append({
            "run_id": run_id, "sheet_index": si,
            "stock_id": expanded[si]["id"] if si < len(expanded) else "",
            "stock_width": sw, "stock_height": sh,
            "physical_sheet_area": round(phys, 2), "usable_sheet_area": round(usable, 2),
            "placed_count": placed_on, "placed_part_area": round(placed_area, 2),
            "physical_utilization_pct": round(100 * placed_area / phys, 4) if phys else 0.0,
            "usable_utilization_pct": round(100 * placed_area / usable, 4) if usable else 0.0,
            "svg_path": str(svg_path.relative_to(ROOT)), "png_path": str(png_path.relative_to(ROOT)),
        })
    # Overview.
    ov_svg = render_overview_svg(run_id, used, sheet_dims, out.get("status"),
                                 out.get("metrics", {}).get("placed_count", 0),
                                 out.get("metrics", {}).get("placed_count", 0) + out.get("metrics", {}).get("unplaced_count", 0))
    ov_svg_path = rdir / "overview.svg"
    ov_svg_path.write_text(ov_svg); svg_count += 1
    ov_png_path = rdir / "overview.png"
    if svg_to_png(ov_svg_path, ov_png_path):
        png_count += 1
    render_total = time.monotonic() - t0
    manifest = {
        "run_id": run_id, "used_sheet_count": len(used), "used_sheet_indices": used,
        "svg_count": svg_count, "png_count": png_count,
        "render_total_ms": round(render_total * 1000, 3),
        "render_svg_total_ms": round(svg_t * 1000, 3), "render_png_total_ms": round(png_t * 1000, 3),
        "render_sheet_count": len(used),
    }
    (rdir / "render_manifest.json").write_text(json.dumps(manifest, indent=2))
    missing_svg = sum(1 for si in range(len(used)) if not (rdir / f"sheet_{si:02d}.svg").exists())
    missing_png = sum(1 for si in range(len(used)) if not (rdir / f"sheet_{si:02d}.png").exists())
    return {
        "per_sheet": per_sheet,
        "render_row": {
            "run_id": run_id, "used_sheet_count": len(used),
            "overview_svg_path": str(ov_svg_path.relative_to(ROOT)),
            "overview_png_path": str(ov_png_path.relative_to(ROOT)),
            "missing_svg_count": missing_svg, "missing_png_count": missing_png,
            "render_status": "ok" if (missing_svg == 0 and missing_png == 0 and ov_png_path.exists()) else "incomplete",
        },
        "manifest": manifest,
    }


def part_polygon_area(part: dict) -> float:
    pts = _part_outer(part) if part else []
    if len(pts) < 3:
        return 0.0
    n = len(pts)
    return abs(0.5 * sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)))


# ── tables ────────────────────────────────────────────────────────────────────

def od(o):
    return o.get("optimizer_diagnostics") or {}


def run_row(scn, inp, out, render_info) -> dict:
    run_id, tier, dataset, sheet_spec, margin, spacing, tl, _b = scn
    d = od(out); m = out.get("metrics", {}); rm = render_info["manifest"]
    total = m.get("placed_count", 0) + m.get("unplaced_count", 0)
    return {
        "run_id": run_id, "tier": tier, "scenario": f"{dataset}/{sheet_spec}/m{margin:g}/s{spacing:g}",
        "dataset": dataset, "seed": 42, "time_limit_s": tl,
        "wall_time_s": round(out.get("_wall_time_s", 0.0), 2),
        "solver_reported_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "status": out.get("status"), "unsupported_reason": out.get("unsupported_reason", ""),
        "placed_count": m.get("placed_count"), "unplaced_count": m.get("unplaced_count"),
        "total_instances": total,
        "used_sheet_count": d.get("sparrow_ms_used_sheet_count"),
        "available_sheet_count": d.get("sparrow_ms_available_sheet_count"),
        "used_sheet_indices": "|".join(map(str, d.get("sparrow_ms_used_sheet_indices") or [])),
        "physical_used_sheet_area": d.get("sparrow_ms_used_sheet_area"),
        "usable_sheet_area": d.get("technology_margin_usable_sheet_area"),
        "placed_part_area": d.get("sparrow_ms_placed_part_area"),
        "physical_utilization_pct": d.get("sparrow_ms_utilization_pct"),
        "usable_utilization_pct": d.get("technology_margin_usable_sheet_area"),
        "final_pairs": d.get("sparrow_ms_final_pairs"),
        "boundary_violations": d.get("sparrow_ms_boundary_violations"),
        "margin_mm": d.get("technology_margin_mm"), "spacing_mm": d.get("technology_part_spacing_mm"),
        "kerf_mm": d.get("technology_kerf_mm"),
        "technology_spacing_offset_mm": d.get("technology_spacing_offset_mm"),
        "technology_margin_violation_count": d.get("technology_margin_violation_count"),
        "technology_spacing_violation_count": d.get("technology_spacing_violation_count"),
        "technology_spacing_safety_net_removed_count": d.get("technology_spacing_safety_net_removed_count"),
        "technology_spacing_offset_failure_count": d.get("technology_spacing_offset_failure_count"),
        "best_full_solution_found": d.get("sparrow_ms_best_full_solution_found"),
        "stock_exhausted": d.get("sparrow_ms_stock_exhausted"),
        "deadline_hit": d.get("sparrow_ms_deadline_hit"),
        "q31_prepare_base_shape_native_hotpath_calls": d.get("sparrow_q31_prepare_base_shape_native_hotpath_calls"),
        "render_sheet_count": rm["render_sheet_count"],
        "render_svg_count": rm["svg_count"], "render_png_count": rm["png_count"],
    }


def stage_row(scn, out):
    d = od(out)
    return {
        "run_id": scn[0], "wall_time_s": round(out.get("_wall_time_s", 0.0), 2),
        "sparrow_ms_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "spacing_offset_build_ms": d.get("technology_spacing_offset_build_ms"),
        "spacing_offset_avg_ms_per_part": d.get("technology_spacing_offset_avg_ms_per_part"),
        "spacing_offset_max_ms_per_part": d.get("technology_spacing_offset_max_ms_per_part"),
        "margin_final_validator_ms": d.get("technology_margin_final_validator_ms"),
        "spacing_final_validator_ms": d.get("technology_spacing_final_validator_ms"),
        "safety_net_ms": d.get("technology_safety_net_ms"),
        "q31_base_shape_cache_build_ms": d.get("sparrow_q31_base_shape_cache_build_ms"),
        "q31_prepare_base_shape_native_hotpath_ms": d.get("sparrow_q31_prepare_base_shape_native_hotpath_ms"),
        "sparrow_iterations": d.get("sparrow_iterations"),
        "sparrow_ms_attempts": d.get("sparrow_ms_attempts"),
        "sparrow_ms_candidate_subsets": d.get("sparrow_ms_candidate_subsets"),
        "search_position_calls": d.get("sparrow_search_position_calls"),
        "search_position_samples": d.get("sparrow_search_position_samples"),
    }


def cde_row(scn, out):
    b = out.get("collision_backend_diagnostics") or {}
    return {
        "run_id": scn[0],
        "cde_batch_candidate_queries": b.get("cde_batch_candidate_queries"),
        "cde_batch_engine_builds": b.get("cde_batch_engine_builds"),
        "cde_batch_hazards_registered": b.get("cde_batch_hazards_registered"),
        "cde_batch_collisions_returned": b.get("cde_batch_collisions_returned"),
        "cde_candidate_session_builds": b.get("cde_candidate_session_builds"),
        "cde_candidate_session_reuses": b.get("cde_candidate_session_reuses"),
        "cde_pair_queries": b.get("cde_pair_queries"),
        "cde_total_queries": b.get("cde_total_queries"),
    }


def write_csv(path, rows):
    TABLES.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows:
            w.writerow(r)


# ── strict gates ────────────────────────────────────────────────────────────

def evaluate_gates(run_rows: dict[str, dict], ran_mandatory: list[str]) -> tuple[dict, list[str]]:
    errs: list[str] = []

    def get(rid, k):
        return run_rows.get(rid, {}).get(k)

    def as_int(v):
        try:
            return int(v)
        except Exception:
            return None

    def no_false_ok(rid):
        r = run_rows.get(rid)
        if not r or r.get("status") != "ok":
            return True
        for k in ("final_pairs", "boundary_violations", "technology_margin_violation_count",
                  "technology_spacing_violation_count"):
            if (as_int(r.get(k)) or 0) > 0:
                errs.append(f"{rid}: status ok but {k}={r.get(k)}")
                return False
        return True

    b0 = run_rows.get("B0")
    dense_ok = bool(b0 and b0.get("status") == "ok" and as_int(b0.get("placed_count")) == 191
                    and as_int(b0.get("unplaced_count")) == 0 and as_int(b0.get("used_sheet_count")) == 1)
    if not dense_ok and "B0" in ran_mandatory:
        errs.append(f"B0 dense191 baseline: {b0.get('status') if b0 else None} placed={b0.get('placed_count') if b0 else None} (need ok 191/191, 1 sheet)")

    b1 = run_rows.get("B1")
    f2_ok = bool(b1 and b1.get("status") == "ok" and as_int(b1.get("placed_count")) == 276
                 and as_int(b1.get("unplaced_count")) == 0 and as_int(b1.get("used_sheet_count")) == 2)
    if not f2_ok and "B1" in ran_mandatory:
        errs.append(f"B1 full276 2-sheet baseline: {b1.get('status') if b1 else None} placed={b1.get('placed_count') if b1 else None} used={b1.get('used_sheet_count') if b1 else None} (need ok 276/276, 2 sheets)")

    b2 = run_rows.get("B2")
    f3_ok = bool(b2 and b2.get("status") == "ok" and as_int(b2.get("placed_count")) == 276
                 and as_int(b2.get("unplaced_count")) == 0 and as_int(b2.get("used_sheet_count")) == 2)
    if not f3_ok and "B2" in ran_mandatory:
        errs.append(f"B2 full276 3-sheet baseline: {b2.get('status') if b2 else None} placed={b2.get('placed_count') if b2 else None} used={b2.get('used_sheet_count') if b2 else None} (need ok 276/276, used 2)")

    # B3 mixed-stock: valid (no false ok); partial allowed.
    b3 = run_rows.get("B3")
    mixed_ok = True
    if "B3" in ran_mandatory:
        if not b3:
            mixed_ok = False
            errs.append("B3 mixed-stock: missing")
        else:
            mixed_ok = no_false_ok("B3") and (as_int(b3.get("final_pairs")) or 0) == 0 and (as_int(b3.get("boundary_violations")) or 0) == 0

    # Mandatory spacing runs: offset failure 0 + no false ok.
    spacing_runs = [r for r in ("S0", "S1", "S2", "S3", "S4", "S5") if r in ran_mandatory]
    spacing_valid = True
    for rid in spacing_runs:
        r = run_rows.get(rid)
        if not r:
            spacing_valid = False
            errs.append(f"{rid}: missing")
            continue
        if (as_int(r.get("technology_spacing_offset_failure_count")) or 0) != 0:
            spacing_valid = False
            errs.append(f"{rid}: offset_failure_count={r.get('technology_spacing_offset_failure_count')} (need 0)")
        if not no_false_ok(rid):
            spacing_valid = False

    no_false = all(no_false_ok(rid) for rid in ran_mandatory)
    hotpath_zero = all((as_int(run_rows.get(rid, {}).get("q31_prepare_base_shape_native_hotpath_calls")) or 0) == 0
                       for rid in ran_mandatory)
    if not hotpath_zero:
        errs.append("q31 prepare_base_shape_native hotpath calls != 0 in a mandatory run")

    renders_present = True
    for rid in ran_mandatory:
        r = run_rows.get(rid, {})
        if (r.get("render_svg_count") or 0) < (r.get("render_sheet_count") or 0) + 1:
            renders_present = False
            errs.append(f"{rid}: missing SVG renders")
        if (r.get("render_png_count") or 0) < (r.get("render_sheet_count") or 0) + 1:
            renders_present = False
            errs.append(f"{rid}: missing PNG renders")

    # Time-limit cap: this runner never caps mandatory; assert declared limits used.
    cap_applied = False
    for rid in ran_mandatory:
        s = scn_by_id(rid)
        if s and run_rows.get(rid, {}).get("time_limit_s") != s[6]:
            cap_applied = True
            errs.append(f"{rid}: time_limit cap mismatch")

    gates = {
        "dense191_baseline_ok": dense_ok if "B0" in ran_mandatory else None,
        "full276_2sheet_baseline_ok": f2_ok if "B1" in ran_mandatory else None,
        "full276_3sheet_baseline_ok": f3_ok if "B2" in ran_mandatory else None,
        "mixed_stock_baseline_valid": mixed_ok if "B3" in ran_mandatory else None,
        "mandatory_spacing_runs_valid": spacing_valid,
        "all_mandatory_renders_present": renders_present,
        "no_false_ok": no_false,
        "hotpath_calls_zero": hotpath_zero,
        "time_limit_cap_applied": cap_applied,
    }
    return gates, errs


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["mandatory", "extended"], default="mandatory")
    ap.add_argument("--only", choices=["dense191_baseline", "full276_baselines", "spacing_runs", "render_check"])
    args = ap.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 1
    for d in (INPUTS, OUTPUTS, TABLES, LOGS, RENDERS):
        d.mkdir(parents=True, exist_ok=True)

    def selected(scn):
        run_id, tier, dataset, *_ = scn
        if args.only == "dense191_baseline":
            return run_id == "B0"
        if args.only == "full276_baselines":
            return run_id in ("B1", "B2", "B3")
        if args.only == "spacing_runs":
            return run_id in ("S0", "S1", "S2", "S3", "S4", "S5")
        if args.only == "render_check":
            return False
        if args.tier == "mandatory":
            return tier == "mandatory"
        return True

    scns = [s for s in SCENARIOS if selected(s)]
    run_rows: dict[str, dict] = {}
    all_rows, per_sheet_rows, stage_rows, cde_rows, render_rows = [], [], [], [], []
    errors: list[str] = []
    ran = []

    for scn in scns:
        run_id = scn[0]
        print(f"\n--- {run_id} ({scn[1]}) {scn[2]} {scn[3]} margin={scn[4]} spacing={scn[5]} time_limit={scn[6]}s ---", flush=True)
        inp = build_input(scn)
        try:
            out = run_solver(scn, inp)
        except Exception as e:
            errors.append(f"{run_id}: {e}")
            print(f"  ERROR: {e}")
            continue
        rinfo = render_run(scn, out)
        rr = run_row(scn, inp, out, rinfo)
        run_rows[run_id] = rr
        ran.append(run_id)
        all_rows.append(rr)
        per_sheet_rows.extend(rinfo["per_sheet"])
        stage_rows.append(stage_row(scn, out))
        cde_rows.append(cde_row(scn, out))
        render_rows.append(rinfo["render_row"])
        print(f"  status={rr['status']} placed={rr['placed_count']}/{rr['total_instances']} "
              f"used={rr['used_sheet_count']} final_pairs={rr['final_pairs']} "
              f"offset_fail={rr['technology_spacing_offset_failure_count']} "
              f"spc_viol={rr['technology_spacing_violation_count']} wall={rr['wall_time_s']}s "
              f"render={rinfo['render_row']['render_status']}", flush=True)

    write_csv(TABLES / "q39_run_summary.csv", all_rows)
    write_csv(TABLES / "q39_per_sheet_summary.csv", per_sheet_rows)
    write_csv(TABLES / "q39_stage_timing.csv", stage_rows)
    write_csv(TABLES / "q39_cde_metrics.csv", cde_rows)
    write_csv(TABLES / "q39_render_summary.csv", render_rows)

    # Quality comparison vs baseline.
    qrows = []
    for scn in SCENARIOS:
        rid, _, _, _, _, _, _, base = scn
        if rid in run_rows and base and base in run_rows:
            r, b = run_rows[rid], run_rows[base]

            def dd(k):
                try:
                    return r.get(k) - b.get(k)
                except Exception:
                    return None
            qrows.append({"run_id": rid, "baseline": base,
                          "delta_placed": dd("placed_count"),
                          "delta_used_sheets": dd("used_sheet_count"),
                          "delta_offset_fail": dd("technology_spacing_offset_failure_count"),
                          "delta_spacing_viol": dd("technology_spacing_violation_count")})
    write_csv(TABLES / "q39_quality_comparison.csv", qrows)

    mandatory_ran = [r for r in ran if scn_by_id(r) and scn_by_id(r)[1] == "mandatory"]
    gates, gate_errs = evaluate_gates(run_rows, mandatory_ran)
    errors.extend(gate_errs)
    (TABLES / "q39_regression_gates.json").write_text(json.dumps(gates, indent=2))

    manifest = {
        "tier": args.tier, "only": args.only,
        "scenarios_run": ran, "mandatory_ran": mandatory_ran,
        "time_limit_cap_applied": False,
        "have_cairosvg": HAVE_CAIROSVG,
        "errors": errors,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_full276": str(BASE_FULL276.relative_to(ROOT)),
        "base_dense191": str(BASE_DENSE191.relative_to(ROOT)),
    }
    (TABLES / "q39_measurement_manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\n{'='*60}")
    print("  regression gates:", json.dumps(gates))
    # FAIL if any mandatory gate is explicitly false.
    fail = errors or any(v is False for k, v in gates.items() if k != "time_limit_cap_applied") or gates["time_limit_cap_applied"]
    if fail:
        for e in errors:
            print(f"   - {e}")
        print("  RESULT: FAIL")
        return 2
    print(f"  runs={len(ran)}  RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
