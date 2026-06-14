#!/usr/bin/env python3
"""SGH-Q43b — Render evidence generator for the 1x1500x6000 own solver run.

Reads artifacts/benchmarks/sgh_q43b/outputs/q43b_full276_1x1500x6000_…_output.json
and produces per-sheet SVG + overview SVG (+ optional PNG via cairosvg).
Mirrors the render block of scripts/bench_sgh_q42_full276_lv8_continuous.py.

Does NOT modify the own solver source. Only reads the output JSON and
the Q42 input to recover the original outer_points polygons.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
Q43B = ROOT / "artifacts" / "benchmarks" / "sgh_q43b"
INPUTS = Q43B / "inputs"
OUTPUTS = Q43B / "outputs"
RENDERS = Q43B / "renders"

Q42_INPUT = ROOT / "artifacts" / "benchmarks" / "sgh_q42" / "inputs" / "q42_full276_3x1500x3000_margin5_spacing8_continuous_1200.json"

STRIP_W = 1500.0
STRIP_H = 6000.0
RUN_ID = "q43b_full276_1x1500x6000_margin5_spacing8_continuous_1200"

try:
    import cairosvg  # noqa: F401
    HAVE_CAIROSVG = True
except Exception:
    HAVE_CAIROSVG = False


def load_input_doc() -> dict[str, Any]:
    return json.loads(Q42_INPUT.read_text())


def parts_by_id(input_doc: dict[str, Any]) -> dict[str, list[list[float]]]:
    return {p["id"]: p.get("outer_points") or [] for p in input_doc["parts"]}


def transform_poly(points: list[list[float]], tx: float, ty: float, rot_deg: float) -> list[tuple[float, float]]:
    theta = math.radians(rot_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    out: list[tuple[float, float]] = []
    for x, y in points:
        rx = x * cos_t - y * sin_t
        ry = x * sin_t + y * cos_t
        out.append((rx + tx, ry + ty))
    return out


def render_sheet_svg(sheet_index: int, sw: float, sh: float, placements: list[dict[str, Any]],
                     pmap: dict[str, list[list[float]]]) -> str:
    parts_on_sheet = [p for p in placements if p.get("sheet_index") == sheet_index]
    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{sw:.0f}" height="{sh:.0f}" '
        f'viewBox="0 0 {sw:.0f} {sh:.0f}">'
    )
    # background
    lines.append(f'<rect x="0" y="0" width="{sw:.0f}" height="{sh:.0f}" fill="#fafafa" stroke="#888" stroke-width="1"/>')
    # 1500 mm scale tick marks (every 500 mm)
    for x in range(0, int(sw) + 1, 500):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{sh:.0f}" stroke="#ddd" stroke-width="0.5"/>')
    for y in range(0, int(sh) + 1, 1000):
        lines.append(f'<line x1="0" y1="{y}" x2="{sw:.0f}" y2="{y}" stroke="#ddd" stroke-width="0.5"/>')
    # sheet label
    lines.append(f'<text x="10" y="20" font-size="14" fill="#333">Q43b sheet {sheet_index}: '
                 f'{len(parts_on_sheet)} placements on {sw:.0f}x{sh:.0f} mm</text>')
    # placements
    for p in parts_on_sheet:
        pid = p.get("part_id")
        tx = float(p.get("x", 0.0))
        ty = float(p.get("y", 0.0))
        rot = float(p.get("rotation_deg", 0.0))
        pts = pmap.get(pid, [])
        if not pts:
            continue
        transformed = transform_poly(pts, tx, ty, rot)
        path_d = "M " + " L ".join(f"{x:.3f},{y:.3f}" for x, y in transformed) + " Z"
        # color by part_id hash for differentiation
        color = f"hsl({abs(hash(pid)) % 360}, 55%, 60%)"
        lines.append(f'<path d="{path_d}" fill="{color}" fill-opacity="0.55" stroke="#333" stroke-width="0.4"/>')
    lines.append("</svg>")
    return "\n".join(lines)


def render_overview_svg(used: list[int], sheet_dims: dict[int, tuple[float, float]]) -> str:
    if not used:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><text x="10" y="60">Q43b: no used sheets</text></svg>'
    # Lay out side-by-side at fixed scale
    scale = 0.15  # 1500 mm -> 225 px
    pad = 20
    label_h = 40
    total_w = 0
    sheet_imgs: list[tuple[int, int, int]] = []  # (render_x, render_y, render_w)
    for sidx in used:
        sw, sh = sheet_dims.get(sidx, (STRIP_W, STRIP_H))
        rw = int(sw * scale)
        rh = int(sh * scale)
        sheet_imgs.append((total_w, label_h, rw))
        total_w += rw + pad
    total_h = max((int(sheet_dims[s][1] * scale) for s in used), default=int(STRIP_H * scale)) + label_h + 20
    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}">'
    )
    lines.append(f'<text x="10" y="20" font-size="14" fill="#333">Q43b overview: {len(used)} used sheet(s) on {STRIP_W}x{STRIP_H} mm</text>')
    for sidx, (rx, ry, rw) in zip(used, sheet_imgs):
        sw, sh = sheet_dims.get(sidx, (STRIP_W, STRIP_H))
        rh = int(sh * scale)
        lines.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="#fafafa" stroke="#888" stroke-width="1"/>')
        lines.append(f'<text x="{rx + 5}" y="{ry + rh + 15}" font-size="11" fill="#333">sheet {sidx} ({sw:.0f}x{sh:.0f})</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def svg_to_png(svg_path: Path, png_path: Path) -> bool:
    if not HAVE_CAIROSVG:
        return False
    try:
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1400)
        return True
    except Exception as e:
        print(f"PNG conversion failed for {svg_path}: {e}")
        return False


def main() -> int:
    RENDERS.mkdir(parents=True, exist_ok=True)
    in_doc = load_input_doc()
    pmap = parts_by_id(in_doc)

    out_doc_path = OUTPUTS / f"{RUN_ID}_output.json"
    if not out_doc_path.exists():
        print(f"missing output: {out_doc_path}")
        return 1
    out_doc = json.loads(out_doc_path.read_text())
    placements = out_doc.get("placements", [])

    used_sheets = sorted({p.get("sheet_index", 0) for p in placements})
    if not used_sheets:
        used_sheets = [0]

    rdir = RENDERS / RUN_ID
    rdir.mkdir(parents=True, exist_ok=True)

    sheet_dims = {0: (STRIP_W, STRIP_H)}

    svg_count = 0
    png_count = 0
    for render_idx, sheet_index in enumerate(used_sheets):
        sw, sh = sheet_dims[sheet_index]
        svg_path = rdir / f"sheet_{render_idx:02d}.svg"
        png_path = rdir / f"sheet_{render_idx:02d}.png"
        svg_text = render_sheet_svg(sheet_index, sw, sh, placements, pmap)
        svg_path.write_text(svg_text)
        svg_count += 1
        if svg_to_png(svg_path, png_path):
            png_count += 1

    # Overview
    overview_svg = rdir / "overview.svg"
    overview_png = rdir / "overview.png"
    overview_svg.write_text(render_overview_svg(used_sheets, sheet_dims))
    svg_count += 1
    if svg_to_png(overview_svg, overview_png):
        png_count += 1

    # Manifest
    manifest = {
        "run_id": RUN_ID,
        "used_sheet_count": len(used_sheets),
        "used_sheet_indices": used_sheets,
        "sheet_dimensions_mm": {str(k): list(v) for k, v in sheet_dims.items()},
        "render_dir": str(rdir),
        "svg_count": svg_count,
        "png_count": png_count,
        "have_cairosvg": HAVE_CAIROSVG,
    }
    (rdir / "render_manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"rendered: {svg_count} SVG, {png_count} PNG in {rdir}")
    print(f"used sheets: {used_sheets}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
