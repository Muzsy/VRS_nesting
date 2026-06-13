#!/usr/bin/env python3
"""SGH-Q41 — Full276 margin 5 / spacing 10 visual production benchmark under the Q40 unified model.

Exactly THREE production benchmark runs on the canonical full276 input, all at margin=5,
spacing=10, kerf=0, seed=42, time_limit=1200 s (NO cap). This is the special Q40 case where
`sheet_inset = margin − spacing/2 = 0`: the solver sheet is the unchanged physical sheet while
the parts carry the spacing as a 5 mm outward offset; output/render use ORIGINAL contours.

Scenarios (canonical full276 only — no dense191, no spacing=2, no Q39 B0–S5 matrix):
  Q41_A_2L    : 2 × 1500×3000
  Q41_B_3L    : 3 × 1500×3000
  Q41_C_MIXED : 1 × 1500×3000 + 2 × 1000×2000

Usage:
  python3 scripts/bench_sgh_q41_full276_m5_s10_visuals.py --tier mandatory
  python3 scripts/bench_sgh_q41_full276_m5_s10_visuals.py --only Q41_A_2L
  python3 scripts/bench_sgh_q41_full276_m5_s10_visuals.py --only Q41_B_3L
  python3 scripts/bench_sgh_q41_full276_m5_s10_visuals.py --only Q41_C_MIXED
  python3 scripts/bench_sgh_q41_full276_m5_s10_visuals.py --only render_check
"""
from __future__ import annotations

import argparse
import copy
import csv
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

Q41 = ROOT / "artifacts/benchmarks/sgh_q41"
INPUTS = Q41 / "inputs"
OUTPUTS = Q41 / "outputs"
TABLES = Q41 / "tables"
LOGS = Q41 / "logs"
RENDERS = Q41 / "renders"

# Q41 fixed technology values (every run).
MARGIN_MM = 5.0
SPACING_MM = 10.0
KERF_MM = 0.0
SEED = 42
TIME_LIMIT_S = 1200
EXPECTED_OFFSET_MM = SPACING_MM / 2.0          # 5.0
EXPECTED_SHEET_INSET_MM = MARGIN_MM - EXPECTED_OFFSET_MM  # 0.0
EXPECTED_INNER_SPACING_MM = 0.0
EXPECTED_OFFSET_PART_COUNT = 12
TOTAL_INSTANCES = 276
# Validator-disabled threshold: ~0 ms when disabled, 37–70 s (37000–70000 ms) when on.
SPACING_VALIDATOR_DISABLED_MAX_MS = 5000.0

try:
    import cairosvg  # noqa: F401
    HAVE_CAIROSVG = True
except Exception:
    HAVE_CAIROSVG = False


def sheets(spec: str) -> list[dict]:
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


# (run_id, scenario_label, sheet_spec, margin, spacing, time_limit)
SCENARIOS = [
    ("Q41_A_2L", "full276/2x1500x3000/m5/s10", "2x1500x3000", MARGIN_MM, SPACING_MM, TIME_LIMIT_S),
    ("Q41_B_3L", "full276/3x1500x3000/m5/s10", "3x1500x3000", MARGIN_MM, SPACING_MM, TIME_LIMIT_S),
    ("Q41_C_MIXED", "full276/mixed/m5/s10", "mixed", MARGIN_MM, SPACING_MM, TIME_LIMIT_S),
]
RUN_IDS = [s[0] for s in SCENARIOS]


def scn_by_id(run_id: str):
    for s in SCENARIOS:
        if s[0] == run_id:
            return s
    return None


# ── inputs (canonical full276 only — never hand-invented parts) ────────────────

def load_parts() -> list[dict]:
    return copy.deepcopy(json.loads(BASE_FULL276.read_text())["parts"])


def part_lookup() -> dict[str, dict]:
    return {p["id"]: p for p in load_parts()}


def stock_config_label(spec: str) -> str:
    return {"2x1500x3000": "2x1500x3000",
            "3x1500x3000": "3x1500x3000",
            "mixed": "1x1500x3000+2x1000x2000"}[spec]


