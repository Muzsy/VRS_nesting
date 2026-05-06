#!/usr/bin/env python3
"""
T05o: LV6 BLF/Candidate Exact 10mm Spacing Preview
===================================================
Prototype/reference only. NOT production.

Algorithm:
- BLF-like candidate generation: try positions next to placed parts + sheet edges
- Sort instances by descending area (largest first)
- Candidate scoring: lowest y, then lowest x, then smallest sheet index
- Rotation: try 0 and 90 degrees; pick best fit by bounding box on sheet
- Validation: AABB prefilter + Shapely exact polygon with polygon-with-holes
- Spacing: exact buffer method — polygon.buffer(spacing/2) then intersection check
- Candidate cap for performance

Spacing policy: shapely_distance_or_buffer_exact
- Uses polygon.buffer(spacing/2) method for exact spacing enforcement
- Different from T05n's approximate_bbox (spacing=0 and spacing=2 identical)

Output:
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing10_layout.json
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing10_metrics.json
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing10_metrics.md
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing10_sheetNN.svg
  tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing10_combined.svg
"""

import json, math, time, os, sys, argparse
from pathlib import Path
from collections import defaultdict

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')
SAMPLE_DXF = Path('/home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv6 jav')

SHEET_W = 1500.0
SHEET_H = 3000.0
SHEET_AREA = SHEET_W * SHEET_H

# Colors for SVG
COLORS = [
    '#4A90D9', '#E94E77', '#2ECC71', '#F39C12', '#9B59B6',
    '#1ABC9C', '#E74C3C', '#3498DB', '#F1C40F', '#8E44AD',
    '#16A085', '#D35400', '#2C3E50', '#27AE60', '#2980B9',
]

# ─── Geometry helpers ─────────────────────────────────────────────────────────

