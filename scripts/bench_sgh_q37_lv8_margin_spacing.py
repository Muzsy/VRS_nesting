#!/usr/bin/env python3
"""SGH-Q37 — Real LV8 margin+spacing benchmark and measurement hardening.

Derives benchmark inputs from the committed canonical LV8 solver inputs:
  - full276 parts: artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json
  - dense191 parts: artifacts/benchmarks/sgh_q31/inputs/dense191.json
(both built from samples/real_work_dxf/0014-01H/lv8jav_normalized; filename quantities
sum to 276 across 12 unique parts). Q37 does NOT hand-invent parts.

Every generated input sets spacing_mm EXPLICITLY (0.0 or 2.0/5.0) so the spacing-default
(= margin) never silently biases the comparison. kerf_mm is always 0.0 and never folded
into spacing.

Usage:
  python3 scripts/bench_sgh_q37_lv8_margin_spacing.py --tier mandatory
  python3 scripts/bench_sgh_q37_lv8_margin_spacing.py --tier extended
  python3 scripts/bench_sgh_q37_lv8_margin_spacing.py --only geometry_inventory|dense191|full276
  python3 scripts/bench_sgh_q37_lv8_margin_spacing.py --tier mandatory --max-time-limit-s 60

`--max-time-limit-s` caps every scenario's solver time limit for a feasible measurement
session; the canonical limits (600/1200) are the defaults written into each input.
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

Q37 = ROOT / "artifacts/benchmarks/sgh_q37"
INPUTS = Q37 / "inputs"
OUTPUTS = Q37 / "outputs"
TABLES = Q37 / "tables"
LOGS = Q37 / "logs"

SHEET_1500 = {"id": "LV8_SHEET", "quantity": 1, "width": 1500.0, "height": 3000.0}


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


# scenario: (run_id, tier, pkg, sheet_spec, margin, spacing, time_limit, baseline_run)
SCENARIOS = [
    ("D0", "mandatory", "dense191", "1x1500x3000", 0.0, 0.0, 600, None),
    ("D1", "mandatory", "dense191", "1x1500x3000", 0.0, 2.0, 600, "D0"),
    ("D2", "mandatory", "dense191", "1x1500x3000", 5.0, 2.0, 600, "D0"),
    ("M0", "mandatory", "full276", "2x1500x3000", 0.0, 0.0, 1200, None),
    ("M1", "mandatory", "full276", "2x1500x3000", 0.0, 2.0, 1200, "M0"),
    ("M2", "mandatory", "full276", "2x1500x3000", 5.0, 2.0, 1200, "M0"),
    ("E1", "extended", "full276", "2x1500x3000", 0.0, 5.0, 1200, "M0"),
    ("E2", "extended", "full276", "2x1500x3000", 5.0, 5.0, 1200, "M0"),
    ("E3", "extended", "full276", "3x1500x3000", 0.0, 2.0, 1200, "E3B"),
    ("E4", "extended", "full276", "3x1500x3000", 5.0, 2.0, 1200, "E3B"),
    ("E5", "extended", "full276", "mixed", 0.0, 2.0, 1200, "E5B"),
    ("E6", "extended", "full276", "mixed", 5.0, 2.0, 1200, "E6B"),
    # Extended baselines (spacing 0, margin 0) for ratio computation.
    ("E3B", "extended", "full276", "3x1500x3000", 0.0, 0.0, 1200, None),
    ("E5B", "extended", "full276", "mixed", 0.0, 0.0, 1200, None),
    ("E6B", "extended", "full276", "mixed", 0.0, 0.0, 1200, None),
]


# ── inputs ────────────────────────────────────────────────────────────────────

def load_parts(pkg: str) -> list[dict]:
    base = BASE_DENSE191 if pkg == "dense191" else BASE_FULL276
    return copy.deepcopy(json.loads(base.read_text())["parts"])


def build_input(run_id: str, pkg: str, sheet_spec: str, margin: float, spacing: float,
                time_limit: int) -> Path:
    parts = load_parts(pkg)
    doc = {
        "contract_version": "v1",
        "project_name": f"sgh_q37_{run_id}_{pkg}",
        "seed": 42,
        "time_limit_s": time_limit,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": margin,
        "spacing_mm": spacing,   # ALWAYS explicit
        "kerf_mm": 0.0,          # never folded into spacing
        "stocks": sheets(sheet_spec),
        "parts": parts,
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"{run_id}_{pkg}_{sheet_spec}_m{margin:g}_s{spacing:g}.json"
    path.write_text(json.dumps(doc, indent=2))
    return path


# ── solver run ─────────────────────────────────────────────────────────────────

def run_solver(run_id: str, input_path: Path, max_time_limit_s: int | None) -> dict[str, Any]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{run_id}_output.json"
    doc = json.loads(input_path.read_text())
    if max_time_limit_s is not None and doc["time_limit_s"] > max_time_limit_s:
        doc["time_limit_s"] = max_time_limit_s
        input_path.write_text(json.dumps(doc, indent=2))
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(input_path), "--output", str(out_path)],
        capture_output=True, text=True, timeout=doc["time_limit_s"] + 600,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{run_id}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\nstderr:\n{proc.stderr[:2000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{run_id} solver exit {proc.returncode}: {proc.stderr[:400]}")
    out = json.loads(out_path.read_text())
    out["_wall_time_s"] = wall
    out["_requested_time_limit_s"] = doc["time_limit_s"]
    return out


# ── Python miter offset (independent geometry-inventory audit; mirrors Rust) ────

EPS = 1e-9


def signed_area(pts: list[tuple[float, float]]) -> float:
    n = len(pts)
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))


def poly_area(pts):
    return abs(signed_area(pts))


def bbox_area(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _line_intersect(p0, d0, p1, d1):
    den = d0[0] * d1[1] - d0[1] * d1[0]
    if abs(den) <= 1e-12:
        return None
    t = ((p1[0] - p0[0]) * d1[1] - (p1[1] - p0[1]) * d1[0]) / den
    return (p0[0] + t * d0[0], p0[1] + t * d0[1])


def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _proper_intersect(a0, a1, b0, b1):
    d1 = _orient(b0, b1, a0); d2 = _orient(b0, b1, a1)
    d3 = _orient(a0, a1, b0); d4 = _orient(a0, a1, b1)
    return ((d1 > EPS and d2 < -EPS) or (d1 < -EPS and d2 > EPS)) and \
           ((d3 > EPS and d4 < -EPS) or (d3 < -EPS and d4 > EPS))


def _self_intersecting(pts):
    n = len(pts)
    if n < 4:
        return False
    for i in range(n):
        a0, a1 = pts[i], pts[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or (i + 1) % n == j:
                continue
            if _proper_intersect(a0, a1, pts[j], pts[(j + 1) % n]):
                return True
    return False


def offset_polygon(pts: list[tuple[float, float]], half: float):
    """Mirror of Rust build_spacing_expanded_outer_polygon. Returns (status, out_pts)."""
    if half <= 0:
        return "ok", list(pts)
    # dedup
    clean = []
    for p in pts:
        if not clean or abs(clean[-1][0] - p[0]) > EPS or abs(clean[-1][1] - p[1]) > EPS:
            clean.append(p)
    if len(clean) >= 2 and abs(clean[0][0] - clean[-1][0]) <= EPS and abs(clean[0][1] - clean[-1][1]) <= EPS:
        clean.pop()
    if len(clean) < 3 or poly_area(clean) <= EPS:
        return "INVALID_SPACING_OFFSET_POLYGON_Q36", None
    sa = signed_area(clean)
    ccw = clean if sa > 0 else list(reversed(clean))
    n = len(ccw)
    lines = []
    for i in range(n):
        a, b = ccw[i], ccw[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ey)
        if ln <= EPS:
            return "INVALID_SPACING_OFFSET_POLYGON_Q36", None
        nx, ny = ey / ln, -ex / ln
        lines.append(((a[0] + half * nx, a[1] + half * ny), (ex, ey)))
    out = []
    for i in range(n):
        p0, d0 = lines[(i + n - 1) % n]
        p1, d1 = lines[i]
        v = _line_intersect(p0, d0, p1, d1)
        if v is None:
            a = ccw[i]
            ex, ey = d1
            ln = math.hypot(ex, ey)
            v = (a[0] + half * ey / ln, a[1] - half * ex / ln)
        out.append(v)
    if any(not (math.isfinite(x) and math.isfinite(y)) for x, y in out):
        return "UNSUPPORTED_SPACING_OFFSET_Q36", None
    if poly_area(out) + EPS < abs(sa):
        return "SELF_INTERSECTING_SPACING_OFFSET_Q36", None
    if _self_intersecting(out):
        return "SELF_INTERSECTING_SPACING_OFFSET_Q36", None
    return "ok", out


def part_polygon(part: dict) -> list[tuple[float, float]] | None:
    raw = part.get("prepared_outer_points") or part.get("outer_points")
    if not raw:
        return None
    pts = []
    for pr in raw:
        if isinstance(pr, (list, tuple)) and len(pr) >= 2:
            pts.append((float(pr[0]), float(pr[1])))
    return pts if len(pts) >= 3 else None


# ── geometry inventory ─────────────────────────────────────────────────────────

def run_geometry_inventory() -> list[dict]:
    parts = load_parts("full276")
    rows = []
    for p in parts:
        poly = part_polygon(p)
        row = {
            "part_id": p["id"],
            "source_dxf": p.get("source_dxf", ""),
            "declared_quantity": p["quantity"],
            "width": p.get("width"),
            "height": p.get("height"),
            "outer_vertex_count": len(poly) if poly else 0,
            "has_outer_points": bool(p.get("outer_points")),
            "has_prepared_outer_points": bool(p.get("prepared_outer_points")),
            "polygon_area": round(poly_area(poly), 4) if poly else 0.0,
            "bbox_area": round(bbox_area(poly), 4) if poly else 0.0,
            "area_to_bbox_ratio": round(poly_area(poly) / bbox_area(poly), 6) if poly and bbox_area(poly) > 0 else 0.0,
            "offset_error_reason": "",
        }
        for spacing in (2.0, 5.0, 10.0):
            half = spacing / 2.0
            tag = f"spacing_{int(spacing)}"
            if poly is None:
                row[f"{tag}_offset_status"] = "NO_POLYGON"
                row[f"{tag}_offset_vertex_count"] = 0
                row[f"{tag}_offset_area"] = 0.0
                row[f"{tag}_offset_bbox_area"] = 0.0
                row[f"{tag}_offset_area_ratio"] = 0.0
                continue
            status, out = offset_polygon(poly, half)
            row[f"{tag}_offset_status"] = status
            if out:
                row[f"{tag}_offset_vertex_count"] = len(out)
                row[f"{tag}_offset_area"] = round(poly_area(out), 4)
                row[f"{tag}_offset_bbox_area"] = round(bbox_area(out), 4)
                row[f"{tag}_offset_area_ratio"] = round(poly_area(out) / poly_area(poly), 6) if poly_area(poly) > 0 else 0.0
            else:
                row[f"{tag}_offset_vertex_count"] = 0
                row[f"{tag}_offset_area"] = 0.0
                row[f"{tag}_offset_bbox_area"] = 0.0
                row[f"{tag}_offset_area_ratio"] = 0.0
                if status != "ok":
                    row["offset_error_reason"] = status
        rows.append(row)
    return rows


# ── metric extraction ────────────────────────────────────────────────────────

def od(o: dict) -> dict:
    return o.get("optimizer_diagnostics") or {}


def run_row(run_id: str, scn, input_path: Path, out: dict) -> dict:
    _, tier, pkg, sheet_spec, margin, spacing, tl, _baseline = scn
    d = od(out)
    m = out.get("metrics", {})
    total = m.get("placed_count", 0) + m.get("unplaced_count", 0)
    return {
        "run_id": run_id, "tier": tier, "scenario": f"{pkg}/{sheet_spec}/m{margin:g}/s{spacing:g}",
        "input_path": str(input_path.relative_to(ROOT)),
        "output_path": str((OUTPUTS / f"{run_id}_output.json").relative_to(ROOT)),
        "seed": out.get("metrics", {}).get("seed", 42),
        "time_limit_s": out.get("_requested_time_limit_s"),
        "wall_time_s": round(out.get("_wall_time_s", 0.0), 3),
        "solver_reported_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "status": out.get("status"),
        "unsupported_reason": out.get("unsupported_reason", ""),
        "placed_count": m.get("placed_count"),
        "unplaced_count": m.get("unplaced_count"),
        "total_instances": total,
        "used_sheet_count": d.get("sparrow_ms_used_sheet_count"),
        "available_sheet_count": d.get("sparrow_ms_available_sheet_count"),
        "physical_used_sheet_area": d.get("sparrow_ms_used_sheet_area"),
        "usable_sheet_area": d.get("technology_margin_usable_sheet_area"),
        "placed_part_area": d.get("sparrow_ms_placed_part_area"),
        "physical_utilization_pct": d.get("sparrow_ms_utilization_pct"),
        "final_pairs": d.get("sparrow_ms_final_pairs"),
        "boundary_violations": d.get("sparrow_ms_boundary_violations"),
        "margin_mm": d.get("technology_margin_mm"),
        "spacing_mm": d.get("technology_part_spacing_mm"),
        "kerf_mm": d.get("technology_kerf_mm"),
        "technology_spacing_offset_mm": d.get("technology_spacing_offset_mm"),
        "technology_margin_violation_count": d.get("technology_margin_violation_count"),
        "technology_spacing_violation_count": d.get("technology_spacing_violation_count"),
        "technology_spacing_safety_net_removed_count": d.get("technology_spacing_safety_net_removed_count"),
        "technology_spacing_offset_failure_count": d.get("technology_spacing_offset_failure_count"),
        "spacing_geometry_applied": d.get("technology_spacing_geometry_applied"),
        "spacing_offset_part_count": d.get("technology_spacing_offset_part_count"),
        "spacing_offset_cache_hits": d.get("technology_spacing_offset_cache_hits"),
        "spacing_offset_cache_misses": d.get("technology_spacing_offset_cache_misses"),
        "boundary_uses_original": d.get("technology_spacing_boundary_uses_original_geometry"),
        "output_uses_original": d.get("technology_spacing_output_uses_original_geometry"),
        "q31_prepare_base_shape_native_hotpath_calls": d.get("sparrow_q31_prepare_base_shape_native_hotpath_calls"),
        "best_full_solution_found": d.get("sparrow_ms_best_full_solution_found"),
        "stock_exhausted": d.get("sparrow_ms_stock_exhausted"),
        "deadline_hit": d.get("sparrow_ms_deadline_hit"),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ── tables ─────────────────────────────────────────────────────────────────────

def stage_timing_row(run_id, out):
    d = od(out)
    return {
        "run_id": run_id,
        "wall_time_s": round(out.get("_wall_time_s", 0.0), 3),
        "sparrow_ms_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "spacing_offset_build_ms": d.get("technology_spacing_offset_build_ms"),
        "spacing_offset_avg_ms_per_part": d.get("technology_spacing_offset_avg_ms_per_part"),
        "spacing_offset_max_ms_per_part": d.get("technology_spacing_offset_max_ms_per_part"),
        "margin_final_validator_ms": d.get("technology_margin_final_validator_ms"),
        "spacing_final_validator_ms": d.get("technology_spacing_final_validator_ms"),
        "safety_net_ms": d.get("technology_safety_net_ms"),
        "q31_base_shape_cache_build_ms": d.get("sparrow_q31_base_shape_cache_build_ms"),
        "sparrow_iterations": d.get("sparrow_iterations"),
        "sparrow_worker_passes": d.get("sparrow_worker_passes"),
        "sparrow_ms_attempts": d.get("sparrow_ms_attempts"),
        "sparrow_ms_candidate_subsets": d.get("sparrow_ms_candidate_subsets"),
        "search_position_calls": d.get("sparrow_search_position_calls"),
        "search_position_samples": d.get("sparrow_search_position_samples"),
    }


def cde_row(run_id, out):
    d = od(out)
    b = out.get("collision_backend_diagnostics") or {}
    return {
        "run_id": run_id,
        "cde_pair_queries": b.get("cde_pair_queries"),
        "cde_boundary_queries": b.get("cde_boundary_queries"),
        "cde_total_queries": b.get("cde_total_queries"),
        "cde_engine_builds": b.get("cde_engine_builds"),
        "cde_collision_results": b.get("cde_collision_results"),
        "cde_no_collision_results": b.get("cde_no_collision_results"),
        "cde_unsupported_results": b.get("cde_unsupported_results"),
        "cde_broadphase_pruned": b.get("cde_broadphase_pruned"),
        "cde_batch_candidate_queries": b.get("cde_batch_candidate_queries"),
        "cde_batch_engine_builds": b.get("cde_batch_engine_builds"),
        "cde_batch_hazards_registered": b.get("cde_batch_hazards_registered"),
        "cde_batch_collisions_returned": b.get("cde_batch_collisions_returned"),
        "cde_pairwise_fallback_queries": b.get("cde_pairwise_fallback_queries"),
        "cde_candidate_session_builds": b.get("cde_candidate_session_builds"),
        "cde_candidate_session_reuses": b.get("cde_candidate_session_reuses"),
    }


REASON_STAGES = {
    "UNSUPPORTED_SPACING_OFFSET_Q36": "spacing_offset",
    "PART_SPACING_VIOLATION_Q35": "spacing_validator",
    "SHEET_MARGIN_VIOLATION_Q34R1": "margin_validator",
    "PART_NEVER_FITS_STOCK": "input_preflight",
    "PART_GEOMETRY_UNSUPPORTED": "input_preflight",
    "STOCK_EXHAUSTED_PARTIAL": "stock_capacity",
    "INSUFFICIENT_STOCK_CAPACITY": "stock_capacity",
    "UNRESOLVED_AFTER_STOCK_EXHAUSTED": "solver_partial",
}


def failure_rows(run_id, out):
    rows = []
    for u in out.get("unplaced", []):
        reason = u.get("reason", "")
        rows.append({
            "run_id": run_id,
            "instance_id": u.get("instance_id"),
            "part_id": u.get("part_id"),
            "reason": reason,
            "source_stage": REASON_STAGES.get(reason, "solver_partial"),
        })
    return rows


def quality_rows(run_rows: dict[str, dict]) -> list[dict]:
    rows = []
    for scn in SCENARIOS:
        run_id, _, _, _, _, _, _, baseline = scn
        if run_id not in run_rows or baseline is None or baseline not in run_rows:
            continue
        r = run_rows[run_id]
        b = run_rows[baseline]

        def delta(k):
            rv, bv = r.get(k), b.get(k)
            return (rv - bv) if isinstance(rv, (int, float)) and isinstance(bv, (int, float)) else None

        def ratio(k):
            rv, bv = r.get(k), b.get(k)
            if isinstance(rv, (int, float)) and isinstance(bv, (int, float)) and bv:
                return round(rv / bv, 4)
            return None

        rows.append({
            "run_id": run_id, "baseline": baseline,
            "delta_placed_count_vs_baseline": delta("placed_count"),
            "delta_used_sheet_count_vs_baseline": delta("used_sheet_count"),
            "delta_physical_utilization_pct_vs_baseline": delta("physical_utilization_pct"),
            "runtime_ratio_vs_baseline": ratio("wall_time_s"),
            "offset_failure_delta_vs_baseline": delta("technology_spacing_offset_failure_count"),
            "spacing_violation_delta_vs_baseline": delta("technology_spacing_violation_count"),
        })
    return rows


# ── false-ok / measurement gate ────────────────────────────────────────────────

def check_run_integrity(run_id, out, errors: list[str]) -> None:
    d = od(out)
    status = out.get("status")
    viol = [
        ("final_pairs", d.get("sparrow_ms_final_pairs")),
        ("boundary_violations", d.get("sparrow_ms_boundary_violations")),
        ("technology_margin_violation_count", d.get("technology_margin_violation_count")),
        ("technology_spacing_violation_count", d.get("technology_spacing_violation_count")),
    ]
    if status == "ok":
        for name, v in viol:
            if v not in (0, None) and v > 0:
                errors.append(f"{run_id}: status==ok but {name}={v}")
    # spacing_mm explicit passthrough + offset = spacing/2 + kerf separate.
    sp = d.get("technology_part_spacing_mm")
    off = d.get("technology_spacing_offset_mm")
    if sp is not None and off is not None and abs(off - sp / 2.0) > 1e-9:
        errors.append(f"{run_id}: technology_spacing_offset_mm {off} != spacing_mm/2 {sp/2.0}")
    kerf = d.get("technology_kerf_mm")
    if kerf not in (0.0, None) and sp is not None and abs((off or 0) - sp / 2.0) > 1e-9:
        errors.append(f"{run_id}: kerf appears folded into spacing")
    hot = d.get("sparrow_q31_prepare_base_shape_native_hotpath_calls")
    if hot not in (0, None) and hot > 0:
        errors.append(f"{run_id}: prepare_base_shape_native_hotpath_calls={hot} (must be 0)")
    for f in ("technology_spacing_geometry_applied", "technology_spacing_offset_mm",
              "technology_spacing_boundary_uses_original_geometry",
              "technology_spacing_output_uses_original_geometry"):
        if f not in d:
            errors.append(f"{run_id}: missing Q36 spacing diagnostic {f}")


# ── main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["mandatory", "extended"], default="mandatory")
    ap.add_argument("--only", choices=["geometry_inventory", "dense191", "full276"])
    ap.add_argument("--max-time-limit-s", type=int, default=None,
                    help="cap each scenario's solver time limit for a feasible session")
    args = ap.parse_args()

    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 1

    for d in (INPUTS, OUTPUTS, TABLES, LOGS):
        d.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []

    # Geometry inventory (always; cheap).
    print("=== Q37 geometry inventory ===")
    inv = run_geometry_inventory()
    write_csv(TABLES / "q37_spacing_geometry_inventory.csv", inv)
    offsettable = {2: 0, 5: 0, 10: 0}
    for r in inv:
        for s in (2, 5, 10):
            if r[f"spacing_{s}_offset_status"] == "ok":
                offsettable[s] += 1
    print(f"  parts={len(inv)} offsettable@2={offsettable[2]} @5={offsettable[5]} @10={offsettable[10]}")

    if args.only == "geometry_inventory":
        print("geometry_inventory only — done")
        return 0

    # Pick scenarios.
    def selected(scn):
        run_id, tier, pkg, *_ = scn
        if args.only == "dense191" and pkg != "dense191":
            return False
        if args.only == "full276" and pkg != "full276":
            return False
        if args.tier == "mandatory":
            return tier == "mandatory"
        return True  # extended runs everything (mandatory + extended + baselines)

    scns = [s for s in SCENARIOS if selected(s)]
    run_rows: dict[str, dict] = {}
    all_run_rows, stage_rows, cde_rows, fail_rows = [], [], [], []

    for scn in scns:
        run_id, tier, pkg, sheet_spec, margin, spacing, tl, _b = scn
        print(f"\n--- {run_id} ({tier}) {pkg} {sheet_spec} margin={margin} spacing={spacing} ---")
        inp = build_input(run_id, pkg, sheet_spec, margin, spacing, tl)
        try:
            out = run_solver(run_id, inp, args.max_time_limit_s)
        except Exception as e:  # runner crash / parse error → hard fail
            errors.append(f"{run_id}: {e}")
            print(f"  ERROR: {e}")
            continue
        check_run_integrity(run_id, out, errors)
        rr = run_row(run_id, scn, inp, out)
        run_rows[run_id] = rr
        all_run_rows.append(rr)
        stage_rows.append(stage_timing_row(run_id, out))
        cde_rows.append(cde_row(run_id, out))
        fail_rows.extend(failure_rows(run_id, out))
        print(f"  status={rr['status']} placed={rr['placed_count']}/{rr['total_instances']} "
              f"used_sheets={rr['used_sheet_count']} spacing_viol={rr['technology_spacing_violation_count']} "
              f"offset_fail={rr['technology_spacing_offset_failure_count']} wall={rr['wall_time_s']}s")

    write_csv(TABLES / "q37_run_summary.csv", all_run_rows)
    write_csv(TABLES / "q37_stage_timing.csv", stage_rows)
    write_csv(TABLES / "q37_cde_metrics.csv", cde_rows)
    write_csv(TABLES / "q37_failure_taxonomy.csv", fail_rows)
    write_csv(TABLES / "q37_quality_comparison.csv", quality_rows(run_rows))

    manifest = {
        "tier": args.tier,
        "only": args.only,
        "max_time_limit_s": args.max_time_limit_s,
        "scenarios_run": list(run_rows.keys()),
        "geometry_inventory_parts": len(inv),
        "offsettable_at_spacing": offsettable,
        "errors": errors,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_full276": str(BASE_FULL276.relative_to(ROOT)),
        "base_dense191": str(BASE_DENSE191.relative_to(ROOT)),
    }
    (TABLES / "q37_measurement_manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\n{'='*56}")
    if errors:
        print("  MEASUREMENT GATE ERRORS:")
        for e in errors:
            print(f"   - {e}")
        print("  RESULT: FAIL")
        return 2
    print(f"  runs={len(run_rows)}  RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