def build_input(scn) -> Path:
    run_id, _label, sheet_spec, margin, spacing, tl = scn
    doc = {
        "contract_version": "v1",
        "project_name": f"sgh_q41_{run_id}",
        "seed": SEED,
        "time_limit_s": tl,  # FULL time limit, NO cap.
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": margin,
        "spacing_mm": spacing,
        "kerf_mm": KERF_MM,
        "stocks": sheets(sheet_spec),
        "parts": load_parts(),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"{run_id}_full276_{sheet_spec}_m{margin:g}_s{spacing:g}.json"
    path.write_text(json.dumps(doc, indent=2))
    return path


def expand_stock_sheets(stock_list: list[dict]) -> list[dict]:
    """Expanded per-sheet stock dims, matching the solver's expand_sheets order."""
    out = []
    for st in stock_list:
        for _ in range(int(st["quantity"])):
            out.append({"id": st["id"], "width": float(st["width"]), "height": float(st["height"])})
    return out


# ── solver ─────────────────────────────────────────────────────────────────────

def run_solver(scn, input_path: Path) -> dict[str, Any]:
    run_id = scn[0]
    tl = scn[5]
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{run_id}_output.json"
    # Guarantee the Q35 spacing validator stays DISABLED by default (never inherit an env flag).
    env = dict(os.environ)
    env.pop("SGH_Q35_SPACING_VALIDATOR", None)
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(input_path), "--output", str(out_path)],
        capture_output=True, text=True, timeout=tl + 1200, env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{run_id}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\ntime_limit_s={tl}\n"
        f"stderr:\n{proc.stderr[:2000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{run_id} solver exit {proc.returncode}: {proc.stderr[:400]}")
    out = json.loads(out_path.read_text())
    out["_wall_time_s"] = wall
    out["_time_limit_s"] = tl
    return out


# ── rendering (ORIGINAL canonical full276 contours, anchor transform) ──────────

_PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
            "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac", "#1f77b4", "#2ca02c"]


def _colour(part_id: str) -> str:
    return _PALETTE[(hash(part_id) & 0xFFFFFF) % len(_PALETTE)]


def _part_outer(part: dict) -> list[tuple[float, float]]:
    """ORIGINAL outer contour from the canonical part record (never the offset solver geometry)."""
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


def part_polygon_area(part: dict) -> float:
    pts = _part_outer(part) if part else []
    if len(pts) < 3:
        return 0.0
    n = len(pts)
    return abs(0.5 * sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                         for i in range(n)))


def render_sheet_svg(run_id, sheet_index, sw, sh, margin, placements, parts_by_id) -> str:
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{sw:.2f}mm" height="{sh:.2f}mm" viewBox="0 0 {sw:.4f} {sh:.4f}">',
        f'  <!-- Q41 {run_id} sheet {sheet_index} ORIGINAL contours (margin {margin:g}, spacing 10) -->',
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
        d = " ".join(f"{'M' if i == 0 else 'L'} {x:.3f} {sh - y:.3f}"
                     for i, (x, y) in enumerate(world)) + " Z"
        lines.append(f'  <path d="{d}" fill="{_colour(pl["part_id"])}" fill-opacity="0.7" '
                     f'stroke="#222" stroke-width="0.5"/>')
        n += 1
    lines.append(f'  <text x="6" y="20" font-size="34" fill="#000">'
                 f'{run_id} sheet {sheet_index}  placed={n}  margin={margin:g} spacing=10</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def render_overview_svg(run_id, used, sheet_dims, status, placed, total) -> str:
    if not used:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120">'
                f'<rect width="400" height="120" fill="#fff" stroke="#000"/>'
                f'<text x="10" y="60" font-size="16">{run_id}: no used sheets '
                f'(status {status}, {placed}/{total})</text></svg>')
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
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w:.0f}" height="{total_hh:.0f}" '
             f'viewBox="0 0 {total_w:.0f} {total_hh:.0f}">',
             f'<rect width="{total_w:.0f}" height="{total_hh:.0f}" fill="#f7f7f7"/>',
             f'<text x="10" y="28" font-size="22" fill="#000">{run_id}  status={status}  '
             f'placed={placed}/{total}  sheets={len(used)}</text>']
    for (bx, si, bw, bh) in boxes:
        lines.append(f'<rect x="{bx:.1f}" y="50" width="{bw:.1f}" height="{bh:.1f}" '
                     f'fill="#dfe7f0" stroke="#000" stroke-width="1.5"/>')
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
    run_id, _label, sheet_spec, margin, spacing, _tl = scn
    rdir = RENDERS / run_id
    rdir.mkdir(parents=True, exist_ok=True)
    parts_by_id = part_lookup()
    expanded = expand_stock_sheets(sheets(sheet_spec))
    sheet_dims = {i: (s["width"], s["height"]) for i, s in enumerate(expanded)}
    placements = out.get("placements", [])
    used = sorted({pl["sheet_index"] for pl in placements})
    t0 = time.monotonic()
    svg_t = png_t = 0.0
    svg_count = png_count = 0
    per_sheet = []
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
    ov_svg = render_overview_svg(run_id, used, sheet_dims, out.get("status"),
                                 out.get("metrics", {}).get("placed_count", 0),
                                 out.get("metrics", {}).get("placed_count", 0)
                                 + out.get("metrics", {}).get("unplaced_count", 0))
    ov_svg_path = rdir / "overview.svg"
    ov_svg_path.write_text(ov_svg); svg_count += 1
    ov_png_path = rdir / "overview.png"
    if svg_to_png(ov_svg_path, ov_png_path):
        png_count += 1
    render_total = time.monotonic() - t0
    missing_svg = sum(1 for i in range(len(used)) if not (rdir / f"sheet_{i:02d}.svg").exists())
    missing_png = sum(1 for i in range(len(used)) if not (rdir / f"sheet_{i:02d}.png").exists())
    if not ov_svg_path.exists():
        missing_svg += 1
    if not ov_png_path.exists():
        missing_png += 1
    manifest = {
        "run_id": run_id, "used_sheet_count": len(used), "used_sheet_indices": used,
        "svg_count": svg_count, "png_count": png_count,
        "render_total_ms": round(render_total * 1000, 3),
        "render_svg_total_ms": round(svg_t * 1000, 3), "render_png_total_ms": round(png_t * 1000, 3),
        "render_sheet_count": len(used),
        "render_source": "original_canonical_full276_contours",
        "have_cairosvg": HAVE_CAIROSVG,
    }
    (rdir / "render_manifest.json").write_text(json.dumps(manifest, indent=2))
    return {
        "per_sheet": per_sheet,
        "render_row": {
            "run_id": run_id, "used_sheet_count": len(used),
            "overview_svg_path": str(ov_svg_path.relative_to(ROOT)),
            "overview_png_path": str(ov_png_path.relative_to(ROOT)),
            "missing_svg_count": missing_svg, "missing_png_count": missing_png,
            "render_status": "ok" if (missing_svg == 0 and missing_png == 0
                                      and ov_png_path.exists()) else "incomplete",
        },
        "manifest": manifest,
    }