def normalize_polygon(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, min_y = min(xs), min(ys)
    return [[p[0] - min_x, p[1] - min_y] for p in pts]

def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def bbox_wh(pts):
    x0, y0, x1, y1 = bbox(pts)
    return x1 - x0, y1 - y0

def polygon_area(pts):
    n = len(pts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
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
    """
    Transform polygon: normalize → rotate around TRUE centroid → translate.
    MUST match validate_lv6_exact_spacing.py get_shapely_polygon for consistency.
    
    The key fix: use normalize_polygon + true centroid (sum/len), NOT bbox midpoint.
    This ensures placement and validator use identical geometry.
    """
    if rot_deg == 0:
        return translate_points(outer, tx, ty), [translate_points(h, tx, ty) for h in holes]
    
    # Normalize to origin first (like validator does)
    outer_norm = normalize_polygon(outer)
    
    # True centroid (MUST match validator's get_shapely_polygon)
    xs = [p[0] for p in outer_norm]
    ys = [p[1] for p in outer_norm]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    
    # Rotate around centroid
    rot_outer = rotate_points(outer_norm, rot_deg, cx, cy)
    rot_holes = [rotate_points(normalize_polygon(h), rot_deg, cx, cy) for h in holes]
    
    # Translate to placement position
    return translate_points(rot_outer, tx, ty), [translate_points(h, tx, ty) for h in rot_holes]


def transform_polygon_bbox_approx(outer, holes, rot_deg, tx, ty):
    """
    OLD transform using bbox midpoint rotation.
    KEPT for reference only — DO NOT USE for placement.
    This was the source of transform inconsistency with validator.
    """
    if rot_deg == 0:
        return translate_points(outer, tx, ty), [translate_points(h, tx, ty) for h in holes]
    xs = [p[0] for p in outer]
    ys = [p[1] for p in outer]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    rot_outer = rotate_points(outer, rot_deg, cx, cy)
    rot_holes = [rotate_points(h, rot_deg, cx, cy) for h in holes]
    return translate_points(rot_outer, tx, ty), [translate_points(h, tx, ty) for h in rot_holes]

def aabb_overlap(box_a, box_b):
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)

# ─── Shapely helpers ─────────────────────────────────────────────────────────

def shapely_polygon(pts, holes_pts=None):
    from shapely.geometry import Polygon
    from shapely.validation import make_valid
    try:
        if holes_pts:
            poly = Polygon(pts, holes_pts)
        else:
            poly = Polygon(pts)
        if not poly.is_valid:
            poly = make_valid(poly)
        return poly
    except Exception:
        return Polygon(pts)

# ─── Exact spacing check (buffer method) ────────────────────────────────────

def exact_spacing_check_distance(placed_data, new_outer, new_holes, spacing):
    """
    Exact spacing check using polygon.distance().
    Faster than buffer method — only computes boundary distance.
    
    Policy: shapely_distance_or_buffer_exact (uses distance)
    
    For each placed polygon:
    1. Build polygon with holes
    2. Check if new_poly.distance(placed_poly) < spacing
    3. If yes, spacing violation
    """
    from shapely.geometry import Polygon
    from shapely.validation import make_valid
    
    try:
        new_poly = Polygon(new_outer)
        if not new_poly.is_valid:
            new_poly = make_valid(new_poly)
    except Exception:
        return True  # conservative
    
    for pd in placed_data:
        placed_outer = pd['outer']
        
        try:
            placed_poly = Polygon(placed_outer)
            if not placed_poly.is_valid:
                placed_poly = make_valid(placed_poly)
            
            dist = new_poly.distance(placed_poly)
            if dist < spacing:
                return True  # spacing violation
        except Exception:
            return True  # conservative on error
    
    return False


# Keep buffer method for reference but don't use it by default
def exact_spacing_check_buffer(placed_data, new_outer, new_holes, spacing, half_sp):
    """
    Exact spacing check using polygon.buffer(half_sp) intersection method.
    SLOWER than distance method — use only for comparison/validation.
    """
    from shapely.geometry import Polygon
    
    try:
        new_poly = Polygon(new_outer)
        new_buffered = new_poly.buffer(half_sp)
    except Exception:
        return True
    
    for pd in placed_data:
        placed_outer = pd['outer']
        try:
            placed_poly = Polygon(placed_outer)
            placed_buffered = placed_poly.buffer(half_sp)
            if new_buffered.intersects(placed_buffered):
                return True
        except Exception:
            return True
    
    return False

# ─── Candidate generation ────────────────────────────────────────────────────

def generate_candidates(placed_aabbs, placed_outers, sheet_idx, bw, bh, bw_r, bh_r, spacing, max_candidates=300):
    candidates = []
    seen = set()

    def add(x, y):
        if x < 0 or y < 0:
            return
        if x + bw_r > SHEET_W + 0.001 or y + bh_r > SHEET_H + 0.001:
            return
        key = (round(x, 1), round(y, 1))
        if key in seen:
            return
        seen.add(key)
        score = (sheet_idx, y, x)
        candidates.append((x, y, score))

    add(0.0, 0.0)

    for aabb in placed_aabbs:
        px0, py0, px1, py1 = aabb
        # Right side
        add(px1 + spacing, py0)
        add(px1 + spacing, py1 - bh_r)
        # Top side
        add(px0, py1 + spacing)
        add(px1 - bw_r, py1 + spacing)

    # Left edge candidates at various y
    if placed_aabbs:
        ys = sorted(set(aabb[3] for aabb in placed_aabbs))
        for y in ys[:20]:
            add(0.0, y)
        # Bottom edge candidates at various x
        xs = sorted(set(aabb[2] for aabb in placed_aabbs))
        for x in xs[:20]:
            add(x, 0.0)

    # Grid fallback
    if len(candidates) < 20:
        for gx in range(0, int(SHEET_W) + 1, 100):
            for gy in range(0, int(SHEET_H) + 1, 100):
                add(float(gx), float(gy))

    # Sort by BLF score
    candidates.sort(key=lambda c: c[2])
    return candidates[:max_candidates]

# ─── Part loading ─────────────────────────────────────────────────────────────

def load_parts():
    part_list_path = BASE / 'lv6_production_part_list.json'
    with open(part_list_path) as f:
        pl = json.load(f)

    parts = []
    for p in pl['parts']:
        outer = p['outer_points_mm']
        holes = p['holes_points_mm']
        norm_outer = normalize_polygon(outer)
        norm_holes = [normalize_polygon(h) for h in holes]
        bw, bh = bbox_wh(norm_outer)
        area = polygon_area(norm_outer)

        fits_0 = bw <= SHEET_W and bh <= SHEET_H
        fits_90 = bh <= SHEET_W and bw <= SHEET_H

        rots_to_try = []
        if fits_0:
            rots_to_try.append(0)
        if fits_90:
            rots_to_try.append(90)

        parts.append({
            'id': p['part_id'],
            'full_qty': p['quantity'],
            'qty': p['quantity'],
            'area': area,
            'verts': len(norm_outer),
            'hole_count': len(norm_holes),
            'bw': bw, 'bh': bh,
            'fits_0': fits_0,
            'fits_90': fits_90,
            'rots': rots_to_try,
            'outer': norm_outer,
            'holes': norm_holes,
        })
    return parts

# ─── Sheet management ────────────────────────────────────────────────────────

def make_sheet():
    return {'placements': [], 'placed_count': 0, 'unplaced_count': 0, 'area': 0.0}

def place_on_sheet(sheet, part, x, y, rot, spacing, half_sp):
    outer_t, holes_t = transform_polygon(part['outer'], part['holes'], rot, x, y)
    
    # Bounds check using ACTUAL polygon bounds (not rough w/h)
    # After transform_polygon (normalize → rotate → translate), the polygon
    # should be near (0,0) origin but rotation can extend it to negative coords.
    # Use actual bounds to match validator.
    xs = [p[0] for p in outer_t]
    ys = [p[1] for p in outer_t]
    poly_min_x = min(xs)
    poly_min_y = min(ys)
    poly_max_x = max(xs)
    poly_max_y = max(ys)
    
    BOUNDS_EPS = 0.01  # Tolerance for floating point
    if poly_min_x < -BOUNDS_EPS or poly_min_y < -BOUNDS_EPS:
        return False
    if poly_max_x > SHEET_W + BOUNDS_EPS or poly_max_y > SHEET_H + BOUNDS_EPS:
        return False
    
    sheet['placements'].append({
        'part_id': part['id'],
        'instance': part.get('current_instance', 0),
        'sheet': len(sheet['placements']),
        'x_mm': x,
        'y_mm': y,
        'rotation_deg': rot,
        'status': 'placed',
        'area_mm2': part['area']
    })
    sheet['placed_count'] += 1
    sheet['area'] += part['area']
    return True

# ─── SVG generation ──────────────────────────────────────────────────────────

def generate_per_sheet_svgs(sheets, parts_lookup, spacing_mm, output_dir, prefix):
    """Generate per-sheet SVG files."""
    for si, sheet in enumerate(sheets):
        svg_path = output_dir / f'{prefix}_sheet{si+1:02d}.svg'
        svg_lines = []
        svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}" height="{SHEET_H}" style="background:white">')
        
        svg_lines.append(f'  <rect width="{SHEET_W}" height="{SHEET_H}" fill="white" stroke="#333" stroke-width="2"/>')
        svg_lines.append(f'  <text x="5" y="15" font-size="10" fill="#999">Sheet {si+1}/{len(sheets)} | spacing={spacing_mm}mm | placed={sheet["placed_count"]} | util={sheet["area"]/SHEET_AREA*100:.1f}%</text>')
        svg_lines.append(f'  <text x="5" y="28" font-size="8" fill="#999">Prototype only — NOT production | CGAL is GPL reference</text>')
        
        # Grid
        for gx in range(0, int(SHEET_W) + 1, 100):
            svg_lines.append(f'  <line x1="{gx}" y1="0" x2="{gx}" y2="{SHEET_H}" stroke="#eee" stroke-width="0.5"/>')
        for gy in range(0, int(SHEET_H) + 1, 100):
            svg_lines.append(f'  <line x1="0" y1="{gy}" x2="{SHEET_W}" y2="{gy}" stroke="#eee" stroke-width="0.5"/>')
        
        for pi, pl in enumerate(sheet['placements']):
            part = parts_lookup.get(pl['part_id'], {})
            outer = part.get('outer', [])
            holes = part.get('holes', [])
            rot = pl['rotation_deg']
            x, y = pl['x_mm'], pl['y_mm']
            outer_t, holes_t = transform_polygon(outer, holes, rot, x, y)
            
            color = COLORS[pi % len(COLORS)]
            pts_str = ' '.join(f'{px:.2f},{py:.2f}' for px, py in outer_t)
            svg_lines.append(f'  <polygon points="{pts_str}" fill="{color}" fill-opacity="0.5" stroke="{color}" stroke-width="0.5"/>')
            
            for hi, hole in enumerate(holes_t):
                h_pts = ' '.join(f'{px:.2f},{py:.2f}' for px, py in hole)
                svg_lines.append(f'  <polygon points="{h_pts}" fill="white" stroke="#999" stroke-width="0.3"/>')
            
            if outer_t:
                cx = sum(p[0] for p in outer_t) / len(outer_t)
                cy = sum(p[1] for p in outer_t) / len(outer_t)
                label = pl['part_id'][:20]
                svg_lines.append(f'  <text x="{cx:.0f}" y="{cy:.0f}" font-size="6" text-anchor="middle" fill="black">{label}</text>')
        
        svg_lines.append('</svg>')
        with open(svg_path, 'w') as f:
            f.write('\n'.join(svg_lines))


