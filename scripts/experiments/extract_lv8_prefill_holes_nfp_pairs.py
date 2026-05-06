#!/usr/bin/env python3
"""
Extract LV8 pre-fill holes NFP pair fixtures.

Reads the raw LV8 input (before cavity_prepack) which contains
outer_points_mm + holes_points_mm for each part.

Creates NFP pair fixtures with real hole geometry.

Output: tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_prefill_holes_*.json
"""

import argparse
import json
import math
import sys
from pathlib import Path

INPUT_PATH = Path("tmp/ne2_input_lv8jav.json")
OUTPUT_DIR = Path("tests/fixtures/nesting_engine/nfp_pairs")


def to_points(raw):
    if not isinstance(raw, list):
        return []
    out = []
    for pt in raw:
        if not isinstance(pt, list) or len(pt) != 2:
            continue
        try:
            x, y = float(pt[0]), float(pt[1])
        except (TypeError, ValueError):
            continue
        out.append([x, y])
    return out


def compute_area(pts):
    """Shoelace area in mm^2."""
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


def make_fixture(part_a_data, part_b_data, pair_id, source):
    """Build nfp_pair_fixture_v1 JSON."""
    fixture = {
        "fixture_version": "nfp_pair_fixture_v1",
        "pair_id": pair_id,
        "fixture_source": source,
        "description": f"Real LV8 pre-fill holes pair: {part_a_data['id']} vs {part_b_data['id']}",
        "metadata": {
            "source": source,
            "cavity_prepack_aware": False,
            "note": "Uses pre-fill geometry (outer_points_mm + holes_points_mm) BEFORE cavity_prepack solidification"
        },
        "part_a": {
            "part_id": part_a_data["id"],
            "geometry_level": "real_lv8_prefill",
            "outer_ring_vertex_count": len(part_a_data["outer_points_mm"]),
            "points_mm": part_a_data["outer_points_mm"],
            "holes_mm": part_a_data["holes_points_mm"],
        },
        "part_b": {
            "part_id": part_b_data["id"],
            "geometry_level": "real_lv8_prefill",
            "outer_ring_vertex_count": len(part_b_data["outer_points_mm"]),
            "points_mm": part_b_data["outer_points_mm"],
            "holes_mm": part_b_data["holes_points_mm"],
        },
    }
    return fixture


def summarize_part(p):
    outer = p.get("outer_points_mm", [])
    holes = p.get("holes_points_mm", [])
    total_hole_v = sum(len(h) for h in holes)
    area = compute_area(outer)
    bbox = compute_bbox(outer)
    return {
        "id": p.get("id", "?"),
        "outer_pts": len(outer),
        "hole_count": len(holes),
        "total_hole_v": total_hole_v,
        "area_mm2": round(area, 2),
        "bbox": bbox,
    }


def main():
    if not INPUT_PATH.exists():
        print(f"ERROR: {INPUT_PATH} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    raw_parts = data.get("parts", [])
    if not raw_parts:
        print("ERROR: no parts in input", file=sys.stderr)
        sys.exit(1)

    # Load all parts
    parts = []
    for item in raw_parts:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        if not pid:
            continue
        outer = to_points(item.get("outer_points_mm", []))
        holes = [to_points(h) for h in item.get("holes_points_mm", []) if to_points(h)]
        parts.append({"id": pid, "outer_points_mm": outer, "holes_points_mm": holes})

    if not parts:
        print("ERROR: no valid parts found", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(parts)} parts")
    print()
    print("Parts with holes:")
    holed = [p for p in parts if p["holes_points_mm"]]
    for p in holed:
        s = summarize_part(p)
        print(f"  {s['id']}: outer={s['outer_pts']}, holes={s['hole_count']}, "
              f"hole_v={s['total_hole_v']}, area={s['area_mm2']}mm²")

    print()

    # Select pairs: prioritize Lv8_11612 (most holes) as part_a
    if not holed:
        print("ERROR: no parts with holes found", file=sys.stderr)
        sys.exit(1)

    # Sort by hole count descending
    holed_sorted = sorted(holed, key=lambda p: -len(p["holes_points_mm"]))

    pairs = []

    # Pair 1: Lv8_11612_6db vs Lv8_07921_50db (most holes vs second most)
    p11612 = next((p for p in holed_sorted if p["id"] == "Lv8_11612_6db"), None)
    p07921 = next((p for p in holed_sorted if p["id"] == "Lv8_07921_50db"), None)
    p15435 = next((p for p in holed_sorted if p["id"] == "Lv8_15435_10db"), None)
    p07920 = next((p for p in holed_sorted if p["id"] == "Lv8_07920_50db"), None)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fixture_num = 1

    if p11612 and p07921:
        f = make_fixture(p11612, p07921, "lv8_pair_prefill_holes_01", "real_lv8_prefill_holes")
        out_path = OUTPUT_DIR / "lv8_pair_prefill_holes_01.json"
        out_path.write_text(json.dumps(f, indent=2), encoding="utf-8")
        print(f"Created: {out_path} ({p11612['id']} vs {p07921['id']})")
        pairs.append(("lv8_pair_prefill_holes_01", f))

    if p11612 and p15435 and p07921 != p15435:
        f = make_fixture(p11612, p15435, "lv8_pair_prefill_holes_02", "real_lv8_prefill_holes")
        out_path = OUTPUT_DIR / "lv8_pair_prefill_holes_02.json"
        out_path.write_text(json.dumps(f, indent=2), encoding="utf-8")
        print(f"Created: {out_path} ({p11612['id']} vs {p15435['id']})")
        pairs.append(("lv8_pair_prefill_holes_02", f))

    if p07921 and p15435:
        f = make_fixture(p07921, p15435, "lv8_pair_prefill_holes_03", "real_lv8_prefill_holes")
        out_path = OUTPUT_DIR / "lv8_pair_prefill_holes_03.json"
        out_path.write_text(json.dumps(f, indent=2), encoding="utf-8")
        print(f"Created: {out_path} ({p07921['id']} vs {p15435['id']})")
        pairs.append(("lv8_pair_prefill_holes_03", f))

    print(f"\nTotal fixtures created: {len(pairs)}")
    for pid, fixture in pairs:
        pa = fixture["part_a"]
        pb = fixture["part_b"]
        print(f"  {pid}:")
        print(f"    part_a: {pa['part_id']} — outer={len(pa['points_mm'])}, holes={len(pa['holes_mm'])}")
        print(f"    part_b: {pb['part_id']} — outer={len(pb['points_mm'])}, holes={len(pb['holes_mm'])}")


if __name__ == "__main__":
    main()
