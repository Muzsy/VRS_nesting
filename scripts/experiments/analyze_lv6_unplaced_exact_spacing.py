#!/usr/bin/env python3
"""
T05q: Analyze LV6 unplaced instances for exact 10mm spacing.
================================================================
Checks whether each unplaced instance can fit on an empty 1500×3000 sheet
with 10mm spacing, at various rotations.

Output:
  tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_unplaced_analysis.json
  tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_unplaced_analysis.md
"""

import json, math, os, sys
from pathlib import Path

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')
SHEET_W = 1500.0
SHEET_H = 3000.0
SPACING = 10.0
# Sheet edge margin: 0mm (spacing applies to part-part only)
SHEET_MARGIN = 0.0

def normalize_polygon(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, min_y = min(xs), min(ys)
    return [[p[0] - min_x, p[1] - min_y] for p in pts]

def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def bbox_dims(pts):
    x0, y0, x1, y1 = bbox(pts)
    return x1 - x0, y1 - y0

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

def polygon_area(pts):
    n = len(pts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return abs(area) / 2.0

def check_fits_on_empty_sheet(outer_pts, holes_pts, rotation_deg, sheet_w, sheet_h, margin):
    """
    Check if part (at given rotation) fits on an empty sheet.
    Returns (fits, reason)
    """
    # Normalize
    outer_norm = normalize_polygon(outer_pts)
    norm_holes = [normalize_polygon(h) for h in holes_pts] if holes_pts else []
    
    # True centroid
    xs = [p[0] for p in outer_norm]
    ys = [p[1] for p in outer_norm]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    
    # Rotate
    rot_outer = rotate_points(outer_norm, rotation_deg, cx, cy)
    rot_holes = [rotate_points(h, rotation_deg, cx, cy) for h in norm_holes]
    
    # Get bounding box of rotated polygon
    all_pts = rot_outer[:]
    for h in rot_holes:
        all_pts.extend(h)
    bw, bh = bbox_dims(all_pts)
    
    # Usable sheet area
    usable_w = sheet_w - 2 * margin
    usable_h = sheet_h - 2 * margin
    
    if bw <= usable_w and bh <= usable_h:
        return True, f"FITS: bbox={bw:.1f}x{bh:.1f} <= {usable_w:.1f}x{usable_h:.1f}"
    else:
        reason = f"DOES NOT FIT: bbox={bw:.1f}x{bh:.1f} > {usable_w:.1f}x{usable_h:.1f}"
        if bw > usable_w and bh > usable_h:
            reason += " (both dimensions exceed sheet)"
        elif bw > usable_w:
            reason += f" (width {bw:.1f} > {usable_w:.1f})"
        else:
            reason += f" (height {bh:.1f} > {usable_h:.1f})"
        return False, reason

def main():
    print("=" * 60)
    print("T05q: LV6 Unplaced Instance Analysis")
    print("=" * 60)
    print(f"Sheet: {SHEET_W}x{SHEET_H}mm")
    print(f"Spacing: {SPACING}mm")
    print(f"Sheet edge margin: {SHEET_MARGIN}mm")
    print()
    
    # Load part list
    with open(BASE / 'lv6_production_part_list.json') as f:
        pl = json.load(f)
    
    # Build geometry lookup
    part_geometry = {}
    for p_entry in pl.get('parts', []):
        outer = p_entry.get('outer_points_mm', [])
        holes = p_entry.get('holes_points_mm', [])
        if not outer:
            continue
        part_geometry[p_entry['part_id']] = {
            'outer': outer,
            'holes': holes,
            'area': polygon_area(outer),
            'verts': len(outer),
            'hole_count': len(holes),
        }
    
    # Load fixed layout
    with open(BASE / 'lv6_blf_candidate_exact_spacing100_fixed_layout.json') as f:
        layout = json.load(f)
    
    # Count placed per part type
    placed_counts = {}
    for sheet_key, sheet in layout.get('sheets', {}).items():
        for p_placement in sheet.get('placements', []):
            pid = p_placement['part_id']
            placed_counts[pid] = placed_counts.get(pid, 0) + 1
    
    # Identify unplaced instances
    unplaced_list = []
    for p_entry in pl.get('parts', []):
        pid = p_entry['part_id']
        qty = p_entry['quantity']
        placed = placed_counts.get(pid, 0)
        unplaced_qty = qty - placed
        if unplaced_qty > 0 and pid in part_geometry:
            for inst_idx in range(placed, qty):
                unplaced_list.append({
                    'part_id': pid,
                    'instance': inst_idx,
                    'qty_requested': qty,
                    'qty_placed': placed,
                    'qty_unplaced': unplaced_qty,
                })
    
    print(f"Unplaced instances: {len(unplaced_list)}")
    print()
    
    # Group by part_id
    unplaced_by_type = {}
    for up in unplaced_list:
        pid = up['part_id']
        if pid not in unplaced_by_type:
            unplaced_by_type[pid] = {
                'part_id': pid,
                'qty_unplaced': up['qty_unplaced'],
                'qty_requested': up['qty_requested'],
                'qty_placed': up['qty_placed'],
                'instances': [],
            }
        unplaced_by_type[pid]['instances'].append(up['instance'])
    
    # Analyze each unplaced type
    results = []
    rotations_to_try = [0, 90, 180, 270]
    
    for pid, info in unplaced_by_type.items():
        geom = part_geometry[pid]
        outer = geom['outer']
        holes = geom['holes']
        bw_orig, bh_orig = bbox_dims(outer)
        
        print(f"Analyzing: {pid}")
        print(f"  Original bbox: {bw_orig:.1f}x{bh_orig:.1f}")
        print(f"  Vertices: {geom['verts']}, Holes: {geom['hole_count']}")
        print(f"  Area: {geom['area']:.1f}mm²")
        print(f"  Unplaced: {info['qty_unplaced']} of {info['qty_requested']}")
        
        fits_info = {}
        best_rotation = None
        best_reason = None
        
        for rot in rotations_to_try:
            fits, reason = check_fits_on_empty_sheet(outer, holes, rot, SHEET_W, SHEET_H, SHEET_MARGIN)
            fits_info[rot] = {'fits': fits, 'reason': reason}
            
            # Also check sheet margins of 10mm
            fits_margin, reason_margin = check_fits_on_empty_sheet(outer, holes, rot, SHEET_W, SHEET_H, 10.0)
            fits_info[f'{rot}_margin10'] = {'fits': fits_margin, 'reason': reason_margin}
            
            print(f"  Rotation {rot}°: {reason}")
            
            if fits and best_rotation is None:
                best_rotation = rot
                best_reason = reason
        
        print()
        
        result = {
            'part_id': pid,
            'qty_unplaced': info['qty_unplaced'],
            'qty_placed': info['qty_placed'],
            'qty_requested': info['qty_requested'],
            'bbox_original': {'width': bw_orig, 'height': bh_orig},
            'area': geom['area'],
            'vertex_count': geom['verts'],
            'hole_count': geom['hole_count'],
            'fits_info': fits_info,
            'best_rotation_for_empty_sheet': best_rotation,
            'best_reason': best_reason,
            'fits_empty_sheet': best_rotation is not None,
        }
        
        # For 10mm sheet margin check
        best_rot_margin = None
        for rot in rotations_to_try:
            if fits_info[f'{rot}_margin10']['fits']:
                best_rot_margin = rot
                break
        
        result['with_10mm_margin'] = {
            'fits': best_rot_margin is not None,
            'best_rotation': best_rot_margin,
            'note': '10mm sheet edge margin vs 0mm margin analysis',
        }
        
        results.append(result)
    
    # Save JSON
    output_json = {
        'analysis': 'lv6_unplaced_exact_spacing10',
        'sheet_width': SHEET_W,
        'sheet_height': SHEET_H,
        'spacing_mm': SPACING,
        'sheet_edge_margin': SHEET_MARGIN,
        'results': results,
        'summary': {
            'total_unplaced_instances': len(unplaced_list),
            'types_unplaced': len(results),
            'types_with_empty_sheet_fit': sum(1 for r in results if r['fits_empty_sheet']),
            'types_with_10mm_margin_fit': sum(1 for r in results if r['with_10mm_margin']['fits']),
        }
    }
    
    json_path = BASE / 'lv6_exact_spacing10_unplaced_analysis.json'
    with open(json_path, 'w') as f:
        json.dump(output_json, f, indent=2)
    print(f"JSON: {json_path}")
    
    # Save Markdown
    md_lines = []
    md_lines.append("# T05q: LV6 Unplaced Instance Analysis")
    md_lines.append("")
    md_lines.append(f"**Layout:** `lv6_blf_candidate_exact_spacing100_fixed_layout.json`")
    md_lines.append(f"**Sheet:** {SHEET_W}x{SHEET_H}mm")
    md_lines.append(f"**Spacing:** {SPACING}mm exact (part-part)")
    md_lines.append(f"**Sheet edge margin:** {SHEET_MARGIN}mm")
    md_lines.append("")
    md_lines.append(f"**Total unplaced:** {len(unplaced_list)} instances across {len(results)} types")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    for r in results:
        md_lines.append(f"## {r['part_id']}")
        md_lines.append("")
        md_lines.append(f"- **Unplaced:** {r['qty_unplaced']} of {r['qty_requested']} (placed: {r['qty_placed']})")
        md_lines.append(f"- **Bbox:** {r['bbox_original']['width']:.1f} × {r['bbox_original']['height']:.1f}mm")
        md_lines.append(f"- **Area:** {r['area']:.1f}mm²")
        md_lines.append(f"- **Vertices:** {r['vertex_count']}, **Holes:** {r['hole_count']}")
        md_lines.append("")
        md_lines.append("### Rotation fit check (0mm sheet margin)")
        for rot in [0, 90, 180, 270]:
            fi = r['fits_info'].get(rot, {})
            status = "✅" if fi.get('fits') else "❌"
            md_lines.append(f"- {status} Rotation {rot}°: {fi.get('reason', 'N/A')}")
        md_lines.append("")
        md_lines.append("### Rotation fit check (10mm sheet margin)")
        for rot in [0, 90, 180, 270]:
            fi = r['fits_info'].get(f'{rot}_margin10', {})
            status = "✅" if fi.get('fits') else "❌"
            md_lines.append(f"- {status} Rotation {rot}° + 10mm margin: {fi.get('reason', 'N/A')}")
        md_lines.append("")
        md_lines.append(f"**Best rotation (0mm margin):** {r['best_rotation_for_empty_sheet']}° — {r['best_reason']}")
        md_lines.append(f"**Fits empty sheet:** {'YES ✅' if r['fits_empty_sheet'] else 'NO ❌'}")
        margin_info = r['with_10mm_margin']
        md_lines.append(f"**With 10mm sheet margin:** {'YES ✅' if margin_info['fits'] else 'NO ❌'} (best rot: {margin_info['best_rotation']}°)")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    
    md_path = BASE / 'lv6_exact_spacing10_unplaced_analysis.md'
    with open(json_path.with_suffix('.md'), 'w') as f:
        f.write('\n'.join(md_lines))
    print(f"Markdown: {json_path.with_suffix('.md')}")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        fits = r['fits_empty_sheet']
        fits_m = r['with_10mm_margin']['fits']
        print(f"  {r['part_id']}: qty={r['qty_unplaced']}, fits_empty={fits}, fits_10mm_margin={fits_m}, best_rot={r['best_rotation_for_empty_sheet']}°")
    
    print()
    types_fitting = sum(1 for r in results if r['fits_empty_sheet'])
    types_fitting_margin = sum(1 for r in results if r['with_10mm_margin']['fits'])
    print(f"Types that fit empty sheet (0mm margin): {types_fitting}/{len(results)}")
    print(f"Types that fit with 10mm sheet margin: {types_fitting_margin}/{len(results)}")
    print(f"Total unplaced instances: {len(unplaced_list)}")
    
    if types_fitting == len(results):
        print()
        print("CONCLUSION: All unplaced types CAN fit on empty sheet. The issue is")
        print("candidate generation / placement algorithm, not geometry fit.")
    elif types_fitting_margin == len(results):
        print()
        print("CONCLUSION: All unplaced types fit with 10mm sheet margin. Using")
        print("sheet edge margin = 0mm is the correct policy.")
    else:
        print()
        print("CONCLUSION: Some types CANNOT fit even on empty sheet. Geometry issue.")

if __name__ == '__main__':
    main()
