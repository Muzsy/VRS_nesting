# Codex checklist - engine_v2_nfp_rc_t03_geometry_cleanup_pipeline

- [x] AGENTS.md + T03 master runner/canvas/YAML/runner prompt beolvasva
- [x] T03 altal eloirt valos fajlok beolvasva (`types.rs`, `pipeline.rs`, `boundary_clean.rs`, `geometry/mod.rs`, T01/T02 outputok)
- [x] `rust/nesting_engine/src/geometry/cleanup.rs` letrehozva
- [x] `rust/nesting_engine/src/geometry/simplify.rs` letrehozva
- [x] `rust/nesting_engine/src/bin/geometry_prepare_benchmark.rs` letrehozva
- [x] `rust/nesting_engine/src/geometry/mod.rs` frissitve (`pub mod cleanup; pub mod simplify;`)
- [x] `cargo check -p nesting_engine` PASS (crate szinten fordul)
- [x] `cargo run --bin geometry_prepare_benchmark -- --help` PASS
- [x] `geometry_prepare_benchmark` lefut `lv8_pair_01` fixture-en, topology_changed=false, area_delta<0.5
- [x] `geometry_prepare_benchmark` lefut `lv8_pair_01..03` fixture-okon panic nelkul
- [x] `SimplifyResult` tartalmazza az osszes kotelezo mezot
- [x] `git diff HEAD -- rust/nesting_engine/src/nfp/boundary_clean.rs` ures (erintetlen)
- [x] Nincs `#[allow(dead_code)]` a publikus API-kon
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/engine_v2_nfp_rc_t03_geometry_cleanup_pipeline.md` PASS