# ── tables ──────────────────────────────────────────────────────────────────────

def od(o):
    return o.get("optimizer_diagnostics") or {}


def _used_indices(d) -> list[int]:
    return list(d.get("sparrow_ms_used_sheet_indices") or [])


def run_row(scn, out, render_info) -> dict:
    run_id, label, sheet_spec, margin, spacing, tl = scn
    d = od(out); m = out.get("metrics", {}); rm = render_info["manifest"]
    placed = m.get("placed_count", 0) or 0
    unplaced = m.get("unplaced_count", 0) or 0
    total = placed + unplaced
    parts_by_id = part_lookup()
    expanded = expand_stock_sheets(sheets(sheet_spec))
    placements = out.get("placements", [])
    used = sorted({pl["sheet_index"] for pl in placements})
    # ORIGINAL placed area (the solver-internal sparrow_ms_placed_part_area is the OFFSET area).
    placed_part_area = sum(part_polygon_area(parts_by_id.get(pl["part_id"], {})) for pl in placements)
    physical_used = 0.0
    usable_used = 0.0
    for si in used:
        if si < len(expanded):
            w, h = expanded[si]["width"], expanded[si]["height"]
            physical_used += w * h
            usable_used += (w - 2 * margin) * (h - 2 * margin) if margin > 0 else w * h
    return {
        "run_id": run_id, "scenario": label, "dataset": "full276",
        "stock_config": stock_config_label(sheet_spec),
        "seed": SEED, "time_limit_s": tl,
        "wall_time_s": round(out.get("_wall_time_s", 0.0), 2),
        "solver_reported_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "status": out.get("status"),
        "placed_count": placed, "unplaced_count": unplaced, "total_instances": total,
        "used_sheet_count": d.get("sparrow_ms_used_sheet_count"),
        "available_sheet_count": d.get("sparrow_ms_available_sheet_count"),
        "used_sheet_indices": "|".join(map(str, _used_indices(d))),
        "physical_used_sheet_area": round(physical_used, 2),
        "usable_sheet_area": round(usable_used, 2),
        "placed_part_area": round(placed_part_area, 2),
        "physical_utilization_pct": round(100 * placed_part_area / physical_used, 4) if physical_used else 0.0,
        "usable_utilization_pct": round(100 * placed_part_area / usable_used, 4) if usable_used else 0.0,
        "final_pairs": d.get("sparrow_ms_final_pairs"),
        "boundary_violations": d.get("sparrow_ms_boundary_violations"),
        "margin_mm": d.get("technology_margin_mm"),
        "spacing_mm": d.get("technology_spacing_mm"),
        "kerf_mm": d.get("technology_kerf_mm"),
        "technology_spacing_offset_mm": d.get("technology_spacing_offset_mm"),
        "technology_solver_sheet_inset_mm": d.get("technology_solver_sheet_inset_mm"),
        "technology_inner_spacing_mm": d.get("technology_inner_spacing_mm"),
        "technology_unified_geometry_model_active": d.get("technology_unified_geometry_model_active"),
        "technology_margin_violation_count": d.get("technology_margin_violation_count"),
        "technology_spacing_violation_count": d.get("technology_spacing_violation_count"),
        "technology_spacing_safety_net_removed_count": d.get("technology_spacing_safety_net_removed_count"),
        "technology_spacing_offset_failure_count": d.get("technology_spacing_offset_failure_count"),
        "technology_spacing_offset_part_count": d.get("technology_spacing_offset_part_count"),
        "technology_spacing_offset_build_ms": d.get("technology_spacing_offset_build_ms"),
        "technology_spacing_offset_avg_ms_per_part": d.get("technology_spacing_offset_avg_ms_per_part"),
        "technology_spacing_offset_max_ms_per_part": d.get("technology_spacing_offset_max_ms_per_part"),
        "technology_spacing_final_validator_ms": d.get("technology_spacing_final_validator_ms"),
        "technology_margin_final_validator_ms": d.get("technology_margin_final_validator_ms"),
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
        "cde_pair_queries": b.get("cde_pair_queries"),
        "cde_boundary_queries": b.get("cde_boundary_queries"),
        "cde_total_queries": b.get("cde_total_queries"),
        "cde_engine_builds": b.get("cde_engine_builds"),
        "cde_collision_results": b.get("cde_collision_results"),
        "cde_no_collision_results": b.get("cde_no_collision_results"),
        "cde_cache_pair_hits": b.get("cde_cache_pair_hits"),
        "cde_cache_pair_misses": b.get("cde_cache_pair_misses"),
        "cde_broadphase_pruned": b.get("cde_broadphase_pruned"),
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


# ── strict gates ────────────────────────────────────────────────────────────────

def _as_int(v):
    try:
        return int(v)
    except Exception:
        return None


def _as_float(v):
    try:
        return float(v)
    except Exception:
        return None


def _approx(v, target, tol=1e-6):
    f = _as_float(v)
    return f is not None and abs(f - target) <= tol


def no_false_ok(r, errs) -> bool:
    if not r or r.get("status") != "ok":
        return True
    bad = []
    for k in ("final_pairs", "boundary_violations",
              "technology_margin_violation_count", "technology_spacing_violation_count"):
        if (_as_int(r.get(k)) or 0) > 0:
            bad.append(f"{k}={r.get(k)}")
    if bad:
        errs.append(f"{r.get('run_id')}: status ok but {bad}")
        return False
    if (_as_int(r.get("placed_count")) or 0) != TOTAL_INSTANCES or (_as_int(r.get("unplaced_count")) or 0) != 0:
        errs.append(f"{r.get('run_id')}: status ok but placed={r.get('placed_count')}/{r.get('unplaced_count')}")
        return False
    return True


def evaluate_gates(run_rows: dict[str, dict], ran: list[str]) -> tuple[dict, list[str]]:
    errs: list[str] = []
    present = [run_rows[r] for r in ran if r in run_rows]

    all_three = len(ran) == 3 and all(r in run_rows for r in RUN_IDS)
    if not all_three:
        errs.append(f"expected exactly 3 full276 runs, ran={ran}")

    all_full276 = all(r.get("dataset") == "full276" and (_as_int(r.get("total_instances")) or 0) == TOTAL_INSTANCES
                      for r in present)
    if not all_full276:
        errs.append("not every run is canonical full276 / 276 instances")

    all_m5_s10 = all(_approx(r.get("margin_mm"), MARGIN_MM) and _approx(r.get("spacing_mm"), SPACING_MM)
                     and _approx(r.get("kerf_mm"), KERF_MM) for r in present)
    if not all_m5_s10:
        errs.append("not every run is margin=5 / spacing=10 / kerf=0")

    all_full_tl = all((_as_int(r.get("time_limit_s")) or 0) == TIME_LIMIT_S for r in present)
    if not all_full_tl:
        errs.append("not every run used the full 1200 s time limit")

    unified = all(r.get("technology_unified_geometry_model_active") is True for r in present)
    if not unified:
        errs.append("Q40 unified model not active in every run")

    inset_zero = all(_approx(r.get("technology_solver_sheet_inset_mm"), EXPECTED_SHEET_INSET_MM)
                     for r in present)
    if not inset_zero:
        errs.append("solver_sheet_inset_mm != 0 in some run")

    inner_zero = all(_approx(r.get("technology_inner_spacing_mm"), EXPECTED_INNER_SPACING_MM)
                     for r in present)
    if not inner_zero:
        errs.append("inner_spacing_mm != 0 in some run")

    offset5 = all(_approx(r.get("technology_spacing_offset_mm"), EXPECTED_OFFSET_MM) for r in present)
    if not offset5:
        errs.append("spacing_offset_mm != 5 in some run")

    offset_fail0 = all((_as_int(r.get("technology_spacing_offset_failure_count")) or 0) == 0
                       for r in present)
    if not offset_fail0:
        errs.append("spacing_offset_failure_count != 0 in some run")

    nf_ok = all(no_false_ok(r, errs) for r in present)

    no_collisions = all((_as_int(r.get("final_pairs")) or 0) == 0 for r in present)
    if not no_collisions:
        errs.append("final_pairs != 0 in some run")

    no_boundary = all((_as_int(r.get("boundary_violations")) or 0) == 0 for r in present)
    if not no_boundary:
        errs.append("boundary_violations != 0 in some run")

    no_margin = all((_as_int(r.get("technology_margin_violation_count")) or 0) == 0 for r in present)
    if not no_margin:
        errs.append("technology_margin_violation_count != 0 in some run")

    hotpath0 = all((_as_int(r.get("q31_prepare_base_shape_native_hotpath_calls")) or 0) == 0
                   for r in present)
    if not hotpath0:
        errs.append("q31 prepare_base_shape_native hotpath calls != 0 in some run")

    validator_off = all((_as_float(r.get("technology_spacing_final_validator_ms")) or 0.0)
                        < SPACING_VALIDATOR_DISABLED_MAX_MS for r in present)
    if not validator_off:
        errs.append("Q35 spacing validator appears enabled (final_validator_ms too high)")

    renders_present = True
    for r in present:
        need = (_as_int(r.get("render_sheet_count")) or 0) + 1  # + overview
        if (_as_int(r.get("render_svg_count")) or 0) < need:
            renders_present = False
            errs.append(f"{r.get('run_id')}: missing SVG renders")
        if (_as_int(r.get("render_png_count")) or 0) < need:
            renders_present = False
            errs.append(f"{r.get('run_id')}: missing PNG renders")

    # The renderer always draws ORIGINAL canonical contours (see render_manifest.render_source).
    render_original = True
    for rid in ran:
        mf = RENDERS / rid / "render_manifest.json"
        if not mf.exists() or json.loads(mf.read_text()).get("render_source") != "original_canonical_full276_contours":
            render_original = False
            errs.append(f"{rid}: render_manifest does not certify original contours")

    gates = {
        "all_three_runs_completed": all_three,
        "all_inputs_full276": all_full276,
        "all_runs_margin_5_spacing_10": all_m5_s10,
        "all_runs_full_time_limit": all_full_tl,
        "q40_unified_model_active": unified,
        "solver_sheet_inset_zero": inset_zero,
        "inner_spacing_zero": inner_zero,
        "offset_mm_is_5": offset5,
        "offset_failure_zero": offset_fail0,
        "no_false_ok": nf_ok,
        "no_final_collisions": no_collisions,
        "no_boundary_violations": no_boundary,
        "no_margin_violations": no_margin,
        "hotpath_calls_zero": hotpath0,
        "spacing_validator_disabled_by_default": validator_off,
        "all_renders_present": renders_present,
        "render_original_contours": render_original,
    }
    return gates, errs


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["mandatory"], default="mandatory")
    ap.add_argument("--only", choices=RUN_IDS + ["render_check"])
    args = ap.parse_args()
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 1
    for d in (INPUTS, OUTPUTS, TABLES, LOGS, RENDERS):
        d.mkdir(parents=True, exist_ok=True)

    # render_check: re-render the 3 runs from existing outputs (no solver), validate renders.
    if args.only == "render_check":
        render_rows = []
        per_sheet_rows = []
        missing = []
        for scn in SCENARIOS:
            run_id = scn[0]
            out_path = OUTPUTS / f"{run_id}_output.json"
            if not out_path.exists():
                missing.append(run_id)
                continue
            out = json.loads(out_path.read_text())
            rinfo = render_run(scn, out)
            render_rows.append(rinfo["render_row"])
            per_sheet_rows.extend(rinfo["per_sheet"])
            print(f"  {run_id}: render={rinfo['render_row']['render_status']}")
        write_csv(TABLES / "q41_render_summary.csv", render_rows)
        write_csv(TABLES / "q41_per_sheet_summary.csv", per_sheet_rows)
        if missing:
            print(f"  render_check: missing outputs for {missing} (run the benchmark first)")
            return 2
        bad = [r for r in render_rows if r["render_status"] != "ok"]
        print("  RESULT:", "FAIL" if bad else "PASS")
        return 2 if bad else 0

    scns = [s for s in SCENARIOS if (args.only is None or s[0] == args.only)]
    run_rows: dict[str, dict] = {}
    all_rows, per_sheet_rows, stage_rows, cde_rows, render_rows = [], [], [], [], []
    errors: list[str] = []
    ran = []

    for scn in scns:
        run_id = scn[0]
        print(f"\n--- {run_id} {scn[1]} time_limit={scn[5]}s (margin={scn[3]} spacing={scn[4]}) ---",
              flush=True)
        inp = build_input(scn)
        try:
            out = run_solver(scn, inp)
        except Exception as e:
            errors.append(f"{run_id}: {e}")
            print(f"  ERROR: {e}")
            continue
        rinfo = render_run(scn, out)
        rr = run_row(scn, out, rinfo)
        run_rows[run_id] = rr
        ran.append(run_id)
        all_rows.append(rr)
        per_sheet_rows.extend(rinfo["per_sheet"])
        stage_rows.append(stage_row(scn, out))
        cde_rows.append(cde_row(scn, out))
        render_rows.append(rinfo["render_row"])
        print(f"  status={rr['status']} placed={rr['placed_count']}/{rr['total_instances']} "
              f"used={rr['used_sheet_count']} final_pairs={rr['final_pairs']} "
              f"boundary={rr['boundary_violations']} margin_viol={rr['technology_margin_violation_count']} "
              f"offset_mm={rr['technology_spacing_offset_mm']} inset={rr['technology_solver_sheet_inset_mm']} "
              f"offset_fail={rr['technology_spacing_offset_failure_count']} "
              f"spc_val_ms={rr['technology_spacing_final_validator_ms']} wall={rr['wall_time_s']}s "
              f"render={rinfo['render_row']['render_status']}", flush=True)

    write_csv(TABLES / "q41_run_summary.csv", all_rows)
    write_csv(TABLES / "q41_per_sheet_summary.csv", per_sheet_rows)
    write_csv(TABLES / "q41_stage_timing.csv", stage_rows)
    write_csv(TABLES / "q41_cde_metrics.csv", cde_rows)
    write_csv(TABLES / "q41_render_summary.csv", render_rows)

    gates, gate_errs = evaluate_gates(run_rows, ran)
    errors.extend(gate_errs)
    (TABLES / "q41_regression_gates.json").write_text(json.dumps(gates, indent=2))

    manifest = {
        "tier": args.tier, "only": args.only,
        "scenarios_run": ran,
        "dataset": "full276",
        "margin_mm": MARGIN_MM, "spacing_mm": SPACING_MM, "kerf_mm": KERF_MM,
        "seed": SEED, "time_limit_s": TIME_LIMIT_S,
        "time_limit_cap_applied": False,
        "spacing_validator_env_forced_off": True,
        "have_cairosvg": HAVE_CAIROSVG,
        "errors": errors,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_full276": str(BASE_FULL276.relative_to(ROOT)),
    }
    (TABLES / "q41_measurement_manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\n{'=' * 60}")
    print("  regression gates:", json.dumps(gates))
    full_run = args.only is None
    # On a full mandatory run every gate must be True. On a single --only run, only
    # gates derivable from the ran subset are asserted (the 3-run gates are expected False).
    if full_run:
        fail = bool(errors) or any(v is not True for v in gates.values())
    else:
        fail = bool(errors)
    if fail:
        for e in errors:
            print(f"   - {e}")
        print("  RESULT: FAIL")
        return 2
    print(f"  runs={len(ran)}  RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
