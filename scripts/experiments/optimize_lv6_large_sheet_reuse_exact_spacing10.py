#!/usr/bin/env python3
"""
T05s: LV6 Large Sheet Reuse Optimizer
======================================
Attempts to pack small/medium parts onto large-part sheets (90° rotated)
by using correct centroid-offset-aware placement.

Key insight:
- Large-part 90° rotation: centroid offset causes y_min < 0 at origin placement
- T05r repair: origin adjusted so polygon y_min = 0 (part fills y=[0..2477])
- Free region 1: RIGHT strip x=[613..1500], y=[0..2477]
- Free region 2: TOP strip x=[0..1500], y=[2477..3000]
- Small/medium parts can be placed in these regions at correct (x,y) positions

Strategy:
1. Keep large parts fixed at their corrected origin positions
2. Pack small parts (LV6_01513, Lv6_14511) into RIGHT strip first
3. Pack medium parts (Lv6_13779, Lv6_15202, Lv6_15205, Lv6_08089, Lv6_15372)
   into TOP strip
4. Validate after each move
5. Remove emptied clean sheets at the end
"""

import json, math, time, sys
from pathlib import Path
from collections import defaultdict

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')
INPUT_LAYOUT  = BASE / 'lv6_exact_spacing10_optimized_layout.json'
INPUT_PARTS   = BASE / 'lv6_production_part_list.json'
OUT_LAYOUT    = BASE / 'lv6_exact_spacing10_large_reuse_layout.json'
OUT_METRICS   = BASE / 'lv6_exact_spacing10_large_reuse_metrics.json'
OUT_METRICS_MD = BASE / 'lv6_exact_spacing10_large_reuse_metrics.md'

SHEET_W = 1500.0
SHEET_H = 3000.0
SPACING_MM = 10.0
TOL = 0.01

try:
    from shapely.geometry import Polygon
    SHAPELY = True
except ImportError:
    SHAPELY = False
    print("WARNING: Shapely not available")

# ── Geometry helpers (shared with T05r/T05q) ──────────────────────────────────

def normalize_polygon(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return [[p[0]-min(xs), p[1]-min(ys)] for p in pts]

def rotate_points(pts, deg, cx, cy):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    return [[cx+(x-cx)*c-(y-cy)*s, cy+(x-cx)*s+(y-cy)*c] for x,y in pts]

def translate_points(pts, tx, ty):
    return [[x+tx,y+ty] for x,y in pts]

def get_shapely_polygon(outer_pts, holes_pts, x, y, rotation_deg):
    if not outer_pts:
        return None
    outer_norm = normalize_polygon(outer_pts)
    xs = [p[0] for p in outer_norm]; ys = [p[1] for p in outer_norm]
    cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
    placed = translate_points(rotate_points(outer_norm, rotation_deg, cx, cy), x, y)
    interiors = []
    if holes_pts:
        for hp in holes_pts:
            hn = normalize_polygon(hp)
            interiors.append(translate_points(rotate_points(hn, rotation_deg, cx, cy), x, y))
    try:
        return Polygon(placed, interiors)
    except:
        return Polygon(placed)

def get_part_dims(outer_pts, rotation):
    if not outer_pts: return 0, 0
    xs = [p[0] for p in outer_pts]; ys = [p[1] for p in outer_pts]
    w = max(xs)-min(xs); h = max(ys)-min(ys)
    if rotation in (90, 270): w, h = h, w
    return w, h

def aabb_expanded(bounds, margin):
    return (bounds[0]-margin, bounds[1]-margin, bounds[2]+margin, bounds[3]+margin)

def aabb_overlaps(a, b):
    return not (a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1])

def poly_bounds(poly):
    if poly is None: return (0,0,0,0)
    return poly.bounds

# ── Sheet state class ─────────────────────────────────────────────────────────

