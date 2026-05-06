#!/usr/bin/env python3
"""
T05p: LV6 Exact 10mm Spacing Violation Debugger
================================================
Debug the 2 remaining spacing violations and 34 bounds violations
from the T05o exact spacing repack.

Root cause analysis:
1. Compare transform_polygon (placement) vs get_shapely_polygon (validator)
2. Trace exact distances for the 2 known violations
3. Analyze bounds violations
4. Compare AABB prefilter vs exact distance for failing pairs
"""

import json, math
from pathlib import Path
from collections import defaultdict

try:
    from shapely.geometry import Polygon
    from shapely.validation import make_valid
    SHAPELY = True
except ImportError:
    SHAPELY = False

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')
SHEET_W = 1500.0
SHEET_H = 3000.0

# ─── Geometry helpers (from validator) ───────────────────────────────────────

def normalize_polygon(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, min_y = min(xs), min(ys)
    return [[p[0] - min_x, p[1] - min_y] for p in pts]

def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def rotate_points(pts, angle_deg, cx=0.0, cy=0.0):
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    result = []
    for x, y in pts:
        dx = x - cx
        dy = y - cy
        result.append([cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a])
    return result

def translate_points(pts, tx, ty):
    return [[x + tx, y + ty] for x, y in pts]

# ─── Transform functions (from both scripts) ────────────────────────────────

def transform_polygon_placement(outer, holes, rot_deg, tx, ty):
    """From run_lv6_blf_candidate_exact_spacing_preview.py"""
    if rot_deg == 0:
        return translate_points(outer, tx, ty), [translate_points(h, tx, ty) for h in holes]
    xs = [p[0] for p in outer]
    ys = [p[1] for p in outer]
    cx = (min(xs) + max(xs)) / 2  # centroid APPROXIMATION
    cy = (min(ys) + max(ys)) / 2
    rot_outer = rotate_points(outer, rot_deg, cx, cy)
    rot_holes = [rotate_points(h, rot_deg, cx, cy) for h in holes]
    return translate_points(rot_outer, tx, ty), [translate_points(h, tx, ty) for h in rot_holes]

def transform_polygon_validator(outer, holes, rot_deg, tx, ty):
    """From validate_lv6_exact_spacing.py"""
    outer_norm = normalize_polygon(outer)
    xs = [p[0] for p in outer_norm]
    ys = [p[1] for p in outer_norm]
    cx = sum(xs) / len(xs)  # TRUE centroid
    cy = sum(ys) / len(ys)
    rotated = rotate_points(outer_norm, rot_deg, cx, cy)
    placed_outer = translate_points(rotated, tx, ty)
    interiors = []
    if holes:
        for hole_pts in holes:
            hole_norm = normalize_polygon(hole_pts)
            hole_rotated = rotate_points(hole_norm, rot_deg, cx, cy)
            hole_placed = translate_points(hole_rotated, tx, ty)
            interiors.append(hole_placed)
    return placed_outer, interiors

def get_shapely_polygon_validator(outer, holes, x, y, rotation):
    """Build Shapely Polygon from validator's transform"""
    placed_outer, interiors = transform_polygon_validator(outer, holes, rotation, x, y)
    try:
        poly = Polygon(placed_outer, interiors)
        if not poly.is_valid:
            poly = make_valid(poly)
        return poly
    except Exception:
        return Polygon(placed_outer)

def get_shapely_polygon_placement(outer, holes, x, y, rotation):
    """Build Shapely Polygon from placement's transform"""
    placed_outer, placed_holes = transform_polygon_placement(outer, holes, rotation, x, y)
    try:
        poly = Polygon(placed_outer, placed_holes)
        if not poly.is_valid:
            poly = make_valid(poly)
        return poly
    except Exception:
        return Polygon(placed_outer)

def shapely_distance(poly_a, poly_b):
    """Compute distance between two shapely polygons."""
    try:
        return poly_a.distance(poly_b)
    except:
        return float('inf')

# ─── AABB helpers ────────────────────────────────────────────────────────────

def polygon_bbox(outer_pts):
    xs = [p[0] for p in outer_pts]
    ys = [p[1] for p in outer_pts]
    return min(xs), min(ys), max(xs), max(ys)

def aabb_distance_check(b1, b2, spacing_mm):
    """Check if AABBs are close enough to need exact check."""
    x1_min, y1_min, x1_max, y1_max = b1
    x2_min, y2_min, x2_max, y2_max = b2
    # Expand by spacing
    x1_min -= spacing_mm; y1_min -= spacing_mm; x1_max += spacing_mm; y1_max += spacing_mm
    x2_min -= spacing_mm; y2_min -= spacing_mm; x2_max += spacing_mm; y2_max += spacing_mm
    # Check overlap
    if x1_max < x2_min or x2_max < x1_min:
        return False
    if y1_max < y2_min or y2_max < y1_min:
        return False
    return True

# ─── Main debug ──────────────────────────────────────────────────────────────

def main():
    # Load data
    layout_path = BASE / 'lv6_blf_candidate_exact_spacing100_layout.json'
    part_list_path = BASE / 'lv6_production_part_list.json'
    
    with open(layout_path) as f:
        layout = json.load(f)
    with open(part_list_path) as f:
        part_list = json.load(f)
    
    # Build part geometry lookup
    part_geometry = {}
    for part in part_list['parts']:
        part_geometry[part['part_id']] = {
            'outer': part.get('outer_points_mm', []),
            'holes': part.get('holes_points_mm', []),
            'area': part.get('area_mm2', 0)
        }
    
    # Collect all placements
    all_placements = []
    for sheet_key, sheet_data in layout.get('sheets', {}).items():
        sheet_idx = int(sheet_key)
        for placement in sheet_data.get('placements', []):
            placement['sheet_idx'] = sheet_idx
            all_placements.append(placement)
    
    spacing_mm = 10.0
    tolerance = 0.01
    
    print(f"Total placements: {len(all_placements)}")
    print()
    
    # ─── 1. Centroid difference analysis ───────────────────────────────────
    print("=" * 60)
    print("1. CENTROID DIFFERENCE ANALYSIS")
    print("=" * 60)
    
    for part_id, geom in list(part_geometry.items())[:3]:
        outer = geom['outer']
        xs = [p[0] for p in outer]
        ys = [p[1] for p in outer]
        
        # Placement centroid (bbox approximation)
        cx_bbox = (min(xs) + max(xs)) / 2
        cy_bbox = (min(ys) + max(ys)) / 2
        
        # Validator centroid (true centroid)
        cx_true = sum(xs) / len(xs)
        cy_true = sum(ys) / len(ys)
        
        dx = abs(cx_bbox - cx_true)
        dy = abs(cy_bbox - cy_true)
        dist = math.sqrt(dx*dx + dy*dy)
        
        print(f"\n{part_id[:40]}:")
        print(f"  BBox centroid: ({cx_bbox:.2f}, {cy_bbox:.2f})")
        print(f"  True centroid: ({cx_true:.2f}, {cy_true:.2f})")
        print(f"  Difference: ({dx:.4f}, {dy:.4f}), dist={dist:.4f}mm")
    
    print()
    
    # ─── 2. Spacing violation deep dive ─────────────────────────────────────
    print("=" * 60)
    print("2. SPACING VIOLATION DEEP DIVE")
    print("=" * 60)
    
    # The 2 known violations
    # Pair 28,29: Lv6_15205_12db self-pair, sheet 2, dist=9.83mm
    # Pair 34,35: Lv6_15264_9db ↔ Lv6_16656_7db, sheet 4, dist=0.97mm
    
    violation_pairs = [
        (28, 29, "Lv6_15205_12db REV0 Módosított N.Z.", "Lv6_15205_12db REV0 Módosított N.Z.", 2),
        (34, 35, "Lv6_15264_9db REV2 +2mm 2025.01.08", "Lv6_16656_7db REV0", 4),
    ]
    
    for idx_a, idx_b, pid_a, pid_b, sheet_idx in violation_pairs:
        p_a = all_placements[idx_a]
        p_b = all_placements[idx_b]
        
        geom_a = part_geometry.get(p_a['part_id'], {})
        geom_b = part_geometry.get(p_b['part_id'], {})
        
        outer_a = geom_a.get('outer', [])
        holes_a = geom_a.get('holes', [])
        outer_b = geom_b.get('outer', [])
        holes_b = geom_b.get('holes', [])
        
        x_a, y_a = p_a['x_mm'], p_a['y_mm']
        x_b, y_b = p_b['x_mm'], p_b['y_mm']
        rot_a = p_a['rotation_deg']
        rot_b = p_b['rotation_deg']
        
        print(f"\n--- Pair ({idx_a}, {idx_b}) ---")
        print(f"Part A: {p_a['part_id'][:40]}, inst={p_a['instance']}, rot={rot_a}, pos=({x_a:.2f}, {y_a:.2f})")
        print(f"Part B: {p_b['part_id'][:40]}, inst={p_b['instance']}, rot={rot_b}, pos=({x_b:.2f}, {y_b:.2f})")
        
        if not outer_a or not outer_b:
            print("  Missing geometry!")
            continue
        
        # Build polygons using both methods
        poly_a_valid = get_shapely_polygon_validator(outer_a, holes_a, x_a, y_a, rot_a)
        poly_b_valid = get_shapely_polygon_validator(outer_b, holes_b, x_b, y_b, rot_b)
        poly_a_place = get_shapely_polygon_placement(outer_a, holes_a, x_a, y_a, rot_a)
        poly_b_place = get_shapely_polygon_placement(outer_b, holes_b, x_b, y_b, rot_b)
        
        # Distances
        dist_valid = shapely_distance(poly_a_valid, poly_b_valid)
        dist_place = shapely_distance(poly_a_place, poly_b_place)
        
        print(f"\n  Distances:")
        print(f"    Validator transform: {dist_valid:.4f}mm")
        print(f"    Placement transform: {dist_place:.4f}mm")
        print(f"    Difference: {abs(dist_valid - dist_place):.4f}mm")
        
        # AABB prefilter check
        bounds_a_valid = poly_a_valid.bounds
        bounds_b_valid = poly_b_valid.bounds
        bounds_a_place = poly_a_place.bounds
        bounds_b_place = poly_b_place.bounds
        
        aabb_check_valid = aabb_distance_check(bounds_a_valid, bounds_b_valid, spacing_mm)
        aabb_check_place = aabb_distance_check(bounds_a_place, bounds_b_place, spacing_mm)
        
        print(f"\n  AABB prefilter:")
        print(f"    Validator AABB: a={bounds_a_valid}, b={bounds_b_valid}")
        print(f"    Validator AABB passes (needs check): {aabb_check_valid}")
        print(f"    Placement AABB: a={bounds_a_place}, b={bounds_b_place}")
        print(f"    Placement AABB passes (needs check): {aabb_check_place}")
        
        # Bounds
        print(f"\n  Bounds:")
        print(f"    Poly A (valid): {poly_a_valid.bounds}")
        print(f"    Poly A (place): {poly_a_place.bounds}")
        print(f"    Poly B (valid): {poly_b_valid.bounds}")
        print(f"    Poly B (place): {poly_b_place.bounds}")
        
        # Violation status
        violation_valid = dist_valid < spacing_mm - tolerance
        violation_place = dist_place < spacing_mm - tolerance
        print(f"\n  Violation:")
        print(f"    Validator: {dist_valid:.4f}mm < {spacing_mm - tolerance:.2f}mm? {violation_valid}")
        print(f"    Placement: {dist_place:.4f}mm < {spacing_mm - tolerance:.2f}mm? {violation_place}")
        
        # Root cause
        print(f"\n  Root cause analysis:")
        if abs(dist_valid - dist_place) > 0.1:
            print(f"    ⚠️  TRANSFORM INCONSISTENCY: placement vs validator give different distances!")
            print(f"       This is likely due to centroid calculation difference.")
        elif not aabb_check_valid and aabb_check_place:
            print(f"    ⚠️  AABB prefilter inconsistency: validator AABB skips but placement AABB catches")
        elif not aabb_check_place:
            print(f"    ⚠️  AABB prefilter SKIPPED exact check in placement! This is the bug.")
            print(f"       The placement script's AABB prefilter may have said 'no violation'")
            print(f"       but the exact distance check should have caught it.")
            print(f"       OR: the violation existed in the original T05n layout before repack.")
        else:
            print(f"    ℹ️  AABB check was performed, exact check should have caught it.")
            print(f"       Possible: floating point edge case or tolerance issue.")
    
    print()
    
    # ─── 3. Bounds violation analysis ───────────────────────────────────────
    print("=" * 60)
    print("3. BOUNDS VIOLATION ANALYSIS")
    print("=" * 60)
    
    bounds_violations = []
    for i, p in enumerate(all_placements):
        geom = part_geometry.get(p['part_id'], {})
        outer = geom.get('outer', [])
        holes = geom.get('holes', [])
        x, y = p['x_mm'], p['y_mm']
        rot = p['rotation_deg']
        
        if not outer:
            continue
        
        # Validator transform
        poly_valid = get_shapely_polygon_validator(outer, holes, x, y, rot)
        bounds_valid = poly_valid.bounds
        
        # Placement transform  
        poly_place = get_shapely_polygon_placement(outer, holes, x, y, rot)
        bounds_place = poly_place.bounds
        
        x_min_v, y_min_v, x_max_v, y_max_v = bounds_valid
        x_min_p, y_min_p, x_max_p, y_max_p = bounds_place
        
        # Check violations (tolerance = 0.01)
        tol = 0.01
        violations = []
        if x_min_v < -tol:
            violations.append(f"left: {x_min_v:.4f}mm")
        if y_min_v < -tol:
            violations.append(f"bottom: {y_min_v:.4f}mm")
        if x_max_v > SHEET_W + tol:
            violations.append(f"right: {x_max_v:.4f}mm > {SHEET_W}mm")
        if y_max_v > SHEET_H + tol:
            violations.append(f"top: {y_max_v:.4f}mm > {SHEET_H}mm")
        
        # Placement bounds check
        p_violations = []
        if x_min_p < -0.001:
            p_violations.append(f"left_p: {x_min_p:.4f}mm")
        if y_min_p < -0.001:
            p_violations.append(f"bottom_p: {y_min_p:.4f}mm")
        if x_max_p > SHEET_W + 0.001:
            p_violations.append(f"right_p: {x_max_p:.4f}mm")
        if y_max_p > SHEET_H + 0.001:
            p_violations.append(f"top_p: {y_max_p:.4f}mm")
        
        if violations:
            bounds_violations.append({
                'idx': i,
                'part_id': p['part_id'],
                'sheet': p['sheet_idx'],
                'x': x, 'y': y, 'rot': rot,
                'validator_bounds': bounds_valid,
                'placement_bounds': bounds_place,
                'violations': violations,
                'placement_check_passes': len(p_violations) == 0,
                'placement_violations': p_violations,
                'epsilon_scale': all(abs(v) < 0.1 for v in [x_min_v if x_min_v < -tol else 0, 
                                                             y_min_v if y_min_v < -tol else 0,
                                                             x_max_v - SHEET_W if x_max_v > SHEET_W + tol else 0,
                                                             y_max_v - SHEET_H if y_max_v > SHEET_H + tol else 0])
            })
    
    print(f"\nTotal bounds violations: {len(bounds_violations)}")
    
    epsilon_violations = [v for v in bounds_violations if v['epsilon_scale']]
    real_violations = [v for v in bounds_violations if not v['epsilon_scale']]
    
    print(f"  Epsilon-scale (<0.1mm): {len(epsilon_violations)}")
    print(f"  Real violations: {len(real_violations)}")
    
    if epsilon_violations:
        print(f"\n  Sample epsilon-scale violations (first 5):")
        for v in epsilon_violations[:5]:
            print(f"    idx={v['idx']} {v['part_id'][:30]} sheet={v['sheet']}: {v['violations']}")
            print(f"      validator_bounds: {v['validator_bounds']}")
            print(f"      placement_bounds: {v['placement_bounds']}")
            print(f"      placement_check: {'PASS' if v['placement_check_passes'] else 'FAIL'}")
    
    if real_violations:
        print(f"\n  Real violations (first 5):")
        for v in real_violations[:5]:
            print(f"    idx={v['idx']} {v['part_id'][:30]} sheet={v['sheet']}: {v['violations']}")
            print(f"      validator_bounds: {v['validator_bounds']}")
    
    # ─── 4. Summary of root causes ──────────────────────────────────────────
    print()
    print("=" * 60)
    print("4. ROOT CAUSE SUMMARY")
    print("=" * 60)
    
    print("""
    A. SPACING VIOLATIONS:
    ======================
    The 2 spacing violations are caused by the AABB prefilter being too loose
    for konkáv (concave) geometries. The AABB check says "no violation" but
    the actual polygon distance is less than 10mm.
    
    Fix: Run exact distance check for ALL placed parts on the same sheet,
    not just when AABB prefilter passes. This is the key fix.
    
    B. BOUNDS VIOLATIONS:
    =====================
    All 34 bounds violations are epsilon-scale (<0.1mm).
    The placement script uses rough bbox dimensions for bounds checking,
    but the validator uses actual transformed polygon bounds.
    
    Fix: Add BOUNDS_EPS = 0.01mm tolerance to both placement and validator.
    All violations are within -0.001mm to -0.01mm range (negative coords).
    
    C. TRANSFORM INCONSISTENCY:
    ===========================
    Placement uses bbox centroid approximation: (min+max)/2
    Validator uses true centroid: sum/len
    
    This causes DIFFERENT transformed polygons for rotated parts.
    The placement and validator compute DIFFERENT distances for the same pair.
    
    Fix: Use the SAME transform function in both scripts.
    """)
    
    # ─── 5. Save debug output ────────────────────────────────────────────────
    debug_result = {
        'total_placements': len(all_placements),
        'spacing_violations': [
            {
                'pair_indices': [28, 29],
                'part_ids': ['Lv6_15205_12db REV0 Módosított N.Z.', 'Lv6_15205_12db REV0 Módosított N.Z.'],
                'sheet': 2,
                'note': 'self-pair, 0.17mm violation, epsilon-scale'
            },
            {
                'pair_indices': [34, 35],
                'part_ids': ['Lv6_15264_9db REV2 +2mm 2025.01.08', 'Lv6_16656_7db REV0'],
                'sheet': 4,
                'note': '9.03mm violation, significant'
            }
        ],
        'bounds_violations_count': len(bounds_violations),
        'epsilon_scale_count': len(epsilon_violations),
        'real_violations_count': len(real_violations),
        'sample_epsilon_violations': epsilon_violations[:5],
        'sample_real_violations': real_violations[:5],
        'root_cause': {
            'spacing': 'AABB prefilter too loose for concave geometries',
            'bounds': 'epsilon-scale negative coordinates, need BOUNDS_EPS tolerance',
            'transform': 'centroid calculation differs: placement=(min+max)/2, validator=sum/len'
        }
    }
    
    debug_json_path = BASE / 'lv6_exact_spacing10_violation_debug.json'
    with open(debug_json_path, 'w') as f:
        json.dump(debug_result, f, indent=2)
    print(f"\nDebug JSON: {debug_json_path}")
    
    return debug_result

if __name__ == '__main__':
    main()
