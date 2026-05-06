#!/usr/bin/env python3
"""
Build LV6 production part list with quantities from filenames.

Input: "/home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv6 jav"
Output:
  tmp/reports/nfp_cgal_probe/lv6_production_part_list.json
  tmp/reports/nfp_cgal_probe/lv6_production_part_list.md
"""

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrs_nesting.dxf.importer import normalize_source_entities, probe_layer_rings


SRC_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("samples/real_work_dxf/0014-01H/lv6 jav")
OUT_DIR = Path("tmp/reports/nfp_cgal_probe")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_area(pts):
    if len(pts) < 3:
        return 0.0
    area = 0.0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return abs(area) / 2.0


def compute_bbox(pts):
    if not pts:
        return 0, 0, 0, 0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def parse_quantity_from_filename(filename: str):
    patterns = [r'_(\d+)db', r'(\d+)db', r'_(\d+)DB', r'(\d+)DB']
    for pat in patterns:
        m = re.search(pat, filename, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def ring_area(pts):
    if len(pts) < 3:
        return 0.0
    a = 0.0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        a += pts[i][0] * pts[j][1]
        a -= pts[j][0] * pts[i][1]
    return abs(a) / 2.0


def get_part_from_dxf(dxf_path: Path):
    entities = normalize_source_entities(dxf_path)

    # Probe layer 0 — LV6 convention: largest ring = outer, rest = holes
    probe = probe_layer_rings(entities, layer="0")
    rings = probe.get("rings", [])
    hard_error = probe.get("hard_error")

    if hard_error or not rings:
        raise RuntimeError(f"Cannot probe {dxf_path.name}: {hard_error or 'no rings'}")

    # Pick largest ring as outer
    ring_area_pairs = [(i, ring_area(r), r) for i, r in enumerate(rings)]
    ring_area_pairs.sort(key=lambda x: x[1], reverse=True)

    outer_idx, outer_area, outer_pts = ring_area_pairs[0]
    hole_rings = [r for _, _, r in ring_area_pairs[1:]]

    # Also probe Gravir layer
    gravir_probe = probe_layer_rings(entities, layer="Gravír")
    gravir_rings = gravir_probe.get("rings", [])
    all_holes = hole_rings + gravir_rings

    return {
        "outer_points_mm": outer_pts,
        "holes_points_mm": all_holes,
        "source_path": str(dxf_path.resolve()),
        "outer_vertex_count": len(outer_pts),
        "hole_count": len(all_holes),
        "total_hole_vertices": sum(len(r) for r in all_holes),
        "area_mm2": round(outer_area, 3),
    }


def main():
    if not SRC_DIR.exists():
        print(f"ERROR: Source directory not found: {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    dxf_files = sorted(SRC_DIR.glob("*.dxf"))
    if not dxf_files:
        print(f"ERROR: No .dxf files found in {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(dxf_files)} DXF files in {SRC_DIR}")

    parts = []
    total_qty = 0
    total_area = 0.0

    for dxf_path in dxf_files:
        try:
            part = get_part_from_dxf(dxf_path)
            qty = parse_quantity_from_filename(dxf_path.name)
            if qty is None:
                print(f"  WARN: Could not parse quantity from {dxf_path.name}, skipping")
                continue

            bbox = compute_bbox(part["outer_points_mm"])
            bbox_w = round(bbox[2] - bbox[0], 6)
            bbox_h = round(bbox[3] - bbox[1], 6)

            parts.append({
                "part_id": dxf_path.stem.strip(),
                "source_file": dxf_path.name,
                "source_path": str(dxf_path.resolve()),
                "quantity": qty,
                "import_status": "accepted_for_import",  # T05g: all 11 are importable
                "outer_points_mm": part["outer_points_mm"],
                "holes_points_mm": part["holes_points_mm"],
                "outer_vertex_count": part["outer_vertex_count"],
                "hole_count": part["hole_count"],
                "total_hole_vertices": part["total_hole_vertices"],
                "area_mm2": part["area_mm2"],
                "bbox_w_mm": bbox_w,
                "bbox_h_mm": bbox_h,
                "bbox_min_x": round(bbox[0], 6),
                "bbox_min_y": round(bbox[1], 6),
                "bbox_max_x": round(bbox[2], 6),
                "bbox_max_y": round(bbox[3], 6),
            })
            total_qty += qty
            total_area += part["area_mm2"] * qty
            print(f"  {dxf_path.name}: qty={qty}, outer={part['outer_vertex_count']}, "
                  f"holes={part['hole_count']}, area={part['area_mm2']:.1f}mm²")
        except Exception as ex:
            print(f"  SKIP {dxf_path.name}: {ex}")

    # Sort by area descending for nesting order
    parts.sort(key=lambda p: p["area_mm2"], reverse=True)

    result = {
        "part_list_version": "lv6_production_part_list_v1",
        "source_dir": str(SRC_DIR.resolve()),
        "sheet_config": {
            "sheet_width_mm": 1500.0,
            "sheet_height_mm": 3000.0,
            "spacing_mm": 2.0,
            "rotations": [0, 90, 180, 270],
            "utilization_target": "preview",
        },
        "summary": {
            "total_part_types": len(parts),
            "total_quantity": total_qty,
            "total_area_mm2": round(total_area, 3),
            "accepted_count": len(parts),
            "review_required_count": 0,
            "rejected_count": 0,
        },
        "parts": parts,
    }

    out_json = OUT_DIR / "lv6_production_part_list.json"
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved: {out_json}")

    # Markdown summary
    md_lines = [
        "# LV6 Production Part List",
        "",
        f"**Source:** `{SRC_DIR}`",
        f"**Sheet:** 1500 x 3000 mm | **Spacing:** 2 mm | **Rotations:** 0/90/180/270",
        "",
        f"**Total part types:** {len(parts)}",
        f"**Total quantity:** {total_qty}",
        f"**Total area:** {total_area:.1f} mm²",
        "",
        "| # | Part ID | Qty | Outer verts | Holes | Hole verts | Area mm² | BBox W×H mm |",
        "|--:|---------|----:|------------:|------:|-----------:|----------:|-------------|",
    ]

    for i, p in enumerate(parts, 1):
        md_lines.append(
            f"| {i} | {p['part_id']} | {p['quantity']} | {p['outer_vertex_count']} | "
            f"{p['hole_count']} | {p['total_hole_vertices']} | {p['area_mm2']:.1f} | "
            f"{p['bbox_w_mm']:.1f} × {p['bbox_h_mm']:.1f} |"
        )

    md_lines.append("")
    total_sheet_area = 1500.0 * 3000.0
    md_lines.append(f"**Sheet area:** {total_sheet_area:.0f} mm²")
    md_lines.append(f"**Theoretical min sheets (util=%):** {total_area / total_sheet_area:.2%}")

    out_md = OUT_DIR / "lv6_production_part_list.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Saved: {out_md}")

    print(f"\nSummary:")
    print(f"  Part types: {len(parts)}")
    print(f"  Total quantity: {total_qty}")
    print(f"  Total area: {total_area:.1f} mm²")
    print(f"  Sheet: 1500 x 3000 mm")
    print(f"  Theoretical utilization: {total_area / total_sheet_area:.1%}")

    return result


if __name__ == "__main__":
    main()
