#!/usr/bin/env python3
"""
Audit LV6 production DXF files for geometry inventory.

Parameterized to accept any DXF source directory path.
Handles spaces in path.
Scans for: layers, colors, entity types, text entities,
           marking/gravir layers, outer/hole geometry metrics.

Usage:
    python scripts/experiments/audit_production_dxf_holes.py \
        "/path/to/lv6 jav"
"""

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrs_nesting.dxf.importer import (
    normalize_source_entities,
    probe_layer_rings,
    DxfImportError,
)
from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles
from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_acceptance_gate import evaluate_dxf_prefilter_acceptance_gate


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


def parse_quantity_from_filename(filename: str):
    """Extract quantity from filename patterns: _20db, _6db, 10db, _50db, etc."""
    patterns = [
        r'_(\d+)db',    # _20db, _6db, _50db
        r'(\d+)db',     # 10db
        r'_(\d+)DB',
        r'(\d+)DB',
    ]
    for pat in patterns:
        m = re.search(pat, filename, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def get_entity_type(entity):
    """Get entity type string robustly."""
    if hasattr(entity, 'dxftype'):
        return entity.dxftype()
    return entity.get('type', entity.get('dxftype', 'UNKNOWN'))


def analyze_dxf(dxf_path: Path):
    """Analyze a single DXF file with both raw importer and preflight chain."""
    result = {
        "file_name": dxf_path.name,
        "parsed_quantity_from_filename": None,
        "import_status": "UNKNOWN",
        "import_category": "UNKNOWN",
        "preflight_status": "NOT_RUN",
        "preflight_category": "UNKNOWN",
        "part_id": dxf_path.stem.strip(),
        "layer_names": [],
        "color_summary": {},
        "entity_type_summary": {},
        "text_entity_count": 0,
        "marking_or_gravir_layers": [],
        "outer_vertex_count": 0,
        "hole_count": 0,
        "total_hole_vertices": 0,
        "bbox_width_mm": 0.0,
        "bbox_height_mm": 0.0,
        "area_mm2": 0.0,
        "min_edge_length_mm": None,
        "has_arcs": False,
        "has_circles": False,
        "has_text": False,
        "has_self_intersection": False,
        "notes": [],
        "error_code": None,
        "error_message": None,
        # raw importer rings
        "raw_outer_probe": None,
        "raw_inner_probe": None,
        # preflight
        "preflight_inspect_result": None,
        "preflight_role_result": None,
        "preflight_dedupe_result": None,
    }

    result["parsed_quantity_from_filename"] = parse_quantity_from_filename(dxf_path.name)

    # ── RAW IMPORTER ──────────────────────────────────────────────
    try:
        entities = normalize_source_entities(dxf_path)
    except Exception as ex:
        result["import_status"] = "IMPORT_FAILED"
        result["import_category"] = "IMPORT_FAILED"
        result["error_code"] = type(ex).__name__
        result["error_message"] = str(ex)
        result["notes"].append("raw_importer_failed")
        return result

    # Layer inventory
    layers = sorted(set(
        e.get("layer", "?") if hasattr(e, "get")
        else (getattr(e, "layer", None) or "?")
        for e in entities
    ))
    result["layer_names"] = layers

    # Entity type inventory
    entity_types = defaultdict(int)
    text_count = 0
    has_arcs = False
    has_circles = False
    has_text = False
    for e in entities:
        etype = get_entity_type(e)
        entity_types[etype] += 1
        if etype in ("TEXT", "MTEXT"):
            text_count += 1
            has_text = True
        if etype in ("ARC",):
            has_arcs = True
        if etype in ("CIRCLE",):
            has_circles = True

    result["text_entity_count"] = text_count
    result["has_text"] = has_text
    result["has_arcs"] = has_arcs
    result["has_circles"] = has_circles
    result["entity_type_summary"] = dict(entity_types)

    # Color inventory
    colors = defaultdict(int)
    for e in entities:
        if hasattr(e, "color") and e.color is not None:
            colors[str(e.color)] += 1
        elif hasattr(e, "get") and "color" in e:
            colors[str(e["color"])] += 1
    result["color_summary"] = dict(colors)

    # Marking/gravir layers
    marking_layers = [l for l in layers if l.lower() in ("gravír", "gravir", "marking", "grav")]
    result["marking_or_gravir_layers"] = marking_layers

    # ── PROBE LAYERS ────────────────────────────────────────────────
    # Try "0" (outer), "Gravír" (inner) — non-standard naming convention
    # ── PROBE LAYERS ────────────────────────────────────────────────
    # LV6 DXF: all geometry may be on "0" layer (no separate CUT_INNER layer).
    # Strategy:
    #   1. Probe "0" layer for ALL rings
    #   2. Pick the LARGEST ring (by area) as outer
    #   3. Remaining rings are holes
    #   4. Also probe "Gravír" layer separately
    outer_probe = probe_layer_rings(entities, layer="0")
    inner_probe = probe_layer_rings(entities, layer="Gravír")
    result["raw_outer_probe"] = outer_probe
    result["raw_inner_probe"] = inner_probe

    all_rings_0 = outer_probe.get("rings", [])
    gravir_rings = inner_probe.get("rings", [])
    outer_hard = outer_probe.get("hard_error")
    inner_hard = inner_probe.get("hard_error")

    # Categorize raw import
    if outer_hard:
        result["import_status"] = "IMPORT_FAILED"
        result["error_code"] = outer_hard["code"]
        result["error_message"] = outer_hard["message"]
        if "UNSUPPORTED_ENTITY_TYPE" in outer_hard["code"]:
            result["import_category"] = "UNSUPPORTED_ENTITY"
        else:
            result["import_category"] = "IMPORT_FAILED"
        result["notes"].append("raw_outer_hard_error")
        return result

    if not all_rings_0:
        result["import_status"] = "IMPORT_FAILED"
        result["error_code"] = "DXF_NO_OUTER_RINGS"
        result["error_message"] = f"No rings found on layer 0 (layers: {layers})"
        result["import_category"] = "INVALID_GEOMETRY"
        result["notes"].append("no_rings_on_layer0")
        return result

    # Pick largest ring as outer (by absolute area), rest as holes
    def ring_area(ring):
        if len(ring) < 3:
            return 0.0
        a = 0.0
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            a += ring[i][0] * ring[j][1]
            a -= ring[j][0] * ring[i][1]
        return abs(a) / 2.0

    ring_areas = [(i, ring_area(r), r) for i, r in enumerate(all_rings_0)]
    ring_areas.sort(key=lambda x: x[1], reverse=True)  # largest first

    outer_idx, outer_area, outer_pts = ring_areas[0]
    outer_rings = [outer_pts]
    hole_rings_from_0 = [r for _, _, r in ring_areas[1:]]

    # Combine holes from layer "0" and "Gravír"
    all_hole_rings = hole_rings_from_0 + gravir_rings

    result["import_status"] = "IMPORT_OK"
    result["outer_vertex_count"] = len(outer_pts)

    if all_hole_rings:
        result["import_status"] = "IMPORT_OK_WITH_HOLES"
        result["import_category"] = "IMPORT_OK_WITH_HOLES"
        result["hole_count"] = len(all_hole_rings)
        result["total_hole_vertices"] = sum(len(r) for r in all_hole_rings)
        result["notes"].append("holes_on_layer0_and_gravir")
    else:
        result["import_status"] = "IMPORT_OK_OUTER_ONLY"
        result["import_category"] = "IMPORT_OK_OUTER_ONLY"
        if inner_hard and inner_hard.get("code"):
            result["notes"].append(f"inner_layer_error:{inner_hard['code']}")

    # Metrics
    bbox = compute_bbox(outer_pts)
    result["bbox_width_mm"] = round(bbox[2] - bbox[0], 6)
    result["bbox_height_mm"] = round(bbox[3] - bbox[1], 6)
    result["area_mm2"] = round(compute_area(outer_pts), 3)
    result["min_edge_length_mm"] = round(min_edge_length(outer_pts), 6)

    if ring_has_self_intersection(outer_pts):
        result["has_self_intersection"] = True
        result["notes"].append("outer_has_self_intersection")

    for i, ring in enumerate(all_hole_rings):
        if ring_has_self_intersection(ring):
            result["notes"].append(f"hole_{i}_has_self_intersection")

    gravir_entities_layer = [e for e in entities if (e.get("layer") if hasattr(e, "get") else getattr(e, "layer", None)) == "Gravír"]
    inner_types = {get_entity_type(e) for e in gravir_entities_layer}
    if "TEXT" in inner_types or "MTEXT" in inner_types:
        result["notes"].append("inner_layer_has_text_annotation")
    if "SPLINE" in inner_types:
        result["notes"].append("inner_layer_has_spline")

    # ── PREFLIGHT CHAIN ─────────────────────────────────────────────
    try:
        inspect_result = inspect_dxf_source(str(dxf_path))
        result["preflight_inspect_result"] = inspect_result

        role_result = resolve_dxf_roles(inspect_result, {})
        result["preflight_role_result"] = role_result

        gap_repair_result = {
            "closed_contour_inventory": [], "diagnostics": [],
            "gap_repair_policies_applied": [], "remaining_open_path_candidates": [],
            "review_required_candidates": [], "blocking_conflicts": [],
            "repaired_path_working_set": [],
        }
        dedupe_result = dedupe_dxf_duplicate_contours(inspect_result, role_result, gap_repair_result, {})
        result["preflight_dedupe_result"] = dedupe_result

        # Determine preflight category based on role resolution + acceptance gate
        # resolved_role_inventory values are dicts with layer_count/entity_count/layers keys
        role_inv = role_result.get("resolved_role_inventory", {})
        _get_count = lambda role: int(role.get("layer_count", 0)) if isinstance(role, dict) else int(role or 0)
        cut_outer_count = _get_count(role_inv.get("CUT_OUTER", {}))
        cut_inner_count = _get_count(role_inv.get("CUT_INNER", {}))
        contour_assignments = role_result.get("contour_role_assignments", [])
        blocking_conflicts = role_result.get("blocking_conflicts", [])

        # Run full preflight chain with acceptance gate to get real outcome
        gap_repair_result = {
            "closed_contour_inventory": [], "diagnostics": [],
            "gap_repair_policies_applied": [], "remaining_open_path_candidates": [],
            "review_required_candidates": [], "blocking_conflicts": [],
            "repaired_path_working_set": [],
        }
        dedupe_for_gate = dedupe_result  # already computed above
        gate_outcome = None
        gate_blocking_count = 0
        gate_review_count = 0
        importer_probe = {"is_pass": False, "outer_point_count": 0, "hole_count": 0}
        try:
            import tempfile as _tempfile
            with _tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as _tf:
                _out_path = _tf.name
            _writer_result = write_normalized_dxf(
                inspect_result, role_result, gap_repair_result, dedupe_for_gate,
                output_path=_out_path
            )
            _gate_result = evaluate_dxf_prefilter_acceptance_gate(
                inspect_result, role_result, gap_repair_result, dedupe_for_gate, _writer_result
            )
            gate_outcome = _gate_result.get("acceptance_outcome")
            gate_blocking_count = len(_gate_result.get("blocking_reasons", []))
            gate_review_count = len(_gate_result.get("review_required_reasons", []))
            importer_probe = _gate_result.get("importer_probe", importer_probe)
        except Exception:
            pass  # gate failures are reflected in outcome

        if gate_outcome == "accepted_for_import":
            result["preflight_status"] = "PREFLIGHT_ACCEPTED"
            result["preflight_category"] = "PREFLIGHT_ACCEPTED"
        elif gate_outcome == "preflight_review_required":
            result["preflight_status"] = "PREFLIGHT_REVIEW_REQUIRED"
            result["preflight_category"] = "PREFLIGHT_REVIEW_REQUIRED"
        elif gate_outcome == "preflight_rejected":
            result["preflight_status"] = "PREFLIGHT_REJECTED"
            result["preflight_category"] = "PREFLIGHT_REJECTED"
        elif cut_outer_count > 0 and cut_inner_count > 0:
            result["preflight_status"] = "PREFLIGHT_OK_WITH_HOLES"
            result["preflight_category"] = "PREFLIGHT_OK_WITH_HOLES"
        elif cut_outer_count > 0:
            result["preflight_status"] = "PREFLIGHT_OK_OUTER_ONLY"
            result["preflight_category"] = "PREFLIGHT_OK_OUTER_ONLY"
        elif contour_assignments:
            # Contour-level resolution happened
            if blocking_conflicts:
                result["preflight_status"] = "PREFLIGHT_FAILED"
                result["preflight_category"] = "PREFLIGHT_FAILED"
                result["notes"].append("preflight_blocking_conflicts")
            else:
                result["preflight_status"] = "PREFLIGHT_REVIEW_REQUIRED"
                result["preflight_category"] = "PREFLIGHT_REVIEW_REQUIRED"
        else:
            # No role assignment at all
            outer_like = len(inspect_result.get("outer_like_candidates", []))
            inner_like = len(inspect_result.get("inner_like_candidates", []))
            if outer_like > 0 and inner_like > 0:
                result["preflight_status"] = "PREFLIGHT_OK_WITH_HOLES"
                result["preflight_category"] = "PREFLIGHT_OK_WITH_HOLES"
            elif outer_like > 0:
                result["preflight_status"] = "PREFLIGHT_OK_OUTER_ONLY"
                result["preflight_category"] = "PREFLIGHT_OK_OUTER_ONLY"
            else:
                result["preflight_status"] = "PREFLIGHT_FAILED"
                result["preflight_category"] = "PREFLIGHT_FAILED"
                result["notes"].append("preflight_no_role_assignment")

        # Store acceptance gate info
        result["acceptance_outcome"] = gate_outcome
        result["gate_blocking_count"] = gate_blocking_count
        result["gate_review_count"] = gate_review_count
        result["importer_outer_points"] = importer_probe.get("outer_point_count", 0)
        result["importer_hole_count"] = importer_probe.get("hole_count", 0)

    except Exception as ex:
        result["preflight_status"] = "PREFLIGHT_FAILED"
        result["preflight_category"] = "PREFLIGHT_FAILED"
        result["error_code"] = type(ex).__name__
        result["error_message"] = str(ex)
        result["notes"].append("preflight_chain_failed")

    return result


def main():
    if not SRC_DIR.exists():
        print(f"ERROR: Source directory not found: {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    dxf_files = sorted(SRC_DIR.glob("*.dxf"))
    if not dxf_files:
        print(f"ERROR: No .dxf files found in {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(dxf_files)} DXF files in {SRC_DIR}")
    results = []

    for dxf_path in dxf_files:
        r = analyze_dxf(dxf_path)
        results.append(r)
        import_cat = r["import_category"]
        pref_cat = r["preflight_category"]
        outer_v = r["outer_vertex_count"]
        holes = r["hole_count"]
        hole_v = r["total_hole_vertices"]
        qty = r["parsed_quantity_from_filename"]
        err = r["error_code"] or ""
        print(f"  {dxf_path.name}: import={import_cat} preflight={pref_cat} outer={outer_v} holes={holes}({hole_v}v) qty={qty} {err}")

    # ── Summary ──────────────────────────────────────────────────
    total = len(results)
    import_cats = defaultdict(int)
    preflight_cats = defaultdict(int)
    total_with_holes = 0
    total_with_text = 0
    total_import_failed = 0
    total_preflight_failed = 0
    total_accepted = 0
    total_review_required = 0
    total_rejected = 0

    for r in results:
        import_cats[r["import_category"]] += 1
        preflight_cats[r["preflight_category"]] += 1
        if r["hole_count"] > 0:
            total_with_holes += 1
        if r["has_text"]:
            total_with_text += 1
        if r["import_category"] in ("IMPORT_FAILED", "INVALID_GEOMETRY"):
            total_import_failed += 1
        if r["preflight_category"] in ("PREFLIGHT_FAILED",):
            total_preflight_failed += 1
        outcome = r.get("acceptance_outcome")
        if outcome == "accepted_for_import":
            total_accepted += 1
        elif outcome == "preflight_review_required":
            total_review_required += 1
        elif outcome == "preflight_rejected":
            total_rejected += 1

    print()
    print("Summary (import):")
    for cat, cnt in sorted(import_cats.items()):
        print(f"  {cat}: {cnt}")
    print(f"  Total: {total}")

    print()
    print("Summary (preflight / acceptance gate):")
    for cat, cnt in sorted(preflight_cats.items()):
        print(f"  {cat}: {cnt}")
    print(f"  accepted_for_import: {total_accepted}")
    print(f"  preflight_review_required: {total_review_required}")
    print(f"  preflight_rejected: {total_rejected}")

    # All layers and colors
    all_layers = set()
    all_entity_types = set()
    all_colors = set()
    for r in results:
        all_layers.update(r["layer_names"])
        all_entity_types.update(r["entity_type_summary"].keys())
        all_colors.update(r["color_summary"].keys())

    print()
    print(f"Unique layers: {sorted(all_layers)}")
    print(f"Unique entity types: {sorted(all_entity_types)}")
    print(f"Unique colors: {sorted(all_colors)}")

    # Quantity parsing summary
    qty_found = sum(1 for r in results if r["parsed_quantity_from_filename"] is not None)
    qty_values = [r["parsed_quantity_from_filename"] for r in results if r["parsed_quantity_from_filename"] is not None]
    print()
    print(f"Quantity parsed: {qty_found}/{total}")
    if qty_values:
        print(f"  Quantities: {sorted(qty_values)}")

    # Write JSON
    output = {
        "audit_version": "t05h_lv6_v1",
        "source_dir": str(SRC_DIR.resolve()),
        "total_dxf": total,
        "summary_import": dict(import_cats),
        "summary_preflight": dict(preflight_cats),
        "with_holes": total_with_holes,
        "with_text": total_with_text,
        "import_failed": total_import_failed,
        "preflight_failed": total_preflight_failed,
        "accepted_for_import": total_accepted,
        "preflight_review_required": total_review_required,
        "preflight_rejected": total_rejected,
        "quantity_parsed": qty_found,
        "quantity_values": sorted(qty_values) if qty_values else [],
        "all_layers": sorted(all_layers),
        "all_entity_types": sorted(all_entity_types),
        "all_colors": sorted(all_colors),
        "results": results,
    }
    out_json = OUT_DIR / "lv6_production_dxf_inventory.json"
    out_json.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON inventory: {out_json}")

    # Write Markdown
    md_lines = [
        "# LV6 Production DXF Hole Inventory (T05h)",
        "",
        f"**Source**: `{SRC_DIR}`",
        f"**Total DXF files**: {total}",
        "",
        "## Import Summary",
        "",
    ]
    for cat, cnt in sorted(import_cats.items()):
        md_lines.append(f"- **{cat}**: {cnt}")
    md_lines.extend(["", "## Preflight / Acceptance Gate Summary", ""])
    for cat, cnt in sorted(preflight_cats.items()):
        md_lines.append(f"- **{cat}**: {cnt}")
    md_lines.extend([
        "",
        "## Acceptance Gate Outcomes",
        f"- **accepted_for_import**: {total_accepted}",
        f"- **preflight_review_required**: {total_review_required}",
        f"- **preflight_rejected**: {total_rejected}",
        "",
        "## Counts",
        f"- With holes: {total_with_holes}",
        f"- With text: {total_with_text}",
        f"- Import failed: {total_import_failed}",
        f"- Preflight failed: {total_preflight_failed}",
        f"- Quantity parsed: {qty_found}/{total} → {sorted(qty_values) if qty_values else 'none'}",
        f"- All layers: {sorted(all_layers)}",
        "",
        "## Detailed Results",
        "",
        "| File | Import Cat | Preflight Cat | Outer verts | Holes | Hole verts | BBox W×H mm | Area mm² | Text | Qty | Acceptance | Notes |",
        "|------|------------|---------------|-------------|-------|------------|-------------|----------|------|-----|------------|-------|",
    ])
    for r in results:
        notes = "; ".join(r["notes"]) if r["notes"] else ""
        qty = r["parsed_quantity_from_filename"] or ""
        acceptance = r.get("acceptance_outcome", "N/A")
        md_lines.append(
            f"| {r['file_name']} | {r['import_category']} | {r['preflight_category']} | "
            f"{r['outer_vertex_count']} | {r['hole_count']} | "
            f"{r['total_hole_vertices']} | {r['bbox_width_mm']:.1f}×{r['bbox_height_mm']:.1f} | "
            f"{r['area_mm2']:.1f} | {r['text_entity_count']} | {qty} | {acceptance} | {notes} |"
        )

    out_md = OUT_DIR / "lv6_production_dxf_inventory.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Markdown inventory: {out_md}")

    return output


if __name__ == "__main__":
    main()
