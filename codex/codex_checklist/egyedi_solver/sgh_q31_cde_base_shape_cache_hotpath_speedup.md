# Codex checklist — sgh_q31_cde_base_shape_cache_hotpath_speedup

## Kötelező workflow

- [ ] Elolvastam: `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`.
- [ ] Elolvastam a Q31 canvas-t.
- [ ] Elolvastam a Q30-R1 summary/report artefaktumokat.
- [ ] Rögzítettem a Q30-R1 dense191 baseline számokat a reportban.
- [ ] Git status / dirty state rögzítve a reportban.

## Implementáció

- [ ] `SPInstance` tárol cache-elt `Rc<CdeBaseShape>` mezőt.
- [ ] `SparrowProblem::from_solver_input` unique part id / geometry szerint base-shape cache-t épít.
- [ ] `sample/search.rs` production hot path nem hív `prepare_base_shape_native(&inst.part)`-ot.
- [ ] `lbf.rs` production hot path nem hív `prepare_base_shape_native(&inst.part)`-ot.
- [ ] `quantify/tracker.rs` routine Sparrow item shape rebuild nem hív `prepare_shape_native(&inst.part, ...)`-ot.
- [ ] Tracker cache-elt base shape + `transform_base_to_candidate` útvonalat használ.
- [ ] Nincs sample budget / worker ordering / GLS / acceptance / touching / compression módosítás.

## Profiler / output

- [ ] Valós Rust oldali `base_shape_cache_build_ms` mérés van.
- [ ] Valós Rust oldali `base_shape_cache_hits` / `base_shape_cache_misses` van.
- [ ] Valós Rust oldali `prepare_base_shape_native_hotpath_calls` van.
- [ ] Valós Rust oldali `prepare_base_shape_native_hotpath_ms` van.
- [ ] A cache-build idő nincs hot-path prepare időnek elkönyvelve.
- [ ] Q31 artefaktum summary/report létrejött.

## Dense191 acceptance

- [ ] dense191 `placed_count == 191`.
- [ ] dense191 `status` nem rosszabb, mint Q30-R1 baseline (`partial` vagy `ok`).
- [ ] dense191 `final_pairs <= 88`.
- [ ] dense191 `prepare_base_shape_native_hotpath_calls == 0`.
- [ ] dense191 `prepare_base_shape_native_hotpath_ms <= 2143.31`.
- [ ] dense191 `base_shape_cache_misses <= unique_part_count + 2`.
- [ ] dense191 `base_shape_cache_hits >= instance_count - unique_part_count`.

## Verifikáció

- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [ ] `python3 scripts/profile_sgh_q31_base_shape_cache_speedup.py` PASS.
- [ ] `python3 scripts/smoke_sgh_q31_cde_base_shape_cache_hotpath_speedup.py` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.md` PASS.

## Report

- [ ] Report Standard v2 szerinti report elkészült.
- [ ] DoD → Evidence Matrix soronként kitöltve path+sor bizonyítékokkal.
- [ ] Marker sorok megvannak:
  - [ ] `Q31_STATUS: PASS|PARTIAL|FAIL`
  - [ ] `DENSE191_BASE_SHAPE_HOTPATH_CALLS: <integer>`
  - [ ] `DENSE191_BASE_SHAPE_HOTPATH_MS: <number>`
  - [ ] `DENSE191_BASE_SHAPE_CACHE_MISSES: <integer>`
  - [ ] `DENSE191_BASE_SHAPE_CACHE_HITS: <integer>`
  - [ ] `DENSE191_PREPARE_BASE_REDUCTION_PCT: <number>%`
  - [ ] `DENSE191_FINAL_PAIRS: <integer>`
  - [ ] `NEXT_HOTSPOT: <path::function or NONE>`
