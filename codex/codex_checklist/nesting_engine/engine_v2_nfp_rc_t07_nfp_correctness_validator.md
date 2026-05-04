# Codex checklist - engine_v2_nfp_rc_t07_nfp_correctness_validator

- [x] AGENTS.md + T07 master runner/canvas/YAML/runner prompt beolvasva
- [x] T07 eloirt valos fajlok beolvasva (`nfp_validation.rs`, `reduced_convolution.rs`, `minkowski_cleanup.rs`, `geometry/types.rs`, `feasibility/aabb.rs`, `feasibility/narrow.rs`, `lv8_pair_01.json`)
- [x] `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` letrehozva
- [x] CLI flag-ek implementalva (`--fixture`, `--nfp-source`, `--sample-*`, `--boundary-perturbation`, `--output-json`)
- [x] `exact_collision_check` implementalva (AABB prefilter + polygon intersection/touch)
- [x] `sample_points_inside` / `sample_points_outside` / `sample_points_on_boundary` implementalva
- [x] `--nfp-source mock_exact` mod implementalva, `false_positive_rate=0.0` teljesul
- [x] JSON output tartalmazza: `false_positive_rate`, `false_negative_rate`, `correctness_verdict`, `nfp_was_available`
- [x] `cargo run --bin nfp_correctness_benchmark -- --help` PASS
- [x] `cargo run --bin nfp_correctness_benchmark -- --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json --nfp-source reduced_convolution_v1 --output-json` PASS
- [x] `cargo run --bin nfp_correctness_benchmark -- --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json --nfp-source mock_exact --output-json` PASS
- [x] `ls rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` PASS
- [x] `cargo check -p nesting_engine` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.md` PASS
- [x] Reportben explicit: `validator_infra_pass`, `rc_correctness_pass`, `t08_unblocked`
- [x] `validator_infra_pass=true`
- [ ] `rc_correctness_pass=true`
- [ ] `t08_unblocked=true`
