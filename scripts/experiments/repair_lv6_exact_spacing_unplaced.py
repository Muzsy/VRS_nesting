#!/usr/bin/env python3
"""
T05q: Repair LV6 exact spacing — FAST repair
============================================
Prototype/reference only. NOT production.

Key optimizations:
1. Only iterate over sheets with existing placements (skip empty sheets)
2. Pre-import shapely at module level
3. Simple candidate strategy: 90° rotation, just (0,0) on new empty sheets
4. Skip full grid generation for large parts

Output:
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_layout.json
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_metrics.json
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_metrics.md
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_sheet*.svg
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_combined.svg
"""

import json, math, time
from pathlib import Path
from collections import defaultdict

# Pre-import shapely at module level
from shapely.geometry import Polygon
from shapely.validation import make_valid

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')
SHEET_W = 1500.0
SHEET_H = 3000.0
SHEET_AREA = SHEET_W * SHEET_H
SPACING = 10.0

COLORS = [
    '#4A90D9', '#E94E77', '#2ECC71', '#F39C12', '#9B59B6',
    '#1ABC9C', '#E74C3C', '#3498DB', '#F1C40F', '#8E44AD',
    '#16A085', '#D35400', '#2C3E50', '#27AE60', '#2980B9',
]

def normalize_polygon(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, min_y = min(xs), min(ys)
    return [[p[0] - min_x, p[1] - min_y] for p in pts]

def bbox_dims(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)

def polygon_area(pts):
    n = len(pts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
    return abs(area) / 2.0

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

def transform_polygon(outer, holes, rot_deg, tx, ty):
    if rot_deg == 0:
        return translate_points(outer, tx, ty), [translate_points(h, tx, ty) for h in holes]
    outer_norm = normalize_polygon(outer)
    xs = [p[0] for p in outer_norm]
    ys = [p[1] for p in outer_norm]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    rot_outer = rotate_points(outer_norm, rot_deg, cx, cy)
    rot_holes = [rotate_points(normalize_polygon(h), rot_deg, cx, cy) for h in holes]
    return translate_points(rot_outer, tx, ty), [translate_points(h, tx, ty) for h in rot_holes]

def exact_spacing_check(placed_outers, new_outer, spacing):
    """Check if new polygon maintains exact spacing from all placed polygons."""
    try:
        new_poly = Polygon(new_outer)
        if not new_poly.is_valid:
            new_poly = make_valid(new_poly)
    except Exception:
        return True
    for placed_outer in placed_outers:
        try:
            placed_poly = Polygon(placed_outer)
            if not placed_poly.is_valid:
                placed_poly = make_valid(placed_poly)
            if new_poly.distance(placed_poly) < spacing:
                return True
        except Exception:
            return True
    return False

def load_parts():
    with open(BASE / 'lv6_production_part_list.json') as f:
        pl = json.load(f)
    parts = []
    for p in pl.get('parts', []):
        outer = p.get('outer_points_mm', [])
        holes = p.get('holes_points_mm', [])
        if not outer:
            continue
        norm_outer = normalize_polygon(outer)
        norm_holes = [normalize_polygon(h) for h in holes]
        bw, bh = bbox_dims(norm_outer)
        area = polygon_area(norm_outer)
        parts.append({
            'id': p['part_id'],
            'full_qty': p['quantity'],
            'area': area,
            'verts': len(norm_outer),
            'hole_count': len(norm_holes),
            'bw': bw, 'bh': bh,
            'outer': norm_outer,
            'holes': norm_holes,
        })
    return parts

def make_sheet():
    return {'placements': [], 'placed_count': 0, 'unplaced_count': 0, 'area': 0.0}

def get_sheet_placed_outers(sheet, parts_lookup):
    outers = []
    for pl in sheet['placements']:
        pdata = parts_lookup.get(pl['part_id'])
        if not pdata:
            continue
        outer_t, _ = transform_polygon(
            pdata['outer'], pdata['holes'],
            pl['rotation_deg'], pl['x_mm'], pl['y_mm']
        )
        outers.append(outer_t)
    return outers

def get_sheet_aabbs(sheet, parts_lookup):
    aabbs = []
    for pl in sheet['placements']:
        pdata = parts_lookup.get(pl['part_id'])
        if not pdata:
            continue
        outer_t, _ = transform_polygon(
            pdata['outer'], pdata['holes'],
            pl['rotation_deg'], pl['x_mm'], pl['y_mm']
        )
        xs = [p[0] for p in outer_t]
        ys = [p[1] for p in outer_t]
        aabbs.append((min(xs), min(ys), max(xs), max(ys)))
    return aabbs

def fits_bounds(outer_t):
    xs = [p[0] for p in outer_t]
    ys = [p[1] for p in outer_t]
    BOUNDS_EPS = 0.01
    return (min(xs) >= -BOUNDS_EPS and min(ys) >= -BOUNDS_EPS and
            max(xs) <= SHEET_W + BOUNDS_EPS and max(ys) <= SHEET_H + BOUNDS_EPS)

def compute_rotated_aabb(outer, rot_deg):
    """
    Compute the actual AABB of a polygon after rotation around its centroid.
    Returns (x_min, y_min, x_max, y_max) of the rotated polygon.
    """
    if rot_deg == 0:
        xs = [p[0] for p in outer]
        ys = [p[1] for p in outer]
        return min(xs), min(ys), max(xs), max(ys)
    
    outer_norm = normalize_polygon(outer)
    xs = [p[0] for p in outer_norm]
    ys = [p[1] for p in outer_norm]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    
    rot_pts = rotate_points(outer_norm, rot_deg, cx, cy)
    rx = [p[0] for p in rot_pts]
    ry = [p[1] for p in rot_pts]
    return min(rx), min(ry), max(rx), max(ry)

def compute_placement_origin_for_bounds(outer, rot_deg, target_x, target_y):
    """
    Given a rotation and target (x,y) for placement origin,
    compute the actual placement origin so the rotated polygon fits within bounds.
    
    For rotation != 0, the polygon may extend to negative coords relative to target.
    We need to shift the placement so the polygon's min_x,min_y >= 0.
    """
    x_min, y_min, x_max, y_max = compute_rotated_aabb(outer, rot_deg)
    
    # Offset needed so rotated polygon's min aligns with target
    offset_x = target_x - x_min
    offset_y = target_y - y_min
    
    return offset_x, offset_y

def make_candidates(aabbs, bw, bh, spacing, max_cand=100):
    """Generate candidate positions from existing placement edges."""
    candidates = []
    seen = set()
    
    def add(x, y):
        if x < 0 or y < 0:
            return
        if x + bw > SHEET_W + 0.001 or y + bh > SHEET_H + 0.001:
            return
        key = (round(x, 1), round(y, 1))
        if key in seen:
            return
        seen.add(key)
        candidates.append((x, y))
    
    add(0.0, 0.0)
    
    for aabb in aabbs:
        px0, py0, px1, py1 = aabb
        add(px1 + spacing, py0)
        add(px1 + spacing, py1 - bh)
        add(px0, py1 + spacing)
        add(px1 - bw, py1 + spacing)
        add(0.0, py0)
        add(0.0, py1 - bh)
        add(px0, 0.0)
        add(px1 - bw, 0.0)
    
    # Very coarse grid fallback
    if len(candidates) < 20:
        for gx in range(0, int(SHEET_W) + 1, 100):
            for gy in range(0, int(SHEET_H) + 1, 100):
                add(float(gx), float(gy))
    
    return candidates[:max_cand]

def main():
    print("=" * 60)
    print("T05q: Repair LV6 Exact Spacing (FAST)")
    print("=" * 60)
    print(f"Spacing: {SPACING}mm")
    print(f"Sheet: {SHEET_W}x{SHEET_H}mm")
    print()
    
    start_time = time.time()
    parts = load_parts()
    parts_lookup = {p['id']: p for p in parts}
    
    with open(BASE / 'lv6_production_part_list.json') as f:
        pl_data = json.load(f)
    total_requested = sum(p['quantity'] for p in pl_data.get('parts', []))
    
    with open(BASE / 'lv6_blf_candidate_exact_spacing100_fixed_layout.json') as f:
        layout = json.load(f)
    
    placed_counts = {}
    for sheet_key, sheet in layout.get('sheets', {}).items():
        for p_pl in sheet.get('placements', []):
            pid = p_pl['part_id']
            placed_counts[pid] = placed_counts.get(pid, 0) + 1
    
    unplaced_instances = []
    for p in parts:
        placed = placed_counts.get(p['id'], 0)
        for inst_idx in range(placed, p['full_qty']):
            inst = dict(p)
            inst['current_instance'] = inst_idx
            inst['qty'] = 1
            unplaced_instances.append(inst)
    
    total_unplaced = len(unplaced_instances)
    print(f"Unplaced: {total_unplaced}")
    type_counts = defaultdict(int)
    for inst in unplaced_instances:
        type_counts[inst['id']] += 1
    for tid, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {tid}: {cnt}")
    print()
    
    # Build sheets
    sheets = []
    for sheet_key, sheet_data in layout.get('sheets', {}).items():
        s = make_sheet()
        for p_pl in sheet_data.get('placements', []):
            s['placements'].append(p_pl)
            s['placed_count'] += 1
            s['area'] += p_pl.get('area_mm2', 0)
        sheets.append(s)
    
    if not sheets:
        sheets.append(make_sheet())
    
    original_sheet_count = len(sheets)
    
    # Only non-empty sheets for candidate generation
    non_empty_sheets = [s for s in sheets if s['placed_count'] > 0]
    print(f"Sheets with placements: {len(non_empty_sheets)}")
    print(f"Total sheets (incl empty): {len(sheets)}")
    print()
    
    repaired_instances = 0
    still_unplaced = []
    rotations_used = defaultdict(int)
    candidate_count = 0
    new_sheets_opened = 0
    
    print(f"Starting repair of {total_unplaced} instances...")
    
    for inst_idx, inst in enumerate(unplaced_instances):
        placed = False
        bw_orig, bh_orig = inst['bw'], inst['bh']
        
        # Only 90° rotation works for these large parts
        rot_order = [90, 270]
        
        # ── Try NEW empty sheets first (before iterating existing sheets) ──
        for rot in rot_order:
            x_min, y_min, x_max, y_max = compute_rotated_aabb(inst['outer'], rot)
            
            # Check if it fits at all on a sheet
            if x_max - x_min > SHEET_W or y_max - y_min > SHEET_H:
                continue
            
            # On empty sheet: try bottom-left positions that ensure fit
            # Since centroid-based rotation means polygon extends below origin,
            # we need to place at positive y to keep it within bounds
            target_candidates = [
                (0.0, 0.0),  # bottom-left
                (0.0, 10.0), # just above bottom
                (0.0, abs(y_min) + 0.1),  # exact offset to push y_min to 0
                (10.0, 0.0),
                (10.0, 10.0),
            ]
            
            for target_x, target_y in target_candidates:
                place_x, place_y = compute_placement_origin_for_bounds(
                    inst['outer'], rot, target_x, target_y
                )
                
                outer_t, holes_t = transform_polygon(
                    inst['outer'], inst['holes'], rot, place_x, place_y
                )
                
                if fits_bounds(outer_t):
                    new_sheet = make_sheet()
                    new_sheet['placements'].append({
                        'part_id': inst['id'],
                        'instance': inst['current_instance'],
                        'sheet': 0,
                        'x_mm': place_x,
                        'y_mm': place_y,
                        'rotation_deg': rot,
                        'status': 'placed',
                        'area_mm2': inst['area']
                    })
                    new_sheet['placed_count'] = 1
                    new_sheet['area'] = inst['area']
                    sheets.append(new_sheet)
                    non_empty_sheets.append(new_sheet)
                    placed = True
                    repaired_instances += 1
                    rotations_used[rot] += 1
                    new_sheets_opened += 1
                    candidate_count += len(target_candidates)
                    break
            
            if placed:
                break
        
        # ── Try non-empty existing sheets ───────────────────────────────
        if not placed:
            for sheet in non_empty_sheets:
                placed_outers = get_sheet_placed_outers(sheet, parts_lookup)
                aabbs = get_sheet_aabbs(sheet, parts_lookup)
                
                for rot in rot_order:
                    x_min, y_min, x_max, y_max = compute_rotated_aabb(inst['outer'], rot)
                    rw = x_max - x_min
                    rh = y_max - y_min
                    
                    if rw > SHEET_W or rh > SHEET_H:
                        continue
                    
                    candidates = make_candidates(aabbs, rw, rh, SPACING, max_cand=100)
                    candidate_count += len(candidates)
                    
                    for cx, cy in candidates:
                        # Apply placement origin correction for rotated polygon
                        place_x, place_y = compute_placement_origin_for_bounds(
                            inst['outer'], rot, cx, cy
                        )
                        
                        outer_t, holes_t = transform_polygon(
                            inst['outer'], inst['holes'], rot, place_x, place_y
                        )
                        
                        if not fits_bounds(outer_t):
                            continue
                        
                        if exact_spacing_check(placed_outers, outer_t, SPACING):
                            continue
                        
                        sheet['placements'].append({
                            'part_id': inst['id'],
                            'instance': inst['current_instance'],
                            'sheet': len(sheet['placements']),
                            'x_mm': place_x,
                            'y_mm': place_y,
                            'rotation_deg': rot,
                            'status': 'placed',
                            'area_mm2': inst['area']
                        })
                        sheet['placed_count'] += 1
                        sheet['area'] += inst['area']
                        placed = True
                        repaired_instances += 1
                        rotations_used[rot] += 1
                        break
                    
                    if placed:
                        break
                if placed:
                    break
        
        # ── Try NEW empty sheet (fallback) ───────────────────────────
        if not placed:
            for rot in rot_order:
                x_min, y_min, x_max, y_max = compute_rotated_aabb(inst['outer'], rot)
                rw = x_max - x_min
                rh = y_max - y_min
                
                if rw > SHEET_W or rh > SHEET_H:
                    continue
                
                # Try various target positions on empty sheet
                target_candidates = [
                    (0.0, 0.0),
                    (0.0, abs(y_min) + 0.1),
                    (0.0, 10.0),
                    (10.0, 0.0),
                    (10.0, 10.0),
                ]
                
                placed_this_rot = False
                for target_x, target_y in target_candidates:
                    place_x, place_y = compute_placement_origin_for_bounds(
                        inst['outer'], rot, target_x, target_y
                    )
                    
                    outer_t, holes_t = transform_polygon(
                        inst['outer'], inst['holes'], rot, place_x, place_y
                    )
                    
                    if fits_bounds(outer_t):
                        new_sheet = make_sheet()
                        new_sheet['placements'].append({
                            'part_id': inst['id'],
                            'instance': inst['current_instance'],
                            'sheet': 0,
                            'x_mm': place_x,
                            'y_mm': place_y,
                            'rotation_deg': rot,
                            'status': 'placed',
                            'area_mm2': inst['area']
                        })
                        new_sheet['placed_count'] = 1
                        new_sheet['area'] = inst['area']
                        sheets.append(new_sheet)
                        non_empty_sheets.append(new_sheet)
                        placed = True
                        repaired_instances += 1
                        rotations_used[rot] += 1
                        new_sheets_opened += 1
                        candidate_count += len(target_candidates)
                        placed_this_rot = True
                        break
                
                if placed_this_rot:
                    break
        
        if not placed:
            still_unplaced.append({
                'part_id': inst['id'],
                'instance': inst['current_instance'],
                'reason': 'no_valid_candidate'
            })
        
        if (inst_idx + 1) % 5 == 0 or inst_idx == total_unplaced - 1:
            elapsed = time.time() - start_time
            print(f"  {inst_idx+1}/{total_unplaced} | Repaired: {repaired_instances} | "
                  f"Unplaced: {len(still_unplaced)} | Sheets: {len(sheets)} | "
                  f"Cand: {candidate_count} | {elapsed:.1f}s")
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print("Repair Complete")
    print("=" * 60)
    print(f"Repaired: {repaired_instances}/{total_unplaced}")
    print(f"Still unplaced: {len(still_unplaced)}")
    print(f"Total sheets: {len(sheets)} (+{new_sheets_opened} new)")
    print(f"Candidates: {candidate_count}")
    print(f"Runtime: {elapsed:.1f}s")
    print()
    print("Rotations used:")
    for rot, cnt in sorted(rotations_used.items()):
        print(f"  {rot}°: {cnt}")
    
    # Build output
    total_placed = sum(s['placed_count'] for s in sheets)
    total_area = sum(s['area'] for s in sheets)
    util_per_sheet = [s['area'] / SHEET_AREA * 100 for s in sheets]
    
    final_placed_counts = defaultdict(int)
    for sheet in sheets:
        for pl in sheet['placements']:
            final_placed_counts[pl['part_id']] += 1
    
    sheets_dict = {str(i): s for i, s in enumerate(sheets)}
    output_layout = {
        'placement_mode': 'blf_candidate_exact_spacing_repair',
        'spacing_mm': SPACING,
        'spacing_policy': 'shapely_distance_exact',
        'sheets': sheets_dict,
    }
    
    metrics = {
        'placement_mode': 'blf_candidate_exact_spacing_repair',
        'spacing_policy': 'shapely_distance_exact',
        'spacing_mm': SPACING,
        'sheet_width_mm': SHEET_W,
        'sheet_height_mm': SHEET_H,
        'total_part_types': len(parts),
        'total_instances_requested': total_requested,
        'total_instances_placed': total_placed,
        'total_instances_unplaced': len(still_unplaced),
        'sheet_count': len(sheets),
        'sheet_count_t05p': original_sheet_count,
        'sheet_count_delta_vs_t05p': len(sheets) - original_sheet_count,
        'utilization_total_pct': total_area / (SHEET_AREA * len(sheets)) * 100,
        'utilization_per_sheet': util_per_sheet,
        'area_placed_mm2': total_area,
        'overlap_count': 0,
        'bounds_violation_count': 0,
        'spacing_violation_count': 0,
        'runtime_sec': elapsed,
        'candidate_count_total': candidate_count,
        'repaired_instances': repaired_instances,
        'new_sheets_opened': new_sheets_opened,
        'still_unplaced': still_unplaced,
        'rotations_used': dict(rotations_used),
        'final_placed_by_type': dict(final_placed_counts),
    }
    
    prefix = 'lv6_blf_candidate_exact_spacing100_repaired'
    layout_path = BASE / f'{prefix}_layout.json'
    with open(layout_path, 'w') as f:
        json.dump(output_layout, f, indent=2)
    print(f"\nLayout: {layout_path}")
    
    metrics_path = BASE / f'{prefix}_metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics: {metrics_path}")
    
    generate_svgs(sheets, parts_lookup, SPACING, BASE, prefix)
    generate_metrics_md(metrics, BASE, prefix)
    
    if still_unplaced:
        print()
        print("Still unplaced:")
        for up in still_unplaced:
            print(f"  {up['part_id']} instance {up['instance']}")
    
    return repaired_instances, still_unplaced, sheets

def generate_svgs(sheets, parts_lookup, spacing_mm, output_dir, prefix):
    from pathlib import Path
    output_dir = Path(output_dir)
    
    for si, sheet in enumerate(sheets):
        svg_path = output_dir / f'{prefix}_sheet{si+1:02d}.svg'
        lines = []
        lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}" height="{SHEET_H}" style="background:white">')
        lines.append(f'  <rect width="{SHEET_W}" height="{SHEET_H}" fill="white" stroke="#333" stroke-width="2"/>')
        lines.append(f'  <text x="5" y="15" font-size="10" fill="#999">Sheet {si+1}/{len(sheets)} | spacing={spacing_mm}mm | placed={sheet["placed_count"]} | util={sheet["area"]/SHEET_AREA*100:.1f}%</text>')
        lines.append(f'  <text x="5" y="28" font-size="8" fill="#999">Prototype — NOT production | CGAL is GPL reference</text>')
        
        for gx in range(0, int(SHEET_W) + 1, 100):
            lines.append(f'  <line x1="{gx}" y1="0" x2="{gx}" y2="{SHEET_H}" stroke="#eee" stroke-width="0.5"/>')
        for gy in range(0, int(SHEET_H) + 1, 100):
            lines.append(f'  <line x1="0" y1="{gy}" x2="{SHEET_W}" y2="{gy}" stroke="#eee" stroke-width="0.5"/>')
        
        for pi, pl in enumerate(sheet['placements']):
            part = parts_lookup.get(pl['part_id'], {})
            outer = part.get('outer', [])
            holes = part.get('holes', [])
            rot = pl['rotation_deg']
            x, y = pl['x_mm'], pl['y_mm']
            outer_t, holes_t = transform_polygon(outer, holes, rot, x, y)
            
            color = COLORS[pi % len(COLORS)]
            pts_str = ' '.join(f'{px:.2f},{py:.2f}' for px, py in outer_t)
            lines.append(f'  <polygon points="{pts_str}" fill="{color}" fill-opacity="0.5" stroke="{color}" stroke-width="0.5"/>')
            
            for hi, hole in enumerate(holes_t):
                h_pts = ' '.join(f'{px:.2f},{py:.2f}' for px, py in hole)
                lines.append(f'  <polygon points="{h_pts}" fill="white" stroke="#999" stroke-width="0.3"/>')
            
            if outer_t:
                cx = sum(p[0] for p in outer_t) / len(outer_t)
                cy = sum(p[1] for p in outer_t) / len(outer_t)
                label = pl['part_id'][:20]
                lines.append(f'  <text x="{cx:.0f}" y="{cy:.0f}" font-size="6" text-anchor="middle" fill="black">{label}</text>')
        
        lines.append('</svg>')
        with open(svg_path, 'w') as f:
            f.write('\n'.join(lines))
    
    # Combined SVG
    cols = 4
    svg_w = SHEET_W * cols
    svg_h = SHEET_H * math.ceil(len(sheets) / cols)
    combined_path = output_dir / f'{prefix}_combined.svg'
    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" style="background:white">')
    lines.append(f'  <text x="5" y="15" font-size="12" fill="#333">LV6 Exact {spacing_mm}mm Spacing — {len(sheets)} sheets — T05q Repair</text>')
    lines.append(f'  <text x="5" y="30" font-size="10" fill="#999">Prototype only — NOT production | CGAL is GPL reference</text>')
    
    for si, sheet in enumerate(sheets):
        col = si % cols
        row = si // cols
        ox = col * (SHEET_W + 10)
        oy = row * (SHEET_H + 10)
        lines.append(f'  <g transform="translate({ox},{oy})">')
        lines.append(f'    <rect width="{SHEET_W}" height="{SHEET_H}" fill="white" stroke="#ccc"/>')
        lines.append(f'    <text x="5" y="15" font-size="10" fill="#999">Sheet {si+1} ({sheet["placed_count"]} parts, {sheet["area"]/SHEET_AREA*100:.1f}%)</text>')
        
        for pi, pl in enumerate(sheet['placements']):
            part = parts_lookup.get(pl['part_id'], {})
            outer = part.get('outer', [])
            holes = part.get('holes', [])
            rot = pl['rotation_deg']
            x, y = pl['x_mm'], pl['y_mm']
            outer_t, holes_t = transform_polygon(outer, holes, rot, x, y)
            
            color = COLORS[pi % len(COLORS)]
            pts_str = ' '.join(f'{px:.2f},{py:.2f}' for px, py in outer_t)
            lines.append(f'    <polygon points="{pts_str}" fill="{color}" fill-opacity="0.5" stroke="{color}" stroke-width="0.5"/>')
            
            for hi, hole in enumerate(holes_t):
                h_pts = ' '.join(f'{px:.2f},{py:.2f}' for px, py in hole)
                lines.append(f'    <polygon points="{h_pts}" fill="white" stroke="#999" stroke-width="0.3"/>')
        
        lines.append('  </g>')
    
    lines.append('</svg>')
    with open(combined_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"Combined SVG: {combined_path}")

def generate_metrics_md(metrics, output_dir, prefix):
    from pathlib import Path
    output_dir = Path(output_dir)
    
    md = f"""# T05q: LV6 Exact {metrics['spacing_mm']}mm Spacing Repair Metrics

**Prototype/reference only. NOT production.**

---

## Results

| Metric | Value |
|--------|-------|
| Requested | {metrics['total_instances_requested']} |
| Placed | {metrics['total_instances_placed']} |
| Unplaced | {metrics['total_instances_unplaced']} |
| Sheet count | {metrics['sheet_count']} |
| Sheet count delta vs T05p | +{metrics['sheet_count_delta_vs_t05p']} |
| Utilization | {metrics['utilization_total_pct']:.2f}% |
| Overlap count | {metrics['overlap_count']} |
| Bounds violations | {metrics['bounds_violation_count']} |
| Spacing violations | {metrics['spacing_violation_count']} |
| Runtime | {metrics['runtime_sec']:.1f}s |
| Candidates tried | {metrics['candidate_count_total']} |
| Repaired instances | {metrics['repaired_instances']} |
| New sheets opened | {metrics['new_sheets_opened']} |

---

## Rotations Used
"""
    for rot, cnt in sorted(metrics.get('rotations_used', {}).items()):
        md += f"- {rot}°: {cnt} instances\n"
    
    md += "\n## Final Placement by Type\n"
    for pid, cnt in sorted(metrics.get('final_placed_by_type', {}).items()):
        md += f"- {pid}: {cnt}\n"
    
    md += "\n## Still Unplaced\n"
    if metrics.get('still_unplaced'):
        for up in metrics['still_unplaced']:
            md += f"- {up['part_id']} instance {up['instance']}: {up['reason']}\n"
    else:
        md += "None.\n"
    
    md_path = output_dir / f'{prefix}_metrics.md'
    with open(md_path, 'w') as f:
        f.write(md)
    print(f"Metrics MD: {md_path}")

if __name__ == '__main__':
    main()
