#!/usr/bin/env python3
"""Generate per-sheet SVG files from a nesting engine solver output.

Usage:
    python3 scripts/visualize_nesting.py \
        --input  tmp/lv8_single_benchmark/prepacked_solver_input.json \
        --output tmp/lv8_single_benchmark/solver_stdout.json \
        --out-dir tmp/lv8_single_benchmark/svg

Or pass the solver output via stdin:
    nesting_engine nest ... < input.json > output.json
    python3 scripts/visualize_nesting.py --input in.json --output output.json --out-dir /tmp/nesting_svg
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── colour palette (cycles) ──────────────────────────────────────────────────

_PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def _colour(part_id: str) -> str:
    h = hash(part_id) & 0xFFFFFF
    idx = h % len(_PALETTE)
    return _PALETTE[idx]


# ── geometry helpers ─────────────────────────────────────────────────────────

def _rotate_point(x: float, y: float, deg: float) -> tuple[float, float]:
    if deg == 0.0:
        return x, y
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    return c * x - s * y, s * x + c * y


def _transform_ring(
    ring: list[list[float]],
    tx: float,
    ty: float,
    rot_deg: float,
) -> list[tuple[float, float]]:
    # Step 1: rotate
    rotated = [_rotate_point(pt[0], pt[1], rot_deg) for pt in ring]
    if not rotated:
        return []
    # Step 2: normalize — engine shifts rotated polygon so its min_x=0, min_y=0
    # (normalize_polygon_min_xy in nfp_placer.rs), then placement tx/ty is in
    # this normalized space.
    min_x = min(p[0] for p in rotated)
    min_y = min(p[1] for p in rotated)
    # Step 3: apply normalization shift + placement translation
    return [(p[0] - min_x + tx, p[1] - min_y + ty) for p in rotated]


def _svg_path_d(
    outer: list[tuple[float, float]],
    holes: list[list[tuple[float, float]]],
    sheet_h: float,
) -> str:
    """Build SVG path data. Flips y-axis so y=0 is top of SVG canvas."""

    def _pts(ring: list[tuple[float, float]]) -> str:
        parts = []
        for i, (x, y) in enumerate(ring):
            sy = sheet_h - y  # flip
            cmd = "M" if i == 0 else "L"
            parts.append(f"{cmd}{x:.4f},{sy:.4f}")
        parts.append("Z")
        return " ".join(parts)

    parts = [_pts(outer)]
    for hole in holes:
        parts.append(_pts(hole))
    return " ".join(parts)


# ── SVG builder ───────────────────────────────────────────────────────────────

def render_sheet_svg(
    *,
    sheet_index: int,
    sheet_w: float,
    sheet_h: float,
    placements: list[dict],
    geometry_by_part_id: dict[str, dict],
) -> str:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg"',
        f'     width="{sheet_w:.2f}mm" height="{sheet_h:.2f}mm"',
        f'     viewBox="0 0 {sheet_w:.4f} {sheet_h:.4f}">',
        f'  <!-- Sheet {sheet_index}: {sheet_w:.0f}mm × {sheet_h:.0f}mm -->',
        f'  <rect width="{sheet_w:.4f}" height="{sheet_h:.4f}" fill="#f0f4f8" stroke="#1e293b" stroke-width="1"/>',
    ]

    for pl in placements:
        if pl.get("sheet") != sheet_index:
            continue
        part_id = pl["part_id"]
        geom = geometry_by_part_id.get(part_id)
        if geom is None:
            continue

        tx = float(pl["x_mm"])
        ty = float(pl["y_mm"])
        rot = float(pl.get("rotation_deg", 0))

        outer = _transform_ring(geom["outer"], tx, ty, rot)
        holes = [_transform_ring(h, tx, ty, rot) for h in geom["holes"]]

        path_d = _svg_path_d(outer, holes, sheet_h)
        fill = _colour(part_id)
        # Strip cavity-composite prefix for label
        label = part_id
        if "__" in label:
            parts = label.split("__")
            label = parts[2] if len(parts) > 2 else label

        lines.append(
            f'  <path d="{path_d}" fill="{fill}" fill-opacity="0.45"'
            f' stroke="#0f172a" stroke-width="0.4" fill-rule="evenodd"'
            f' data-part-id="{part_id}" data-rot="{rot}"/>'
        )
        # Centroid label
        cx = sum(x for x, _ in outer) / len(outer)
        cy_raw = sum(y for _, y in outer) / len(outer)
        cy_svg = sheet_h - cy_raw
        short_label = label[:16]
        lines.append(
            f'  <text x="{cx:.1f}" y="{cy_svg:.1f}" font-size="3"'
            f' text-anchor="middle" fill="#1e293b" opacity="0.7">{short_label}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize nesting engine output as SVG")
    parser.add_argument("--input", required=True, help="Solver input JSON (with geometry)")
    parser.add_argument("--output", required=True, help="Solver output JSON (with placements)")
    parser.add_argument("--out-dir", default=".", help="Directory to write SVG files (default: .)")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        inp = json.load(f)
    with open(args.output, encoding="utf-8") as f:
        out = json.load(f)

    sheet_w = float(inp["sheet"]["width_mm"])
    sheet_h = float(inp["sheet"]["height_mm"])

    # Build geometry index: part_id → {outer, holes}
    geometry_by_part_id: dict[str, dict] = {}
    for part in inp.get("parts", []):
        pid = part["id"]
        geometry_by_part_id[pid] = {
            "outer": part.get("outer_points_mm", []),
            "holes": part.get("holes_points_mm", []),
        }

    placements = out.get("placements", [])
    sheets_used = int(out.get("sheets_used", 1))

    print(f"Placed: {len(placements)} parts on {sheets_used} sheet(s)")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for sheet_idx in range(sheets_used):
        sheet_placements = [p for p in placements if p.get("sheet") == sheet_idx]
        svg = render_sheet_svg(
            sheet_index=sheet_idx,
            sheet_w=sheet_w,
            sheet_h=sheet_h,
            placements=placements,
            geometry_by_part_id=geometry_by_part_id,
        )
        svg_path = out_dir / f"sheet_{sheet_idx:02d}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        print(f"  Sheet {sheet_idx}: {len(sheet_placements)} parts → {svg_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
