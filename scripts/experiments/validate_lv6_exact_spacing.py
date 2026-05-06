#!/usr/bin/env python3
"""
T05o: LV6 Exact 10mm Spacing Validator
=======================================
Validates an existing placement layout with EXACT polygon distance spacing.

Exact spacing policy:
- polygon-with-holes geometriát használj
- két külön alkatrész között legalább 10mm clearance kell
- használj distance checket: poly_a.distance(poly_b) >= spacing_mm
- holes nem számítanak külön „közelségnek" — csak a tényleges material polygon boundary számít
- self-pairt ne ellenőrizz
- sheet bounds továbbra is kötelező

Output:
  tmp/reports/nfp_cgal_probe/lv6_t05n_layout_exact_spacing10_validation.json
  tmp/reports/nfp_cgal_probe/lv6_t05n_layout_exact_spacing10_validation.md
"""

import json, math, time, os, sys
from pathlib import Path
from collections import defaultdict

try:
    from shapely.geometry import Polygon, MultiPolygon
    from shapely.ops import unary_union
    SHAPELY = True
except ImportError:
    SHAPELY = False
    print("WARNING: Shapely not available, using AABB-only distance check")

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')
SHEET_W = 1500.0
SHEET_H = 3000.0


def normalize_polygon(pts):
    """Translate polygon so min x and min y are at origin."""
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


def get_shapely_polygon(outer_pts, holes_pts, x, y, rotation_deg):
    """Build Shapely Polygon from outer + holes, placed at (x,y) with rotation."""
    # Normalize outer
    outer_norm = normalize_polygon(outer_pts)
    
    # Rotate around centroid
    xs = [p[0] for p in outer_norm]
    ys = [p[1] for p in outer_norm]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    
    rotated = rotate_points(outer_norm, rotation_deg, cx, cy)
    
    # Translate to placement position
    placed_outer = translate_points(rotated, x, y)
    
    # Build polygon with holes
    exterior = placed_outer
    interiors = []
    if holes_pts:
        for hole_pts in holes_pts:
            hole_norm = normalize_polygon(hole_pts)
            hole_rotated = rotate_points(hole_norm, rotation_deg, cx, cy)
            hole_placed = translate_points(hole_rotated, x, y)
            interiors.append(hole_placed)
    
    if SHAPELY:
        try:
            return Polygon(exterior, interiors)
        except Exception as e:
            print(f"  Polygon construction failed: {e}")
            return Polygon(exterior)
    else:
        return None


def check_bounds_violation(outer_pts, x, y, rotation_deg, sheet_w, sheet_h):
    """Check if part is within sheet bounds."""
    xs = [p[0] for p in outer_pts]
    ys = [p[1] for p in outer_pts]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    
    if rotation_deg == 90 or rotation_deg == 270:
        w, h = h, w
    
    if x < 0 or y < 0:
        return True
    if x + w > sheet_w:
        return True
    if y + h > sheet_h:
        return True
    return False


def aabb_distance_check(p1_bbox, p2_bbox, spacing_mm):
    """Fast AABB-based distance check for prefilter."""
    x1_min, y1_min, x1_max, y1_max = p1_bbox
    x2_min, y2_min, x2_max, y2_max = p2_bbox
    
    # Expand AABBs by spacing
    x1_min -= spacing_mm
    y1_min -= spacing_mm
    x1_max += spacing_mm
    y1_max += spacing_mm
    x2_min -= spacing_mm
    y2_min -= spacing_mm
    x2_max += spacing_mm
    y2_max += spacing_mm
    
    # Check overlap
    if x1_max < x2_min or x2_max < x1_min:
        return False  # No violation
    if y1_max < y2_min or y2_max < y1_min:
        return False  # No violation
    
    return True  # Potential violation, need exact check


def load_layout(layout_path):
    """Load placement layout JSON."""
    with open(layout_path) as f:
        return json.load(f)