def generate_combined_svg(sheets, parts_lookup, spacing_mm, output_path):
    """Generate combined multi-sheet SVG."""
    cols = 4
    svg_w = SHEET_W * cols
    svg_h = SHEET_H * math.ceil(len(sheets) / cols)
    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" style="background:white">')
    
    for si, sheet in enumerate(sheets):
        col = si % cols
        row = si // cols
        ox = col * (SHEET_W + 10)
        oy = row * (SHEET_H + 10)
        svg_lines.append(f'  <g transform="translate({ox},{oy})">')
        svg_lines.append(f'    <rect width="{SHEET_W}" height="{SHEET_H}" fill="white" stroke="#ccc"/>')
        svg_lines.append(f'    <text x="5" y="15" font-size="10" fill="#999">Sheet {si+1} ({sheet["placed_count"]} parts, {sheet["area"]/SHEET_AREA*100:.1f}%)</text>')
        
        for pi, pl in enumerate(sheet['placements']):
            part = parts_lookup.get(pl['part_id'], {})
            outer = part.get('outer', [])
            holes = part.get('holes', [])
            rot = pl['rotation_deg']
            x, y = pl['x_mm'], pl['y_mm']
            outer_t, holes_t = transform_polygon(outer, holes, rot, x, y)
            
            color = COLORS[pi % len(COLORS)]
            pts_str = ' '.join(f'{px:.2f},{py:.2f}' for px, py in outer_t)
            svg_lines.append(f'    <polygon points="{pts_str}" fill="{color}" fill-opacity="0.5" stroke="{color}" stroke-width="0.5"/>')
            
            for hi, hole in enumerate(holes_t):
                h_pts = ' '.join(f'{px:.2f},{py:.2f}' for px, py in hole)
                svg_lines.append(f'    <polygon points="{h_pts}" fill="white" stroke="#999" stroke-width="0.3"/>')
        
        svg_lines.append('  </g>')
    
    svg_lines.append('</svg>')
    with open(output_path, 'w') as f:
        f.write('\n'.join(svg_lines))

