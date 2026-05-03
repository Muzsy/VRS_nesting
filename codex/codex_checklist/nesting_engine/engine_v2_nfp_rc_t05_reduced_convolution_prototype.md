# Codex checklist - engine_v2_nfp_rc_t05_reduced_convolution_prototype

- [x] AGENTS.md + T05 master runner/canvas/YAML/runner prompt beolvasva
- [x] T05 altal eloirt valos fajlok beolvasva (`nfp/mod.rs`, `nfp/concave.rs`, `geometry/types.rs`, `geometry/cleanup.rs`, `geometry/simplify.rs`, `lv8_pair_01.json`, `geometry_preparation_contract_v1.md`)
- [x] Architektura dontesi check lefutott (`tools/nfp_cgal_probe`, `cmake`, `pkg-config cgal`)
- [x] `rust/nesting_engine/src/nfp/reduced_convolution.rs` letrehozva
- [x] `rust/nesting_engine/src/bin/nfp_rc_prototype_benchmark.rs` letrehozva
- [x] `rust/nesting_engine/src/nfp/mod.rs` frissitve (`pub mod reduced_convolution;`)
- [x] `cargo check -p nesting_engine` PASS
- [x] `cargo run --bin nfp_rc_prototype_benchmark -- --help` PASS
- [x] `lv8_pair_01` benchmark fut (`verdict=SUCCESS`, `raw_vertex_count>0`)
- [x] `lv8_pair_02` benchmark fut (`verdict=SUCCESS`, `raw_vertex_count>0`)
- [x] `lv8_pair_03` benchmark fut (`verdict=SUCCESS`, `raw_vertex_count>0`)
- [x] Kritikus kapu teljesult: legalabb 1 (tenylegesen 3/3) fixture `SUCCESS` es `raw_vertex_count>0` (prototype envelope polygon)
- [x] `RcNfpError::NotImplemented` explicit jelen van (nem panic/silent fallback)
- [x] `git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs` ures (erintetlen)
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/engine_v2_nfp_rc_t05_reduced_convolution_prototype.md` PASS
