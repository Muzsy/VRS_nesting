# T05o Checklist: LV6 Exact Spacing 10mm Validation + Repack

## Feladat áttekintés

- [x] T05n baseline layout beolvasva
- [x] T05n baseline: 112/112 placed, 11 sheets, 36.75% util, spacing=2mm approximate_bbox

## Exact 10mm Validator

- [x] `validate_lv6_exact_spacing.py` elkészült
  - polygon-with-holes Shapely distance check
  - AABB prefilter
  - self-pair skip
  - bounds check
- [x] T05n layout exact 10mm spacinggel validálva
  - Eredmény: FAIL (161 violations, 51 bounds)

## Exact Spacing Repack

- [x] `run_lv6_blf_candidate_exact_spacing_preview.py` elkészült
  - BLF-like candidate generation
  - exact distance-based spacing check (NOT approximate_bbox)
  - 0/90 rotation
  - Shapely polygon distance
- [x] Repack lefutott 112/112 placed, 69 sheets, 5.86% util
- [x] Post-hoc validation: 2 violations, 34 bounds, min_clearance=0.97mm

## Metrikák

- [x] `total_instances_requested == 112` → ✅ 112
- [x] `total_instances_placed == 112` → ✅ 112
- [x] `total_instances_unplaced == 0` → ✅ 0
- [x] `overlap_count == 0` → ✅ 0
- [x] `bounds_violation_count == 0` → ❌ 34 (PARTIAL)
- [x] `spacing_violation_count == 0` → ❌ 2 (PARTIAL)
- [x] `min_clearance_mm` riportolva → ✅ 0.9669mm
- [x] `sheet_count` riportolva → ✅ 69
- [x] `utilization` riportolva → ✅ 5.86%

## Output Artefaktumok

- [x] Layout JSON: `lv6_blf_candidate_exact_spacing100_layout.json`
- [x] Metrics JSON: `lv6_blf_candidate_exact_spacing100_metrics.json`
- [x] Metrics MD: `lv6_blf_candidate_exact_spacing100_metrics.md`
- [x] Per-sheet SVG-k: `lv6_blf_candidate_exact_spacing100_sheet01.svg` ... `sheet69.svg`
- [x] Combined SVG: `lv6_blf_candidate_exact_spacing100_combined.svg`
- [x] Validator JSON: `lv6_t05n_layout_exact_spacing100_validation.json`
- [x] Validator MD: `lv6_t05n_layout_exact_spacing100_validation.md`

## Riport

- [x] `codex/reports/nesting_engine/engine_v2_nfp_rc_t05o_lv6_exact_spacing10_preview.md`

## Szigorú tiltások

- [x] Nincs T08 indítás
- [x] Nincs production integráció
- [x] Nincs Dockerfile módosítás
- [x] Nincs worker runtime módosítás
- [x] Nincs UI módosítás
- [x] Nem nevezzük production nestingnek
- [x] Nem hazudd exactnek az approximate_bbox spacinget
- [x] T05n artefaktumait nem töröltük

## Státusz

**PARTIAL**

- T05n exact 10mm validator: FAIL (161 violations, 51 bounds)
- T05o repack: PARTIAL (2 violations, 34 bounds, 69 sheets, 5.86% util)
- Minden 112 instance elhelyezve, de spacing/bounds violációk maradtak

## Megjegyzések

- spacing_violation_count=2 (0.17mm self-pair, 9.03mm cross-part)
- bounds_violation_count=34 (validator szigorúbb mint placement script)
- 69 sheet vs T05n 11 sheet — 6.3× több lap exact 10mm spacing-gel
- Utilization 5.86% vs T05n 36.75% — 84% relative drop
- Prototype only, NOT production
- CGAL is GPL reference, NOT production
