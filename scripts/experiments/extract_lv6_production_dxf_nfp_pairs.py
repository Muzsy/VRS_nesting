#!/usr/bin/env python3
"""
Extract NFP pair fixtures from LV6 production DXF files.

Input: "/path/to/lv6 jav" directory
Output: lv6_production_dxf_pair_*.json fixtures

Strategy for LV6:
  - All DXFs have holes (largest ring = outer, rest = holes)
  - Create diverse pairs: hole-hole, different vertex counts, different hole counts
  - Target: 5-8 pairs minimum
"""

import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrs_nesting.dxf.importer import normalize_source_entities, probe_layer_rings


SRC_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("samples/real_work_dxf/0014-01H/lv6 jav")
OUT_DIR = Path("tests/fixtures/nesting_engine/nfp_pairs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


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


def get_part_from_dxf(dxf_path: Path) -> dict[str, Any]:
    """Extract part geometry from DXF using LV6 largest-ring=outer heuristic."""
    entities = normalize_source_entities(dxf_path)

    # Probe layer 0
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

    # Also probe Gravír layer
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


def parse_quantity_from_filename(filename: str):
    import re
    patterns = [r'_(\d+)db', r'(\d+)db', r'_(\d+)DB', r'(\d+)DB']
    for pat in patterns:
        m = re.search(pat, filename, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def make_fixture(part_a: dict, part_b: dict, pair_id: str, source_files: list[Path],
                  pair_type: str, quantities: dict) -> dict:
    fixture = {
        "fixture_version": "nfp_pair_fixture_v1",
        "pair_id": pair_id,
        "fixture_source": "lv6_production_dxf",
        "description": f"LV6 production DXF NFP pair from {', '.join(f.name for f in source_files)}",
        "metadata": {
            "source": "lv6_production_dxf",
            "source_files": [str(f.resolve()) for f in source_files],
            "parsed_quantities": quantities,
            "pair_type": pair_type,
            "layer_convention": "LV6: layer=0 (all rings), largest=outer, rest=holes; layer=Gravír (holes)",
            "warning": "Non-standard layer names: outer and holes on same layer 0",
        },
        "part_a": {
            "part_id": part_a.get("source_path", source_files[0].stem).split("/")[-1].rsplit(".", 1)[0],
            "geometry_level": "lv6_production_dxf",
            "outer_ring_vertex_count": len(part_a["outer_points_mm"]),
            "hole_count": len(part_a["holes_points_mm"]),
            "total_hole_vertices": part_a["total_hole_vertices"],
            "points_mm": part_a["outer_points_mm"],
            "holes_mm": part_a["holes_points_mm"],
        },
        "part_b": {
            "part_id": part_b.get("source_path", source_files[1].stem).split("/")[-1].rsplit(".", 1)[0],
            "geometry_level": "lv6_production_dxf",
            "outer_ring_vertex_count": len(part_b["outer_points_mm"]),
            "hole_count": len(part_b["holes_points_mm"]),
            "total_hole_vertices": part_b["total_hole_vertices"],
            "points_mm": part_b["outer_points_mm"],
            "holes_mm": part_b["holes_points_mm"],
        },
    }
    return fixture


def main():
    if not SRC_DIR.exists():
        print(f"ERROR: Source dir not found: {SRC_DIR}")
        sys.exit(1)

    dxf_files = sorted(SRC_DIR.glob("*.dxf"))
    print(f"Found {len(dxf_files)} DXFs in {SRC_DIR}")

    # Load all parts
    parts = []
    for dxf_path in dxf_files:
        try:
            part = get_part_from_dxf(dxf_path)
            qty = parse_quantity_from_filename(dxf_path.name)
            parts.append({
                "path": dxf_path,
                "part": part,
                "qty": qty,
                "outer_v": part["outer_vertex_count"],
                "hole_count": part["hole_count"],
                "hole_v": part["total_hole_vertices"],
            })
            print(f"  {dxf_path.name}: outer={part['outer_vertex_count']} holes={part['hole_count']} ({part['total_hole_vertices']}v) area={part['area_mm2']:.1f}mm²")
        except Exception as ex:
            print(f"  SKIP {dxf_path.name}: {ex}")

    if len(parts) < 2:
        print("Not enough valid DXFs to create pairs!")
        sys.exit(1)

    # Sort by complexity for pair selection
    # Strategy: pick diverse pairs covering:
    # 1. Most complex with different complexity
    # 2. Mid-complexity pairs
    # 3. Simple vs complex
    parts_sorted = sorted(parts, key=lambda x: (x["outer_v"], x["hole_count"]), reverse=True)

    print(f"\nParts sorted by complexity (outer_v desc):")
    for p in parts_sorted:
        print(f"  {p['path'].name}: outer={p['outer_v']} holes={p['hole_count']}({p['hole_v']}v)")

    fixtures = []
    fixture_num = 1

    # Pair selection strategy:
    # Top-complex vs rest
    # Mid-complexity pairs
    # Ensure variety in hole count combinations

    used_pairs = set()

    # Pair 1: most complex vs simplest
    p1 = parts_sorted[0]
    p11 = parts_sorted[-1]
    pair_id = f"lv6_production_dxf_pair_{fixture_num:02d}"
    fixture = make_fixture(p1["part"], p11["part"], pair_id, [p1["path"], p11["path"]],
                           "hole_hole_complex", {p1["path"].name: p1["qty"], p11["path"].name: p11["qty"]})
    out_path = OUT_DIR / f"{pair_id}.json"
    out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nCreated: {pair_id} = {p1['path'].name} (outer={p1['outer_v']}, holes={p1['hole_count']}) vs {p11['path'].name} (outer={p11['outer_v']}, holes={p11['hole_count']})")
    fixtures.append((pair_id, fixture, out_path))
    used_pairs.add(frozenset([p1["path"].name, p11["path"].name]))
    fixture_num += 1

    # Pair 2: 2nd most complex vs 2nd simplest
    p2 = parts_sorted[1]
    p10 = parts_sorted[-2]
    if frozenset([p2["path"].name, p10["path"].name]) not in used_pairs:
        pair_id = f"lv6_production_dxf_pair_{fixture_num:02d}"
        fixture = make_fixture(p2["part"], p10["part"], pair_id, [p2["path"], p10["path"]],
                               "hole_hole_complex", {p2["path"].name: p2["qty"], p10["path"].name: p10["qty"]})
        out_path = OUT_DIR / f"{pair_id}.json"
        out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Created: {pair_id} = {p2['path'].name} vs {p10['path'].name}")
        fixtures.append((pair_id, fixture, out_path))
        used_pairs.add(frozenset([p2["path"].name, p10["path"].name]))
        fixture_num += 1

    # Pair 3: 3rd most complex vs 3rd simplest
    p3 = parts_sorted[2]
    p9 = parts_sorted[-3]
    if frozenset([p3["path"].name, p9["path"].name]) not in used_pairs:
        pair_id = f"lv6_production_dxf_pair_{fixture_num:02d}"
        fixture = make_fixture(p3["part"], p9["part"], pair_id, [p3["path"], p9["path"]],
                               "hole_hole_complex", {p3["path"].name: p3["qty"], p9["path"].name: p9["qty"]})
        out_path = OUT_DIR / f"{pair_id}.json"
        out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Created: {pair_id} = {p3['path'].name} vs {p9['path'].name}")
        fixtures.append((pair_id, fixture, out_path))
        used_pairs.add(frozenset([p3["path"].name, p9["path"].name]))
        fixture_num += 1

    # Pair 4: adjacent mid-complexity (5 vs 6 in sorted list)
    p5 = parts_sorted[4]
    p6 = parts_sorted[5]
    if frozenset([p5["path"].name, p6["path"].name]) not in used_pairs:
        pair_id = f"lv6_production_dxf_pair_{fixture_num:02d}"
        fixture = make_fixture(p5["part"], p6["part"], pair_id, [p5["path"], p6["path"]],
                               "hole_hole_mid", {p5["path"].name: p5["qty"], p6["path"].name: p6["qty"]})
        out_path = OUT_DIR / f"{pair_id}.json"
        out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Created: {pair_id} = {p5['path'].name} vs {p6['path'].name}")
        fixtures.append((pair_id, fixture, out_path))
        used_pairs.add(frozenset([p5["path"].name, p6["path"].name]))
        fixture_num += 1

    # Pair 5: 4th vs 8th (varied complexity)
    p4 = parts_sorted[3]
    p8 = parts_sorted[7]
    if frozenset([p4["path"].name, p8["path"].name]) not in used_pairs:
        pair_id = f"lv6_production_dxf_pair_{fixture_num:02d}"
        fixture = make_fixture(p4["part"], p8["part"], pair_id, [p4["path"], p8["path"]],
                               "hole_hole_varied", {p4["path"].name: p4["qty"], p8["path"].name: p8["qty"]})
        out_path = OUT_DIR / f"{pair_id}.json"
        out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Created: {pair_id} = {p4['path'].name} vs {p8['path'].name}")
        fixtures.append((pair_id, fixture, out_path))
        used_pairs.add(frozenset([p4["path"].name, p8["path"].name]))
        fixture_num += 1

    # If we have more valid DXFs, create a few more pairs
    # Pair 6: most holes vs fewest holes
    by_holes = sorted(parts, key=lambda x: x["hole_count"], reverse=True)
    ph_max = by_holes[0]
    ph_min = by_holes[-1]
    if frozenset([ph_max["path"].name, ph_min["path"].name]) not in used_pairs:
        pair_id = f"lv6_production_dxf_pair_{fixture_num:02d}"
        fixture = make_fixture(ph_max["part"], ph_min["part"], pair_id, [ph_max["path"], ph_min["path"]],
                               "many_holes_vs_few_holes", {ph_max["path"].name: ph_max["qty"], ph_min["path"].name: ph_min["qty"]})
        out_path = OUT_DIR / f"{pair_id}.json"
        out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Created: {pair_id} = {ph_max['path'].name} (holes={ph_max['hole_count']}) vs {ph_min['path'].name} (holes={ph_min['hole_count']})")
        fixtures.append((pair_id, fixture, out_path))
        used_pairs.add(frozenset([ph_max["path"].name, ph_min["path"].name]))
        fixture_num += 1

    # Pair 7: 2nd most holes vs 2nd fewest
    if len(by_holes) > 2:
        ph2_max = by_holes[1]
        ph2_min = by_holes[-2]
        if frozenset([ph2_max["path"].name, ph2_min["path"].name]) not in used_pairs:
            pair_id = f"lv6_production_dxf_pair_{fixture_num:02d}"
            fixture = make_fixture(ph2_max["part"], ph2_min["part"], pair_id, [ph2_max["path"], ph2_min["path"]],
                                   "many_holes_vs_few_holes", {ph2_max["path"].name: ph2_max["qty"], ph2_min["path"].name: ph2_min["qty"]})
            out_path = OUT_DIR / f"{pair_id}.json"
            out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Created: {pair_id} = {ph2_max['path'].name} (holes={ph2_max['hole_count']}) vs {ph2_min['path'].name} (holes={ph2_min['hole_count']})")
            fixtures.append((pair_id, fixture, out_path))
            fixture_num += 1

    print(f"\nTotal fixtures: {len(fixtures)}")
    for pid, f, _ in fixtures:
        pa = f["part_a"]
        pb = f["part_b"]
        print(f"  {pid}: {pa['part_id']}(outer={pa['outer_ring_vertex_count']},holes={pa['hole_count']}) vs "
              f"{pb['part_id']}(outer={pb['outer_ring_vertex_count']},holes={pb['hole_count']})")

    return fixtures


if __name__ == "__main__":
    main()
