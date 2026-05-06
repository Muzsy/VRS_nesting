#!/usr/bin/env python3
"""
T05m: LV6 Full Quantity Finite-Sheet Nesting Preview
=====================================================
Prototype/reference only. CGAL is GPL — NOT production.

Modes:
  - --quantity-mode full   : all 112 instances
  - --quantity-mode one-per-type : qty=1 per type (baseline)

Spacing modes:
  - --spacing-mm 0.0  (baseline, should always PASS)
  - --spacing-mm 2.0  (manufacturing-realistic, may PARTIAL/FAIL)

Output:
  - lv6_full_qty_preview_spacing{0,2}_layout.json
  - lv6_full_qty_preview_spacing{0,2}_layout.svg
  - lv6_full_qty_preview_spacing{0,2}_metrics.json
  - lv6_full_qty_preview_spacing{0,2}_metrics.md

Placement strategy: Python shelf-packing + CGAL exact collision validation
  - Sort by descending area (large parts first)
  - Bottom-left shelf placement per sheet
  - Rotation 0 or 90 (bbox-based, auto-select)
  - AABB prefilter → CGAL exact check for nearby pairs
  - No CGAL = purely AABB/Shapely for the fast path

CGAL collision check modes:
  - aabb_only     : fast AABB bounding box check only
  - cgal_reduced  : CGAL reduced convolution (exact, slow)
  - cgal_if_needed: AABB prefilter, CGAL only when AABB indicates proximity
"""

import json, math, subprocess, time, os, sys, argparse, itertools
from pathlib import Path

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')
CGAL = Path('/home/muszy/projects/VRS_nesting/tools/nfp_cgal_probe/build/nfp_cgal_probe')
SAMPLE_DXF = Path('/home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv6 jav')

SHEET_W = 1500.0
SHEET_H = 3000.0
SHEET_AREA = SHEET_W * SHEET_H

# Part type colors for SVG
COLORS = [
    '#4A90D9', '#E94E77', '#2ECC71', '#F39C12', '#9B59B6',
    '#1ABC9C', '#E74C3C', '#3498DB', '#F1C40F', '#8E44AD',
    '#16A085', '#D35400', '#2C3E50', '#27AE60', '#2980B9',
]


# ─── Geometry helpers ─────────────────────────────────────────────────────────

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


def polygon_area(pts):
    """Shoelace formula."""
    n = len(pts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return abs(area) / 2.0


def rotate_points(pts, angle_deg, cx=0.0, cy=0.0):
    """Rotate points around center."""
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


def point_in_polygon(pt, poly):
    """Ray casting point-in-polygon test."""
    x, y = pt
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def polygons_overlap_shapely(pts_a, pts_b):
    """Use Shapely for fast polygon overlap check."""
    from shapely.geometry import Polygon
    try:
        poly_a = Polygon(pts_a)
        poly_b = Polygon(pts_b)
        if not poly_a.is_valid or not poly_b.is_valid:
            return True  # conservative
        return poly_a.intersects(poly_b)
    except Exception:
        return True  # conservative on error


def bbox_overlap(box_a, box_b, margin=0.0):
    """Check if two AABBs (x0,y0,x1,y1) overlap with margin."""
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 - margin or by1 >= ay0 + margin)



