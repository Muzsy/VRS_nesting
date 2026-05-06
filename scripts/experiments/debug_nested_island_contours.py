#!/usr/bin/env python3
"""
Debug script: dump nested island topology for the two problematic DXFs.

Usage:
    python scripts/experiments/debug_nested_island_contours.py \
        "/path/to/Lv6_08089_1db REV2 MÓDOSÍTOTT!.dxf" \
        "/path/to/Lv8_11612_6db REV3.dxf"
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles


def compute_containment_depth(contour_key, contained_by_map, depth_cache=None):
    """Compute the nesting depth of a contour (0 = top-level)."""
    if depth_cache is None:
        depth_cache = {}
    if contour_key in depth_cache:
        return depth_cache[contour_key]
    parents = contained_by_map.get(contour_key, [])
    if not parents:
        depth = 0
    else:
        depth = 1 + max(
            compute_containment_depth(p, contained_by_map, depth_cache)
            for p in parents
        )
    depth_cache[contour_key] = depth
    return depth


def dump_topology(dxf_path: Path):
    """Dump full contour topology with containment depth."""
    print(f"\n{'='*70}")
    print(f"FILE: {dxf_path.name}")
    print(f"{'='*70}")

    inspect_result = inspect_dxf_source(str(dxf_path))
    role_result = resolve_dxf_roles(inspect_result, {})

    # Build containment maps
    outer_like = inspect_result.get("outer_like_candidates", [])
    inner_like = inspect_result.get("inner_like_candidates", [])

    contains_map = {}
    for item in outer_like:
        key = (str(item["layer"]), int(item["ring_index"]))
        refs = [
            (str(r["layer"]), int(r["ring_index"]))
            for r in item.get("contains_ring_references", [])
        ]
        contains_map[key] = refs

    contained_by_map = {}
    for item in inner_like:
        key = (str(item["layer"]), int(item["ring_index"]))
        refs = [
            (str(r["layer"]), int(r["ring_index"]))
            for r in item.get("contained_by_ring_references", [])
        ]
        contained_by_map[key] = refs

    contour_candidates = inspect_result.get("contour_candidates", [])
    contour_role_assignments = role_result.get("contour_role_assignments", [])
    review_required = role_result.get("review_required_candidates", [])

    # Index assignments by key
    assignment_by_key = {}
    for a in contour_role_assignments:
        key = (str(a["layer"]), int(a["ring_index"]))
        assignment_by_key[key] = a

    # Compute depth for all contours
    all_keys = set(contains_map.keys()) | set(contained_by_map.keys())
    depth_cache = {}
    for key in all_keys:
        compute_containment_depth(key, contained_by_map, depth_cache)

    # Also compute depth for contour candidates
    candidate_depth = {}
    for c in contour_candidates:
        key = (str(c["layer"]), int(c["ring_index"]))
        candidate_depth[key] = compute_containment_depth(key, contained_by_map, depth_cache)

    # Print review_required
    print("\nReview required candidates:")
    for r in review_required:
        print(f"  family={r['family']} layer={r.get('layer')} ring={r.get('ring_index')} severity={r['severity']}")

    # Print contour table
    print("\nContour topology:")
    print(f"  {'Key':<20} {'Depth':<6} {'Role':<20} {'Decision':<35} {'Area':<12}")
    print(f"  {'-'*20} {'-'*6} {'-'*20} {'-'*35} {'-'*12}")

    rows = []
    for c in contour_candidates:
        key = (str(c["layer"]), int(c["ring_index"]))
        depth = candidate_depth.get(key, -1)
        assignment = assignment_by_key.get(key, {})
        role = assignment.get("canonical_role", "UNASSIGNED")
        decision = assignment.get("decision_source", "")
        area = c.get("area_abs_mm2", 0.0)
        rows.append({
            "key": key,
            "depth": depth,
            "role": role,
            "decision": decision,
            "area": area,
            "contour_id": c.get("contour_id", ""),
            "layer": str(c["layer"]),
            "ring_index": int(c["ring_index"]),
            "bbox": c.get("bbox"),
        })

    # Sort by depth then layer then ring
    rows.sort(key=lambda r: (r["depth"], r["layer"], r["ring_index"]))

    for row in rows:
        key_str = f"{row['layer']}:{row['ring_index']}"
        print(f"  {key_str:<20} {row['depth']:<6} {row['role']:<20} {row['decision']:<35} {row['area']:.2f}")

    # Summary by depth
    print("\nContour count by depth:")
    from collections import Counter
    depth_counts = Counter(r["depth"] for r in rows)
    for depth in sorted(depth_counts.keys()):
        print(f"  depth={depth}: {depth_counts[depth]} contours")

    # Build JSON output
    topology = {
        "file_name": dxf_path.name,
        "source_path": str(dxf_path),
        "total_contours": len(rows),
        "review_required": [
            {"family": r["family"], "layer": r.get("layer"), "ring_index": r.get("ring_index"), "severity": r["severity"]}
            for r in review_required
        ],
        "contours": [
            {
                "contour_id": row["contour_id"],
                "layer": row["layer"],
                "ring_index": row["ring_index"],
                "containment_depth": row["depth"],
                "area_abs_mm2": row["area"],
                "bbox": row["bbox"],
                "proposed_role": row["role"],
                "decision_source": row["decision"],
                "contained_by": [str(p) for p in contained_by_map.get(row["key"], [])],
                "contains": [str(p) for p in contains_map.get(row["key"], [])],
            }
            for row in rows
        ],
        "depth_distribution": {str(k): v for k, v in depth_counts.items()},
    }
    return topology


def main():
    if len(sys.argv) < 3:
        print("Usage: debug_nested_island_contours.py <lv6_dxf> <lv8_dxf>")
        sys.exit(1)

    lv6_path = Path(sys.argv[1])
    lv8_path = Path(sys.argv[2])

    out_dir = Path("tmp/reports/nfp_cgal_probe")
    out_dir.mkdir(parents=True, exist_ok=True)

    lv6_topology = dump_topology(lv6_path)
    lv8_topology = dump_topology(lv8_path)

    # Save JSON
    lv6_out = out_dir / "nested_island_topology_lv6.json"
    lv8_out = out_dir / "nested_island_topology_lv8.json"

    with open(lv6_out, "w") as f:
        json.dump(lv6_topology, f, indent=2)
    print(f"\nSaved: {lv6_out}")

    with open(lv8_out, "w") as f:
        json.dump(lv8_topology, f, indent=2)
    print(f"Saved: {lv8_out}")


if __name__ == "__main__":
    main()
