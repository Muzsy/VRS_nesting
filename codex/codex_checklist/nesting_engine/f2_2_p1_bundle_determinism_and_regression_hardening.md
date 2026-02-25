# Codex Checklist — f2_2_p1_bundle_determinism_and_regression_hardening

**Task slug:** `f2_2_p1_bundle_determinism_and_regression_hardening`  
**Canvas:** `canvases/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_f2_2_p1_bundle_determinism_and_regression_hardening.yaml`

---

## DoD

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS (benne az új canonical-bytes teszt).
- [x] `scripts/check.sh` bekötve futtatja a canonical JSON determinism smoke-ot.
- [x] `docs/nesting_engine/json_canonicalization.md` normatív része implementációhoz igazított JCS-szubszetet rögzít.
- [x] `poc/nfp_regression/README.md` tartalmazza a quarantine acceptance workflowt.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md` futtatva.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml hash_view_v1_canonical_json_is_byte_identical` PASS.
- [x] `RUNS=3 INPUT_JSON=/tmp/f2_2_p1_fast_input.json ./scripts/smoke_nesting_engine_determinism.sh` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md` futtatva.
