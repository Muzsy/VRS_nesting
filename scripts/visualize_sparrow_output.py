#!/usr/bin/env python3
"""Visualize a vrs_solver (Sparrow) run as per-sheet SVG files.

The Sparrow solver places parts using an **anchor** coordinate convention:
    world_point = anchor + rotate(local_point, rotation_deg)
where local_point is in the part's local frame (outer_points as given).

This is different from the legacy NFP visualizer which uses rect-min convention
(the bottom-left of the rotated bounding box). This script uses the correct
Sparrow anchor transform directly.

Usage:
    python3 scripts/visualize_sparrow_output.py \\
        --input  artifacts/benchmarks/sgh_q31/inputs/dense191.json \\
        --output /tmp/dense191_long_out.json \\
        --out-dir /tmp/dense191_svg

    # PNG (requires inkscape):
    inkscape sheet_00.svg --export-type=png --export-filename=sheet_00.png --export-width=1800
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

_PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def _colour(part_id: str) -> str:
    h = hash(part_id) & 0xFFFFFF
    return _PALETTE[h % len(_PALETTE)]


def _transform_ring_anchor(
    ring: list[list[float]],
    anchor_x: float,
    anchor_y: float,
    rot_deg: float,
) -> list[tuple[float, float]]:
    """Sparrow anchor transform: world = anchor + rotate(local_pt).

    Matches transform_polygon() in collision_backend.rs:
        world_x = anchor_x + local_x * cos(rot) - local_y * sin(rot)
        world_y = anchor_y + local_x * sin(rot) + local_y * cos(rot)
    """
    theta = math.radians(rot_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    return [
        (anchor_x + px * cos_t - py * sin_t,
         anchor_y + px * sin_t + py * cos_t)
        for px, py in ring
    ]


def _svg_path_d(
    outer: list[tuple[float, float]],
    holes: list[list[tuple[float, float]]],
    sheet_h: float,
) -> str:
    """SVG path, y-axis flipped so y=0 is the top of the canvas."""
    def _pts(ring: list[tuple[float, float]]) -> str:
        parts = []
        for i, (x, y) in enumerate(ring):
            sy = sheet_h - y
            parts.append(f"{'M' if i == 0 else 'L'}{x:.4f},{sy:.4f}")
        parts.append("Z")
        return " ".join(parts)

    rings = [_pts(outer)] + [_pts(h) for h in holes]
    return " ".join(rings)


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
        f'  <!-- Sheet {sheet_index}: {sheet_w:.0f}mm x {sheet_h:.0f}mm -->',
        f'  <rect width="{sheet_w:.4f}" height="{sheet_h:.4f}" '
        f'fill="#f0f4f8" stroke="#1e293b" stroke-width="1"/>',
    ]

    for pl in placements:
        if pl.get("sheet_index") != sheet_index:
            continue
        part_id = pl["part_id"]
        geom = geometry_by_part_id.get(part_id)
        if geom is None:
            continue

        ax = float(pl["x"])
        ay = float(pl["y"])
        rot = float(pl.get("rotation_deg", 0.0))

        outer = _transform_ring_anchor(geom["outer"], ax, ay, rot)
        holes = [_transform_ring_anchor(h, ax, ay, rot) for h in geom["holes"]]

        if not outer:
            continue

        path_d = _svg_path_d(outer, holes, sheet_h)
        fill = _colour(part_id)
        label = part_id.split("__")[-1] if "__" in part_id else part_id

        lines.append(
            f'  <path d="{path_d}" fill="{fill}" fill-opacity="0.5"'
            f' stroke="#0f172a" stroke-width="0.5" fill-rule="evenodd"'
            f' data-part-id="{part_id}" data-rot="{rot}"/>'
        )
        cx = sum(x for x, _ in outer) / len(outer)
        cy_raw = sum(y for _, y in outer) / len(outer)
        lines.append(
            f'  <text x="{cx:.1f}" y="{sheet_h - cy_raw:.1f}" font-size="4"'
            f' text-anchor="middle" fill="#1e293b" opacity="0.8">{label[:14]}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize Sparrow (vrs_solver) output as SVG")
    parser.add_argument("--input",   required=True, help="Solver input JSON (vrs_solver format)")
    parser.add_argument("--output",  required=True, help="Solver output JSON (vrs_solver format)")
    parser.add_argument("--out-dir", default=".",   help="Directory to write SVG files (default: .)")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        inp = json.load(f)
    with open(args.output, encoding="utf-8") as f:
        out = json.load(f)

    stocks = inp.get("stocks", [])
    if not stocks:
        print("ERROR: no stocks in input", file=sys.stderr)
        return 1
    sheet_w = float(stocks[0]["width"])
    sheet_h = float(stocks[0]["height"])

    geometry_by_part_id: dict[str, dict] = {}
    for part in inp.get("parts", []):
        outer_raw = part.get("outer_points") or []
        holes_raw = part.get("holes_points") or []
        # Normalise: outer_points may be [[x,y],...] or [[[x,y],...]] (nested)
        if outer_raw and isinstance(outer_raw[0][0], list):
            outer_raw = outer_raw[0]
        geometry_by_part_id[part["id"]] = {
            "outer": [[float(p[0]), float(p[1])] for p in outer_raw],
            "holes": [
                [[float(p[0]), float(p[1])] for p in ring]
                for ring in (holes_raw if holes_raw else [])
                if ring
            ],
        }

    placements = out.get("placements", [])
    sheets_used = max((p.get("sheet_index", 0) for p in placements), default=0) + 1

    metrics = out.get("metrics", {})
    od = out.get("optimizer_diagnostics", {})
    print(f"status        : {out.get('status', '?')}")
    print(f"placed        : {metrics.get('placed_count', len(placements))} / {len(placements)}")
    print(f"sheets_used   : {sheets_used}")
    print(f"sheet size    : {sheet_w:.0f} x {sheet_h:.0f} mm")
    print(f"final_pairs   : {od.get('sparrow_collision_graph_final_pairs', '?')}")
    print(f"converged     : {od.get('sparrow_converged', '?')}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for sheet_idx in range(sheets_used):
        sheet_pls = [p for p in placements if p.get("sheet_index", 0) == sheet_idx]
        svg = render_sheet_svg(
            sheet_index=sheet_idx,
            sheet_w=sheet_w,
            sheet_h=sheet_h,
            placements=placements,
            geometry_by_part_id=geometry_by_part_id,
        )
        svg_path = out_dir / f"sheet_{sheet_idx:02d}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        print(f"  Sheet {sheet_idx}: {len(sheet_pls)} parts -> {svg_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
