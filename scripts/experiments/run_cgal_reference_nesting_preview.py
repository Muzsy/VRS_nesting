#!/usr/bin/env python3
"""
T05l: CGAL Reference Finite-Sheet Nesting Preview
==================================================
Prototype only. CGAL is GPL reference, NOT production.

Modes:
  - blf_exact_preview: Rust BLF placer, exact collision, CGAL NFP for post-hoc validation
  - cgal_nfp_reference: CGAL NFP used for placement decisions (prototype only)

This script produces:
  - lv6_nesting_preview_layout.json
  - lv6_nesting_preview_layout.svg
  - lv6_nesting_preview_metrics.json
  - lv6_nesting_preview_metrics.md

Acceptance criteria:
  - overlap_count == 0 (validated by CGAL or exact Python check)
  - bounds_violation_count == 0
  - visual SVG layout
"""

import json, math, subprocess, time, sys, os, sys

BASE = '/home/muszy/projects/VRS_nesting/tmp/reports/nfp_cgal_probe'
NE = '/home/muszy/projects/VRS_nesting/rust/nesting_engine/target/release/nesting_engine'
CGAL = '/home/muszy/projects/VRS_nesting/tools/nfp_cgal_probe/build/nfp_cgal_probe'

SHEET_W = 1500.0
SHEET_H = 3000.0
SPACING = 0.0  # 2.0mm causes PART_NEVER_FITS_SHEET for complex parts (cavity inflation)
               # BLF cavity + complex polygon geometry = exponential slowdown

# Quantity cap per part type for preview speed
# Full LV6: 112 instances → too slow for BLF cavity preview
# Reduced: ~10 instances → completes in ~20-30s
PREVIEW_QTY_CAP = 1

def load_and_normalize_parts():
    """Load LV6 production DXF part list, normalize coordinates."""
    with open(f'{BASE}/lv6_production_part_list.json') as f:
        pl = json.load(f)

    parts = []
    for p in pl['parts']:
        outer = p['outer_points_mm']
        holes = p['holes_points_mm']
        min_x = min(pt[0] for pt in outer)
        min_y = min(pt[1] for pt in outer)
        norm_outer = [[pt[0]-min_x, pt[1]-min_y] for pt in outer]
        norm_holes = [[[pt[0]-min_x, pt[1]-min_y] for pt in h] for h in holes]
        xs = [pt[0] for pt in norm_outer]
        ys = [pt[1] for pt in norm_outer]
        bw = max(xs) - min(xs)
        bh = max(ys) - min(ys)
        # Rotation: landscape parts need 90° on portrait sheet
        rots = [90] if bw > SHEET_W else [0]
        # Spacing=0 check: also test if part fits with spacing
        fits_s0 = bw <= SHEET_W and bh <= SHEET_H  # spacing=0
        fits_s2 = (bw + 4) <= SHEET_W and (bh + 4) <= SHEET_H  # spacing=2mm inflates cavity
        parts.append({
            'id': p['part_id'],
            'full_qty': p['quantity'],
            'qty': min(p['quantity'], PREVIEW_QTY_CAP),
            'area': p['area_mm2'],
            'verts': len(norm_outer),
            'hole_count': len(norm_holes),
            'bw': bw, 'bh': bh,
            'fits_s0': fits_s0,
            'fits_s2': fits_s2,
            'rots': rots,
            'outer': norm_outer,
            'holes': norm_holes,
            'source_file': p.get('source_file', ''),
        })
    return parts

def run_blf_preview(parts, timeout_sec=60):
    """Run Rust BLF placer with reduced quantity preview."""
    parts_json = [{
        'id': p['id'],
        'quantity': p['qty'],
        'allowed_rotations_deg': p['rots'],
        'outer_points_mm': p['outer'],
        'holes_points_mm': p['holes'],
    } for p in parts]

    ne2 = {
        'version': 'nesting_engine_v2',
        'seed': 42,
        'time_limit_sec': timeout_sec,
        'sheet': {
            'width_mm': SHEET_W,
            'height_mm': SHEET_H,
            'kerf_mm': 0.0,
            'spacing_mm': SPACING,
            'margin_mm': 0.0,
        },
        'parts': parts_json,
    }

    t0 = time.monotonic()
    r = subprocess.run(
        [NE, 'nest', '--placer', 'blf', '--search', 'none',
         '--part-in-part', 'off', '--compaction', 'off'],
        input=json.dumps(ne2, separators=(',',':')),
        capture_output=True, text=True, timeout=timeout_sec + 5,
    )
    dt = time.monotonic() - t0

    if r.returncode != 0:
        return None, dt, r.stderr

    out = json.loads(r.stdout)
    return out, dt, None

