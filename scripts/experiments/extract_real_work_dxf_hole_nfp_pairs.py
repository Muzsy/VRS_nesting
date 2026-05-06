#!/usr/bin/env python3
"""
Extract NFP pair fixtures from real_work_dxf DXF files.

Uses the actual DXF layer conventions found in samples/real_work_dxf/0014-01H/lv8jav:
- CUT_OUTER equivalent: layer "0"
- CUT_INNER equivalent: layer "Gravír"

Creates real_work_dxf_holes_pair_*.json fixtures.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrs_nesting.dxf.importer import normalize_source_entities, probe_layer_rings, import_part_raw


SRC_DIR = Path("samples/real_work_dxf/0014-01H/lv8jav")
OUT_DIR = Path("tests/fixtures/nesting_engine/nfp_pairs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

INVENTORY_PATH = Path("tmp/reports/nfp_cgal_probe/real_work_dxf_hole_inventory.json")


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


def load_inventory():
    if INVENTORY_PATH.exists():
        return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    return None


def get_part_raw(dxf_path, *, outer_layer="0", inner_layer="Gravír"):
    """Extract PartRaw from DXF using non-standard layer names."""
    entities = normalize_source_entities(dxf_path)

    # Probe outer
    outer_probe = probe_layer_rings(entities, layer=outer_layer)
    outer_rings = outer_probe.get("rings", [])

    if not outer_rings:
        raise RuntimeError(f"No outer rings in {dxf_path.name} on layer {outer_layer}")

    # Probe inner
    inner_probe = probe_layer_rings(entities, layer=inner_layer)
    inner_rings = inner_probe.get("rings", [])

    return {
        "outer_points_mm": outer_rings[0],
        "holes_points_mm": inner_rings,
        "source_path": str(dxf_path.resolve()),
    }


def make_fixture(part_a, part_b, pair_id, source_files):
    fixture = {
        "fixture_version": "nfp_pair_fixture_v1",
        "pair_id": pair_id,
        "fixture_source": "real_work_dxf_holes",
        "description": f"Real work DXF NFP pair from {', '.join(f.name for f in source_files)}",
        "metadata": {
            "source": "real_work_dxf_holes",
            "source_files": [str(f.resolve()) for f in source_files],
            "cavity_prepack_aware": False,
            "note": "Uses raw DXF import with non-standard layer names: outer='0', inner='Gravír'"
        },
        "part_a": {
            "part_id": part_a.get("part_id", source_files[0].stem if source_files else "?"),
            "geometry_level": "real_work_dxf",
            "outer_ring_vertex_count": len(part_a["outer_points_mm"]),
            "points_mm": part_a["outer_points_mm"],
            "holes_mm": part_a["holes_points_mm"],
        },
        "part_b": {
            "part_id": part_b.get("part_id", source_files[1].stem if len(source_files) > 1 else "?"),
            "geometry_level": "real_work_dxf",
            "outer_ring_vertex_count": len(part_b["outer_points_mm"]),
            "points_mm": part_b["outer_points_mm"],
            "holes_mm": part_b["holes_points_mm"],
        },
    }
    return fixture


def main():
    # Load inventory
    inventory = load_inventory()

    # Find hole-bearing DXFs from inventory
    holed_dxfs = []
    outer_only_dxfs = []
    failed_dxfs = []

    if inventory:
        for r in inventory.get("results", []):
            fname = r["file_name"]
            dxf_path = SRC_DIR / fname
            if r["import_category"] == "IMPORT_OK_WITH_HOLES":
                holed_dxfs.append((dxf_path, r))
            elif r["import_category"] == "IMPORT_OK_OUTER_ONLY":
                outer_only_dxfs.append((dxf_path, r))
            elif r["import_category"] in ("IMPORT_FAILED", "INVALID_GEOMETRY"):
                failed_dxfs.append((dxf_path, r))
    else:
        # Fallback: probe all DXFs directly
        for dxf_path in sorted(SRC_DIR.glob("*.dxf")):
            try:
                part = get_part_raw(dxf_path)
                if part["holes_points_mm"]:
                    holed_dxfs.append((dxf_path, None))
                else:
                    outer_only_dxfs.append((dxf_path, None))
            except Exception as ex:
                failed_dxfs.append((dxf_path, str(ex)))

    print(f"Holed DXFs: {len(holed_dxfs)}")
    print(f"Outer-only DXFs: {len(outer_only_dxfs)}")
    print(f"Failed: {len(failed_dxfs)}")

    # Print holed details
    if holed_dxfs:
        print("\nHoled DXFs:")
        for dxf_path, r in holed_dxfs:
            if r:
                print(f"  {dxf_path.name}: outer={r['outer_vertex_count']}, holes={r['hole_count']}, hole_v={r['total_hole_vertices']}")
            else:
                print(f"  {dxf_path.name}")

    # Print complex outer-only (high vertex count)
    complex_outer = [(p, r) for p, r in outer_only_dxfs if r and r["outer_vertex_count"] >= 100] if r else []
    if complex_outer:
        print(f"\nComplex outer-only (>=100 verts): {len(complex_outer)}")
        for dxf_path, r in complex_outer:
            print(f"  {dxf_path.name}: outer={r['outer_vertex_count']}")

    # Build pairs
    fixtures = []
    fixture_num = 1

    # Strategy:
    # 1. Pair holed DXFs with each other (complex-holes)
    # 2. Pair holed with complex outer-only (hole-complex)
    # 3. Fill remaining with outer-only pairs (complex-complex)

    # Pairs of holed with holed
    for i in range(len(holed_dxfs)):
        for j in range(i + 1, len(holed_dxfs)):
            pa_path, _ = holed_dxfs[i]
            pb_path, _ = holed_dxfs[j]
            pair_id = f"real_work_dxf_holes_pair_{fixture_num:02d}"

            try:
                pa = get_part_raw(pa_path)
                pb = get_part_raw(pb_path)
                fixture = make_fixture(pa, pb, pair_id, [pa_path, pb_path])
                out_path = OUT_DIR / f"{pair_id}.json"
                out_path.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
                print(f"Created: {out_path} ({pa_path.name} vs {pb_path.name})")
                fixtures.append((pair_id, fixture, "complex_with_holes"))
                fixture_num += 1
            except Exception as ex:
                print(f"FAILED {pa_path.name} vs {pb_path.name}: {ex}")

    # Pairs of holed with complex outer-only
    complex_paths = [p for p, r in outer_only_dxfs if r and r["outer_vertex_count"] >= 100]
    for h_path, _ in holed_dxfs:
        for c_path in complex_paths[:2]:  # max 2 per holed
            if h_path == c_path:
                continue
            pair_id = f"real_work_dxf_holes_pair_{fixture_num:02d}"
            try:
                pa = get_part_raw(h_path)
                pb = get_part_raw(c_path)
                fixture = make_fixture(pa, pb, pair_id, [h_path, c_path])
                out_path = OUT_DIR / f"{pair_id}.json"
                out_path.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
                print(f"Created: {out_path} ({h_path.name} vs {c_path.name}) [hole-complex]")
                fixtures.append((pair_id, fixture, "hole_complex"))
                fixture_num += 1
            except Exception as ex:
                print(f"FAILED {h_path.name} vs {c_path.name}: {ex}")

    # Remaining complex-complex outer-only
    used = set()
    for i, (pa_path, pa_r) in enumerate(complex_outer):
        for pb_path, pb_r in complex_outer[i+1:]:
            if pa_path == pb_path:
                continue
            pair_id = f"real_work_dxf_holes_pair_{fixture_num:02d}"
            try:
                pa = get_part_raw(pa_path)
                pb = get_part_raw(pb_path)
                fixture = make_fixture(pa, pb, pair_id, [pa_path, pb_path])
                out_path = OUT_DIR / f"{pair_id}.json"
                out_path.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
                print(f"Created: {out_path} ({pa_path.name} vs {pb_path.name}) [complex-complex outer-only]")
                fixtures.append((pair_id, fixture, "complex_outer_only"))
                fixture_num += 1
            except Exception as ex:
                print(f"FAILED {pa_path.name} vs {pb_path.name}: {ex}")

    print(f"\nTotal fixtures created: {len(fixtures)}")
    for pid, f, kind in fixtures:
        pa = f["part_a"]
        pb = f["part_b"]
        print(f"  {pid} [{kind}]: {pa['part_id']}(outer={len(pa['points_mm'])},holes={len(pa['holes_mm'])}) vs "
              f"{pb['part_id']}(outer={len(pb['points_mm'])},holes={len(pb['holes_mm'])})")

    return fixtures


if __name__ == "__main__":
    main()
