# T05m Checklist — LV6 Full Quantity Nesting Preview

## Feladat
LV6 production batch teljes mennyiségű (112 instance) finite-sheet nesting preview.

---

## Előkészítés
- [x] T05l qty=1 baseline reprodukálva vagy validált
  - T05l output: `lv6_nesting_preview_layout.svg` (11/11, 1 sheet, 49.6% util)
  - T05l riport: `engine_v2_nfp_rc_t05l_cgal_reference_nesting_preview.md`
- [x] lv6_production_part_list.json elérhető
  - 11 part type, 112 instance, 18,193,314 mm²
- [x] CGAL probe binary elérhető
  - `/home/muszy/projects/VRS_nesting/tools/nfp_cgal_probe/build/nfp_cgal_probe`

---

## Script implementáció
- [x] full quantity mode implementálva
  - `run_cgal_reference_nesting_full_qty_preview.py`
  - Shelf-packing algoritmus, descending area sort
  - Persistent cursor, per-sheet retry
- [x] Spacing módok támogatva
  - `--spacing-mm 0.0`
  - `--spacing-mm 2.0`
- [x] Collision check módok
  - `aabb_only`, `cgal_if_needed`, `cgal_reduced`

---

## Spacing=0.0mm run
- [x] spacing=0 full quantity run lefutott
- [x] total_instances_requested == 112
- [x] total_instances_placed == 112
- [x] total_instances_unplaced == 0
- [x] overlap_count == 0
- [x] bounds_violation_count == 0
- [x] SVG elkészült (17 sheet)
  - Sheet boundary, grid, part contours, hole contours, part ID
  - Utilization label, prototype felirat
- [x] metrics JSON elkészült
- [x] metrics MD elkészült
- [x] layout JSON elkészült

---

## Spacing=2.0mm run
- [x] spacing=2 run lefutott (PASS — 112/112 placed, 0 overlap, 0 bounds)
- [x] SVG elkészült (17 sheet)
- [x] metrics JSON elkészült
- [x] metrics MD elkészült

---

## Unplaced / Violations
- [x] unplaced lista: nincs (0/112 unplaced spacing=0 és spacing=2)
- [x] overlap: 0 spacing=0 és spacing=2
- [x] bounds violation: 0 spacing=0 és spacing=2
- [x] spacing violation: 0 (spacing=0 és spacing=2)

---

## Utilization riport
- [x] Sheet utilization per sheet: 17 sheet
- [x] Total utilization: 23.8% (spacing=0 és spacing=2)
- [x] Sheet distribution dokumentálva (16,13,3,13,4,6,6,6,6,6,6,6,6,6,5,2,2)

---

## Production tiltások
- [x] Nincs production integráció
- [x] Nincs T08 indítás
- [x] Nincs CGAL production útvonalba integrálva
- [x] Nincs Dockerfile módosítás
- [x] Nincs worker runtime módosítás
- [x] Nincs UI módosítás
- [x] Nincs production nestingnek minősítés
- [x] First-fit preview nem hazudtolja magát optimalizáltként

---

## Riportok és outputok
- [x] T05m riport elkészült
  - `codex/reports/nesting_engine/engine_v2_nfp_rc_t05m_lv6_full_quantity_nesting_preview.md`
- [x] T05m checklist elkészült
  - `codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t05m_lv6_full_quantity_nesting_preview.md`
- [x] Spacing=0 artefaktumok
  - `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_layout.json`
  - `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_sheet*.svg` (17)
  - `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_metrics.json`
  - `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_metrics.md`
- [x] Spacing=2 artefaktumok
  - `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_layout.json`
  - `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_sheet*.svg` (17)
  - `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_metrics.json`
  - `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_metrics.md`

---

## Státusz

| Mód | Requested | Placed | Unplaced | Sheets | Util | Overlap | Bounds | Státusz |
|-----|-----------|--------|----------|--------|------|---------|--------|---------|
| spacing=0.0mm | 112 | 112 | 0 | 17 | 23.8% | 0 | 0 | **PASS** |
| spacing=2.0mm | 112 | 112 | 0 | 17 | 23.8% | 0 | 0 | **PASS** |

**Összesített státusz: PASS**

---

## Futtatott parancsok
```bash
# Spacing=0
python3 scripts/experiments/run_cgal_reference_nesting_full_qty_preview.py \
  --spacing-mm 0.0 --collision-mode cgal_if_needed

# Spacing=2
python3 scripts/experiments/run_cgal_reference_nesting_full_qty_preview.py \
  --spacing-mm 2.0 --collision-mode cgal_if_needed
```

---

## Limitációk dokumentálva
1. Alacsony utilization (23.8%) — shelf-packing row-based
2. Nincs rotation optimalizáció (csak 0°/90°)
3. CGAL nem használva (Shapely exact collision)
4. Rust BLF/NFP timeout komplex LV6 partokkal
5. 17 sheet nem optimális (teoretikus alsó becslés: ~5 sheet)