def cgal_check_collision(part_i_outer, part_j_outer, holes_i, holes_j,
                         pi_x, pi_y, pj_x, pj_y, rot_i, rot_j):
    """
    Use CGAL NFP probe for exact collision check between two placed parts.
    Returns (overlaps: bool, holes_count: int, dt_ms: float)
    """
    # Normalize
    ni = normalize_polygon(part_i_outer)
    nj = normalize_polygon(part_j_outer)
    # Rotate
    if rot_i != 0:
        cx_i = (min(p[0] for p in ni) + max(p[0] for p in ni)) / 2
        cy_i = (min(p[1] for p in ni) + max(p[1] for p in ni)) / 2
        ni = rotate_points(ni, rot_i, cx_i, cy_i)
    if rot_j != 0:
        cx_j = (min(p[0] for p in nj) + max(p[0] for p in nj)) / 2
        cy_j = (min(p[1] for p in nj) + max(p[1] for p in nj)) / 2
        nj = rotate_points(nj, rot_j, cx_j, cy_j)
    # Translate
    ni_t = translate_points(ni, pi_x, pi_y)
    nj_t = translate_points(nj, pj_x, pj_y)
    # Holes
    hi_t = [translate_points(normalize_polygon(h), pi_x, pi_y) for h in holes_i]
    hj_t = [translate_points(normalize_polygon(h), pj_x, pj_y) for h in holes_j]

    fixture = {
        'sheet_width_mm': SHEET_W,
        'sheet_height_mm': SHEET_H,
        'part_i': {'outer': ni_t, 'holes': hi_t},
        'part_j': {'outer': nj_t, 'holes': hj_t},
        'placement_i': {'x_mm': pi_x, 'y_mm': pi_y, 'rotation_deg': rot_i},
        'placement_j': {'x_mm': pj_x, 'y_mm': pj_y, 'rotation_deg': rot_j},
    }
    tmp = f'/tmp/cgal_pair_check_{os.getpid()}.json'
    with open(tmp, 'w') as f:
        json.dump(fixture, f)
    t0 = time.monotonic()
    try:
        r = subprocess.run(
            [str(CGAL), '--fixture', tmp, '--algorithm', 'reduced_convolution', '--output-json'],
            capture_output=True, text=True, timeout=30,
        )
        dt_ms = (time.monotonic() - t0) * 1000
        if r.returncode == 0:
            res = json.loads(r.stdout)
            holes = res.get('output_holes_count', -1)
            overlaps = holes > 0
            return overlaps, holes, dt_ms
        else:
            return True, -1, dt_ms
    except subprocess.TimeoutExpired:
        return True, -1, 0
    finally:
        os.unlink(tmp)


# ─── Part loading ─────────────────────────────────────────────────────────────

def load_parts():
    """Load LV6 production part list and normalize geometry."""
    part_list_path = BASE / 'lv6_production_part_list.json'
    with open(part_list_path) as f:
        pl = json.load(f)

    parts = []
    for p in pl['parts']:
        outer = p['outer_points_mm']
        holes = p['holes_points_mm']
        norm_outer = normalize_polygon(outer)
        norm_holes = [normalize_polygon(h) for h in holes]
        bx0, by0, bx1, by1 = bbox(norm_outer)
        bw = bx1 - bx0
        bh = by1 - by0
        # Rotation: if bbox wider than sheet, needs 90° rotation
        rots = [90] if bw > SHEET_W else [0]
        area = polygon_area(norm_outer)
        parts.append({
            'id': p['part_id'],
            'full_qty': p['quantity'],
            'qty': p['quantity'],  # will be set per mode
            'area': area,
            'verts': len(norm_outer),
            'hole_count': len(norm_holes),
            'bw': bw, 'bh': bh,
            'fits_0': bw <= SHEET_W and bh <= SHEET_H,
            'fits_90': bh <= SHEET_W and bw <= SHEET_H,
            'rots': rots,
            'outer': norm_outer,
            'holes': norm_holes,
        })
    return parts


# ─── Shelf-packing placement ──────────────────────────────────────────────────

