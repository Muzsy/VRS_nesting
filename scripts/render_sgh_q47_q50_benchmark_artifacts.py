#!/usr/bin/env python3
"""Render SGH-Q47-Q50 benchmark solver outputs as SVG and PNG sheet plans."""
from __future__ import annotations

import json
import math
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

try:
    import cairosvg  # type: ignore

    HAVE_CAIROSVG = True
except Exception:
    cairosvg = None
    HAVE_CAIROSVG = False

RUNS = {
    47: [
        ("q47_A_profileon_300", "inputs/q47_full276_6x1500x3000_margin5_spacing8_continuous_300.json", "outputs/q47_A_profileon_300_output.json"),
        ("q47_B_profileoff_300", "inputs/q47_full276_6x1500x3000_margin5_spacing8_continuous_300.json", "outputs/q47_B_profileoff_300_output.json"),
    ],
    48: [
        ("q48_A_densityon_300", "inputs/q48_full276_6x1500x3000_margin5_spacing8_continuous_300.json", "outputs/q48_A_densityon_300_output.json"),
        ("q48_B_densityoff_300", "inputs/q48_full276_6x1500x3000_margin5_spacing8_continuous_300.json", "outputs/q48_B_densityoff_300_output.json"),
    ],
    49: [
        ("q49_A_densityon_300", "inputs/q49_full276_6x1500x3000_margin5_spacing8_continuous_300.json", "outputs/q49_A_densityon_300_output.json"),
        ("q49_B_densityoff_300", "inputs/q49_full276_6x1500x3000_margin5_spacing8_continuous_300.json", "outputs/q49_B_densityoff_300_output.json"),
    ],
    50: [
        ("q50_A_lnson_300", "inputs/q50_full276_6x1500x3000_margin5_spacing8_continuous_300.json", "outputs/q50_A_lnson_300_output.json"),
        ("q50_B_lnsoff_300", "inputs/q50_full276_6x1500x3000_margin5_spacing8_continuous_300.json", "outputs/q50_B_lnsoff_300_output.json"),
    ],
}