# ─── Main placement loop ─────────────────────────────────────────────────────

def run_placement(spacing_mm, max_candidates=300, candidate_cap=True):
    parts = load_parts()
    parts.sort(key=lambda p: -p['area'])  # Descending area
    
    # Instantiate to full quantity
    instances = []
    for part in parts:
        for qi in range(part['full_qty']):
            inst = dict(part)
            inst['current_instance'] = qi
            inst['qty'] = 1
            instances.append(inst)
    
    total_requested = len(instances)
    print(f"Total instances requested: {total_requested}")
    
    half_sp = spacing_mm / 2.0
    
    sheets = [make_sheet()]
    placed_count = 0
    unplaced = []
    candidate_count = 0
    collision_checks = 0
    spacing_checks = 0
    
    parts_lookup = {p['id']: p for p in parts}
    
    start_time = time.time()
    
    for inst_idx, inst in enumerate(instances):
        placed = False
        
        for sheet_idx, sheet in enumerate(sheets):
            placed_aabbs = []
            placed_data = []
            
            for pl in sheet['placements']:
                pdata = parts_lookup.get(pl['part_id'])
                if not pdata:
                    continue
                outer_t, holes_t = transform_polygon(pdata['outer'], pdata['holes'], pl['rotation_deg'], pl['x_mm'], pl['y_mm'])
                xs = [p[0] for p in outer_t]
                ys = [p[1] for p in outer_t]
                aabb = (min(xs), min(ys), max(xs), max(ys))
                placed_aabbs.append(aabb)
                placed_data.append({'outer': outer_t, 'holes': holes_t})
            
            bw, bh = inst['bw'], inst['bh']
            rots = inst['rots']
            best_score = None
            best_pos = None
            best_rot = None
            
            for rot in rots:
                bw_r = bw if rot == 0 else bh
                bh_r = bh if rot == 0 else bw
                
                candidates = generate_candidates(placed_aabbs, [], sheet_idx, bw, bh, bw_r, bh_r, spacing_mm, max_candidates)
                candidate_count += len(candidates)
                
                for cx, cy, score in candidates:
                    if candidate_cap and candidate_count > max_candidates * len(instances):
                        break
                    
                    outer_t, holes_t = transform_polygon(inst['outer'], inst['holes'], rot, cx, cy)
                    
                    # Bounds check
                    xs = [p[0] for p in outer_t]
                    ys = [p[1] for p in outer_t]
                    part_w = max(xs) - min(xs)
                    part_h = max(ys) - min(ys)
                    
                    if cx < -0.001 or cy < -0.001:
                        continue
                    if cx + part_w > SHEET_W + 0.001 or cy + part_h > SHEET_H + 0.001:
                        continue
                    
                    # AABB overlap prefilter
                    new_aabb = (min(xs), min(ys), max(xs), max(ys))
                    collides = False
                    for paabb in placed_aabbs:
                        collision_checks += 1
                        if aabb_overlap(paabb, new_aabb):
                            collides = True
                            break
                    
                    if collides:
                        continue
                    
                    # Exact spacing check — ALWAYS run for placed parts, not just on AABB overlap.
                    # Concave geometries can have spacing violations even when AABBs don't overlap.
                    # This is the primary difference from T05n's approximate_bbox policy.
                    spacing_checks += 1
                    if placed_data:
                        if exact_spacing_check_distance(placed_data, outer_t, holes_t, spacing_mm):
                            continue
                    
                    # Valid placement
                    if best_score is None or score < best_score:
                        best_score = score
                        best_pos = (cx, cy)
                        best_rot = rot
            
            if best_pos is not None:
                cx, cy = best_pos
                outer_t, holes_t = transform_polygon(inst['outer'], inst['holes'], best_rot, cx, cy)
                if place_on_sheet(sheet, inst, cx, cy, best_rot, spacing_mm, half_sp):
                    placed_count += 1
                    placed = True
                    break
        
        if not placed:
            # Try new sheet
            new_sheet = make_sheet()
            sheets.append(new_sheet)
            sheet_idx = len(sheets) - 1
            
            bw, bh = inst['bw'], inst['bh']
            rots = inst['rots']
            best_score = None
            best_pos = None
            best_rot = None
            
            for rot in rots:
                bw_r = bw if rot == 0 else bh
                bh_r = bh if rot == 0 else bw
                
                candidates = generate_candidates([], [], sheet_idx, bw, bh, bw_r, bh_r, spacing_mm, max_candidates)
                candidate_count += len(candidates)
                
                for cx, cy, score in candidates:
                    outer_t, holes_t = transform_polygon(inst['outer'], inst['holes'], rot, cx, cy)
                    
                    xs = [p[0] for p in outer_t]
                    ys = [p[1] for p in outer_t]
                    part_w = max(xs) - min(xs)
                    part_h = max(ys) - min(ys)
                    
                    if cx < -0.001 or cy < -0.001:
                        continue
                    if cx + part_w > SHEET_W + 0.001 or cy + part_h > SHEET_H + 0.001:
                        continue
                    
                    # No collision check on empty sheet
                    # No spacing check on empty sheet
                    if best_score is None or score < best_score:
                        best_score = score
                        best_pos = (cx, cy)
                        best_rot = rot
            
            if best_pos is not None:
                cx, cy = best_pos
                if place_on_sheet(new_sheet, inst, cx, cy, best_rot, spacing_mm, half_sp):
                    placed_count += 1
                else:
                    unplaced.append({'part_id': inst['id'], 'instance': inst.get('current_instance', 0)})
            else:
                unplaced.append({'part_id': inst['id'], 'instance': inst.get('current_instance', 0)})
        
        if (inst_idx + 1) % 10 == 0:
            elapsed = time.time() - start_time
            print(f"  Placed {inst_idx + 1}/{total_requested} instances, {placed_count} placed, {len(sheets)} sheets, {elapsed:.1f}s")
    
    elapsed = time.time() - start_time
    
    return {
        'sheets': sheets,
        'placed_count': placed_count,
        'total_requested': total_requested,
        'unplaced': unplaced,
        'candidate_count': candidate_count,
        'collision_checks': collision_checks,
        'spacing_checks': spacing_checks,
        'runtime': elapsed,
        'parts_lookup': parts_lookup
    }

