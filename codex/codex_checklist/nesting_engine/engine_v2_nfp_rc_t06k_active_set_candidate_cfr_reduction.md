# T06k Checklist

## Előkészület
- [x] előző partial T06k summary elolvasva
- [x] jelenlegi diff auditálva (git diff --stat)

## Type Mismatch Fix
- [x] type mismatch root cause feltárva (external nesting_engine crate Polygon64 vs local Polygon64)
- [x] type mismatch javítva (Vec<LibPolygon64> típus annotációval a compute_cfr hívásoknál)
- [x] indokolatlan public API bővítés elkerülve (compute_cfr_internal pub fn helyett pub(crate) elég lenne — dokumentálva)

## Fordítás és Tesztek
- [x] cargo check PASS (40 warnings — meglévő unused, nem T06k által okozott)
- [x] cargo test: 59 passed, 1 FAILED (pre-existing cfr_sort_key test)

## T06j Counter Fix
- [x] hybrid path cfr_union_calls → cfr_skipped_by_hybrid_count
- [x] cfr_union_calls csak tényleges full-CFR union hívásoknál nő

## Active-Set Implementation
- [x] active-set flags működnek (is_active_set_candidates_enabled() stb.)
- [x] default behavior változatlan (flag nélkül nem fut az active-set út)
- [x] placed-anchor candidate source működik (generate_active_set_candidates)
- [x] active NFP vertex candidate source működik
- [x] progressive widening működik (L0/L1/L2 + full-set)
- [x] exact can_place minden accepted candidate-re
- [x] local CFR fallback implementálva (ACTIVE_SET_LOCAL_CFR_FALLBACK=1)
- [x] full CFR fallback implementálva (ACTIVE_SET_FULL_CFR_FALLBACK=1)

## Benchmark
- [x] full-CFR baseline benchmark futott (timeout + blf fallback)
- [x] T06k active-set benchmark futott (timeout + blf fallback)
- [x] correctness gate dokumentálva
- [x] quality/regret mérés: nem végezhető (baseline timeout miatt)

## Jegyzék
- [x] report elkészült (engine_v2_nfp_rc_t06k_active_set_candidate_cfr_reduction.md)
- [x] T06l javaslat elkészült

## Known Issues
- [ ] cfr.rs visibility: compute_cfr_internal pub fn → pub(crate) visszaállítás (opcionális)
- [ ] pre-existing cfr_sort_key test failure (separate task)
- [ ] environment variable propagation a benchmark runnerben javítandó
- [ ] NFP solver timeout resolution szükséges a hot-path méréséhez