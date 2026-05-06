# T05g Checklist — LV6 Production DXF Sweep / CGAL Geometry Robustness Audit

## Feladat státusz

- [x] T05f regression PASS
- [x] LV6 production DXF inventory elkészült
- [x] Mind a 11 DXF vizsgálva vagy hiány dokumentálva
- [x] Layer/color/entity/text összesítő elkészült
- [x] Darabszám parsing elkészült
- [x] Legalább 5 NFP pair fixture létrejött (7 készült)
- [x] Minden fixture real DXF-ből származik
- [x] CGAL probe lefutott minden fixture-re (7/7 success)
- [x] T07 correctness lefutott minden success CGAL outputra (7/7 PASS)
- [x] FP/FN riport készült (0 FP, 0 FN minden párnál)
- [x] Hole boundary sampling mezők riportolva (pair_06: hole_samples=10, HOLES_AWARE active)
- [x] output_holes állapot dokumentált (pair_06: 2 output holes)
- [x] Nincs production integráció
- [x] Nincs T08 indítás

## Részletek

### T05f regression
- [x] CGAL build: SUCCESS (v0.2.0)
- [x] real_work_dxf_holes_pair_02: CGAL success, T07 PASS
- [x] HOLES_AWARE active, hole_boundary_samples=2

### LV6 DXF inventory
- [x] Script: `scripts/experiments/audit_production_dxf_holes.py`
- [x] 11 DXF vizsgálva
- [x] Mind 11: `IMPORT_OK_WITH_HOLES`
- [x] Mind 11: `PREFLIGHT_FAILED` (TypeError — non-standard layer nevek)
- [x] Mind 11: tartalmaz TEXT/MTEXT entity-t
- [x] Darabszám: 11/11 parsed
- [x] Layers: `['0', 'Gravir', 'Gravír', 'jel']`
- [x] Output: `tmp/reports/nfp_cgal_probe/lv6_production_dxf_inventory.json`
- [x] Output: `tmp/reports/nfp_cgal_probe/lv6_production_dxf_inventory.md`

### NFP pair fixture-ök
- [x] Script: `scripts/experiments/extract_lv6_production_dxf_nfp_pairs.py`
- [x] 7 fixture készült
- [x] Mind valódi LV6 DXF-ből
- [x] Fixture-ök: lv6_production_dxf_pair_01..07.json

### CGAL sidecar
- [x] 7/7: CGAL success
- [x] pair_06: output_holes=2 (egyetlen output-hole-os eset)
- [x] Leglassabb: pair_04 — 58.16ms
- [x] Legnagyobb output: pair_05 — 374 outer vertices

### T07 correctness
- [x] 7/7: T07 PASS
- [x] 0 FP, 0 FN minden párnál
- [x] pair_06: HOLES_AWARE active, hole_boundary_samples=10, hole_boundary_collision_count=10
- [x] boundary_holes_supported: true (pair_06 only)
- [x] hole_boundary_penetration_max_mm: 0.01 (pair_06 only)

### Kötöttségek betartása
- [x] Nincs T08 indítás
- [x] Nincs production CGAL integráció
- [x] Nincs worker runtime módosítás
- [x] Nincs Dockerfile módosítás
- [x] Nincs synthetic adatnak való DXF státusz hazugság
- [x] Hole/inner contour/TEXT adatok nincsenek csendben ignorálva
- [x] Nincs silent fallback