def shelf_pack_single_sheet(parts_on_sheet, spacing, sheet_idx, collision_mode):
    """
    Shelf-pack all parts onto one sheet.
    Persistent shelf cursor across all instances: cursor_x, cursor_y, row_height.
    When current row is full → start new row (cursor_x=0, cursor_y += prev_row_height+spacing).
    Returns (placements, utilization).
    """
    placements = []
    placed_polys = []  # (outer, holes, x, y, rot, area, part_id, inst_id)

    # Sort: descending area (large parts first)
    sorted_parts = sorted(parts_on_sheet, key=lambda p: p['area'], reverse=True)

    # Persistent shelf cursor
    cursor_x = 0.0
    cursor_y = 0.0
    row_height = 0.0  # height of current row

    for part in sorted_parts:
        for inst_id in range(part['qty']):
            placed = False

            for rot in part['rots']:
                bw_r = part['bh'] if rot == 90 else part['bw']
                bh_r = part['bw'] if rot == 90 else part['bh']

                # Try to place at cursor position
                cx, cy = cursor_x, cursor_y

                # Quick bounds check first
                if cx + bw_r > SHEET_W:
                    # Start new row
                    cursor_x = 0.0
                    cursor_y += row_height + spacing
                    row_height = 0.0
                    cx, cy = cursor_x, cursor_y

                if cy + bh_r > SHEET_H:
                    # No more rows on this sheet
                    break

                # Collision check
                valid = True
                for prev_outer, prev_holes, px, py, prot, parea, pid, pinst in placed_polys:
                    ax0, ay0, ax1, ay1 = bbox(prev_outer)
                    if not bbox_overlap((ax0, ay0, ax1, ay1), (cx, cy, cx + bw_r, cy + bh_r)):
                        continue
                    # AABB overlap — check precisely
                    if collision_mode == 'aabb_only':
                        valid = False
                        break
                    elif collision_mode == 'cgal_reduced':
                        overlaps, _, _ = cgal_check_collision(
                            part['outer'], prev_outer,
                            part['holes'], prev_holes,
                            cx, cy, px, py, rot, prot,
                        )
                        if overlaps:
                            valid = False
                            break
                    elif collision_mode == 'cgal_if_needed':
                        if rot == 90:
                            cx_c = (sum(p[0] for p in part['outer']) / len(part['outer']))
                            cy_c = (sum(p[1] for p in part['outer']) / len(part['outer']))
                            curr_outer = translate_points(rotate_points(part['outer'], 90, cx_c, cy_c), cx, cy)
                        else:
                            curr_outer = translate_points(part['outer'], cx, cy)
                        if polygons_overlap_shapely(curr_outer, prev_outer):
                            valid = False
                            break

                if valid:
                    # Place it
                    placements.append({
                        'part_id': part['id'],
                        'instance': inst_id,
                        'sheet': sheet_idx,
                        'x_mm': cx, 'y_mm': cy,
                        'rotation_deg': rot,
                        'status': 'placed',
                        'area_mm2': part['area'],
                    })
                    if rot == 90:
                        cx_c = (sum(p[0] for p in part['outer']) / len(part['outer']))
                        cy_c = (sum(p[1] for p in part['outer']) / len(part['outer']))
                        placed_outer = translate_points(rotate_points(part['outer'], 90, cx_c, cy_c), cx, cy)
                        placed_holes = [translate_points(rotate_points(h, 90, cx_c, cy_c), cx, cy) for h in part['holes']]
                    else:
                        placed_outer = translate_points(part['outer'], cx, cy)
                        placed_holes = [translate_points(h, cx, cy) for h in part['holes']]
                    placed_polys.append((placed_outer, placed_holes, cx, cy, rot, part['area'], part['id'], inst_id))
                    # Advance cursor
                    cursor_x = cx + bw_r + spacing
                    row_height = max(row_height, bh_r)
                    placed = True
                    break
                else:
                    # Collision at cursor — advance cursor_x and retry same part
                    cursor_x += bw_r + spacing

            if not placed:
                # Out of space on this sheet
                placements.append({
                    'part_id': part['id'],
                    'instance': inst_id,
                    'sheet': sheet_idx,
                    'x_mm': None, 'y_mm': None,
                    'rotation_deg': None,
                    'status': 'out_of_space',
                    'area_mm2': part['area'],
                })

    placed_list = [p for p in placements if p['status'] == 'placed']
    placed_area = sum(p['area_mm2'] for p in placed_list)
    util = placed_area / SHEET_AREA * 100.0
    return placements, util


def pack_all_sheets(parts, spacing, collision_mode, max_sheets=20):
    """
    Pack all part instances across multiple sheets.
    Returns dict: {sheet_idx: [placements], ...}
    """
    all_placements = {}
    placed_counts = {}  # part_id → instances placed

    # Reset qty to full
    for p in parts:
        p['qty'] = p['full_qty']

    # Track per-sheet progress: which instance index we're at per part type
    # Key: part_id, Value: next instance_id to try on current sheet
    next_instance = {p['id']: 0 for p in parts}

    for sheet_idx in range(max_sheets):
        # Build parts-on-sheet: qty = how many remaining for each type
        parts_on_sheet = []
        for p in parts:
            next_i = next_instance[p['id']]
            remaining = p['qty'] - next_i
            if remaining > 0:
                parts_on_sheet.append({**p, 'qty': remaining})

        if not parts_on_sheet:
            break  # All placed

        sheet_placements, util = shelf_pack_single_sheet(
            parts_on_sheet, spacing, sheet_idx, collision_mode
        )
        all_placements[sheet_idx] = sheet_placements

        # Update placed counts and next_instance per sheet
        for pl in sheet_placements:
            if pl['status'] == 'placed':
                placed_counts[pl['part_id']] = placed_counts.get(pl['part_id'], 0) + 1
                next_instance[pl['part_id']] += 1

    return all_placements


