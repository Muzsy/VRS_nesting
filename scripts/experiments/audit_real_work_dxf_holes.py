#!/usr/bin/env python3
"""
Audit real_work_dxf hole inventory.

Scans /home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv8jav
for DXF files, probes CUT_OUTER ("0") and CUT_INNER ("Gravír") layers,
and produces a structured inventory report.
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrs_nesting.dxf.importer import (
    normalize_source_entities,
    probe_layer_rings,
    DxfImportError,
)


SRC_DIR = Path("samples/real_work_dxf/0014-01H/lv8jav")
OUT_JSON = Path("tmp/reports/nfp_cgal_probe/real_work_dxf_hole_inventory.json")
OUT_MD = Path("tmp/reports/nfp_cgal_probe/real_work_dxf_hole_inventory.md")
OUT_DIR = OUT_JSON.parent
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


def min_edge_length(pts):
    if len(pts) < 2:
        return 0.0
    min_d = float("inf")
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        dx = pts[i][0] - pts[j][0]
        dy = pts[i][1] - pts[j][1]
        d = math.sqrt(dx * dx + dy * dy)
        if d < min_d:
            min_d = d
    return min_d


def ring_has_self_intersection(ring):
    n = len(ring)
    if n < 4:
        return False
    # Check for any pair of non-adjacent edges intersecting
    def seg_intersects(a1, a2, b1, b2):
        def orient(a, b, c):
            v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            return 1 if v > 0 else -1 if v < 0 else 0
        o1 = orient(a1, a2, b1)
        o2 = orient(a1, a2, b2)
        o3 = orient(b1, b2, a1)
        o4 = orient(b1, b2, a2)
        if o1 != o2 and o3 != o4:
            return True
        return False
    for i in range(n):
        a1 = ring[i]
        a2 = ring[(i + 1) % n]
        for j in range(i + 2, n):
            if j == (i - 1) % n:
                continue
            b1 = ring[j]
            b2 = ring[(j + 1) % n]
            if seg_intersects(a1, a2, b1, b2):
                return True
    return False


def analyze_dxf(dxf_path):
    """Analyze a single DXF file, probe both outer and Gravír layers."""
    result = {
        "file_name": dxf_path.name,
        "import_status": "UNKNOWN",
        "import_category": "UNKNOWN",
        "part_id": dxf_path.stem.strip(),
        "outer_probe": None,
        "inner_probe": None,
        "outer_vertex_count": 0,
        "hole_count": 0,
        "total_hole_vertices": 0,
        "bbox_width_mm": 0.0,
        "bbox_height_mm": 0.0,
        "area_mm2": 0.0,
        "has_self_intersection": False,
        "min_edge_length_mm": None,
        "error_code": None,
        "error_message": None,
        "layers_found": [],
        "notes": [],
    }

    try:
        entities = normalize_source_entities(dxf_path)
    except Exception as ex:
        result["import_status"] = "IMPORT_FAILED"
        result["import_category"] = "IMPORT_FAILED"
        result["error_code"] = type(ex).__name__
        result["error_message"] = str(ex)
        return result

    # Discover unique layers
    layers = sorted(set(e.get("layer", "?") for e in entities))
    result["layers_found"] = layers

    # Categorize entity types per layer
    layer_types = defaultdict(list)
    for e in entities:
        layer_types[e.get("layer", "?")].append(e.dxftype() if hasattr(e, "dxftype") else e.get("type", "?"))

    # Probe outer layer ("0")
    outer_probe = probe_layer_rings(entities, layer="0")
    result["outer_probe"] = outer_probe

    # Probe inner layer ("Gravír") — the actual inner layer name in these DXFs
    inner_probe = probe_layer_rings(entities, layer="Gravír")
    result["inner_probe"] = inner_probe

    outer_rings = outer_probe.get("rings", [])
    inner_rings = inner_probe.get("rings", [])
    outer_hard = outer_probe.get("hard_error")
    inner_hard = inner_probe.get("hard_error")

    # Determine import status
    if outer_hard:
        result["import_status"] = "IMPORT_FAILED"
        result["error_code"] = outer_hard["code"]
        result["error_message"] = outer_hard["message"]
        result["import_category"] = "IMPORT_FAILED"
        if "UNSUPPORTED_ENTITY_TYPE" in outer_hard["code"]:
            result["import_category"] = "UNSUPPORTED_ENTITY"
        return result

    if not outer_rings:
        result["import_status"] = "IMPORT_FAILED"
        result["error_code"] = "DXF_NO_OUTER_RINGS"
        result["error_message"] = f"No outer rings found (layers: {layers})"
        result["import_category"] = "INVALID_GEOMETRY"
        return result

    # Success
    outer_pts = outer_rings[0]
    result["import_status"] = "IMPORT_OK"
    result["outer_vertex_count"] = len(outer_pts)

    if inner_rings:
        result["import_status"] = "IMPORT_OK_WITH_HOLES"
        result["hole_count"] = len(inner_rings)
        result["total_hole_vertices"] = sum(len(r) for r in inner_rings)
        result["import_category"] = "IMPORT_OK_WITH_HOLES"
    else:
        result["import_status"] = "IMPORT_OK_OUTER_ONLY"
        result["import_category"] = "IMPORT_OK_OUTER_ONLY"
        if inner_hard and inner_hard.get("code"):
            result["notes"].append(f"inner_layer_error: {inner_hard['code']}")

    bbox = compute_bbox(outer_pts)
    result["bbox_width_mm"] = round(bbox[2] - bbox[0], 3)
    result["bbox_height_mm"] = round(bbox[3] - bbox[1], 3)
    result["area_mm2"] = round(compute_area(outer_pts), 3)
    result["min_edge_length_mm"] = round(min_edge_length(outer_pts), 6)

    if ring_has_self_intersection(outer_pts):
        result["has_self_intersection"] = True
        result["notes"].append("outer_has_self_intersection")

    # Check if inner rings have self-intersection
    for i, ring in enumerate(inner_rings):
        if ring_has_self_intersection(ring):
            result["notes"].append(f"hole_{i}_has_self_intersection")

    # Note if inner layer has unsupported entities
    inner_layer_entities = [e for e in entities if e.get("layer") == "Gravír"]
    inner_types = set(e.dxftype() if hasattr(e, "dxftype") else e.get("type", "?") for e in inner_layer_entities)
    if "TEXT" in inner_types or "MTEXT" in inner_types:
        result["notes"].append("inner_layer_has_text_annotation")
    if "SPLINE" in inner_types:
        result["notes"].append("inner_layer_has_spline")

    return result


def main():
    dxf_files = sorted(SRC_DIR.glob("*.dxf"))
    if not dxf_files:
        print(f"ERROR: No .dxf files found in {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(dxf_files)} DXF files in {SRC_DIR}")
    results = []
    for dxf_path in dxf_files:
        r = analyze_dxf(dxf_path)
        results.append(r)
        status = r["import_status"]
        outer_v = r["outer_vertex_count"]
        holes = r["hole_count"]
        hole_v = r["total_hole_vertices"]
        err = r["error_code"] or ""
        print(f"  {dxf_path.name}: {status} outer={outer_v} holes={holes} ({hole_v}v) {err}")

    # Summary
    total = len(results)
    categories = defaultdict(int)
    for r in results:
        categories[r["import_category"]] += 1

    print()
    print("Summary:")
    for cat, cnt in sorted(categories.items()):
        print(f"  {cat}: {cnt}")
    print(f"  Total: {total}")

    # Write JSON
    output = {
        "audit_version": "t05e_v1",
        "source_dir": str(SRC_DIR.resolve()),
        "total_dxf": total,
        "summary": {k: v for k, v in categories.items()},
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON inventory: {OUT_JSON}")

    # Write Markdown
    md_lines = [
        "# Real Work DXF Hole Inventory",
        "",
        f"**Source**: `{SRC_DIR}`",
        f"**Total DXF files**: {total}",
        "",
        "## Summary",
        "",
    ]
    for cat, cnt in sorted(categories.items()):
        md_lines.append(f"- **{cat}**: {cnt}")

    md_lines.extend(["", "## Detailed Results", ""])
    md_lines.append("| File | Category | Outer verts | Holes | Hole verts | BBox W×H mm | Area mm² | Self-intersect | Notes |")
    md_lines.append("|------|----------|-------------|-------|------------|-------------|----------|-----------------|-------|")
    for r in results:
        notes = "; ".join(r["notes"]) if r["notes"] else ""
        md_lines.append(
            f"| {r['file_name']} | {r['import_category']} | "
            f"{r['outer_vertex_count']} | {r['hole_count']} | "
            f"{r['total_hole_vertices']} | "
            f"{r['bbox_width_mm']}×{r['bbox_height_mm']} | "
            f"{r['area_mm2']} | {r['has_self_intersection']} | "
            f"{notes} |"
        )

    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Markdown inventory: {OUT_MD}")

    return output


if __name__ == "__main__":
    main()
