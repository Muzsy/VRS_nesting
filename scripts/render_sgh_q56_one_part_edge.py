#!/usr/bin/env python3
"""SGH-Q56 — render one-part sheet-edge placements (sheet, margin, placed offset contour, target
edge, aligned extremum, rotation) to PNG for visual verification."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
Q56 = ROOT / "artifacts/benchmarks/sgh_q56"


def render(jpath: Path) -> Path:
    d = json.loads(jpath.read_text())
    sw, sh = d["sheet_width"], d["sheet_height"]
    margin = d["margin_mm"]
    edge = d["target_sheet_edge"]
    contour = d["world_contour"]

    scale = 360.0 / sw  # fit width to 360 px
    pad = 40
    W = int(sw * scale) + 2 * pad
    H = int(sh * scale) + 2 * pad
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)

    def tx(x: float, y: float) -> tuple[float, float]:
        # world (0,0) bottom-left -> image top-left, y flipped
        return (pad + x * scale, pad + (sh - y) * scale)

    # sheet outline
    dr.rectangle([tx(0, sh), tx(sw, 0)], outline="black", width=2)
    # margin line (inset rectangle)
    dr.rectangle([tx(margin, sh - margin), tx(sw - margin, margin)], outline=(150, 150, 150), width=1)

    # placed offset contour (filled translucent + outline)
    poly = [tx(px, py) for px, py in contour]
    dr.polygon(poly, fill=(180, 210, 255), outline=(0, 80, 200))

    # highlight target sheet edge (thick red) + the margin line it aligns to (dashed green)
    if edge == "left":
        dr.line([tx(0, 0), tx(0, sh)], fill="red", width=4)
        dr.line([tx(margin, 0), tx(margin, sh)], fill=(0, 160, 0), width=2)
        cx = d["rotated_offset_min_x"] + d["translation_x"]
        dr.line([tx(cx, 0), tx(cx, sh)], fill=(0, 160, 0), width=1)
    elif edge == "right":
        dr.line([tx(sw, 0), tx(sw, sh)], fill="red", width=4)
        dr.line([tx(sw - margin, 0), tx(sw - margin, sh)], fill=(0, 160, 0), width=2)
    elif edge == "bottom":
        dr.line([tx(0, 0), tx(sw, 0)], fill="red", width=4)
        dr.line([tx(0, margin), tx(sw, margin)], fill=(0, 160, 0), width=2)
    elif edge == "top":
        dr.line([tx(0, sh), tx(sw, sh)], fill="red", width=4)
        dr.line([tx(0, sh - margin), tx(sw, sh - margin)], fill=(0, 160, 0), width=2)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    lines = [
        f"part: {d['part_id']}",
        f"target edge: {edge} (red)  margin line: green",
        f"sel edge angle: {d['selected_part_edge_angle_deg']:.3f} deg  len {d['selected_part_edge_length']:.1f}",
        f"rotation: {d['rotation_after_deg']:.3f} deg (continuous={d['continuous_rotation']})",
        f"margin_dist: {d['distance_to_target_margin_line']:.5f} mm",
        f"boundary_clear: {d['boundary_clear']}  accepted: {d['accepted_sheet_edge_alignment']}",
    ]
    for i, ln in enumerate(lines):
        dr.text((6, 4 + i * 12), ln, fill="black", font=font)

    out = jpath.with_suffix(".png")
    img.save(out)
    return out


def main() -> int:
    files = sorted(Q56.glob("placement_*.json"))
    if not files:
        print("no placement json found; run the Q56 test first")
        return 2
    for f in files:
        out = render(f)
        print(f"rendered {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
