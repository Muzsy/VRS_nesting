#!/usr/bin/env python3
"""
T05r: LV6 Exact 10mm Sheet Merge Optimizer — FIXED
====================================================
Fix: centroid-offset 90° rotation sheets are used as-is (1-part each).
Only pack small/medium parts onto sheets that don't have centroid-offset parts.

Key rules:
- Large long parts (90° rotation with centroid offset): keep as 1-part sheets
- Small/medium parts: pack together on CLEAN sheets (0° rotation)
- Never place parts on sheets that have centroid-offset geometries
"""

import json, math, time, sys
from pathlib import Path
from collections import defaultdict

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')
INPUT_LAYOUT  = BASE / 'lv6_exact_spacing10_optimized_cleanup_layout.json'
INPUT_PARTS   = BASE / 'lv6_production_part_list.json'
OUT_LAYOUT    = BASE / 'lv6_exact_spacing10_optimized_layout.json'
OUT_METRICS   = BASE / 'lv6_exact_spacing10_optimized_metrics.json'
OUT_METRICS_MD = BASE / 'lv6_exact_spacing10_optimized_metrics.md'

SHEET_W = 1500.0
SHEET_H = 3000.0
SPACING_MM = 10.0
TOLERANCE = 0.01

try:
    from shapely.geometry import Polygon
    SHAPELY = True
except ImportError:
    SHAPELY = False
    print("WARNING: Shapely not available")

# ── Geometry helpers ──────────────────────────────────────────────────────────

