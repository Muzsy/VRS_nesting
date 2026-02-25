# Codex Checklist — nfp_concave_orbit_no_silent_fallback

**Task slug:** `nfp_concave_orbit_no_silent_fallback`  
**Canvas:** `canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_orbit_no_silent_fallback.yaml`

---

## DoD

- [x] ExactOrbit no-fallback módban dead-end/loop/max_steps esetén explicit `Err(NfpError::...)`, nincs `Ok(stable_seed)`.
- [x] Orbit sikertelenség fallback engedélyezve explicit outcome-ként jelölve (`FallbackStable`).
- [x] Belső outcome telemetria (`steps_count`, `events_count`) bevezetve.
- [x] Regressziós teszt prefer_exact esetekre explicit proof policyval fut (`ExactClosed` vagy `expect_exact_error`).
- [x] Legalább 3 prefer_exact fixture explicit mezőkkel frissítve.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md` futtatva.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave::tests::` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md` futtatva.