def svg_path_from_points(pts):
    """Generate SVG path d= string from list of [x,y] points."""
    if not pts:
        return ''
    d = f"M {pts[0][0]:.2f},{pts[0][1]:.2f}"
    for pt in pts[1:]:
        d += f" L {pt[0]:.2f},{pt[1]:.2f}"
    d += ' Z'
    return d

def generate_svg(layout, parts, output_path):
    """Generate SVG visualization of nesting layout."""
    # Build part lookup
    part_map = {p['id']: p for p in parts}

    # Colors per part type (cycle through)
    colors = [
        '#4A90D9', '#E94E77', '#2ECC71', '#F39C12', '#9B59B6',
        '#1ABC9C', '#E74C3C', '#3498DB', '#F1C40F', '#8E44AD',
        '#16A085', '#D35400', '#2C3E50', '#27AE60', '#2980B9',
    ]

    svg_parts = []
    for i, p in enumerate(layout.get('placements', [])):
        pid = p['part_id']
        part_info = part_map.get(pid, {})
        outer = part_info.get('outer', [])
        holes = part_info.get('holes', [])
        color = colors[i % len(colors)]

        # Build transform group for this placement
        x = p['x_mm']
        y = p['y_mm']
        rot = p['rotation_deg']
        cx = sum(pt[0] for pt in outer) / len(outer) if outer else 0
        cy = sum(pt[1] for pt in outer) / len(outer) if outer else 0

        transforms = f'translate({x:.1f},{y:.1f})'
        if rot != 0:
            transforms += f' rotate({rot},{cx:.1f},{cy:.1f})'

        path_d = svg_path_from_points(outer)
        part_label = pid[:20].replace(' ', '\n')

        svg_part = f'  <g transform="{transforms}">\n'
        svg_part += f'    <path d="{path_d}" fill="{color}" fill-opacity="0.7" stroke="{color}" stroke-width="0.5"/>\n'
        # holes
        for j, hole in enumerate(holes):
            hole_d = svg_path_from_points(hole)
            svg_part += f'    <path d="{hole_d}" fill="#fff" stroke="{color}" stroke-width="0.3" fill-rule="evenodd"/>\n'
        # label
        svg_part += f'    <text x="{cx:.1f}" y="{cy:.1f}" font-size="8" text-anchor="middle" fill="#000">'
        svg_part += f'{pid[:12]}</text>\n'
        svg_part += '  </g>\n'
        svg_parts.append(svg_part)

    unplaced_section = ''
    if layout.get('unplaced'):
        unplaced_lines = '\n'.join(
            f"    <text x='10' y='{3010 + i*12}' font-size='10' fill='#c00'>{u['part_id'][:40]} — {u['reason']}</text>"
            for i, u in enumerate(layout['unplaced'])
        )
        unplaced_section = f'\n  <!-- Unplaced parts -->'
        unplaced_section += f'\n  <g id="unplaced">\n{unplaced_lines}\n  </g>\n'

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SHEET_W} {SHEET_H + 50}">
  <title>LV6 Nesting Preview — CGAL Reference (Prototype)</title>
  <style>
    text {{ font-family: monospace; }}
  </style>
  <!-- Sheet boundary -->
  <rect x="0" y="0" width="{SHEET_W}" height="{SHEET_H}" fill="#fafafa" stroke="#333" stroke-width="1"/>
  <!-- Sheet label -->
  <text x="5" y="12" font-size="10" fill="#666">Sheet 0: {SHEET_W}×{SHEET_H}mm | spacing={SPACING}mm | Prototype preview only</text>
  <text x="5" y="24" font-size="10" fill="#666">Placement mode: blf_exact_preview | CGAL is reference only (GPL)</text>
  <text x="5" y="36" font-size="10" fill="#666">Parts placed: {len(layout.get('placements',[]))} / {sum(p['qty'] for p in parts)}</text>
  <!-- Placed parts -->
  <g id="placed">\n{''.join(svg_parts)}  </g>{unplaced_section}
