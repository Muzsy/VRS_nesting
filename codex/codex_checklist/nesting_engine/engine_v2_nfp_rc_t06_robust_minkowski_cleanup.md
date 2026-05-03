# Codex checklist - engine_v2_nfp_rc_t06_robust_minkowski_cleanup

- [x] AGENTS.md + T06 master runner/canvas/YAML/runner prompt beolvasva
- [x] T06 altal eloirt valos fajlok beolvasva (`boundary_clean.rs`, `reduced_convolution.rs`, `geometry/cleanup.rs`, `geometry/types.rs`, T02 contract)
- [x] `rust/nesting_engine/src/nfp/nfp_validation.rs` letrehozva
- [x] `rust/nesting_engine/src/nfp/minkowski_cleanup.rs` letrehozva
- [x] `rust/nesting_engine/src/nfp/mod.rs` frissitve (`pub mod minkowski_cleanup;` + `pub mod nfp_validation;`)
- [x] `run_minkowski_cleanup` 9 lepeses pipeline implementalva
- [x] `polygon_is_valid` es `polygon_validation_report` implementalva
- [x] Invarians teljesul: `is_valid=false` eseten `polygon=None`
- [x] `CleanupError::InvalidAfterCleanup` explicit hibaag implementalva
- [x] `cargo check -p nesting_engine` PASS
- [x] `cargo test -p nesting_engine -- minkowski_cleanup` PASS
- [x] `cargo test -p nesting_engine -- nfp_validation` PASS
- [x] `git diff HEAD -- rust/nesting_engine/src/nfp/boundary_clean.rs` ures (erintetlen)
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/engine_v2_nfp_rc_t06_robust_minkowski_cleanup.md` PASS
