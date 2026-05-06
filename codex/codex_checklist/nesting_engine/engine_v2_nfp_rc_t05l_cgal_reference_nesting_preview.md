# T05l Checklist: CGAL Reference Nesting Preview

## Előkészület

- [x] T05g/T05f CGAL/T07 regresszió PASS (dokumentálva T05g riportban)
- [x] LV6 part list darabszámokkal elkészült
- [x] Part list JSON mentve: `tmp/reports/nfp_cgal_probe/lv6_production_part_list.json`

## Sheet és Konfiguráció

- [x] Sheet config dokumentált: 1500×3000mm, spacing=0mm
- [x] Spacing=2.0mm limitáció dokumentálva (komplex multi-hole partoknál PART_NEVER_FITS_SHEET)
- [x] Rotation constraints dokumentálva (4 part >1500mm széles → rot90)

## CGAL NFP Cache / Reference

- [x] CGAL NFP használat módja dokumentálva (exact collision validation, nem placement decision)
- [x] CGAL hívások száma: 11
- [x] CGAL összes idő: 462ms
- [x] NFP cache: nincs perzisztens cache, online computation

## Placement Preview

- [x] Python first-fit + CGAL NFP exact validation script kész
- [x] 11/11 part elhelyezve
- [x] 0 overlap
- [x] 0 bounds violation
- [x] 0 unplaced (qty=1 preview)

## Output Artefaktumok

- [x] SVG layout: `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_layout.svg`
- [x] Layout JSON: `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_layout.json`
- [x] Metrics JSON: `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_metrics.json`
- [x] Metrics MD: `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_metrics.md`
- [x] Riport: `codex/reports/nesting_engine/engine_v2_nfp_rc_t05l_cgal_reference_nesting_preview.md`

## Placement Mode Dokumentáció

- [x] Őszintén dokumentálva: `blf_exact_preview`, NEM `cgal_nfp_reference`
- [x] CGAL szerepe: exact collision validation only
- [x] CGAL GPL figyelmeztetés minden outputban

## Integritási Védelem

- [x] Nincs production integráció
- [x] Nincs T08 indítás
- [x] Nincs Dockerfile módosítás
- [x] Nincs worker runtime módosítás
- [x] Nincs UI módosítás
- [x] CGAL nem kötelező dependency
- [x] Eredeti DXF fájlok változatlanok

## Limitációk Dokumentálva

- [x] Spacing=2.0mm nem működik komplex partokkal (cavity inflation)
- [x] Rust BLF/NFP engine timeout komplex LV6 partokkal
- [x] Reduced quantity preview (qty=1 per típus)
- [x] First-fit, nem optimalizált layout
- [x] Nincs perzisztens NFP cache
- [x] Teljes mennyiség becslés: ~5 lap (404% utilization)

## Összefoglaló Metrikák

```
placement_mode: blf_exact_preview
total_parts_requested: 11
total_parts_placed: 11
total_parts_unplaced: 0
sheet_count: 1
utilization_pct: 49.6%
overlap_count: 0
bounds_violation_count: 0
runtime_sec: 0.46
cgal_nfp_calls: 11
cgal_time_ms: 462
full_quantity_estimate: 5 sheets (404% util)
```

## Státusz: ✅ PASS

Minden checklist item teljesítve.
