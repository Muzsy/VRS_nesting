#!/usr/bin/env python3
"""Generate SVG output for T05r optimized layout."""
import json, math
from pathlib import Path

BASE = Path('/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe')

with open(BASE / 'lv6_exact_spacing10_optimized_layout.json') as f:
    layout = json.load(f)
with open(BASE / 'lv6_production_part_list.json') as f:
    parts_data = json.load(f)

part_geo = {p['part_id']: {'outer': p.get('outer_points_mm', []),
                             'holes': p.get('holes_points_mm', [])}
            for p in parts_data['parts']}

SHEET_W, SHEET_H = 1500.0, 3000.0
SCALE = 0.05

def normalize_polygon(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return [[p[0]-min(xs), p[1]-min(ys)] for p in pts]

def rotate_points(pts, deg, cx, cy):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    return [[cx+(x-cx)*c-(y-cy)*s, cy+(x-cx)*s+(y-cy)*c] for x,y in pts]

def translate_points(pts, tx, ty):
    return [[x+tx,y+ty] for x,y in pts]

def part_to_svg_path(outer, holes, x, y, rot, scale):
    if not outer: return ''
    o = normalize_polygon(outer)
    xs=[p[0] for p in o]; ys=[p[1] for p in o]
    cx,cy = sum(xs)/len(xs), sum(ys)/len(ys)
    placed = translate_points(rotate_points(o, rot, cx, cy), x, y)
    pts_flat = [f'{px*scale:.1f},{py*scale:.1f}' for px,py in placed]
    return 'M ' + ' L '.join(pts_flat) + ' Z'

colors = {
    'Lv6_15264_9db REV2 +2mm 2025.01.08': '#e74c3c',
    'Lv6_16656_7db REV0': '#e67e22',
    'LV6_01745_6db L módosítva CSB REV10': '#f1c40f',
    'Lv6_15270_12db REV2': '#2ecc71',
    'Lv6_15372_3db REV0': '#1abc9c',
    'Lv6_15202_8db REV0 Módosított N.Z.': '#3498db',
    'Lv6_15205_12db REV0 Módosított N.Z.': '#9b59b6',
    'Lv6_08089_1db REV2 MÓDOSÍTOTT!': '#34495e',
    'Lv6_13779_22db Módósitott NZ REV2': '#e91e63',
    'LV6_01513_9db REV6': '#00bcd4',
    'Lv6_14511_23db REV1': '#8bc34a',
}

svg_w = SHEET_W * SCALE
svg_h = SHEET_H * SCALE

# Combined SVG
svg_lines = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w:.0f} {svg_h:.0f}">',
    f'<rect width="{svg_w:.0f}" height="{svg_h:.0f}" fill="#f8f8f8" stroke="#ccc"/>',
    f'<text x="5" y="15" font-size="10" fill="#333">Sheet count: {len(layout["sheets"])} | Parts: 112 | Exact 10mm spacing</text>',
]
for sid_str, sdata in sorted(layout['sheets'].items(), key=lambda x: int(x[0])):
    for pl in sdata.get('placements', []):
        pid = pl['part_id']
        geo = part_geo.get(pid)
        if not geo or not geo['outer']: continue
        d = part_to_svg_path(geo['outer'], geo.get('holes', []),
                             pl['x_mm'], pl['y_mm'],
                             pl.get('rotation_deg', 0), SCALE)
        color = colors.get(pid, '#999')
        svg_lines.append(f'<path d="{d}" fill="{color}" stroke="#333" stroke-width="0.5" opacity="0.85"/>')
svg_lines.append('</svg>')
with open(BASE / 'lv6_exact_spacing10_optimized_combined.svg', 'w') as f:
    f.write('\n'.join(svg_lines))
print('Combined SVG done')

# Individual sheets (first 20)
for sid_str in list(sorted(layout['sheets'].keys(), key=int))[:20]:
    sdata = layout['sheets'][sid_str]
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w:.0f} {svg_h:.0f}">',
        f'<rect width="{svg_w:.0f}" height="{svg_h:.0f}" fill="#f8f8f8" stroke="#ccc"/>',
        f'<text x="5" y="15" font-size="10" fill="#333">Sheet {int(sid_str)+1} | Parts: {len(sdata["placements"])}</text>',
    ]
    for pl in sdata.get('placements', []):
        pid = pl['part_id']
        geo = part_geo.get(pid)
        if not geo or not geo['outer']: continue
        d = part_to_svg_path(geo['outer'], geo.get('holes', []),
                             pl['x_mm'], pl['y_mm'],
                             pl.get('rotation_deg', 0), SCALE)
        color = colors.get(pid, '#999')
        svg_lines.append(f'<path d="{d}" fill="{color}" stroke="#333" stroke-width="0.5" opacity="0.85"/>')
    svg_lines.append('</svg>')
    sheet_num = int(sid_str) + 1
    with open(BASE / f'lv6_exact_spacing10_optimized_sheet{sheet_num:02d}.svg', 'w') as f:
        f.write('\n'.join(svg_lines))
print('Individual sheet SVGs done (first 20)')