PALETTE = [
    "#4e79a7",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#59a14f",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
    "#1f77b4",
    "#2ca02c",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def expand_stock_sheets(stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sheets: list[dict[str, Any]] = []
    for stock in stocks:
        for _ in range(int(stock["quantity"])):
            sheets.append(
                {
                    "id": stock["id"],
                    "width": float(stock["width"]),
                    "height": float(stock["height"]),
                }
            )
    return sheets


def part_outer(part: dict[str, Any]) -> list[tuple[float, float]]:
    raw = part.get("outer_points") or part.get("prepared_outer_points") or []
    pts = [
        (float(item[0]), float(item[1]))
        for item in raw
        if isinstance(item, (list, tuple)) and len(item) >= 2
    ]
    if pts:
        return pts
    return [
        (0.0, 0.0),
        (float(part.get("width", 0.0)), 0.0),
        (float(part.get("width", 0.0)), float(part.get("height", 0.0))),
        (0.0, float(part.get("height", 0.0))),
    ]


def transform(
    ring: list[tuple[float, float]],
    anchor_x: float,
    anchor_y: float,
    rot_deg: float,
) -> list[tuple[float, float]]:
    theta = math.radians(rot_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    return [
        (anchor_x + x * cos_t - y * sin_t, anchor_y + x * sin_t + y * cos_t)
        for x, y in ring
    ]


def polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    return abs(
        0.5
        * sum(
            points[i][0] * points[(i + 1) % len(points)][1]
            - points[(i + 1) % len(points)][0] * points[i][1]
            for i in range(len(points))
        )
    )


def color(part_id: str) -> str:
    idx = int(sha256(part_id.encode("utf-8")).hexdigest()[:8], 16) % len(PALETTE)
    return PALETTE[idx]


def render_sheet_svg(
    run_id: str,
    sheet_index: int,
    sheet_w: float,
    sheet_h: float,
    margin_mm: float,
    placements: list[dict[str, Any]],
    parts_by_id: dict[str, dict[str, Any]],
) -> str:
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{sheet_w:.2f}mm" height="{sheet_h:.2f}mm" viewBox="0 0 {sheet_w:.4f} {sheet_h:.4f}">',
        f'  <!-- {run_id} sheet {sheet_index} rendered from solver output placements and input outer_points -->',
        f'  <rect width="{sheet_w:.4f}" height="{sheet_h:.4f}" fill="#ffffff" stroke="#111827" stroke-width="2"/>',
        f'  <rect x="{margin_mm:.4f}" y="{margin_mm:.4f}" width="{sheet_w - 2 * margin_mm:.4f}" '
        f'height="{sheet_h - 2 * margin_mm:.4f}" fill="none" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="8,6"/>',
    ]
    count = 0
    for placement in placements:
        if int(placement.get("sheet_index", -1)) != sheet_index:
            continue
        part_id = str(placement["part_id"])
        part = parts_by_id.get(part_id)
        if not part:
            continue
        world = transform(
            part_outer(part),
            float(placement["x"]),
            float(placement["y"]),
            float(placement.get("rotation_deg", 0.0)),
        )
        path_d = " ".join(
            f"{'M' if idx == 0 else 'L'} {x:.3f} {sheet_h - y:.3f}"
            for idx, (x, y) in enumerate(world)
        )
        lines.append(
            f'  <path d="{path_d} Z" fill="{color(part_id)}" fill-opacity="0.68" '
            f'stroke="#1f2937" stroke-width="0.45" data-part-id="{part_id}" '
            f'data-instance-id="{placement.get("instance_id", "")}" '
            f'data-rotation-deg="{float(placement.get("rotation_deg", 0.0)):.6f}"/>'
        )
        count += 1
    lines.append(
        f'  <text x="8" y="28" font-family="Arial, sans-serif" font-size="26" fill="#111827">'
        f'{run_id} sheet {sheet_index} placed={count}</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_overview_svg(
    run_id: str,
    used: list[int],
    sheet_dims: dict[int, tuple[float, float]],
    status: str,
    placed: int,
    total: int,
) -> str:
    target_h = 600.0
    gap = 40.0
    x = gap
    boxes = []
    for sheet_index in used:
        sheet_w, sheet_h = sheet_dims[sheet_index]
        scale = target_h / sheet_h
        box_w, box_h = sheet_w * scale, sheet_h * scale
        boxes.append((x, sheet_index, box_w, box_h))
        x += box_w + gap
    width = max(x, 420.0)
    height = target_h + 95.0
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">',
        f'  <rect width="{width:.0f}" height="{height:.0f}" fill="#f8fafc"/>',
        f'  <text x="12" y="30" font-family="Arial, sans-serif" font-size="22" fill="#111827">'
        f'{run_id} status={status} placed={placed}/{total} sheets={len(used)}</text>',
    ]
    for box_x, sheet_index, box_w, box_h in boxes:
        lines.append(
            f'  <rect x="{box_x:.1f}" y="55" width="{box_w:.1f}" height="{box_h:.1f}" '
            f'fill="#e5edf6" stroke="#111827" stroke-width="1.5"/>'
        )
        lines.append(
            f'  <text x="{box_x + 8:.1f}" y="82" font-family="Arial, sans-serif" font-size="18" fill="#111827">'
            f'sheet {sheet_index}</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def svg_to_png(svg_path: Path, png_path: Path, output_width: int = 1800) -> bool:
    if not HAVE_CAIROSVG or cairosvg is None:
        return False
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=output_width)
    return True


def render_run(task_no: int, run_id: str, input_rel: str, output_rel: str) -> dict[str, Any]:
    root = ROOT / "artifacts" / "benchmarks" / f"sgh_q{task_no}"
    input_doc = load_json(root / input_rel)
    output_doc = load_json(root / output_rel)
    parts_by_id = {part["id"]: part for part in input_doc.get("parts", [])}
    sheets = expand_stock_sheets(input_doc.get("stocks", []))
    sheet_dims = {idx: (sheet["width"], sheet["height"]) for idx, sheet in enumerate(sheets)}
    placements = output_doc.get("placements", [])
    used = sorted({int(pl["sheet_index"]) for pl in placements})
    out_dir = root / "renders" / run_id
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
        sheet_placements = [pl for pl in placements if int(pl.get("sheet_index", -1)) == sheet_index]
        area = sum(polygon_area(part_outer(parts_by_id.get(str(pl["part_id"]), {}))) for pl in sheet_placements)
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
        "task": f"SGH-Q{task_no}",
        "input_path": str((root / input_rel).relative_to(ROOT)),
        "output_path": str((root / output_rel).relative_to(ROOT)),
        "render_source": "input_outer_points_plus_solver_output_anchor_placements",
        "used_sheet_count": len(used),
        "used_sheet_indices": used,
        "svg_count": svg_count,
        "png_count": png_count,
        "have_cairosvg": HAVE_CAIROSVG,
        "per_sheet": per_sheet,
        "overview_svg": str(overview_svg.relative_to(ROOT)),
        "overview_png": str(overview_png.relative_to(ROOT)) if overview_png.exists() else None,
    }
    (out_dir / "render_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> int:
    manifests = []
    for task_no, runs in RUNS.items():
        for run_id, input_rel, output_rel in runs:
            manifest = render_run(task_no, run_id, input_rel, output_rel)
            manifests.append(manifest)
            print(
                f"[render] {run_id}: sheets={manifest['used_sheet_count']} "
                f"svg={manifest['svg_count']} png={manifest['png_count']}"
            )
    if not all(m["png_count"] == m["svg_count"] for m in manifests):
        raise SystemExit("not all SVG renders have matching PNG outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
