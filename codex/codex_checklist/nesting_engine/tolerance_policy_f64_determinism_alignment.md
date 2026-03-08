# Codex Checklist — tolerance_policy_f64_determinism_alignment

**Task slug:** `tolerance_policy_f64_determinism_alignment`  
**Canvas:** `canvases/nesting_engine/tolerance_policy_f64_determinism_alignment.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_tolerance_policy_f64_determinism_alignment.yaml`

---

## DoD

- [x] A/B/C determinism boundary modell dokumentálva van, doc-code drift nélkül.
- [x] Van központosított float-policy helper, és az érintett geometry modulok ezt használják.
- [x] Nincs ad hoc epsilon szétszórva az érintett döntési pontokon.
- [x] Van dedikált `offset_determinism_` regressziós evidence.
- [x] Van dedikált `pipeline_float_policy_` regressziós evidence.
- [x] Van dedikált `narrow_float_policy_` regressziós evidence.
- [x] Van célzott float-boundary repeated-run determinism smoke.
- [x] A smoke a `scripts/check.sh` része (PR gate útvonalon fut).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.md` PASS.
- [x] KI-007 lezárása explicit és követhető.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml offset_determinism_` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml pipeline_float_policy_` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml narrow_float_policy_` PASS.
- [x] `RUNS=10 ./scripts/smoke_nesting_engine_float_policy_determinism.sh` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.md` futtatva.
