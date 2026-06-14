#!/usr/bin/env python3
"""SGH-Q45 — Full276 LV8 BPP sheet-reduction minimal-used-sheet benchmark.

Runs the native vrs_solver `sparrow_cde_multisheet` pipeline (now the coroush-style BPP
sheet-reduction path) on the canonical full276 LV8 package with Q42 technology parameters
(margin 5, spacing 8, kerf 0, continuous rotation), on 1500×3000 mm finite stock. The
objective is the MINIMAL number of used sheets — there is no 2-sheet hard cap; the stock
pool quantity is configurable (default 6).

The report distinguishes "valid full layout" from "minimal-sheet proof":
  AREA_LOWER_BOUND_MATCHED | GAP_TO_AREA_LOWER_BOUND=n | BEST_FOUND_NOT_PROVEN_MINIMAL.
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

Q45 = ROOT / "artifacts/benchmarks/sgh_q45"
INPUTS = Q45 / "inputs"
OUTPUTS = Q45 / "outputs"
LOGS = Q45 / "logs"
RENDERS = Q45 / "renders"

MARGIN_MM = 5.0
SPACING_MM = 8.0
KERF_MM = 0.0
SEED = 42
TOTAL_INSTANCES = 276
SHEET_W = 1500.0
SHEET_H = 3000.0

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


def run_id(time_limit_s: int, stock_qty: int) -> str:
    return f"q45_full276_bpp_{stock_qty}x1500x3000_margin5_spacing8_continuous_{time_limit_s}"


def build_input(time_limit_s: int, stock_qty: int) -> Path:
    doc = {
        "contract_version": "v1",
        "project_name": f"sgh_q45_full276_bpp_{time_limit_s}_q{stock_qty}",
        "seed": SEED,
        "time_limit_s": time_limit_s,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": MARGIN_MM,
        "spacing_mm": SPACING_MM,
        "kerf_mm": KERF_MM,
        "rotation_policy": "continuous",
        "stocks": [{"id": "S1500x3000", "quantity": stock_qty, "width": SHEET_W, "height": SHEET_H}],
        "parts": load_parts(),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"{run_id(time_limit_s, stock_qty)}.json"
    path.write_text(json.dumps(doc, indent=2))
    return path


def output_path(time_limit_s: int, stock_qty: int) -> Path:
    return OUTPUTS / f"{run_id(time_limit_s, stock_qty)}_output.json"


def run_solver(time_limit_s: int, stock_qty: int, input_path: Path) -> dict[str, Any]:
    rid = run_id(time_limit_s, stock_qty)
    out_path = output_path(time_limit_s, stock_qty)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.pop("SGH_Q35_SPACING_VALIDATOR", None)
    env.pop("VRS_MULTISHEET_MODE", None)  # ensure the BPP path (default) runs
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(input_path), "--output", str(out_path)],
        capture_output=True, text=True, timeout=time_limit_s + 1800, env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{rid}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\ntime_limit_s={time_limit_s}\nstock_qty={stock_qty}\n"
        f"stdout:\n{proc.stdout[:4000]}\nstderr:\n{proc.stderr[:4000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{rid} solver exit {proc.returncode}: {proc.stderr[:800]}")
    out = json.loads(out_path.read_text())
    out["_wall_time_s"] = wall
    out["_exit_code"] = proc.returncode
    return out


def _part_outer(part: dict[str, Any]) -> list[tuple[float, float]]:
    raw = part.get("outer_points") or part.get("prepared_outer_points") or []
    pts = [(float(i[0]), float(i[1])) for i in raw if isinstance(i, (list, tuple)) and len(i) >= 2]
    if not pts:
        w, h = float(part.get("width", 0.0)), float(part.get("height", 0.0))
        pts = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
    return pts


def polygon_area(part: dict[str, Any]) -> float:
    pts = _part_outer(part)
    if len(pts) < 3:
        return 0.0
    return abs(0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                         for i in range(len(pts))))


def _transform(ring, ax, ay, rot_deg):
    th = math.radians(rot_deg)
    c, s = math.cos(th), math.sin(th)
    return [(ax + x * c - y * s, ay + x * s + y * c) for x, y in ring]


def render(rid: str, out: dict[str, Any], used: list[int]) -> dict[str, Any]:
    rdir = RENDERS / rid
    rdir.mkdir(parents=True, exist_ok=True)
    parts_by_id = base_part_lookup()
    placements = out.get("placements", [])
    palette = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
               "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac", "#1f77b4", "#2ca02c"]
    svg_count = png_count = 0
    per_sheet = []
    for render_idx, si in enumerate(used):
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W:.1f}mm" height="{SHEET_H:.1f}mm" '
            f'viewBox="0 0 {SHEET_W:.1f} {SHEET_H:.1f}">',
            f'<rect width="{SHEET_W:.1f}" height="{SHEET_H:.1f}" fill="#fff" stroke="#000" stroke-width="2"/>',
            f'<rect x="{MARGIN_MM}" y="{MARGIN_MM}" width="{SHEET_W-2*MARGIN_MM:.1f}" height="{SHEET_H-2*MARGIN_MM:.1f}" '
            f'fill="none" stroke="#c00" stroke-width="1.5" stroke-dasharray="8,6"/>',
        ]
        cnt = 0
        area = 0.0
        for pl in placements:
            if int(pl.get("sheet_index", -1)) != si:
                continue
            part = parts_by_id.get(pl["part_id"])
            if not part:
                continue
            world = _transform(_part_outer(part), float(pl["x"]), float(pl["y"]), float(pl.get("rotation_deg", 0.0)))
            d = " ".join(f"{'M' if i==0 else 'L'} {x:.2f} {SHEET_H-y:.2f}" for i, (x, y) in enumerate(world)) + " Z"
            col = palette[(hash(pl["part_id"]) & 0xFFFFFF) % len(palette)]
            lines.append(f'<path d="{d}" fill="{col}" fill-opacity="0.7" stroke="#222" stroke-width="0.5"/>')
            cnt += 1
            area += polygon_area(part)
        lines.append(f'<text x="6" y="26" font-size="34">{rid} sheet {si} placed={cnt}</text></svg>')
        svg_path = rdir / f"sheet_{render_idx:02d}.svg"
        svg_path.write_text("\n".join(lines))
        svg_count += 1
        png_path = rdir / f"sheet_{render_idx:02d}.png"
        if HAVE_CAIROSVG:
            try:
                import cairosvg
                cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1000)
                png_count += 1
            except Exception:
                pass
        per_sheet.append({
            "sheet_index": si, "placed_count": cnt, "placed_part_area": round(area, 2),
            "physical_utilization_pct": round(100.0 * area / (SHEET_W * SHEET_H), 4),
            "svg_path": str(svg_path.relative_to(ROOT)),
        })
    manifest = {"run_id": rid, "used_sheet_indices": used, "svg_count": svg_count,
                "png_count": png_count, "have_cairosvg": HAVE_CAIROSVG, "per_sheet": per_sheet}
    (rdir / "render_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def is_orthogonal(deg: float) -> bool:
    return any(abs((deg % 360.0) - t) <= 1e-6 for t in (0.0, 90.0, 180.0, 270.0))


def summarize(time_limit_s: int, stock_qty: int, out: dict[str, Any]) -> dict[str, Any]:
    d = out.get("optimizer_diagnostics", {}) or {}
    b = d.get("bpp_reduction", {}) or {}
    m = out.get("metrics", {})
    placements = out.get("placements", [])
    used = sorted({int(p["sheet_index"]) for p in placements})
    rots = [float(p.get("rotation_deg", 0.0)) % 360.0 for p in placements]
    non_orth = [r for r in rots if not is_orthogonal(r)]
    manifest = render(run_id(time_limit_s, stock_qty), out, used)
    full = out.get("status") == "ok" and int(m.get("unplaced_count", 0)) == 0
    row = {
        "run_id": run_id(time_limit_s, stock_qty),
        "time_limit_s": time_limit_s,
        "stock_qty": stock_qty,
        "status": out.get("status"),
        "exit_code": out.get("_exit_code"),
        "wall_time_s": round(out["_wall_time_s"], 2) if isinstance(out.get("_wall_time_s"), (int, float)) else None,
        "placed_count": int(m.get("placed_count", 0)),
        "unplaced_count": int(m.get("unplaced_count", 0)),
        "full_placement_achieved": full,
        "valid_geometry": int(d.get("sparrow_ms_final_pairs") or 0) == 0
        and int(d.get("sparrow_ms_boundary_violations") or 0) == 0,
        "final_pairs": d.get("sparrow_ms_final_pairs"),
        "boundary_violations": d.get("sparrow_ms_boundary_violations"),
        "margin_violation_count": d.get("technology_margin_violation_count"),
        "spacing_violation_count": d.get("technology_spacing_violation_count"),
        "used_sheet_count": d.get("sparrow_ms_used_sheet_count", len(used)),
        "used_sheet_indices": d.get("sparrow_ms_used_sheet_indices", used),
        "available_sheet_count": d.get("sparrow_ms_available_sheet_count"),
        "area_lower_bound": b.get("bpp_area_lower_bound"),
        "gap_to_area_lower_bound": b.get("bpp_gap_to_area_lower_bound"),
        "minimality_status": b.get("bpp_minimality_status"),
        "bpp_reduction_active": b.get("bpp_reduction_active"),
        "bpp_initial_sheet_count": b.get("bpp_initial_sheet_count"),
        "bpp_final_sheet_count": b.get("bpp_final_sheet_count"),
        "bpp_elimination_attempts": b.get("bpp_elimination_attempts"),
        "bpp_elimination_successes": b.get("bpp_elimination_successes"),
        "bpp_elimination_failures": b.get("bpp_elimination_failures"),
        "bpp_transfer_attempts": b.get("bpp_transfer_attempts"),
        "bpp_transfer_successes": b.get("bpp_transfer_successes"),
        "bpp_swap_attempts": b.get("bpp_swap_attempts"),
        "bpp_compaction_calls": b.get("bpp_compaction_calls"),
        "bpp_compaction_successes": b.get("bpp_compaction_successes"),
        "bpp_separator_calls": b.get("bpp_separator_calls"),
        "bpp_runtime_ms": b.get("bpp_runtime_ms"),
        "rotation_policy_input": "continuous",
        "non_orthogonal_rotation_count": len(non_orth),
        "continuous_rotation_proven_by_output": len(non_orth) > 0,
        "solver_reported_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "render_svg_count": manifest.get("svg_count"),
        "render_png_count": manifest.get("png_count"),
        "bpp_full_diagnostics": b,
    }
    row["technically_successful"] = (
        row["exit_code"] == 0
        and (full or row["unplaced_count"] > 0)  # full OR explicit partial
        and int(row["final_pairs"] or 0) == 0
        and int(row["boundary_violations"] or 0) == 0
        and int(row["margin_violation_count"] or 0) == 0
        and int(row["spacing_violation_count"] or 0) == 0
        and bool(row["bpp_reduction_active"])
    )
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-limit", type=int, default=1200)
    ap.add_argument("--stock-qty", type=int, default=6)
    args = ap.parse_args()
    if not SOLVER_BIN.exists():
        raise SystemExit(f"missing solver binary: {SOLVER_BIN}")
    Q45.mkdir(parents=True, exist_ok=True)
    inp = build_input(args.time_limit, args.stock_qty)
    print(f"Q45 BPP run: time_limit={args.time_limit}s stock_qty={args.stock_qty} → solving …", flush=True)
    out = run_solver(args.time_limit, args.stock_qty, inp)
    row = summarize(args.time_limit, args.stock_qty, out)

    summary_path = Q45 / f"summary_{args.time_limit}_q{args.stock_qty}.json"
    summary_path.write_text(json.dumps(row, indent=2))
    # also maintain a combined summary.json (latest run wins per (time,qty) key)
    combined = {}
    cpath = Q45 / "summary.json"
    if cpath.exists():
        try:
            combined = json.loads(cpath.read_text())
        except Exception:
            combined = {}
    combined[row["run_id"]] = row
    cpath.write_text(json.dumps(combined, indent=2))

    print(f"  status={row['status']} placed={row['placed_count']}/{TOTAL_INSTANCES} "
          f"used_sheets={row['used_sheet_count']} init={row['bpp_initial_sheet_count']} "
          f"lb={row['area_lower_bound']} gap={row['gap_to_area_lower_bound']} "
          f"minimality={row['minimality_status']} elim_ok={row['bpp_elimination_successes']} "
          f"technically_successful={row['technically_successful']} wall={row['wall_time_s']}s")
    print(f"  wrote {summary_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
