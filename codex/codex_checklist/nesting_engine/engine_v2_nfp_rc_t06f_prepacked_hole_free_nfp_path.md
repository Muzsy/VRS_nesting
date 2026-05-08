# T06f Checklist — Prepacked Hole-Free NFP Path + CGAL Kernel Wiring Audit

## Teljesített Feladatok

- [x] T06e report elolvasva
- [x] cavity_prepack útvonal audit: call graph dokumentálva
- [x] worker/main.py cavity_prepack hívás: part_in_part=prepack → build_cavity_prepacked_engine_input_v2() → validate_prepack_solver_input_hole_free()
- [x] quality_cavity_prepack profile: EXISTS at nesting_quality_profiles.py:49-54, nfp_kernel HIÁNYZIK
- [x] quality_profile → runtime_policy → CLI args átadás útvonal dokumentálva
- [x] build_nesting_engine_cli_args_from_runtime_policy(): nfp_kernel NEM része — HIÁNYZÓ
- [x] Rust --nfp-kernel flag: implementálva (main.rs:269-284)
- [x] Rust hybrid gating bypass: implementálva (main.rs:476-484)
- [x] NFP kernel wiring: Python réteg hiányzó, Rust működik
- [x] lv8_pair_01 CGAL benchmark: 189ms SUCCESS
- [x] lv8_pair_02 CGAL benchmark: 112ms SUCCESS (T06e-ből)
- [x] lv8_pair_03 CGAL benchmark: 73ms SUCCESS (T06e-ből)
- [x] 3-rect CGAL regression: 9/9 placed, 1 sheet
- [x] LV8 partial CGAL runtime (60s timeout): nfp_poly_count=33-37, CFR 43-60ms
- [x] cargo check: PASS (39 warnings)
- [x] cargo test: PARTIAL_WITH_KNOWN_PREEXISTING_FAIL (1 pre-existing failing test)
- [x] Pre-existing failing test: blf_part_in_part_hole_collapsed_like_outer_only_source_is_ignored (blf.rs:1316) — T06f NEM módosított fájlt, ami ezt érinthetné
- [x] quality_cavity_prepack + cgal_reference kombináció: nem éles profile-ban, de technikailag lehetséges
- [x] NfpRuntimeDiagV1 emisszió: nem volt scope (T06f = wiring audit)
- [x] NFP provider compute per-pair timing: T06e-ből ismert, most megismételve
- [x] Módosítások a 6. szekcióban: csak javaslat, NEM implementáció (T06f = audit)
- [x] következő task javaslat: T06g — Quality Profile NFP Kernel Wiring

## Nyitott/TODO

- [ ] T06g: quality_cavity_prepack profile-ba nfp_kernel=cgal_reference hozzáadása
- [ ] T06g: Python quality profile réteg nfp_kernel CLI args builder kiegészítése
- [ ] T06g: teljes LV8 benchmark quality_cavity_prepack + cgal_reference kombinációval

## Kritikus Megállapítások

1. **cavity_prepack_v2 wiring: HELYES** — guard aktív, prepack hole-free solver inputot gyárt
2. **NFP kernel wiring: HIÁNYZIK a Python profile rétegből** — nfp_kernel nem része _RUNTIME_POLICY_KEYS
3. **CGAL provider: minden toxic LV8 pair-t megold ~374ms alatt** (3 pair összesen)
4. **Rust --nfp-kernel flag: tökéletesen működik** — csak a Python propagálás hiányzik
5. **Pre-existing failing test: blf_part_in_part_hole_collapsed_like_outer_only_source_is_ignored** — nem T06f által hozzáadott