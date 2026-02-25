# Codex Checklist — nfp_concave_orbit_next_event

**Task slug:** `nfp_concave_orbit_next_event`  
**Canvas:** `canvases/nesting_engine/nfp_concave_orbit_next_event.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_orbit_next_event.yaml`

---

## DoD

- [x] ExactOrbit next-event léptetés racionális `t`-vel implementálva (`Fraction` + eseményjelöltek + tie-break).
- [x] Touching group többkontaktos komponens-képzéssel és determinisztikus candidate rendezéssel működik.
- [x] Exact ciklus visited-signature loop guarddal és boundary-clean kimenettel fut.
- [x] Legalább 3 concave fixture exact no-fallback futásra van jelölve és regresszióban ellenőrizve.
- [x] Determinisztika: exact no-fallback kétszeri futtatás canonical ring egyezést ad.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_next_event.md` futtatva.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave::tests::` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_next_event.md` futtatva.
