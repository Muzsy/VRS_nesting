#!/usr/bin/env python3
"""
T05k — Lv8_11612_6db REV3.dxf — Gravír Layer Entity-Level Audit

Purpose:
  Detailed entity-level audit of the "Gravír" layer in the nested-island DXF.
  Classifies each contour as CUT_INNER / MARKING / ARTIFACT / MATERIAL_ISLAND / UNKNOWN_REVIEW.

Usage:
  python scripts/experiments/audit_lv8_11612_gravir_entities.py \
    "/home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv8jav/Lv8_11612_6db REV3.dxf"

Output:
  tmp/reports/nfp_cgal_probe/t05k_lv8_11612_gravir_entity_audit.json
  tmp/reports/nfp_cgal_probe/t05k_lv8_11612_gravir_entity_audit.md
  tmp/reports/nfp_cgal_probe/t05k_lv8_11612_nested_contours_ascii.md
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles
from vrs_nesting.dxf.importer import normalize_source_entities, probe_layer_rings


DXF_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "samples/real_work_dxf/0014-01H/lv8jav/Lv8_11612_6db REV3.dxf"
)
OUT_DIR = Path("tmp/reports/nfp_cgal_probe")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

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
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "min_x": min(xs), "min_y": min(ys),
        "max_x": max(xs), "max_y": max(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }


def compute_centroid(pts):
    """Shoelace centroid."""
    if len(pts) < 3:
        return None
    cx, cy, a = 0.0, 0.0, 0.0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        cross = pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
        a += cross
        cx += (pts[i][0] + pts[j][0]) * cross
        cy += (pts[i][1] + pts[j][1]) * cross
    a *= 0.5
    if abs(a) < 1e-12:
        return None
    cx /= 6 * a
    cy /= 6 * a
    return [round(cx, 4), round(cy, 4)]


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


def ring_is_closed(pts, eps=0.5):
    """Check if ring is closed (first == last within epsilon)."""
    if len(pts) < 2:
        return False
    dx = pts[0][0] - pts[-1][0]
    dy = pts[0][1] - pts[-1][1]
    return math.sqrt(dx * dx + dy * dy) < eps


def get_ring_closed_status(ring_pts):
    """More robust check: also check if points form a closed LWPOLYLINE.

    An LWPOLYLINE ring is closed if it was defined with the closed flag,
    AND first point == last point. But the normalized ring always has
    first==last due to the ring-closing normalization in the importer.
    So we check if first == last within eps AND has 3+ points.
    """
    if len(ring_pts) < 3:
        return False
    # Normalized rings always have first == last
    dx = ring_pts[0][0] - ring_pts[-1][0]
    dy = ring_pts[0][1] - ring_pts[-1][1]
    return math.sqrt(dx * dx + dy * dy) < 1.0  # 1mm tolerance


def point_in_ring(pt, ring):
    """Ray casting point-in-polygon test."""
    x, y = pt[0], pt[1]
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------------------
# Entity type helpers
# ---------------------------------------------------------------------------

def get_entity_type(entity):
    if hasattr(entity, "dxftype"):
        return entity.dxftype()
    return entity.get("type", entity.get("dxftype", "UNKNOWN"))


def get_entity_props(entity):
    """Extract all relevant properties from a DXF entity."""
    etype = get_entity_type(entity)
    props = {
        "entity_type": etype,
        "handle": str(entity.handle) if hasattr(entity, "handle") else None,
        "layer": str(entity.dxf.layer) if hasattr(entity, "dxf") and hasattr(entity.dxf, "layer") else None,
        "color_index": entity.color if hasattr(entity, "color") else None,
        "linetype": entity.linetype if hasattr(entity, "linetype") else None,
    }

    if etype in ("CIRCLE", "ARC"):
        if hasattr(entity, "dxf"):
            dxf = entity.dxf
            props["center"] = [round(dxf.center.x, 4), round(dxf.center.y, 4)]
            props["radius"] = round(dxf.radius, 4) if hasattr(dxf, "radius") else None
            if etype == "ARC" and hasattr(dxf, "start_angle"):
                props["start_angle"] = round(dxf.start_angle, 4)
                props["end_angle"] = round(dxf.end_angle, 4)

    elif etype in ("LINE",):
        if hasattr(entity, "dxf"):
            dxf = entity.dxf
            props["start"] = [round(dxf.start.x, 4), round(dxf.start.y, 4)]
            props["end"] = [round(dxf.end.x, 4), round(dxf.end.y, 4)]

    elif etype in ("TEXT",):
        if hasattr(entity, "dxf"):
            dxf = entity.dxf
            props["text"] = str(dxf.text) if hasattr(dxf, "text") else None
            props["insert"] = [round(dxf.insert.x, 4), round(dxf.insert.y, 4)] if hasattr(dxf, "insert") else None
            props["height"] = round(dxf.height, 4) if hasattr(dxf, "height") else None

    elif etype in ("MTEXT",):
        if hasattr(entity, "dxf"):
            dxf = entity.dxf
            props["text"] = str(dxf.text)[:200] if hasattr(dxf, "text") else None
            props["insert"] = [round(dxf.insert.x, 4), round(dxf.insert.y, 4)] if hasattr(dxf, "insert") else None
            props["height"] = round(dxf.char_height, 4) if hasattr(dxf, "char_height") else None

    elif etype in ("LWPOLYLINE", "POLYLINE"):
        if hasattr(entity, "dxf"):
            dxf = entity.dxf
            props["closed"] = bool(dxf.flags & 1) if hasattr(dxf, "flags") else None
            props["point_count"] = len(list(entity.points())) if hasattr(entity, "points") else None

    return props


# ---------------------------------------------------------------------------
# Topology depth computation
# ---------------------------------------------------------------------------

def build_topology_maps(contour_candidates, inner_like, outer_like):
    """Build contains/contained_by maps and compute containment depth."""
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

    def depth(key, cache=None):
        if cache is None:
            cache = {}
        if key in cache:
            return cache[key]
        parents = contained_by_map.get(key, [])
        if not parents:
            d = 0
        else:
            d = 1 + max(depth(p, cache) for p in parents)
        cache[key] = d
        return d

    depth_cache = {}
    candidate_depth = {}
    for c in contour_candidates:
        key = (str(c["layer"]), int(c["ring_index"]))
        candidate_depth[key] = depth(key, depth_cache)

    return contains_map, contained_by_map, candidate_depth


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

def classify_contour(contour, depth, ring_points, text_entities_on_layer,
                    gravir_circle_entities, gravir_line_entities):
    """
    Classify a contour's proposed interpretation.

    Rules (from T05k task):
    A) Gravír closed geometric contour, inner-like, no text, cut-hole-sized → CUT_INNER
    B) Gravír TEXT/MTEXT → MARKING
    C) depth=2 very small / coincident / duplicate / text-marking context → ARTIFACT / MARKING_REVIEW
    D) depth=2 genuine closed cut contour, manufacturing island → MATERIAL_ISLAND / UNKNOWN_REVIEW

    Additional T05k findings:
    - Gravír layer circles at nested island centers (radius~9mm) = crosshair/center-finding
      markers = ARTIFACT (manufacturing aid, not cut geometry)
    - Gravír layer has no actual closed contour geometry — just circle traces
    - Empty TEXT entities = import placeholders, not real annotations

    Returns: (proposed_interpretation, confidence, reason)
    """
    layer = str(contour.get("source_layer", contour.get("layer", "")))
    area = float(contour.get("area_abs_mm2", 0))
    bbox = contour.get("bbox", {})
    ring_idx = int(contour.get("ring_index", -1))
    entity_types = contour.get("entity_types", [])
    point_count = int(contour.get("point_count", 0))
    has_text_content = len(text_entities_on_layer) > 0
    has_nonempty_text = len(contour.get("nonempty_text_entities", [])) > 0

    # Check if it's a pure text contour (no actual geometry)
    if entity_types and all(et in ("TEXT", "MTEXT") for et in entity_types):
        if has_nonempty_text:
            return "MARKING", "HIGH", "TEXT/MTEXT entity with real content on layer — marking annotation"
        else:
            return "ARTIFACT", "MEDIUM", "TEXT/MTEXT entity with empty text — import placeholder artifact"

    # Check if it's purely text entities on the same layer
    if has_text_content and not has_nonempty_text and area < 1.0:
        return "ARTIFACT", "HIGH", "Text annotation layer with empty text — import placeholder"

    # Gravír layer analysis (T05k key finding)
    if layer.lower() in ("gravír", "gravir", "grav"):
        # Gravír circles are crosshair/center-finding markers (radius ~9mm)
        # positioned at the center of nested island holes.
        # This is manufacturing aid geometry, not cut geometry.
        has_circles = any(et == "CIRCLE" for et in entity_types)
        has_lines = any(et == "LINE" for et in entity_types)
        is_circle_trace = (point_count >= 8 and point_count <= 72 and
                           area > 100 and area < 500 and has_circles)

        if is_circle_trace:
            return ("ARTIFACT", "HIGH",
                    "Gravír CIRCLE crosshair/center-finding marker at nested island center — "
                    "manufacturing aid geometry, not cut contour")

        # Gravír depth=1 ring that's actually a partial trace of crosshair geometry
        if depth == 1 and area < 500 and not has_nonempty_text:
            return ("ARTIFACT", "MEDIUM",
                    "Gravír layer small ring from circle+line assembly — "
                    "manufacturing marker geometry, not production cut")

        # Otherwise Gravír closed contour
        if depth == 0:
            return "CUT_OUTER", "HIGH", "Gravír layer outer ring (depth=0)"
        elif depth == 1:
            if area < 10000:
                return ("CUT_INNER", "MEDIUM",
                        "Gravír closed contour, inner-like, no text, cut-hole-sized — likely CUT_INNER")
            else:
                return ("CUT_INNER", "LOW",
                        "Gravír closed contour but unusually large for a cut hole")
        elif depth >= 2:
            if area < 100:
                return ("ARTIFACT", "MEDIUM",
                        "Gravír depth>=2 contour, very small area — likely import artifact")
            else:
                return ("MATERIAL_ISLAND", "LOW",
                        "Gravír depth>=2 contour, larger area — possible material island, needs review")

    # Default: layer 0 contours
    if layer == "0":
        if depth == 0:
            return "CUT_OUTER", "HIGH", "Layer 0 outer ring"
        elif depth == 1:
            if area < 10:
                return ("ARTIFACT", "LOW",
                        "Layer 0 depth=1 contour, very small — possible artifact")
            return "CUT_INNER", "HIGH", "Layer 0 inner ring"
        elif depth >= 2:
            if area < 10:
                return "ARTIFACT", "MEDIUM", "Layer 0 depth>=2 very small contour"
            return ("MATERIAL_ISLAND", "LOW",
                    "Layer 0 depth>=2 contour — nested island, needs review")

    return "UNKNOWN_REVIEW", "LOW", "Unclassified contour"


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def audit_gravir_layer(dxf_path: Path):
    print(f"\n{'='*70}")
    print(f"AUDIT: {dxf_path.name}")
    print(f"{'='*70}")

    # 1. Run preflight inspect + role resolution
    inspect_result = inspect_dxf_source(str(dxf_path))
    role_result = resolve_dxf_roles(inspect_result, {})

    # 2. Normalize source entities for raw entity access
    entities = normalize_source_entities(dxf_path)
    print(f"Total entities: {len(entities)}")

    # 3. Group entities by layer
    entities_by_layer = defaultdict(list)
    for e in entities:
        layer = e.get("layer", "?") if hasattr(e, "get") else getattr(e, "layer", "?")
        entities_by_layer[layer].append(e)

    layers = sorted(entities_by_layer.keys())
    print(f"Layers: {layers}")

    # 4. Find TEXT/MTEXT entities on Gravír layer
    gravir_layer_names = [l for l in layers if l.lower() in ("gravír", "gravir", "grav")]
    text_entities_gravir = []
    for e in entities_by_layer.get("Gravír", []) + entities_by_layer.get("gravir", []) + entities_by_layer.get("Gravir", []):
        etype = get_entity_type(e)
        if etype in ("TEXT", "MTEXT"):
            props = get_entity_props(e)
            text_entities_gravir.append(props)

    print(f"Gravír layer text entities: {len(text_entities_gravir)}")

    # 5. Probe rings from each layer
    layer_ring_data = {}
    all_ring_points = {}  # key -> points

    for layer in layers:
        probe = probe_layer_rings(entities, layer=layer)
        rings = probe.get("rings", [])
        layer_ring_data[layer] = {"rings": rings, "probe": probe}

        for idx, ring_pts in enumerate(rings):
            key = (layer, idx)
            all_ring_points[key] = ring_pts

    # 6. Build topology maps
    outer_like = inspect_result.get("outer_like_candidates", [])
    inner_like = inspect_result.get("inner_like_candidates", [])
    contour_candidates = inspect_result.get("contour_candidates", [])

    contains_map, contained_by_map, candidate_depth = build_topology_maps(
        contour_candidates, inner_like, outer_like
    )

    # 7. Index contour candidates by key
    contour_by_key = {}
    for c in contour_candidates:
        key = (str(c["layer"]), int(c["ring_index"]))
        contour_by_key[key] = c

    # 8. Build per-layer entity type index
    layer_by_type = {}
    for layer in layers:
        layer_ents = entities_by_layer.get(layer, [])
        by_t = {}
        for e in layer_ents:
            t = get_entity_type(e)
            by_t.setdefault(t, []).append(e)
        layer_by_type[layer] = by_t

    # 9. Classify each contour
    classified_contours = []
    for (layer, ring_idx), ring_pts in all_ring_points.items():
        key = (layer, ring_idx)
        depth = candidate_depth.get(key, -1)
        area = compute_area(ring_pts)
        bbox = compute_bbox(ring_pts)
        centroid = compute_centroid(ring_pts)
        min_edge = min_edge_length(ring_pts)
        closed = get_ring_closed_status(ring_pts)

        # Per-layer entity type breakdown
        by_t = layer_by_type.get(layer, {})
        layer_ents = entities_by_layer.get(layer, [])
        ent_types = sorted(set(get_entity_type(e) for e in layer_ents))

        # Text on this layer
        text_on_layer = [
            get_entity_props(e) for e in layer_ents
            if get_entity_type(e) in ("TEXT", "MTEXT")
        ]

        # Actual non-empty text on this layer
        nonempty_text = [
            get_entity_props(e) for e in layer_ents
            if get_entity_type(e) in ("TEXT", "MTEXT") and
               str(e.get("text", "")).strip()
        ]

        # Parent contours
        parents = [str(p) for p in contained_by_map.get(key, [])]
        children = [str(c) for c in contains_map.get(key, [])]

        # Classification
        contour_info = {
            "source_layer": layer,
            "ring_index": ring_idx,
            "depth": depth,
            "area_abs_mm2": round(area, 4),
            "bbox": bbox,
            "centroid": centroid,
            "min_edge_mm": round(min_edge, 4),
            "closed": closed,
            "entity_types": ent_types,
            "point_count": len(ring_pts),
            "text_entities_on_layer": text_on_layer,
            "nonempty_text_entities": nonempty_text,
            "contained_by": parents,
            "contains": children,
            "current_role": contour_by_key.get(key, {}).get("assigned_role", "UNASSIGNED"),
        }

        proposed, confidence, reason = classify_contour(
            contour_info, depth, ring_pts, text_on_layer,
            gravir_circle_entities=by_t.get("CIRCLE", []),
            gravir_line_entities=by_t.get("LINE", []),
        )
        contour_info["proposed_interpretation"] = proposed
        contour_info["confidence"] = confidence
        contour_info["reason"] = reason
        classified_contours.append(contour_info)

        print(f"  [{layer}:{ring_idx}] depth={depth} area={area:.2f}mm² "
              f"closed={closed} role={proposed} ({confidence}) — {reason[:60]}")

    # 9. Build JSON output
    output = {
        "source_path": str(dxf_path),
        "file_name": dxf_path.name,
        "audit_type": "T05k_gravir_layer_entity_audit",
        "total_entities": len(entities),
        "layers": layers,
        "gravir_text_entities": text_entities_gravir,
        "total_contours": len(classified_contours),
        "contours": classified_contours,
    }

    # Layer summary
    layer_summary = []
    for layer in layers:
        layer_ents = entities_by_layer.get(layer, [])
        ent_types = sorted(set(get_entity_type(e) for e in layer_ents))
        text_count = sum(1 for e in layer_ents if get_entity_type(e) in ("TEXT", "MTEXT"))
        closed_ring_count = 0
        total_ring_area = 0.0
        layer_contours = [c for c in classified_contours if c["source_layer"] == layer]
        for c in layer_contours:
            if c["closed"]:
                closed_ring_count += 1
            total_ring_area += c["area_abs_mm2"]

        cut_candidates = [c for c in layer_contours if c["proposed_interpretation"] in ("CUT_OUTER", "CUT_INNER")]
        marking_candidates = [c for c in layer_contours if c["proposed_interpretation"] == "MARKING"]

        layer_summary.append({
            "layer_name": layer,
            "entity_types": ent_types,
            "entity_count": len(layer_ents),
            "text_mtext_count": text_count,
            "closed_ring_count": closed_ring_count,
            "total_area_mm2": round(total_ring_area, 4),
            "cut_candidate_count": len(cut_candidates),
            "marking_candidate_count": len(marking_candidates),
        })

    output["layer_summary"] = layer_summary

    # ASCII debug export
    ascii_lines = []
    ascii_lines.append("# T05k — Nested Contour ASCII Debug Export")
    ascii_lines.append(f"File: {dxf_path.name}")
    ascii_lines.append(f"Total contours: {len(classified_contours)}\n")

    # Group by depth
    by_depth = defaultdict(list)
    for c in classified_contours:
        by_depth[c["depth"]].append(c)

    for d in sorted(by_depth.keys()):
        ascii_lines.append(f"\n## Depth {d}")
        for c in sorted(by_depth[d], key=lambda x: (x["source_layer"], x["ring_index"])):
            role_marker = "⚠" if c["proposed_interpretation"] == "UNKNOWN_REVIEW" else (
                "◆" if c["proposed_interpretation"] == "MATERIAL_ISLAND" else (
                "●" if c["proposed_interpretation"] in ("CUT_OUTER", "CUT_INNER") else "○"
            ))
            bbox = c["bbox"]
            centroid = c["centroid"]
            ascii_lines.append(
                f"  {role_marker} [{c['source_layer']}:{c['ring_index']}] "
                f"role={c['proposed_interpretation']:<20} "
                f"depth={c['depth']} area={c['area_abs_mm2']:.2f}mm² "
                f"closed={c['closed']} "
                f"bbox=[{bbox['min_x']:.1f},{bbox['min_y']:.1f}]→[{bbox['max_x']:.1f},{bbox['max_y']:.1f}] "
                f"centroid={centroid} "
                f"min_edge={c['min_edge_mm']:.3f}mm "
                f"reason={c['reason'][:50]}"
            )

    ascii_lines.append("\n## ASCII Legend")
    ascii_lines.append("  ⚠ = UNKNOWN_REVIEW (needs manual)")
    ascii_lines.append("  ◆ = MATERIAL_ISLAND (nested island)")
    ascii_lines.append("  ● = CUT_OUTER / CUT_INNER")
    ascii_lines.append("  ○ = MARKING / ARTIFACT")

    # Markdown output
    md_lines = []
    md_lines.append("# T05k — Lv8_11612_6db REV3.dxf — Gravír Layer Entity Audit")
    md_lines.append("")
    md_lines.append(f"**File:** `{dxf_path.name}`")
    md_lines.append(f"**Path:** `{dxf_path}`")
    md_lines.append(f"**Audit type:** T05k Gravír Layer Geometry Review")
    md_lines.append("")
    md_lines.append("## Entity Summary")
    md_lines.append(f"- Total entities: {len(entities)}")
    md_lines.append(f"- Layers: {', '.join(layers)}")
    md_lines.append(f"- Gravír layer text entities: {len(text_entities_gravir)}")
    md_lines.append(f"- Total contours: {len(classified_contours)}")
    md_lines.append("")

    md_lines.append("## Layer Summary")
    md_lines.append("")
    md_lines.append("| layer | entity_types | entity_count | text_count | closed_rings | total_area_mm² | cut_candidates | marking_candidates |")
    md_lines.append("|-------|-------------|-------------|-----------|-------------|----------------|----------------|--------------------|")
    for ls in layer_summary:
        md_lines.append(
            f"| {ls['layer_name']} | {','.join(ls['entity_types'])} | {ls['entity_count']} | "
            f"{ls['text_mtext_count']} | {ls['closed_ring_count']} | {ls['total_area_mm2']:.2f} | "
            f"{ls['cut_candidate_count']} | {ls['marking_candidate_count']} |"
        )
    md_lines.append("")

    md_lines.append("## Contour Classification")
    md_lines.append("")
    md_lines.append("| contour_id | layer | depth | area_mm² | current_role | proposed_interpretation | confidence | reason |")
    md_lines.append("|------------|-------|-------|---------|-------------|------------------------|------------|--------|")
    for c in sorted(classified_contours, key=lambda x: (x["depth"], x["source_layer"], x["ring_index"])):
        cid = f"{c['source_layer']}:{c['ring_index']}"
        md_lines.append(
            f"| {cid} | {c['source_layer']} | {c['depth']} | {c['area_abs_mm2']:.2f} | "
            f"{c['current_role']} | {c['proposed_interpretation']} | {c['confidence']} | "
            f"{c['reason'][:60]} |"
        )
    md_lines.append("")

    md_lines.append("## Gravír Layer Text Entities")
    if text_entities_gravir:
        md_lines.append("")
        md_lines.append("| entity_type | text | insert | height |")
        md_lines.append("|-------------|------|--------|--------|")
        for te in text_entities_gravir:
            md_lines.append(
                f"| {te['entity_type']} | {str(te.get('text',''))[:40]} | {te.get('insert')} | {te.get('height')} |"
            )
    else:
        md_lines.append("*(none found)*")
    md_lines.append("")

    md_lines.append("## Decision Summary")
    gravir_contours = [c for c in classified_contours if c["source_layer"].lower() in ("gravír", "gravir")]
    md_lines.append(f"- Gravír layer contours: {len(gravir_contours)}")
    for c in gravir_contours:
        md_lines.append(f"  - [{c['source_layer']}:{c['ring_index']}] depth={c['depth']} "
                        f"interpretation={c['proposed_interpretation']} confidence={c['confidence']}")
        md_lines.append(f"    reason: {c['reason']}")
    md_lines.append("")
    md_lines.append("## ASCII Debug Export Path")
    md_lines.append(f"`tmp/reports/nfp_cgal_probe/t05k_lv8_11612_nested_contours_ascii.md`")

    return output, "\n".join(md_lines), "\n".join(ascii_lines)


def main():
    if not DXF_PATH.exists():
        print(f"ERROR: file not found: {DXF_PATH}", file=sys.stderr)
        sys.exit(1)

    output, md_content, ascii_content = audit_gravir_layer(DXF_PATH)

    # Save outputs
    json_out = OUT_DIR / "t05k_lv8_11612_gravir_entity_audit.json"
    md_out = OUT_DIR / "t05k_lv8_11612_gravir_entity_audit.md"
    ascii_out = OUT_DIR / "t05k_lv8_11612_nested_contours_ascii.md"

    with open(json_out, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {json_out}")

    with open(md_out, "w") as f:
        f.write(md_content)
    print(f"Saved: {md_out}")

    with open(ascii_out, "w") as f:
        f.write(ascii_content)
    print(f"Saved: {ascii_out}")

    # Print markdown to stdout
    print("\n" + "="*70)
    print(md_content)


if __name__ == "__main__":
    main()
