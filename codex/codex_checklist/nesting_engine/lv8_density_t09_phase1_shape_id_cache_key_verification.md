# T09 Checklist — lv8_density_t09_phase1_shape_id_cache_key_verification

- [x] Kötelező források beolvasva (`AGENTS.md`, Codex/QA szabályok, T09 canvas/YAML/runner, T07/T08 report).
- [x] T07 előfeltétel ellenőrizve: `PASS_WITH_NOTES`.
- [x] T08 előfeltétel ellenőrizve: `PASS`.
- [x] Új invariáns teszt létrehozva: `rust/nesting_engine/tests/nfp_cache_key_invariants.rs`.
- [x] Lefedett invariánsok: geometry change, equivalent boundary stability, holes inclusion, equivalent hole stability, kernel separation, rotation separation, order sensitivity.
- [x] `cargo check -p nesting_engine` futtatva — PASS.
- [x] `cargo test -p nesting_engine --test nfp_cache_key_invariants -- --nocapture` futtatva — PASS (7/7).
- [x] `cargo test -p nesting_engine nfp::cache -- --nocapture` futtatva — PASS.
- [x] Production cache-key módosítás NEM történt (`cache.rs`/`nfp_placer.rs` változatlan a task scope-ban).
- [x] Report decision matrix kitöltve.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md` futtatása.