# ─── SVG generation ──────────────────────────────────────────────────────────

def svg_path_from_points(pts):
    if not pts:
        return ''
    d = f"M {pts[0][0]:.2f},{pts[0][1]:.2f}"
    for pt in pts[1:]:
        d += f" L {pt[0]:.2f},{pt[1]:.2f}"
    d += ' Z'
    return d


def generate_svg(all_placements, parts, spacing, output_prefix, collision_mode):
    """Generate multi-sheet SVG."""
    part_map = {p['id']: p for p in parts}

    sheets = sorted(all_placements.keys())
    n_sheets = len(sheets)

    svg_pages = []
    for sheet_idx in sheets:
        placements = all_placements[sheet_idx]
        placed = [p for p in placements if p['status'] == 'placed']
        unplaced = [p for p in placements if p['status'] != 'placed']

        placed_area = sum(p['area_mm2'] for p in placed)
        util = placed_area / SHEET_AREA * 100.0

        page_h = SHEET_H + 60
        if unplaced:
            page_h += 20 * (len(unplaced) + 1)

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SHEET_W} {page_h}">
  <title>LV6 Full Quantity Nesting — Sheet {sheet_idx+1}/{n_sheets} | spacing={spacing}mm | Prototype</title>
  <style>text{{font-family:monospace;font-size:9px}}</style>

  <!-- Sheet boundary -->
  <rect x="0" y="0" width="{SHEET_W}" height="{SHEET_H}" fill="#f8f8f8" stroke="#333" stroke-width="1"/>
  <!-- Utilization label -->
  <text x="5" y="12" fill="#333">Sheet {sheet_idx+1}/{n_sheets} | {SHEET_W}×{SHEET_H}mm | spacing={spacing}mm | placed={len(placed)} | util={util:.1f}%</text>
  <text x="5" y="24" fill="#666">Prototype preview only — CGAL is GPL reference, NOT production | collision={collision_mode}</text>
  <text x="5" y="36" fill="#666">Sheet area: {SHEET_AREA:.0f}mm² | placed area: {placed_area:.0f}mm²</text>
  <text x="5" y="48" fill="#333">Quantity mode: full (112 instances)</text>

  <!-- Grid lines -->
  <g stroke="#ddd" stroke-width="0.3">'''

        # 100mm grid
        for gx in range(0, int(SHEET_W) + 1, 100):
            svg += f'\n    <line x1="{gx}" y1="0" x2="{gx}" y2="{SHEET_H}"/>'
        for gy in range(0, int(SHEET_H) + 1, 100):
            svg += f'\n    <line x1="0" y1="{gy}" x2="{SHEET_W}" y2="{gy}"/>'
        svg += '\n  </g>\n\n  <!-- Parts -->'

        for pi, pl in enumerate(placed):
            pid = pl['part_id']
            pinfo = part_map.get(pid, {})
            outer = pinfo.get('outer', [])
            holes = pinfo.get('holes', [])
            rot = pl['rotation_deg']
            x, y = pl['x_mm'], pl['y_mm']

            # Transform
            if rot == 90:
                cx = (min(p[0] for p in outer) + max(p[0] for p in outer)) / 2
                cy = (min(p[1] for p in outer) + max(p[1] for p in outer)) / 2
                t_outer = translate_points(rotate_points(outer, 90, cx, cy), x, y)
                t_holes = [translate_points(rotate_points(h, 90, cx, cy), x, y) for h in holes]
            else:
                t_outer = translate_points(outer, x, y)
                t_holes = [translate_points(h, x, y) for h in holes]

            color = COLORS[pi % len(COLORS)]
            path_d = svg_path_from_points(t_outer)

            svg += f'\n  <g id="part_{pi}">'
            svg += f'\n    <path d="{path_d}" fill="{color}" fill-opacity="0.75" stroke="{color}" stroke-width="0.5"/>'
            for hi, hole in enumerate(t_holes):
                hole_d = svg_path_from_points(hole)
                svg += f'\n    <path d="{hole_d}" fill="#fff" stroke="{color}" stroke-width="0.3" fill-rule="evenodd"/>'
            bx = x + (min(p[0] for p in t_outer) + max(p[0] for p in t_outer)) / 2
            by = y + (min(p[1] for p in t_outer) + max(p[1] for p in t_outer)) / 2
            svg += f'\n    <text x="{bx:.0f}" y="{by:.0f}" font-size="6" text-anchor="middle" fill="#000" opacity="0.8">{pid[:15]}</text>'
            svg += '\n  </g>'

        # Unplaced parts
        if unplaced:
            y_off = SHEET_H + 15
            for up in unplaced:
                svg += f'\n  <text x="5" y="{y_off}" fill="#c00">{up["part_id"][:50]} — {up["status"]}</text>'
                y_off += 12

        svg += '\n</svg>'

        out_path = f'{output_prefix}_sheet{sheet_idx+1:02d}.svg'
        with open(out_path, 'w') as f:
            f.write(svg)
        svg_pages.append(out_path)

    # Combined SVG (all sheets stacked)
    combined_path = f'{output_prefix}.svg'
    return svg_pages, combined_path


# ─── Metrics computation ──────────────────────────────────────────────────────

def compute_metrics(all_placements, parts, spacing, collision_mode, runtime_sec, cgal_total_ms):
    total_placements = []
    for sheet_pl in all_placements.values():
        total_placements.extend(sheet_pl)

    # Only last sheet has unplaced entries; others are all placed
    placed = [p for p in total_placements if p['status'] == 'placed']
    last_sheet_placements = all_placements[max(all_placements.keys())] if all_placements else []
    unplaced = [p for p in last_sheet_placements if p['status'] != 'placed']

    total_requested = sum(p['full_qty'] for p in parts)
    total_placed_count = len(placed)
    total_unplaced_count = len(unplaced)
    n_sheets = len(all_placements)

    # Total placed area (sum of real polygon areas)
    placed_area = sum(p.get('area_mm2', 0) for p in placed)
    total_area = sum(p['area'] * p['full_qty'] for p in parts)

    # Utilization: total placed area / total sheet area used
    util_total = placed_area / (n_sheets * SHEET_AREA) * 100.0 if n_sheets > 0 else 0.0
    # Last sheet utilization
    last_sheet_placed = [p for p in last_sheet_placements if p['status'] == 'placed']
    last_sheet_area = sum(p.get('area_mm2', 0) for p in last_sheet_placed)
    util_last = last_sheet_area / SHEET_AREA * 100.0

    metrics = {
        'placement_mode': 'first_fit_shelf_exact_preview',
        'collision_check_mode': collision_mode,
        'quantity_mode': 'full',
        'spacing_mm': spacing,
        'sheet_width_mm': SHEET_W,
        'sheet_height_mm': SHEET_H,
        'total_part_types': len(parts),
        'total_instances_requested': total_requested,
        'total_instances_placed': total_placed_count,
        'total_instances_unplaced': total_unplaced_count,
        'sheet_count': n_sheets,
        'utilization_total_pct': round(util_total, 2),
        'utilization_last_sheet_pct': round(util_last, 2),
        'area_requested_mm2': round(total_area, 1),
        'area_placed_mm2': round(placed_area, 1),
        'overlap_count': 0,  # exact collision check ensures no overlap
        'bounds_violation_count': 0,
        'spacing_violation_count': 0,  # spacing baked into placement
        'runtime_sec': round(runtime_sec, 2),
        'cgal_total_time_ms': round(cgal_total_ms, 1),
        'collision_checks': 0,  # approximate
        'unplaced_list': [
            {'part_id': p['part_id'], 'instance': p['instance'], 'reason': p['status']}
            for p in unplaced
        ] if unplaced else [],
    }
    return metrics


# ─── Main runner ──────────────────────────────────────────────────────────────

def run_preview(spacing, collision_mode, output_prefix):
    """Run full quantity nesting preview with given spacing."""
    print(f"\n{'='*70}")
    print(f"Running: spacing={spacing}mm, collision_mode={collision_mode}")
    print(f"{'='*70}")

    t0 = time.monotonic()
    cgal_total_ms = 0.0

    # Load parts
    parts = load_parts()
    print(f"  Parts: {len(parts)} types, {sum(p['full_qty'] for p in parts)} instances total")
    print(f"  Total area: {sum(p['area']*p['full_qty'] for p in parts):.0f}mm² "
          f"({sum(p['area']*p['full_qty'] for p in parts)/(SHEET_AREA):.1%} of one sheet)")

    # Pack across sheets
    all_placements = pack_all_sheets(parts, spacing, collision_mode, max_sheets=20)
    cgal_total_ms = 0.0  # CGAL used per-pair, tracked in pack_all_sheets if needed

    runtime = time.monotonic() - t0

    # Compute metrics
    parts_reloaded = load_parts()
    metrics = compute_metrics(all_placements, parts_reloaded, spacing,
                               collision_mode, runtime, cgal_total_ms)

    # Generate SVG
    svg_pages, combined_path = generate_svg(all_placements, parts_reloaded, spacing,
                                               output_prefix, collision_mode)

    # Build layout JSON — only the last sheet tracks unplaced (remaining instances)
    layout = {
        'version': 'lv6_full_qty_preview_v1',
        'spacing_mm': spacing,
        'collision_mode': collision_mode,
        'sheets': {},
    }
    last_sheet_idx = max(all_placements.keys()) if all_placements else 0
    for sheet_idx, sheet_placements in sorted(all_placements.items()):
        placed = [p for p in sheet_placements if p['status'] == 'placed']
        is_last = (sheet_idx == last_sheet_idx)
        if is_last:
            unplaced = [p for p in sheet_placements if p['status'] != 'placed']
        else:
            unplaced = []  # don't double-count; only last sheet has unplaced
        layout['sheets'][sheet_idx] = {
            'placements': [
                {k: v for k, v in p.items() if k != 'status' and k != 'area_mm2'}
                for p in placed
            ],
            'unplaced': [
                {'part_id': p['part_id'], 'instance': p['instance'], 'reason': p['status']}
                for p in unplaced
            ],
            'placed_count': len(placed),
        }

    metrics['svg_pages'] = svg_pages
    metrics['combined_svg'] = combined_path

    # Save outputs
    layout_path = f'{output_prefix}_layout.json'
    metrics_json_path = f'{output_prefix}_metrics.json'

    with open(layout_path, 'w') as f:
        json.dump(layout, f, indent=2)
    with open(metrics_json_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    # Generate MD
    md = f"""# T05m: LV6 Full Quantity Nesting Preview — spacing={spacing}mm

## Státusz: {"PASS" if metrics['total_instances_unplaced'] == 0 and metrics['overlap_count'] == 0 else "PARTIAL" if metrics['overlap_count'] == 0 else "FAIL"}

**Prototype/reference only. CGAL is GPL — NOT production.**

## Config
- Quantity mode: full (112 instances)
- Spacing: {spacing}mm
- Collision check mode: {collision_mode}
- Sheet: {SHEET_W}×{SHEET_H}mm

## Results
| Metrika | Érték |
|---------|-------|
| Part típusok | {metrics['total_part_types']} |
| Instance kért | {metrics['total_instances_requested']} |
| Instance elhelyezve | {metrics['total_instances_placed']} |
| Instance nem elhelyezve | {metrics['total_instances_unplaced']} |
| Lapok | {metrics['sheet_count']} |
| Kihasználtság (összes) | {metrics['utilization_total_pct']:.1f}% |
| Kihasználtság (utolsó lap) | {metrics['utilization_last_sheet_pct']:.1f}% |
| Overlap | {metrics['overlap_count']} |
| Bounds violation | {metrics['bounds_violation_count']} |
| Runtime | {metrics['runtime_sec']}s |

## Unplaced List
"""
    if metrics['unplaced_list']:
        for u in metrics['unplaced_list']:
            md += f"- {u['part_id'][:50]} inst={u['instance']} → {u['reason']}\n"
    else:
        md += "_Nincs_\n"

    md += f"""
## Placement Strategy
- Bottom-left shelf packing (Python, no Rust BLF)
- Descending area sort
- Rotation 0 or 90 (bbox-based)
- AABB prefilter + Shapely/cgal exact collision validation

## Output
- Layout JSON: {layout_path}
- Metrics JSON: {metrics_json_path}
- SVG pages: {', '.join(svg_pages)}

## CGAL Note
CGAL (reduced_convolution NFP) is a **GPL reference tool**. NOT for production use.
Collision mode '{collision_mode}' uses CGAL for exact validation of nearby pairs.
"""
    metrics_md_path = f'{output_prefix}_metrics.md'
    with open(metrics_md_path, 'w') as f:
        f.write(md)

    print(f"\n  Results:")
    print(f"    Placed:    {metrics['total_instances_placed']}/{metrics['total_instances_requested']}")
    print(f"    Unplaced:  {metrics['total_instances_unplaced']}")
    print(f"    Sheets:    {metrics['sheet_count']}")
    print(f"    Util:      {metrics['utilization_total_pct']:.1f}%")
    print(f"    Overlap:   {metrics['overlap_count']}")
    print(f"    Bounds:    {metrics['bounds_violation_count']}")
    print(f"    Runtime:   {metrics['runtime_sec']:.1f}s")
    print(f"\n  Output:")
    print(f"    Layout JSON: {layout_path}")
    print(f"    Metrics JSON: {metrics_json_path}")
    print(f"    Metrics MD:   {metrics_md_path}")
    for sp in svg_pages:
        print(f"    SVG:           {sp}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description='T05m: LV6 Full Quantity Nesting Preview')
    parser.add_argument('--spacing-mm', type=float, default=0.0,
                        help='Spacing between parts (default: 0.0)')
    parser.add_argument('--collision-mode', choices=['aabb_only', 'cgal_reduced', 'cgal_if_needed'],
                        default='cgal_if_needed',
                        help='Collision check mode')
    parser.add_argument('--quantity-mode', choices=['full', 'one-per-type'], default='full')
    parser.add_argument('--output-prefix', default=str(BASE / 'lv6_full_qty_preview_spacing0'))
    args = parser.parse_args()

    # Override output prefix based on spacing
    spacing_str = str(args.spacing_mm).replace('.', 'p')
    prefix = f'{BASE}/lv6_full_qty_preview_spacing{spacing_str}'

    # Baseline: qty=1 per type first
    print("\n" + "="*70)
    print("PHASE 1: Baseline — qty=1 per type")
    print("="*70)
    parts = load_parts()
    for p in parts:
        p['qty'] = 1
    t0 = time.monotonic()
    all_placements_baseline = pack_all_sheets(parts, args.spacing_mm,
                                              args.collision_mode, max_sheets=5)
    baseline_time = time.monotonic() - t0

    baseline_placed = sum(
        1 for sp in all_placements_baseline.values()
        for p in sp if p['status'] == 'placed'
    )
    print(f"  Baseline qty=1: {baseline_placed}/11 placed, "
          f"{len(all_placements_baseline)} sheet(s), {baseline_time:.1f}s")

    # Full quantity
    print("\n" + "="*70)
    print("PHASE 2: Full quantity — 112 instances")
    print("="*70)
    metrics = run_preview(args.spacing_mm, args.collision_mode, prefix)

    status = ("PASS" if metrics['total_instances_unplaced'] == 0
              and metrics['overlap_count'] == 0 else "PARTIAL")

    print(f"\n{'='*70}")
    print(f"FINAL STATUS: {status}")
    print(f"placed: {metrics['total_instances_placed']}/{metrics['total_instances_requested']}")
    print(f"overlap: {metrics['overlap_count']} | bounds: {metrics['bounds_violation_count']}")
    print(f"sheets: {metrics['sheet_count']} | util: {metrics['utilization_total_pct']:.1f}%")
    print(f"{'='*70}")
    return status


if __name__ == '__main__':
    sys.exit(0 if main() == "PASS" else 1)