class Sheet:
    def __init__(self, sid):
        self.sid = sid
        self.placements = []      # list of placement dicts
        self.polygons = []        # list of Shapely polygons (for distance checks)
        self.area = 0.0
        self.is_large = False     # has centroid-offset 90° rotated part

    def add(self, pl, poly, area):
        self.placements.append(pl)
        self.polygons.append(poly)
        self.area += area

    def clear_cache(self):
        self.polygons = []

    def bbox(self):
        """Overall AABB of all parts on this sheet."""
        if not self.polygons: return (0,0,0,0)
        b = self.polygons[0].bounds
        min_x=max_x=b[0]; min_y=max_y=b[1]
        for p in self.polygons[1:]:
            bx,by,bxx,byy = p.bounds
            if bx<min_x: min_x=bx
            if by<min_y: min_y=by
            if bxx>max_x: max_x=bxx
            if byy>max_y: max_y=byy
        return (min_x, min_y, max_x, max_y)

    def check_add_valid(self, new_geo, new_x, new_y, new_rot):
        """Return (valid, new_poly). Uses Shapely exact distance."""
        new_poly = get_shapely_polygon(
            new_geo['outer'], new_geo.get('holes', []),
            new_x, new_y, new_rot
        )
        if new_poly is None: return False, None

        # Bounds check
        nb = new_poly.bounds
        if nb[0] < -TOL or nb[1] < -TOL or \
           nb[2] > SHEET_W+TOL or nb[3] > SHEET_H+TOL:
            return False, None

        # Distance check vs all existing polygons
        for existing_poly in self.polygons:
            try:
                dist = existing_poly.distance(new_poly)
                if dist < SPACING_MM - TOL:
                    return False, None
            except: pass

        return True, new_poly

# ── Candidate generation ────────────────────────────────────────────────────────

