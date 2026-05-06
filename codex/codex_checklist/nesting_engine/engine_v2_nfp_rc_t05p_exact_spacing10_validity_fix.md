# T05p Checklist: LV6 Exact 10mm Spacing Validity Fix

## Root Cause Fixes

- [x] T05o violation reprodukálva (2 spacing, 34 bounds)
- [x] spacing violation debug dump elkészült
- [x] bounds violation debug dump elkészült
- [x] bounds root cause dokumentálva (transform inconsistency + rough bounds check)
- [x] spacing root cause dokumentálva (transform inconsistency)
- [x] transform_polygon javítva (normalize + true centroid)
- [x] place_on_sheet bounds check javítva (actual polygon bounds)
- [x] placed_count return value javítva
- [x] parts_lookup debug hozzáadva

## Final Validation

- [x] final layout generálva
- [x] overlap_count == 0
- [x] bounds_violation_count == 0
- [x] spacing_violation_count == 0 (a 78 placed part-ra)
- [x] 78/112 placed — unplaced explicit dokumentálva

## SVG + Metrics

- [x] SVG layout elkészült (combined + per-sheet)
- [x] metrics JSON/MD elkészült
- [x] validation JSON/MD elkészült

## Constraints

- [x] nincs production integráció
- [x] nincs T08 indítás
- [x] CGAL nem használva spacing check-hez (Shapely)

## Jelentés

- [x] codex report elkészült
- [x] debug JSON/MD elkészült

## Status: PARTIAL

A 78 placed part teljesen valid (0 violations).
34 unplaced instance explicit listázva.
