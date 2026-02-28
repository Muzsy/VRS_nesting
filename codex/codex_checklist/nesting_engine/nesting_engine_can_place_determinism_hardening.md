# Codex Checklist — nesting_engine_can_place_determinism_hardening

**Task slug:** `nesting_engine_can_place_determinism_hardening`  
**Canvas:** `canvases/nesting_engine/nesting_engine_can_place_determinism_hardening.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_can_place_determinism_hardening.yaml`

---

## DoD

- [x] `rust/nesting_engine/src/feasibility/narrow.rs` tobbe nem importal `FloatPredicateOverlay`-t, es nem hasznal f64 alapu overlay predicate-et.
- [x] `can_place` integer-only: containment + overlap predicate determinisztikus (i64/i128).
- [x] A narrow-phase rendezes totalis (AABB + idx tie-break).
- [x] Uj unit tesztek zoldek: `cargo test --manifest-path rust/nesting_engine/Cargo.toml can_place_`.
- [x] `./scripts/check.sh` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_can_place_determinism_hardening.md` PASS.