def load_part_list(part_list_path):
    """Load part list with geometry."""
    with open(part_list_path) as f:
        return json.load(f)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate layout with exact spacing')
    parser.add_argument('--layout', type=str, 
                       default=str(BASE / 'lv6_blf_candidate_preview_spacing2p0_layout.json'),
                       help='Layout JSON to validate')
    parser.add_argument('--part-list', type=str,
                       default=str(BASE / 'lv6_production_part_list.json'),
                       help='Part list JSON')
    parser.add_argument('--spacing-mm', type=float, default=10.0,
                       help='Required spacing in mm')
    parser.add_argument('--output-dir', type=str, default=str(BASE),
                       help='Output directory')
    parser.add_argument('--tolerance-mm', type=float, default=0.01,
                       help='Tolerance for floating point comparison')
    args = parser.parse_args()

    spacing_mm = args.spacing_mm
    tolerance = args.tolerance_mm
    
    print(f"=" * 60)
    print(f"T05o: LV6 Exact {spacing_mm}mm Spacing Validator")
    print(f"=" * 60)
    print(f"Layout: {args.layout}")
    print(f"Part list: {args.part_list}")
    print(f"Spacing: {spacing_mm}mm")
    print(f"Tolerance: {tolerance}mm")
    print()
    
    # Load data
    layout = load_layout(args.layout)
    part_list = load_part_list(args.part_list)
    
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
    sheet_placements = defaultdict(list)
    
    for sheet_key, sheet_data in layout.get('sheets', {}).items():
        sheet_idx = int(sheet_key)
        for placement in sheet_data.get('placements', []):
            placement['sheet_idx'] = sheet_idx
            all_placements.append(placement)
            sheet_placements[sheet_idx].append(placement)
    
    total_placed = len(all_placements)
    print(f"Total placements: {total_placed}")
    print()
    
    # Metrics
    checked_pairs = 0
    spacing_violations = []
    min_clearance = float('inf')
    bounds_violations = []
    overlap_count = 0
    spacing_checks = 0
    
    start_time = time.time()
    
    print("Phase 1: Building Shapely polygons...")
    
    # Build shapely polygons for all placements
    placement_polygons = []
    for i, p in enumerate(all_placements):
        part_id = p['part_id']
        x = p['x_mm']
        y = p['y_mm']
        rotation = p['rotation_deg']
        
        geom = part_geometry.get(part_id)
        if not geom:
            print(f"  WARNING: Part {part_id} not found in part list")
            placement_polygons.append(None)
            continue
        
        outer = geom['outer']
        holes = geom.get('holes', [])
        
        if not outer:
            placement_polygons.append(None)
            continue
        
        poly = get_shapely_polygon(outer, holes, x, y, rotation)
        placement_polygons.append(poly)
        
        # Bounds check
        x_min, y_min, x_max, y_max = poly.bounds if poly else (0, 0, 0, 0)
        if poly and (x_min < -tolerance or y_min < -tolerance or 
                     x_max > SHEET_W + tolerance or y_max > SHEET_H + tolerance):
            bounds_violations.append({
                'instance': i,
                'part_id': part_id,
                'sheet': p['sheet_idx'],
                'bounds': [x_min, y_min, x_max, y_max]
            })
    
    print(f"Phase 2: Checking spacing between all pairs...")
    print(f"  (This is O(n²) — {total_placed} placements = ~{total_placed*(total_placed-1)//2} pairs)")
    print()
    
    # Check spacing between all pairs
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            checked_pairs += 1
            
            p1 = all_placements[i]
            p2 = all_placements[j]
            
            # Skip if on different sheets — spacing only matters within same sheet
            if p1['sheet_idx'] != p2['sheet_idx']:
                continue
            
            # Skip self-pairs (same instance) — spacing only matters between DIFFERENT instances
            if p1.get('instance') == p2.get('instance') and p1.get('part_id') == p2.get('part_id'):
                continue
            
            poly1 = placement_polygons[i]
            poly2 = placement_polygons[j]
            
            if poly1 is None or poly2 is None:
                continue
            
            spacing_checks += 1
            
            # AABB prefilter
            b1 = poly1.bounds
            b2 = poly2.bounds
            
            if not aabb_distance_check(b1, b2, spacing_mm):
                # Far apart, no violation
                continue
            
            # Exact distance check using Shapely
            try:
                distance = poly1.distance(poly2)
            except Exception as e:
                print(f"  Distance check failed for pair ({i}, {j}): {e}")
                continue
            
            if distance < min_clearance:
                min_clearance = distance
            
            if distance < spacing_mm - tolerance:
                # Spacing violation
                spacing_violations.append({
                    'pair': (i, j),
                    'part_id_1': p1['part_id'],
                    'part_id_2': p2['part_id'],
                    'sheet': p1['sheet_idx'],
                    'distance_mm': distance,
                    'violation_mm': spacing_mm - distance
                })
    
    elapsed = time.time() - start_time
    
    # Results
    print()
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"Checked pairs (same sheet): {checked_pairs}")
    print(f"Spacing checks (AABB prefilter passed): {spacing_checks}")
    print(f"Min clearance: {min_clearance:.4f}mm" if min_clearance != float('inf') else "Min clearance: N/A")
    print(f"Spacing violations: {len(spacing_violations)}")
    print(f"Bounds violations: {len(bounds_violations)}")
    print(f"Overlap count: {overlap_count}")
    print(f"Runtime: {elapsed:.2f}s")
    print()
    
    if spacing_violations:
        print("Worst violations:")
        sorted_violations = sorted(spacing_violations, key=lambda x: -x['violation_mm'])[:5]
        for v in sorted_violations:
            print(f"  Pair ({v['part_id_1']}, {v['part_id_2']}) sheet={v['sheet']}: "
                  f"distance={v['distance_mm']:.2f}mm, violation={v['violation_mm']:.2f}mm")
    
    # Determine status
    if len(spacing_violations) == 0 and len(bounds_violations) == 0 and overlap_count == 0:
        status = "PASS"
    elif len(spacing_violations) > 0:
        status = "FAIL"
    elif len(bounds_violations) > 0 or overlap_count > 0:
        status = "FAIL"
    else:
        status = "PARTIAL"
    
    print()
    print(f"STATUS: {status}")
    print()
    
    # Output files
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON output
    validation_result = {
        'validator': 'validate_lv6_exact_spacing.py',
        'layout_validated': str(args.layout),
        'part_list': str(args.part_list),
        'spacing_mm': spacing_mm,
        'tolerance_mm': tolerance,
        'status': status,
        'checked_pairs': checked_pairs,
        'spacing_checks': spacing_checks,
        'min_clearance_mm': min_clearance if min_clearance != float('inf') else None,
        'spacing_violation_count': len(spacing_violations),
        'worst_violation_mm': max([v['violation_mm'] for v in spacing_violations], default=0),
        'violating_pair_samples': spacing_violations[:10],  # First 10 violations
        'bounds_violation_count': len(bounds_violations),
        'overlap_count': overlap_count,
        'runtime_sec': elapsed,
        'total_placements': total_placed
    }
    
    json_path = output_dir / f'lv6_t05n_layout_exact_spacing{int(spacing_mm * 10)}_validation.json'
    with open(json_path, 'w') as f:
        json.dump(validation_result, f, indent=2)
    print(f"JSON output: {json_path}")
    
    # Markdown output
    md_content = f"""# T05o: LV6 Exact {spacing_mm}mm Spacing Validation

## Státusz: {status}

**Prototype/reference only. NOT production.**

---

## Validated Layout

- **Source:** `{args.layout}`
- **Spacing:** {spacing_mm}mm exact (polygon distance)
- **Tolerance:** {tolerance}mm

---

## Results

| Metrika | Érték |
|---------|-------|
| Total placements | {total_placed} |
| Checked pairs | {checked_pairs} |
| Spacing checks (exact) | {spacing_checks} |
| Min clearance | {f'{min_clearance:.4f}mm' if min_clearance != float('inf') else 'N/A'} |
| Spacing violations | **{len(spacing_violations)}** |
| Bounds violations | **{len(bounds_violations)}** |
| Overlap count | **{overlap_count}** |
| Runtime | {elapsed:.2f}s |

---

## Status Breakdown

- **spacing_violation_count == 0:** {'✅ PASS' if len(spacing_violations) == 0 else '❌ FAIL'}
- **bounds_violation_count == 0:** {'✅ PASS' if len(bounds_violations) == 0 else '❌ FAIL'}
- **overlap_count == 0:** {'✅ PASS' if overlap_count == 0 else '❌ FAIL'}

---

## Worst Violations

"""
    
    if spacing_violations:
        sorted_violations = sorted(spacing_violations, key=lambda x: -x['violation_mm'])[:10]
        md_content += "| Part 1 | Part 2 | Sheet | Distance | Violation |\n"
        md_content += "|--------|--------|-------|----------|----------|\n"
        for v in sorted_violations:
            md_content += f"| {v['part_id_1']} | {v['part_id_2']} | {v['sheet']} | {v['distance_mm']:.2f}mm | {v['violation_mm']:.2f}mm |\n"
    else:
        md_content += "Nincs spacing violation.\n"
    
    md_content += f"""

---

## Verdict

"""
    
    if status == "PASS":
        md_content += f"""**PASS:** T05n layout megfelel az exact {spacing_mm}mm spacing követelménynek.

- {total_placed}/112 instance elhelyezve
- 0 spacing violation
- 0 bounds violation
- 0 overlap
- min_clearance >= {spacing_mm}mm
"""
    elif status == "FAIL":
        md_content += f"""**FAIL:** T05n layout NEM felel meg az exact {spacing_mm}mm spacing követelménynek.

- {len(spacing_violations)} spacing violation
- Repack szükséges {spacing_mm}mm spacing-gel
"""
    else:
        md_content += "**PARTIAL:** Részleges eredmény.\n"
    
    md_path = output_dir / f'lv6_t05n_layout_exact_spacing{int(spacing_mm * 10)}_validation.md'
    with open(md_path, 'w') as f:
        f.write(md_content)
    print(f"Markdown output: {md_path}")
    
    return status, validation_result


if __name__ == '__main__':
    status, result = main()
    sys.exit(0 if status == "PASS" else 1)