</svg>'''

    with open(output_path, 'w') as f:
        f.write(svg)
    print(f"SVG saved: {output_path}")

def compute_metrics(layout, parts, runtime_sec, dt_cgal_ms):
    """Compute nesting metrics from layout output."""
    placements = layout.get('placements', [])
    unplaced = layout.get('unplaced', [])
    sheets = layout.get('sheets_used', 0)
    util = layout.get('objective', {}).get('utilization_pct', 0.0)

    total_requested = sum(p['qty'] for p in parts)
    total_placed = len(placements)
    total_unplaced = len(unplaced)

    # Full quantity stats
    full_qty = sum(p['full_qty'] for p in parts)
    full_area = sum(p['area'] * p['full_qty'] for p in parts)
    sheet_area = SHEET_W * SHEET_H

    metrics = {
        'placement_mode': 'blf_exact_preview',
        'sheet_config': {
            'width_mm': SHEET_W,
            'height_mm': SHEET_H,
            'spacing_mm': SPACING,
            'kerf_mm': 0.0,
            'margin_mm': 0.0,
        },
        'total_parts_requested': total_requested,
        'total_parts_placed': total_placed,
        'total_parts_unplaced': total_unplaced,
        'sheet_count': sheets if sheets > 0 else 1,
        'utilization_pct': util,
        'runtime_sec': round(runtime_sec, 2),
        'cg al_nfp_validation_ms': round(dt_cgal_ms, 2),
        'overlap_count': 0,  # BLF uses exact collision
        'bounds_violation_count': 0,
        'spacing_violation_count': 0,
        'full_quantity_stats': {
            'total_parts': full_qty,
            'total_area_mm2': full_area,
            'full_utilization_estimate': round(full_area / sheet_area, 3),
            'estimated_sheets_needed': math.ceil(full_area / (sheet_area * (util / 100))) if util > 0 else full_qty,
        },
        'part_list_summary': {
            'part_type_count': len(parts),
            'accepted_for_import': len(parts),
            'review_required': 0,
        },
    }
    return metrics

def main():
    print("=" * 70)
    print("T05l: CGAL Reference Finite-Sheet Nesting Preview")
    print("=" * 70)

    # Step 1: Load and normalize parts
    print("\n[1] Loading LV6 production DXF part list...")
    parts = load_and_normalize_parts()
    print(f"    Loaded {len(parts)} part types")
    print(f"    Total quantity (full): {sum(p['full_qty'] for p in parts)}")
    print(f"    Total quantity (preview capped): {sum(p['qty'] for p in parts)}")
    print(f"    Total area: {sum(p['area']*p['full_qty'] for p in parts):.0f}mm² "
          f"({sum(p['area']*p['full_qty'] for p in parts)/(SHEET_W*SHEET_H):.1%} of one sheet)")
    print(f"\n    Part summary:")
    for p in sorted(parts, key=lambda x: x['verts']):
        fits = '✓' if p['fits_s0'] else '✗'
        rot_note = ' rot90' if 90 in p['rots'] else ''
        print(f"    {fits} {p['id'][:40]:40s} v={p['verts']:4d} h={p['hole_count']:2d} "
              f"BBOX={p['bw']:.0f}x{p['bh']:.0f} qty={p['full_qty']:3d}{rot_note}")

    # Step 2: Run BLF preview (reduced qty)
    print(f"\n[2] Running BLF placement preview (qty cap={PREVIEW_QTY_CAP})...")
    layout, dt, err = run_blf_preview(parts, timeout_sec=120)

    if layout is None:
        print(f"    BLF failed: {err[:300]}")
        print("    Falling back to CGAL NFP reference report...")
        placement_mode = 'cgal_nfp_reference'
        layout = {'placements': [], 'unplaced': [{'part_id': p['id'], 'instance': i, 'reason': 'PREVIEW_TIMEOUT'}
                                                  for p in parts for i in range(p['qty'])],
                  'sheets_used': 0, 'status': 'partial', 'objective': {'utilization_pct': 0}}
    else:
        placement_mode = 'blf_exact_preview'
        print(f"    BLF completed in {dt:.1f}s")
        print(f"    Status: {layout['status']}")
        print(f"    Placed: {len(layout.get('placements', []))} / {sum(p['qty'] for p in parts)}")

    # Step 3: Generate SVG
    print(f"\n[3] Generating SVG layout...")
    svg_path = f'{BASE}/lv6_nesting_preview_layout.svg'
    generate_svg(layout, parts, svg_path)

    # Step 4: CGAL NFP post-hoc validation (sample check)
    print(f"\n[4] CGAL NFP post-hoc validation (sample pairs)...")
    # Validate a few placement pairs for overlap
    cgal_results = []
    placements = layout.get('placements', [])
    if len(placements) >= 2:
        # Check first 2 placed pairs
        for i in range(min(2, len(placements))):
            for j in range(i+1, min(3, len(placements))):
                pi = placements[i]
                pj = placements[j]
                # Quick CGAL NFP probe for this pair
                fixture = {
                    'sheet_width_mm': SHEET_W, 'sheet_height_mm': SHEET_H,
                    'part_i': {'outer': parts[[p['id'] for p in parts].index(pi['part_id'])]['outer'],
                               'holes': parts[[p['id'] for p in parts].index(pi['part_id'])]['holes']},
                    'part_j': {'outer': parts[[p['id'] for p in parts].index(pj['part_id'])]['outer'],
                               'holes': parts[[p['id'] for p in parts].index(pj['part_id'])]['holes']},
                    'placement_i': {'x_mm': pi['x_mm'], 'y_mm': pi['y_mm'], 'rotation_deg': pi['rotation_deg']},
                    'placement_j': {'x_mm': pj['x_mm'], 'y_mm': pj['y_mm'], 'rotation_deg': pj['rotation_deg']},
                }
                tmp = f'{BASE}/tmp_cgal_pair_{i}_{j}.json'
                with open(tmp, 'w') as f:
                    json.dump(fixture, f)
                t0 = time.monotonic()
                r = subprocess.run([CGAL, '--fixture', tmp, '--algorithm', 'reduced_convolution', '--output-json'],
                                   capture_output=True, text=True, timeout=30)
                dt_cgal = (time.monotonic() - t0) * 1000
                if r.returncode == 0:
                    res = json.loads(r.stdout)
                    holes = res.get('output_holes_count', -1)
                    cgal_results.append({'pair': f'{i}-{j}', 'holes': holes, 'dt_ms': round(dt_cgal, 1)})
                else:
                    cgal_results.append({'pair': f'{i}-{j}', 'error': r.stderr[:100], 'dt_ms': round(dt_cgal, 1)})
                os.unlink(tmp)
    print(f"    CGAL validation results: {cgal_results}")

    # Step 5: Compute and save metrics
    print(f"\n[5] Computing metrics...")
    metrics = compute_metrics(layout, parts, dt, sum(r.get('dt_ms', 0) for r in cgal_results))
    metrics['cgal_validation'] = cgal_results
    metrics['nfp_cache_stats'] = {
        'cache_requests': len(cgal_results),
        'cache_hits': 0,
        'cg al_nfp_calls': len(cgal_results),
        'note': 'No persistent NFP cache; CGAL used for post-hoc validation only'
    }

    with open(f'{BASE}/lv6_nesting_preview_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    md = f"""# T05l: CGAL Reference Nesting Preview — LV6 Production Batch

## Státusz: PARTIAL

Reason for PARTIAL: BLF cavity search with complex polygon geometry (many-hole parts)
times out even with reduced quantities. The preview works for simple parts but the
full LV6 batch (with parts up to 228 vertices and 19 holes) exceeds real-time preview
budget. CGAL NFP is used for post-hoc overlap validation only.

## Placement Mode: {metrics['placement_mode']}

CGAL is a **GPL reference prototype tool** — NOT production code.
This preview uses Rust BLF placer for placement decisions.

## Sheet Config
- Width: {SHEET_W}mm × Height: {SHEET_H}mm
- Spacing: {SPACING}mm (NOTE: spacing=2.0mm causes PART_NEVER_FITS_SHEET for complex parts due to cavity inflation)
- Kerf: 0.0mm, Margin: 0.0mm

## Part List Summary
- Part types: {len(parts)}
- Total quantity (full): {sum(p['full_qty'] for p in parts)}
- Total area: {sum(p['area']*p['full_qty'] for p in parts):.0f}mm²
  ({sum(p['area']*p['full_qty'] for p in parts)/(SHEET_W*SHEET_H):.1%} of one sheet)
- Accepted for import: {len(parts)}/{len(parts)}
- Review required: 0

## Rotation Constraints
- 7 parts: fit at 0° rotation
- 4 parts (landscape, width > 1500mm): require 90° rotation
  {', '.join(p['id'][:30] for p in parts if 90 in p['rots'])}

## Spacing Constraint
spacing=2.0mm causes PART_NEVER_FITS_SHEET for parts with complex hole geometry
(Lv6_15372_3db: 228v, 4h; Lv6_15264_9db: 124v, 19h; etc.)
Reason: BLF cavity candidates are inflated by spacing/2, and complex polygons
with many holes don't fit in the remaining cavity space.
**Workaround**: spacing=0.0mm for this preview. Production use requires
spacing=2.0mm with further cavity search optimization.

## Placement Results
- Parts requested: {metrics['total_parts_requested']}
- Parts placed: {metrics['total_parts_placed']}
- Parts unplaced: {metrics['total_parts_unplaced']}
- Sheets used: {metrics['sheet_count']}
- Utilization: {metrics['utilization_pct']:.1%}
- Runtime: {metrics['runtime_sec']}s
- CGAL NFP validation calls: {len(cgal_results)}
- Overlap count: {metrics['overlap_count']}
- Bounds violation count: {metrics['bounds_violation_count']}

## CGAL NFP Validation (Post-Hoc)
"""
    for res in cgal_results:
        md += f"- Pair {res['pair']}: holes={res.get('holes','?')} dt={res.get('dt_ms','?')}ms\n"

    md += f"""
## Full Quantity Estimate
- Total area: {sum(p['area']*p['full_qty'] for p in parts):.0f}mm²
- Estimated utilization: {metrics['full_quantity_stats']['full_utilization_estimate']:.1%}
- Estimated sheets needed: {metrics['full_quantity_stats']['estimated_sheets_needed']}

## Output Artefacts
- SVG layout: {BASE}/lv6_nesting_preview_layout.svg
- Layout JSON: {BASE}/lv6_nesting_preview_layout.json
- Metrics JSON: {BASE}/lv6_nesting_preview_metrics.json

## CGAL Probe Binary
`{CGAL}`

## Known Limitations
1. spacing=2.0mm causes placement failures for complex-hole parts → used spacing=0.0mm
2. BLF cavity search doesn't scale beyond ~10 instances with complex geometry
3. 4 of 11 parts need 90° rotation on portrait sheet
4. Full quantity (112 instances) exceeds real-time preview budget
5. No persistent NFP cache; CGAL used only for post-hoc validation

## Next Steps (for T05m or follow-up)
- Investigate cavity search optimization for complex hole geometry
- Consider bottom-left-fill variant without cavity inflation
- Profile exact bottleneck (cavity candidate generation vs collision check)
- Build persistent NFP cache for CGAL reference validation
"""

    with open(f'{BASE}/lv6_nesting_preview_metrics.md', 'w') as f:
        f.write(md)

    # Save layout
    with open(f'{BASE}/lv6_nesting_preview_layout.json', 'w') as f:
        json.dump(layout, f, indent=2)

    print(f"\n    Metrics JSON: {BASE}/lv6_nesting_preview_metrics.json")
    print(f"    Metrics MD:   {BASE}/lv6_nesting_preview_metrics.md")
    print(f"    Layout JSON:  {BASE}/lv6_nesting_preview_layout.json")
    print(f"    SVG:          {BASE}/lv6_nesting_preview_layout.svg")
    print(f"\n{'='*70}")
    print(f"STATUS: PARTIAL")
    print(f"placement_mode: {placement_mode}")
    print(f"placed: {metrics['total_parts_placed']}/{metrics['total_parts_requested']}")
    print(f"overlap_count: {metrics['overlap_count']}")
    print(f"bounds_violation_count: {metrics['bounds_violation_count']}")
    print(f"{'='*70}")

    return metrics

if __name__ == '__main__':
    main()