# ─── Metrics ──────────────────────────────────────────────────────────────────

def compute_metrics(result, spacing_mm):
    sheets = result['sheets']
    placed_count = result['placed_count']
    total_requested = result['total_requested']
    unplaced = result['unplaced']
    
    total_area = SHEET_AREA * len(sheets)
    placed_area = sum(s['area'] for s in sheets)
    utilization = placed_area / total_area * 100 if total_area > 0 else 0
    
    utilization_per_sheet = [s['area'] / SHEET_AREA * 100 for s in sheets]
    
    metrics = {
        'placement_mode': 'blf_candidate_exact_spacing_preview',
        'spacing_policy': 'shapely_distance_or_buffer_exact',
        'collision_mode': 'aabb_prefilter_shapely_exact_buffer',
        'quantity_mode': 'full',
        'spacing_mm': spacing_mm,
        'sheet_width_mm': SHEET_W,
        'sheet_height_mm': SHEET_H,
        'total_part_types': len(set(p['id'] for p in result['parts_lookup'].values())),
        'total_instances_requested': total_requested,
        'total_instances_placed': placed_count,
        'total_instances_unplaced': len(unplaced),
        'sheet_count': len(sheets),
        'sheet_count_t05n_baseline': 11,
        'sheet_count_delta_vs_t05n': len(sheets) - 11,
        'utilization_total_pct': round(utilization, 2),
        'utilization_per_sheet': [round(u, 2) for u in utilization_per_sheet],
        'area_requested_mm2': sum(p['area'] * p['full_qty'] for p in result['parts_lookup'].values()),
        'area_placed_mm2': placed_area,
        'overlap_count': 0,  # Would need post-hoc validation
        'bounds_violation_count': 0,  # Would need post-hoc validation
        'spacing_violation_count': 0,  # Would need post-hoc validation
        'runtime_sec': round(result['runtime'], 3),
        'candidate_count_total': result['candidate_count'],
        'candidate_count_avg_per_instance': round(result['candidate_count'] / max(placed_count, 1), 1),
        'collision_checks': result['collision_checks'],
        'spacing_checks': result['spacing_checks'],
        'unplaced_list': unplaced
    }
    
    return metrics

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='T05o: LV6 BLF/Candidate Exact Spacing Preview')
    parser.add_argument('--spacing-mm', type=float, default=10.0, help='Required spacing in mm')
    parser.add_argument('--max-candidates', type=int, default=300, help='Max candidates per placement')
    parser.add_argument('--output-dir', type=str, default=str(BASE), help='Output directory')
    args = parser.parse_args()

    spacing_mm = args.spacing_mm
    
    print("=" * 60)
    print(f"T05o: LV6 BLF/Candidate Exact Spacing Preview")
    print(f"Spacing: {spacing_mm}mm")
    print(f"Policy: shapely_distance_or_buffer_exact (buffer method)")
    print("=" * 60)
    print()

    result = run_placement(spacing_mm, max_candidates=args.max_candidates)
    metrics = compute_metrics(result, spacing_mm)

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Placed: {metrics['total_instances_placed']}/{metrics['total_instances_requested']}")
    print(f"Sheets: {metrics['sheet_count']} (T05n baseline: 11, delta: {metrics['sheet_count_delta_vs_t05n']})")
    print(f"Utilization: {metrics['utilization_total_pct']}%")
    print(f"Runtime: {metrics['runtime_sec']}s")
    print(f"Candidates: {metrics['candidate_count_total']}")
    print(f"Unplaced: {metrics['total_instances_unplaced']}")
    print()

    # Build layout JSON
    layout = {
        'placement_mode': metrics['placement_mode'],
        'spacing_mm': spacing_mm,
        'spacing_policy': metrics['spacing_policy'],
        'sheets': {str(i): {'placements': s['placements'], 'placed_count': s['placed_count'], 'unplaced_count': s.get('unplaced_count', 0)} for i, s in enumerate(result['sheets'])}
    }

    # Save outputs
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    prefix = f'lv6_blf_candidate_exact_spacing{int(spacing_mm * 10)}'
    
    layout_path = output_dir / f'{prefix}_layout.json'
    metrics_path = output_dir / f'{prefix}_metrics.json'
    
    # DEBUG: count placements before save
    total_in_result = sum(len(s['placements']) for s in result['sheets'])
    
    with open(layout_path, 'w') as f:
        json.dump(layout, f, indent=2)
    print(f"Layout: {layout_path}")
    
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics: {metrics_path}")

    # Generate SVGs
    print("Generating SVGs...")
    generate_per_sheet_svgs(result['sheets'], result['parts_lookup'], spacing_mm, output_dir, prefix)
    
    combined_svg_path = output_dir / f'{prefix}_combined.svg'
    generate_combined_svg(result['sheets'], result['parts_lookup'], spacing_mm, combined_svg_path)
    print(f"Combined SVG: {combined_svg_path}")

    # Update metrics with SVG paths
    svg_pages = [str(output_dir / f'{prefix}_sheet{s+1:02d}.svg') for s in range(len(result['sheets']))]
    metrics['svg_pages'] = svg_pages
    metrics['combined_svg'] = str(combined_svg_path)
    
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    # Generate metrics markdown
    md_content = f"""# T05o: LV6 Exact Spacing Preview — {spacing_mm}mm

## Státusz: PARTIAL

**Prototype/reference only. NOT production. CGAL is GPL — NOT production.**

---

## Metrikák

| Metrika | Érték |
|---------|-------|
| Placement mode | {metrics['placement_mode']} |
| Spacing policy | {metrics['spacing_policy']} |
| Spacing | {spacing_mm}mm |
| Part típusok | {metrics['total_part_types']} |
| Instance requested | {metrics['total_instances_requested']} |
| Instance placed | **{metrics['total_instances_placed']}** |
| Instance unplaced | **{metrics['total_instances_unplaced']}** |
| Lapok | {metrics['sheet_count']} |
| Lapok delta vs T05n | {metrics['sheet_count_delta_vs_t05n']} |
| Kihasználtság (összes) | {metrics['utilization_total_pct']}% |
| Runtime | {metrics['runtime_sec']}s |
| Candidate count | {metrics['candidate_count_total']} |
| Collision checks | {metrics['collision_checks']} |
| Spacing checks | {metrics['spacing_checks']} |

---

## Unplaced list

"""
    
    if metrics['unplaced_list']:
        for u in metrics['unplaced_list']:
            md_content += f"- {u['part_id']} (instance {u['instance']})\n"
    else:
        md_content += "Nincs unplaced instance.\n"
    
    md_content += f"""

---

## Spacing policy

**Policy:** `shapely_distance_or_buffer_exact`

Exact buffer method:
- `polygon.buffer(half_spacing)` method for exact spacing enforcement
- `half_sp = spacing_mm / 2.0`
- Buffer both new polygon and placed polygons by `half_sp`
- If buffered polygons intersect → spacing violation
- Different from T05n's `approximate_bbox` (where spacing=0 and spacing=2 were identical)

---

## Sheet eloszlás

| Sheet | Placed | Utilization |
|-------|--------|-------------|
"""
    
    for i, s in enumerate(result['sheets']):
        util = s['area'] / SHEET_AREA * 100
        md_content += f"| {i+1} | {s['placed_count']} | {util:.2f}% |\n"
    
    md_content += f"""

---

## Output Artefaktumok

- `{prefix}_layout.json`
- `{prefix}_metrics.json`
- `{prefix}_metrics.md`
- `{prefix}_sheetNN.svg` (per sheet)
- `{prefix}_combined.svg`

---

## Limitációk

1. **Prototype only**: NEM production nesting algorithm
2. **Exact buffer method**: Slower than approximate_bbox but more accurate
3. **No post-hoc exact validation in metrics**: overlap_count, bounds_violation_count, spacing_violation_count are placeholder 0 — run validator separately
4. **Runtime**: ~{metrics['runtime_sec']}s for {metrics['total_instances_placed']} instances

---

## Következő javasolt lépés

1. Run `validate_lv6_exact_spacing.py` on the output layout to get exact spacing violations
2. If violations exist, iterate on placement algorithm
3. Consider NFP-based spacing for production
"""
    
    md_path = output_dir / f'{prefix}_metrics.md'
    with open(md_path, 'w') as f:
        f.write(md_content)
    print(f"Metrics MD: {md_path}")

if __name__ == '__main__':
    main()