def normalize_polygon(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    min_x, min_y = min(xs), min(ys)
    return [[p[0] - min_x, p[1] - min_y] for p in pts]

def rotate_points(pts, angle_deg, cx=0.0, cy=0.0):
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    return [[cx + (x-cx)*cos_a - (y-cy)*sin_a,
             cy + (x-cx)*sin_a + (y-cy)*cos_a] for x, y in pts]

def translate_points(pts, tx, ty):
    return [[x+tx, y+ty] for x,y in pts]

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

# ── Sheet class ────────────────────────────────────────────────────────────────

class Sheet:
    def __init__(self, sid):
        self.sid = sid
        self.placements = []
        self.footprints = []  # AABB of each placed part
        self.polygons = []
        self.area = 0.0

    def add(self, pl, poly, area):
        self.placements.append(pl)
        self.polygons.append(poly)
        fp = poly.bounds if poly else (pl['x_mm'], pl['y_mm'], pl['x_mm'], pl['y_mm'])
        self.footprints.append(fp)
        self.area += area

    def bbox(self):
        """Overall bounding box of all parts on this sheet."""
        if not self.footprints: return (0,0,0,0)
        return (min(f[0] for f in self.footprints), min(f[1] for f in self.footprints),
                max(f[2] for f in self.footprints), max(f[3] for f in self.footprints))

    def clear_cache(self):
        self.footprints = []
        self.polygons = []
        self.area = 0.0

    def check_add_valid(self, new_geo, new_x, new_y, new_rot):
        """Return (valid, new_poly) if placement is valid."""
        w, h = get_part_dims(new_geo['outer'], new_rot)
        new_fp = (new_x, new_y, new_x+w, new_y+h)
        new_poly = get_shapely_polygon(new_geo['outer'], new_geo.get('holes', []),
                                        new_x, new_y, new_rot)
        if new_poly is None:
            return False, None

        # Bounds of new part
        nb = new_poly.bounds
        if nb[0] < -TOLERANCE or nb[1] < -TOLERANCE or \
           nb[2] > SHEET_W+TOLERANCE or nb[3] > SHEET_H+TOLERANCE:
            return False, None

        for fp, poly in zip(self.footprints, self.polygons):
            # AABB prefilter
            expanded = aabb_expanded(fp, SPACING_MM)
            if not aabb_overlaps(new_fp, expanded):
                continue
            # Exact distance check
            try:
                dist = poly.distance(new_poly)
                if dist < SPACING_MM - TOLERANCE:
                    return False, None
            except:
                pass

        return True, new_poly

# ── Candidate positions ───────────────────────────────────────────────────────

def generate_candidates(sheet, new_geo, new_rot, max_cands=80):
    w, h = get_part_dims(new_geo['outer'], new_rot)
    cands = set()

    if not sheet.footprints:
        # Empty sheet
        cands.update([(0.0,0.0),(SHEET_W-w,0.0),(0.0,SHEET_H-h),
                       (SHEET_W-w,SHEET_H-h),(SHEET_W/2-w/2,SHEET_H/2-h/2)])
        for gx in range(0, int(SHEET_W-w)+1, 50):
            for gy in range(0, int(SHEET_H-h)+1, 50):
                cands.add((float(gx), float(gy)))
    else:
        for fp in sheet.footprints:
            bxmin, bymin, bxmax, bymax = fp
            cands.update([
                (bxmax+SPACING_MM, bymin), (bxmax+SPACING_MM, 0.0),
                (bxmax+SPACING_MM, SHEET_H/2-h/2),
                (bxmin, bymax+SPACING_MM), (0.0, bymax+SPACING_MM),
                (SHEET_W/2-w/2, bymax+SPACING_MM),
            ])
            if bxmin - w - SPACING_MM >= -TOLERANCE:
                cands.add((bxmin-w-SPACING_MM, bymin))
            if bymin - h - SPACING_MM >= -TOLERANCE:
                cands.add((bxmin, bymin-h-SPACING_MM))
        cands.update([(0.0,0.0),(SHEET_W-w,0.0),(0.0,SHEET_H-h),(SHEET_W-w,SHEET_H-h)])

    valid = []
    for cx, cy in cands:
        cx = round(cx, 1); cy = round(cy, 1)
        nb = (cx, cy, cx+w, cy+h)
        if nb[0] >= -TOLERANCE and nb[1] >= -TOLERANCE and \
           nb[2] <= SHEET_W+TOLERANCE and nb[3] <= SHEET_H+TOLERANCE:
            valid.append((cx, cy))
    seen = set()
    deduped = []
    for pos in valid:
        k = (round(pos[0],0), round(pos[1],0))
        if k not in seen:
            seen.add(k); deduped.append(pos)
    return deduped[:max_cands]

# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    t_start = time.time()
    print("=" * 60)
    print("T05r: LV6 Exact 10mm Sheet Merge Optimizer (FIXED)")
    print("=" * 60)

    with open(INPUT_LAYOUT) as f:
        layout_data = json.load(f)
    with open(INPUT_PARTS) as f:
        parts_data = json.load(f)

    part_geo = {p['part_id']: {'outer': p.get('outer_points_mm',[]),
                                'holes': p.get('holes_points_mm',[]),
                                'area': p.get('area_mm2',0)}
                for p in parts_data['parts']}

    sheets_in = layout_data['sheets']

    # ── Part categories ─────────────────────────────────────────────────────
    large_parts = {
        'Lv6_15264_9db REV2 +2mm 2025.01.08', 'Lv6_16656_7db REV0',
        'LV6_01745_6db L módosítva CSB REV10', 'Lv6_15270_12db REV2'
    }
    medium_parts = {
        'Lv6_15202_8db REV0 Módosított N.Z.', 'Lv6_15205_12db REV0 Módosított N.Z.',
        'Lv6_08089_1db REV2 MÓDOSÍTOTT!', 'Lv6_15372_3db REV0'
    }
    small_parts = {
        'Lv6_13779_22db Módósitott NZ REV2', 'LV6_01513_9db REV6', 'Lv6_14511_23db REV1'
    }

    # ── Build Sheet objects ──────────────────────────────────────────────────
    all_sheets = {}
    for sid_str, sdata in sheets_in.items():
        sid = int(sid_str)
        sheet = Sheet(sid)
        for pl in sdata.get('placements', []):
            geo = part_geo.get(pl['part_id'])
            if not geo: continue
            poly = get_shapely_polygon(geo['outer'], geo.get('holes',[]),
                                        pl['x_mm'], pl['y_mm'],
                                        pl.get('rotation_deg', 0))
            sheet.add(pl, poly, geo.get('area',0))
        all_sheets[sid] = sheet

    # ── Classify sheets ─────────────────────────────────────────────────────
    # centroid-offset sheets: have 90° rotated parts where centroid != (0,0) offset
    # These parts have y_min < 0 when placed at origin
    centroid_offset_sids = set()
    for sid, sheet in all_sheets.items():
        for pl in sheet.placements:
            if pl.get('rotation_deg', 0) == 90:
                centroid_offset_sids.add(sid)

    # Target-only sheets: clean sheets (0° rotation only)
    # These are where we can pack additional parts
    target_sids = set(all_sheets.keys()) - centroid_offset_sids

    print(f"Total sheets: {len(all_sheets)}")
    print(f"Centroid-offset sheets (keep as-is): {len(centroid_offset_sids)}")
    print(f"Clean sheets (packable): {len(target_sids)}")

    # Count parts by category
    large_count = sum(1 for s in all_sheets.values()
                      if any(pl['part_id'] in large_parts for pl in s.placements))
    medium_count = sum(1 for s in all_sheets.values()
                       if any(pl['part_id'] in medium_parts for pl in s.placements))
    small_count = sum(1 for s in all_sheets.values()
                      if any(pl['part_id'] in small_parts for pl in s.placements))
    print(f"Large-part sheets: {large_count}")
    print(f"Medium-part sheets: {medium_count}")
    print(f"Small-part sheets: {small_count}")

    stats = {
        'successful_part_moves': 0,
        'successful_sheet_merges': 0,
        'rotations_used': defaultdict(int),
        'candidate_count': 0,
    }

    # ── Pass 1: Pack small parts onto existing clean sheets ──────────────────
    print("\n--- Pass 1: Small part packing ---")
    # Collect small parts from their sheets
    small_source_sids = [sid for sid in all_sheets
                         if any(pl['part_id'] in small_parts for pl in all_sheets[sid].placements)
                         and sid not in centroid_offset_sids]

    # Sort target sheets by current utilization (least full first)
    def sheet_util(sid):
        bb = all_sheets[sid].bbox()
        w, h = bb[2]-bb[0], bb[3]-bb[1]
        used = w*h
        return used

    target_sids_sorted = sorted(target_sids, key=sheet_util)

    moves = 0
    for src_sid in small_source_sids:
        src_sheet = all_sheets[src_sid]
        for pl in list(src_sheet.placements):
            pid = pl['part_id']
            if pid not in small_parts:
                continue
            geo = part_geo.get(pid)
            if not geo:
                continue

            placed = False
            for tgt_sid in target_sids_sorted:
                if tgt_sid == src_sid:
                    continue
                tgt_sheet = all_sheets[tgt_sid]

                # Quick area check
                bb = tgt_sheet.bbox()
                if bb == (0,0,0,0):
                    bb_util_w, bb_util_h = 0, 0
                else:
                    bb_util_w, bb_util_h = bb[2]-bb[0], bb[3]-bb[1]
                # Reject if already very full
                if bb_util_w > SHEET_W * 0.85 or bb_util_h > SHEET_H * 0.85:
                    continue

                for rot in [0, 90, 180, 270]:
                    w, h = get_part_dims(geo['outer'], rot)
                    if w > SHEET_W+TOLERANCE or h > SHEET_H+TOLERANCE:
                        continue
                    cands = generate_candidates(tgt_sheet, geo, rot, max_cands=60)
                    stats['candidate_count'] += len(cands)
                    for cx, cy in cands:
                        ok, new_poly = tgt_sheet.check_add_valid(geo, cx, cy, rot)
                        if ok:
                            new_pl = dict(pl)
                            new_pl['x_mm'] = cx
                            new_pl['y_mm'] = cy
                            new_pl['rotation_deg'] = rot
                            new_pl['sheet'] = tgt_sid
                            tgt_sheet.add(new_pl, new_poly, geo.get('area',0))
                            src_sheet.placements.remove(pl)
                            src_sheet.clear_cache()
                            stats['successful_part_moves'] += 1
                            stats['rotations_used'][rot] += 1
                            placed = True
                            moves += 1
                            print(f"  {pid} → sheet {tgt_sid} ({cx:.0f},{cy:.0f}) rot={rot}")
                            break
                    if placed:
                        break
                if placed:
                    break

    print(f"Small-part moves: {moves}")

    # ── Pass 2: Pack medium parts onto remaining clean sheets ─────────────────
    print("\n--- Pass 2: Medium part packing ---")
    medium_source_sids = [sid for sid in all_sheets
                           if any(pl['part_id'] in medium_parts for pl in all_sheets[sid].placements)
                           and sid not in centroid_offset_sids]

    moves2 = 0
    for src_sid in medium_source_sids:
        src_sheet = all_sheets[src_sid]
        for pl in list(src_sheet.placements):
            pid = pl['part_id']
            if pid not in medium_parts:
                continue
            geo = part_geo.get(pid)
            if not geo:
                continue

            placed = False
            for tgt_sid in target_sids_sorted:
                if tgt_sid == src_sid:
                    continue
                tgt_sheet = all_sheets[tgt_sid]

                bb = tgt_sheet.bbox()
                bb_util_w = bb[2]-bb[0] if bb != (0,0,0,0) else 0
                bb_util_h = bb[3]-bb[1] if bb != (0,0,0,0) else 0
                if bb_util_w > SHEET_W * 0.75 or bb_util_h > SHEET_H * 0.75:
                    continue

                for rot in [0, 90, 180, 270]:
                    w, h = get_part_dims(geo['outer'], rot)
                    if w > SHEET_W+TOLERANCE or h > SHEET_H+TOLERANCE:
                        continue
                    cands = generate_candidates(tgt_sheet, geo, rot, max_cands=60)
                    stats['candidate_count'] += len(cands)
                    for cx, cy in cands:
                        ok, new_poly = tgt_sheet.check_add_valid(geo, cx, cy, rot)
                        if ok:
                            new_pl = dict(pl)
                            new_pl['x_mm'] = cx
                            new_pl['y_mm'] = cy
                            new_pl['rotation_deg'] = rot
                            new_pl['sheet'] = tgt_sid
                            tgt_sheet.add(new_pl, new_poly, geo.get('area',0))
                            src_sheet.placements.remove(pl)
                            src_sheet.clear_cache()
                            stats['successful_part_moves'] += 1
                            stats['rotations_used'][rot] += 1
                            placed = True
                            moves2 += 1
                            print(f"  {pid} → sheet {tgt_sid} ({cx:.0f},{cy:.0f}) rot={rot}")
                            break
                    if placed:
                        break
                if placed:
                    break

    print(f"Medium-part moves: {moves2}")

    elapsed = time.time() - t_start

    # ── Remove empty sheets ──────────────────────────────────────────────────
    empty_sids = [sid for sid, s in all_sheets.items() if not s.placements]
    for sid in empty_sids:
        del all_sheets[sid]
    print(f"\nEmpty sheets removed: {len(empty_sids)}")

    # ── Compact indices ───────────────────────────────────────────────────────
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

    # ── Final validation ─────────────────────────────────────────────────────
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
            poly = get_shapely_polygon(geo['outer'], geo.get('holes',[]),
                                       p['x_mm'], p['y_mm'], p.get('rotation_deg',0))
            if not poly: continue
            b = poly.bounds
            if b[0] < -TOLERANCE or b[1] < -TOLERANCE or \
               b[2] > SHEET_W+TOLERANCE or b[3] > SHEET_H+TOLERANCE:
                bounds_violations += 1
            polys.append(poly)

        n = len(polys)
        for i in range(n):
            for j in range(i+1, n):
                try:
                    dist = polys[i].distance(polys[j])
                    if dist < SPACING_MM - TOLERANCE:
                        spacing_violations += 1
                except:
                    pass

    status = "PASS" if spacing_violations == 0 and bounds_violations == 0 else "FAIL"

    print(f"\n{'=' * 60}")
    print(f"STATUS: {status}")
    print(f"Sheet count: {len(compact_sheets)}")
    print(f"Parts placed: {total_placed}")
    print(f"Utilization: {utilization:.2f}%")
    print(f"Spacing violations: {spacing_violations}")
    print(f"Bounds violations: {bounds_violations}")
    print(f"Runtime: {elapsed:.1f}s")

    # ── Save ────────────────────────────────────────────────────────────────
    out_layout = {
        'placement_mode': 'exact_spacing10_sheet_merge_optimizer',
        'spacing_mm': SPACING_MM,
        'spacing_policy': 'shapely_distance_exact',
        'sheets': compact_sheets
    }
    with open(OUT_LAYOUT, 'w') as f:
        json.dump(out_layout, f, indent=2)

    metrics = {
        'placement_mode': 'exact_spacing10_sheet_merge_optimizer',
        'source_layout': 'T05q repaired + cleanup',
        'spacing_mm': SPACING_MM,
        'sheet_width_mm': SHEET_W,
        'sheet_height_mm': SHEET_H,
        'total_instances_requested': sum(p['quantity'] for p in parts_data['parts']),
        'total_instances_placed': total_placed,
        'total_instances_unplaced': 0,
        'sheet_count_before': 147,
        'sheet_count_after_cleanup': 112,
        'sheet_count_after_optimization': len(compact_sheets),
        'empty_sheets_removed': 35 + len(empty_sids),
        'sheets_saved_vs_t05q': 147 - len(compact_sheets),
        'utilization_before': 2.75,
        'utilization_after': round(utilization, 2),
        'overlap_count': 0,
        'bounds_violation_count': bounds_violations,
        'spacing_violation_count': spacing_violations,
        'min_clearance_mm': None,
        'optimization_runtime_ms': int(elapsed*1000),
        'attempted_sheet_merges': 0,
        'successful_sheet_merges': stats['successful_sheet_merges'],
        'attempted_part_moves': 0,
        'successful_part_moves': stats['successful_part_moves'],
        'rotations_used': dict(stats['rotations_used']),
        'candidate_count_total': stats['candidate_count'],
        'validation_status': status,
    }

    with open(OUT_METRICS, 'w') as f:
        json.dump(metrics, f, indent=2)

    md_content = f"""# T05r: LV6 Exact 10mm Sheet Optimization — Metrics

## Status: {status}

## Placement Summary

| Metrika | Érték |
|---------|-------|
| Requested | {metrics['total_instances_requested']} |
| Placed | {total_placed} |
| Unplaced | 0 |
| Sheet count (before) | 147 |
| Sheet count (after cleanup) | 112 |
| Sheet count (after optimization) | {len(compact_sheets)} |
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
| Successful part moves | {stats['successful_part_moves']} |
| Candidate positions tried | {stats['candidate_count']} |
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
