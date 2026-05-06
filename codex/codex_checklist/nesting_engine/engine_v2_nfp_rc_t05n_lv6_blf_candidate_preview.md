# T05n Checklist: LV6 BLF/Candidate Preview

## T05m Baseline beolvasva
- [x] T05m baseline metrics beolvasva (17 sheets, 23.8% util, 112/112 placed)
- [x] T05m riport: `codex/reports/nesting_engine/engine_v2_nfp_rc_t05m_lv6_full_quantity_nesting_preview.md`
- [x] T05m metrics JSON: `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_metrics.json`

## Instance expansion
- [x] 112 instance full quantity expandálva
- [x] Part list: `tmp/reports/nfp_cgal_probe/lv6_production_part_list.json`
- [x] 11 part type, 112 total instances

## BLF/Candidate placement implementálva
- [x] Prototype script: `scripts/experiments/run_lv6_blf_candidate_preview.py`
- [x] Instance sort: descending area (large parts first)
- [x] Candidate generation: next-to-placed + sheet edges + grid fallback
- [x] Candidate scoring: (sheet_idx, y, x) — classic BLF
- [x] Rotation 0/90 implementálva és működik
- [x] AABB prefilter + Shapely exact collision check
- [x] Spacing check: approximate_bbox policy

## Spacing=2 run
- [x] spacing=2.0 run lefutott
- [x] spacing=0.0 run lefutott (összehasonlításhoz)

## Placement eredmények
- [x] total_instances_placed == 112 (PASS)
- [x] total_instances_unplaced == 0 (PASS)
- [x] overlap_count == 0 (PASS)
- [x] bounds_violation_count == 0 (PASS)
- [x] spacing_violation_count == 0 (by construction)
- [x] sheet_count == 11 < 17 T05m baseline (PASS — 6 sheet reduction)

## SVG output
- [x] 11 per-sheet SVG elkészült (lv6_blf_candidate_preview_spacing2p0_sheet01.svg ... sheet11.svg)
- [x] Combined SVG elkészült (lv6_blf_candidate_preview_spacing2p0_combined.svg)

## Metrics JSON/MD
- [x] Metrics JSON: `lv6_blf_candidate_preview_spacing2p0_metrics.json`
- [x] Metrics MD: `lv6_blf_candidate_preview_spacing2p0_metrics.md`
- [x] Layout JSON: `lv6_blf_candidate_preview_spacing2p0_layout.json`

## Riportok
- [x] Fő riport: `codex/reports/nesting_engine/engine_v2_nfp_rc_t05n_lv6_blf_candidate_preview.md`
- [x] Spacing policy őszintén dokumentálva: approximate_bbox
- [x] Limitációk dokumentálva
- [x] Következő lépések dokumentálva

## Szigorú tiltások ellenőrzése
- [x] Nincs T08 indítás
- [x] Nincs production integráció
- [x] Nincs módosított production Dockerfile
- [x] Nincs módosított worker runtime
- [x] Nincs módosított UI
- [x] Nem nevezzük production nestingnek
- [x] T05m artefaktumai nem törölve

## T05m vs T05n összehasonlítás
- [x] Sheet count: T05m=17 → T05n=11 (delta: -6)
- [x] Utilization: T05m=23.8% → T05n=36.75% (delta: +12.95%)
- [x] Runtime: T05m=0.03s → T05n=41.9s (delta: +41.9s)
- [x] Spacing policy különbség dokumentálva
- [x] Placement mode különbség dokumentálva

## Spacing policy őszinteség
- [x] spacing_policy = approximate_bbox dokumentálva
- [x] spacing=0 és spacing=2 azonos eredményt ad — dokumentálva
- [x] Ez nem production spacing — explicit dokumentálva

## Státusz
**PASS** — Minden elfogadási feltétel teljesül (112/112 placed, 0 overlap, 0 bounds, 11 sheets < 17 baseline)

---

## Summary

| Feltétel | Eredmény |
|----------|----------|
| Requested | 112 |
| Placed | 112 |
| Unplaced | 0 |
| Sheet count | 11 (vs T05m baseline 17) |
| Improvement | -6 sheets (35% reduction) |
| Utilization | 36.75% (vs T05m baseline 23.8%) |
| Overlap | 0 |
| Bounds violation | 0 |
| Spacing violation | 0 (approximate_bbox policy) |
| Placement mode | blf_candidate_preview |
| Spacing policy | approximate_bbox |
| Runtime | ~42s |
| Status | **PASS** |