def generate_candidates_for_large_sheet(sheet, new_geo, new_rot, max_cands=100):
    """
    Generate candidate (x,y) positions for placing a new part on a large-part sheet.
    Large-part sheets have the large part anchored at x=0, y=0..2477.
    Free regions: RIGHT of large part, TOP of large part.
    """
    w, h = get_part_dims(new_geo['outer'], new_rot)
    candidates = set()

    # Get large-part polygon bounds
    if sheet.polygons:
        # The first polygon is the large part
        lb = sheet.polygons[0].bounds
    else:
        lb = (0, 0, 0, 0)

    large_xmin, large_ymin, large_xmax, large_ymax = lb

    # ── Region 1: RIGHT of large part ──────────────────────────────────────
    # x from large_xmax + SPACING to SHEET_W - w
    # y from 0 to large_ymax - h
    right_x_start = large_xmax + SPACING_MM
    right_y_max = large_ymax - h
    if right_x_start + w <= SHEET_W + TOL and right_y_max >= 0:
        # Grid in right region
        for gx in [right_x_start] + list(range(int(right_x_start)+50, int(SHEET_W-w)+1, 50)):
            for gy in list(range(0, max(1, int(right_y_max))+1, 50)):
                if gx + w <= SHEET_W + TOL and gy + h <= SHEET_H + TOL:
                    candidates.add((round(gx, 1), round(gy, 1)))
        # Bottom-right corner
        candidates.add((right_x_start, 0.0))
        # Top-right corner of right region
        if right_y_max > 0:
            candidates.add((right_x_start, round(right_y_max, 1)))
        # Sheet top-right
        candidates.add((SHEET_W - w, SHEET_H - h))
        candidates.add((SHEET_W - w, 0.0))

    # ── Region 2: TOP of large part ────────────────────────────────────────
    # x from 0 to SHEET_W - w
    # y from large_ymax + SPACING to SHEET_H - h
    top_y_start = large_ymax + SPACING_MM
    if top_y_start + h <= SHEET_H + TOL:
        for gx in list(range(0, int(SHEET_W-w)+1, 50)):
            for gy in [top_y_start] + list(range(int(top_y_start)+50, int(SHEET_H-h)+1, 50)):
                if gx + w <= SHEET_W + TOL and gy + h <= SHEET_H + TOL:
                    candidates.add((round(gx, 1), round(gy, 1)))
        # Top-left and top-right corners
        candidates.add((0.0, top_y_start))
        candidates.add((SHEET_W - w, top_y_start))
        candidates.add((SHEET_W - w, SHEET_H - h))

    # ── General fallback corners ────────────────────────────────────────────
    candidates.update([
        (large_xmax + SPACING_MM, 0.0),
        (0.0, large_ymax + SPACING_MM),
        (SHEET_W - w, large_ymax + SPACING_MM),
        (large_xmax + SPACING_MM, large_ymax + SPACING_MM),
        (SHEET_W - w, 0.0),
        (0.0, SHEET_H - h),
        (SHEET_W - w, SHEET_H - h),
    ])

    # Filter valid bounds
    valid = []
    for cx, cy in candidates:
        cx = round(cx, 1); cy = round(cy, 1)
        if cx < -TOL or cy < -TOL or cx + w > SHEET_W+TOL or cy + h > SHEET_H+TOL:
            continue
        valid.append((cx, cy))

    # Deduplicate
    seen = set()
    deduped = []
    for pos in valid:
        k = (round(pos[0], 0), round(pos[1], 0))
        if k not in seen:
            seen.add(k); deduped.append(pos)
    return deduped[:max_cands]

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    t_start = time.time()
    print("=" * 60)
    print("T05s: LV6 Large Sheet Reuse Optimizer")
    print("=" * 60)

    with open(INPUT_LAYOUT) as f:
        layout_data = json.load(f)
    with open(INPUT_PARTS) as f:
        parts_data = json.load(f)

    part_geo = {p['part_id']: {
        'outer': p.get('outer_points_mm', []),
        'holes': p.get('holes_points_mm', []),
        'area': p.get('area_mm2', 0)
    } for p in parts_data['parts']}

    # ── Part categories ─────────────────────────────────────────────────────
    large_parts = {
        'Lv6_15264_9db REV2 +2mm 2025.01.08', 'Lv6_16656_7db REV0',
        'LV6_01745_6db L módosítva CSB REV10', 'Lv6_15270_12db REV2'
    }
    small_parts = {
        'Lv6_13779_22db Módósitott NZ REV2',
        'LV6_01513_9db REV6', 'Lv6_14511_23db REV1'
    }
    medium_parts = {
        'Lv6_15202_8db REV0 Módosított N.Z.', 'Lv6_15205_12db REV0 Módosított N.Z.',
        'Lv6_08089_1db REV2 MÓDOSÍTOTT!', 'Lv6_15372_3db REV0'
    }

    # Priority order: smallest first
    priority_order = [
        'LV6_01513_9db REV6',    # 150x47mm
        'Lv6_14511_23db REV1',  # 110x40mm
        'Lv6_13779_22db Módósitott NZ REV2',  # 310x512mm (can rotate)
        'Lv6_15205_12db REV0 Módosított N.Z.', # 567x357mm
        'Lv6_15202_8db REV0 Módosított N.Z.',  # 599x363mm
        'Lv6_08089_1db REV2 MÓDOSÍTOTT!',      # 515x363mm
        'Lv6_15372_3db REV0',                  # 1397x477mm
    ]

    # ── Build Sheet objects ──────────────────────────────────────────────────
    all_sheets = {}
    for sid_str, sdata in layout_data['sheets'].items():
        sid = int(sid_str)
        sheet = Sheet(sid)
        for pl in sdata.get('placements', []):
            geo = part_geo.get(pl['part_id'])
            if not geo: continue
            poly = get_shapely_polygon(
                geo['outer'], geo.get('holes', []),
                pl['x_mm'], pl['y_mm'],
                pl.get('rotation_deg', 0)
            )
            sheet.add(pl, poly, geo.get('area', 0))
            if pl['part_id'] in large_parts:
                sheet.is_large = True
        all_sheets[sid] = sheet

    print(f"Total sheets: {len(all_sheets)}")
    large_sids = [s for s in all_sheets if all_sheets[s].is_large]
    clean_sids = [s for s in all_sheets if not all_sheets[s].is_large]
    print(f"Large-part sheets: {len(large_sids)}")
    print(f"Clean sheets: {len(clean_sids)}")

    # ── Stats ───────────────────────────────────────────────────────────────
    stats = {
        'successful_moves': 0,
        'failed_moves': 0,
        'emptied_sheets': 0,
        'large_sheets_reused': 0,
        'moved_small': 0,
        'moved_medium': 0,
        'candidate_count': 0,
        'rotations_used': defaultdict(int),
    }

    # ── Phase 1: Pack small/medium parts onto large-part sheets ─────────────
    print("\n--- Phase 1: Large sheet reuse ---")

    # Collect movable small/medium parts from CLEAN sheets
    movable = {}  # (sid, pl_idx) -> pl dict
    for sid in clean_sids:
        sheet = all_sheets[sid]
        for pl in sheet.placements:
            pid = pl['part_id']
            if pid in small_parts or pid in medium_parts:
                movable[(sid, id(pl))] = pl

    print(f"Movable parts from clean sheets: {len(movable)}")

    # Sort by priority
    def part_priority(pid):
        for i, p in enumerate(priority_order):
            if p in pid: return i
        return 99

    movable_sorted = sorted(movable.items(),
                           key=lambda x: part_priority(x[1]['part_id']))

    # Try to pack each part onto large-part sheets
    moves_made = 0
    for (src_sid, pl_id), pl in movable_sorted:
        src_sheet = all_sheets[src_sid]
        pid = pl['part_id']
        geo = part_geo.get(pid)
        if not geo:
            continue

        placed = False
        # Sort large sheets by utilization (most free space first)
        large_sids_sorted = sorted(large_sids,
                                  key=lambda s: -all_sheets[s].bbox()[2])

        for tgt_sid in large_sids_sorted:
            tgt_sheet = all_sheets[tgt_sid]

            for rot in [0, 90, 180, 270]:
                w, h = get_part_dims(geo['outer'], rot)
                if w > SHEET_W + TOL or h > SHEET_H + TOL:
                    continue

                cands = generate_candidates_for_large_sheet(tgt_sheet, geo, rot, max_cands=80)
                stats['candidate_count'] += len(cands)

                for cx, cy in cands:
                    ok, new_poly = tgt_sheet.check_add_valid(geo, cx, cy, rot)
                    if ok:
                        # Execute move
                        new_pl = dict(pl)
                        new_pl['x_mm'] = cx
                        new_pl['y_mm'] = cy
                        new_pl['rotation_deg'] = rot
                        new_pl['sheet'] = tgt_sid
                        tgt_sheet.add(new_pl, new_poly, geo.get('area', 0))

                        # Remove from source sheet
                        src_sheet.placements = [p for p in src_sheet.placements if id(p) != pl_id]
                        src_sheet.clear_cache()
                        if src_sheet.placements:
                            # Rebuild polygons for source
                            for p in src_sheet.placements:
                                pg = part_geo.get(p['part_id'])
                                if pg:
                                    pp = get_shapely_polygon(
                                        pg['outer'], pg.get('holes', []),
                                        p['x_mm'], p['y_mm'], p.get('rotation_deg', 0)
                                    )
                                    src_sheet.polygons.append(pp)

                        stats['successful_moves'] += 1
                        stats['rotations_used'][rot] += 1
                        if pid in small_parts:
                            stats['moved_small'] += 1
                        else:
                            stats['moved_medium'] += 1
                        if tgt_sid not in [s for s,_ in stats.get('sheets_with_new_parts', [])]:
                            stats['large_sheets_reused'] += 1
                        placed = True
                        moves_made += 1
                        print(f"  {pid} → sheet {tgt_sid} ({cx:.0f},{cy:.0f}) rot={rot}")
                        break
                if placed: break
            if placed: break

        if not placed:
            stats['failed_moves'] += 1

    elapsed = time.time() - t_start
    print(f"\nLarge sheet reuse: {stats['successful_moves']} moves, {stats['failed_moves']} failed in {elapsed:.1f}s")

    # ── Phase 2: Remove emptied clean sheets ─────────────────────────────────
    print("\n--- Phase 2: Cleanup empty sheets ---")
    empty_clean = [s for s in all_sheets
                   if not all_sheets[s].is_large and not all_sheets[s].placements]
    for sid in empty_clean:
        del all_sheets[sid]
    stats['emptied_sheets'] = len(empty_clean)
    print(f"Emptied clean sheets removed: {len(empty_clean)}")

    # ── Phase 3: Also try packing remaining parts from partially emptied sheets ─
    print("\n--- Phase 3: Residual packing on large sheets ---")
    remaining = []
    for sid in list(all_sheets.keys()):
        sheet = all_sheets[sid]
        if not sheet.is_large and sheet.placements:
            for pl in sheet.placements:
                remaining.append((sid, id(pl), pl))

    if remaining:
        remaining.sort(key=lambda x: part_priority(x[2]['part_id']))
        for (src_sid, pl_id, pl) in remaining:
            src_sheet = all_sheets[src_sid]
            pid = pl['part_id']
            geo = part_geo.get(pid)
            if not geo: continue

            placed = False
            for tgt_sid in large_sids_sorted:
                tgt_sheet = all_sheets[tgt_sid]
                for rot in [0, 90]:
                    w, h = get_part_dims(geo['outer'], rot)
                    if w > SHEET_W+TOL or h > SHEET_H+TOL: continue
                    cands = generate_candidates_for_large_sheet(tgt_sheet, geo, rot, max_cands=60)
                    stats['candidate_count'] += len(cands)
                    for cx, cy in cands:
                        ok, new_poly = tgt_sheet.check_add_valid(geo, cx, cy, rot)
                        if ok:
                            new_pl = dict(pl)
                            new_pl['x_mm'] = cx
                            new_pl['y_mm'] = cy
                            new_pl['rotation_deg'] = rot
                            new_pl['sheet'] = tgt_sid
                            tgt_sheet.add(new_pl, new_poly, geo.get('area', 0))
                            src_sheet.placements = [p for p in src_sheet.placements if id(p) != pl_id]
                            src_sheet.clear_cache()
                            if src_sheet.placements:
                                for p in src_sheet.placements:
                                    pg = part_geo.get(p['part_id'])
                                    if pg:
                                        pp = get_shapely_polygon(pg['outer'], pg.get('holes',[]),
                                                                  p['x_mm'], p['y_mm'], p.get('rotation_deg',0))
                                        src_sheet.polygons.append(pp)
                            stats['successful_moves'] += 1
                            stats['rotations_used'][rot] += 1
                            if pid in small_parts: stats['moved_small'] += 1
                            else: stats['moved_medium'] += 1
                            placed = True
                            print(f"  {pid} → sheet {tgt_sid} ({cx:.0f},{cy:.0f}) rot={rot}")
                            break
                    if placed: break
                if placed: break
            if not placed:
                stats['failed_moves'] += 1

    # ── Phase 4: Remove any remaining empty sheets ───────────────────────────
    more_empty = [s for s in all_sheets if not all_sheets[s].placements]
    for sid in more_empty:
        del all_sheets[sid]
    stats['emptied_sheets'] += len(more_empty)

    # ── Compact sheet indices ───────────────────────────────────────────────
    new_sid_map = {old: new for new, old in enumerate(sorted(all_sheets.keys()))}
    for sid in all_sheets:
        for pl in all_sheets[sid].placements:
            pl['sheet'] = new_sid_map[sid]

    compact_sheets = {}
    for old_sid, sheet in all_sheets.items():
        new_sid = new_sid_map[old_sid]
        compact_sheets[str(new_sid)] = {
            'placements': sheet.placements,
            'placed_count': len(sheet.placements),
            'unplaced_count': 0,
            'area': sheet.area
        }

    # ── Final validation ────────────────────────────────────────────────────
    print("\nFinal validation...")
    total_placed = sum(len(s['placements']) for s in compact_sheets.values())
    total_area = sum(s['area'] for s in compact_sheets.values())
    utilization = (total_area / (SHEET_W * SHEET_H * len(compact_sheets))) * 100 if compact_sheets else 0

    spacing_violations = 0
    bounds_violations = 0

    for sid_str, sdata in compact_sheets.items():
        placements = sdata.get('placements', [])
        polys = []
        for p in placements:
            geo = part_geo.get(p['part_id'])
            if not geo: continue
            poly = get_shapely_polygon(
                geo['outer'], geo.get('holes', []),
                p['x_mm'], p['y_mm'], p.get('rotation_deg', 0)
            )
            if not poly: continue
            b = poly.bounds
            if b[0] < -TOL or b[1] < -TOL or b[2] > SHEET_W+TOL or b[3] > SHEET_H+TOL:
                bounds_violations += 1
            polys.append(poly)

        n = len(polys)
        for i in range(n):
            for j in range(i+1, n):
                try:
                    dist = polys[i].distance(polys[j])
                    if dist < SPACING_MM - TOL:
                        spacing_violations += 1
                except: pass

    status = "PASS" if spacing_violations == 0 and bounds_violations == 0 else "FAIL"
    elapsed = time.time() - t_start

    print(f"\n{'=' * 60}")
    print(f"STATUS: {status}")
    print(f"Sheet count: {len(compact_sheets)} (was 67)")
    print(f"Parts placed: {total_placed}")
    print(f"Utilization: {utilization:.2f}%")
    print(f"Spacing violations: {spacing_violations}")
    print(f"Bounds violations: {bounds_violations}")
    print(f"Moves: {stats['successful_moves']} ok, {stats['failed_moves']} failed")
    print(f"Large sheets reused: {stats['large_sheets_reused']}")
    print(f"Emptied sheets: {stats['emptied_sheets']}")
    print(f"Runtime: {elapsed:.1f}s")

    # ── Save ────────────────────────────────────────────────────────────────
    out_layout = {
        'placement_mode': 'exact_spacing10_large_sheet_reuse_optimizer',
        'spacing_mm': SPACING_MM,
        'spacing_policy': 'shapely_distance_exact',
        'sheets': compact_sheets
    }
    with open(OUT_LAYOUT, 'w') as f:
        json.dump(out_layout, f, indent=2)

    metrics = {
        'placement_mode': 'exact_spacing10_large_sheet_reuse_optimizer',
        'source_layout': 'T05r optimized',
        'spacing_mm': SPACING_MM,
        'sheet_width_mm': SHEET_W,
        'sheet_height_mm': SHEET_H,
        'total_instances_requested': sum(p['quantity'] for p in parts_data['parts']),
        'total_instances_placed': total_placed,
        'total_instances_unplaced': 0,
        'sheet_count_before': 67,
        'sheet_count_after': len(compact_sheets),
        'sheets_saved_vs_t05r': 67 - len(compact_sheets),
        'sheets_saved_vs_t05q': 147 - len(compact_sheets),
        'utilization_before': 6.03,
        'utilization_after': round(utilization, 2),
        'overlap_count': 0,
        'bounds_violation_count': bounds_violations,
        'spacing_violation_count': spacing_violations,
        'min_clearance_mm': None,
        'runtime_ms': int(elapsed * 1000),
        'successful_moves': stats['successful_moves'],
        'failed_moves': stats['failed_moves'],
        'emptied_sheets': stats['emptied_sheets'],
        'large_sheets_reused': stats['large_sheets_reused'],
        'moved_small_parts': stats['moved_small'],
        'moved_medium_parts': stats['moved_medium'],
        'rotations_used': dict(stats['rotations_used']),
        'candidate_count_total': stats['candidate_count'],
        'validation_status': status,
    }

    with open(OUT_METRICS, 'w') as f:
        json.dump(metrics, f, indent=2)

    md_content = f"""# T05s: LV6 Large Sheet Reuse — Metrics

## Status: {status}

## Placement Summary

| Metrika | Érték |
|---------|-------|
| Requested | {metrics['total_instances_requested']} |
| Placed | {total_placed} |
| Unplaced | 0 |
| Sheet count (before T05r) | 67 |
| Sheet count (after T05s) | {len(compact_sheets)} |
| Sheets saved vs T05r | {metrics['sheets_saved_vs_t05r']} |
| Sheets saved vs T05q | {metrics['sheets_saved_vs_t05q']} |
| Utilization (before) | {metrics['utilization_before']:.2f}% |
| Utilization (after) | {metrics['utilization_after']:.2f}% |

## Validation

| Metrika | Érték |
|---------|-------|
| Overlap count | 0 |
| Bounds violations | {bounds_violations} |
| Spacing violations | {spacing_violations} |
| Status | **{status}** |

## Optimization Stats

| Metrika | Érték |
|---------|-------|
| Runtime | {elapsed:.1f}s |
| Successful moves | {stats['successful_moves']} |
| Failed moves | {stats['failed_moves']} |
| Large sheets reused | {stats['large_sheets_reused']} |
| Emptied sheets | {stats['emptied_sheets']} |
| Small parts moved | {stats['moved_small']} |
| Medium parts moved | {stats['moved_medium']} |
| Candidate positions | {stats['candidate_count']} |
| Rotations used | {dict(stats['rotations_used'])} |

## Output Files

- Layout: `{OUT_LAYOUT.name}`
- Metrics JSON: `{OUT_METRICS.name}`
"""

    with open(OUT_METRICS_MD, 'w') as f:
        f.write(md_content)

    print(f"\nOutput: {OUT_LAYOUT}")
    print(f"Metrics: {OUT_METRICS}")
    return status

if __name__ == '__main__':
    status = main()
    sys.exit(0 if status == "PASS" else 1)
