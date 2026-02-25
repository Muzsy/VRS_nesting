# Codex Checklist — nfp_orbit_exact_closed_p0

**Task slug:** `nfp_orbit_exact_closed_p0`  
**Canvas:** `canvases/nesting_engine/nfp_orbit_exact_closed_p0.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_orbit_exact_closed_p0.yaml`

---

## DoD

- [x] `cd rust/nesting_engine && cargo test -q nfp_regression` PASS.
- [x] Legalább 3 `prefer_exact: true` concave fixture no-fallback módban `ExactClosed` outcome-ot ad.
- [x] A prefer_exact proof továbbra is ellenőrzi: exact canonical ring != stable canonical ring (ha `allow_exact_equals_stable != true`).
- [x] A no-silent-fallback policy marad: no-fallback orbit fail továbbra is explicit hiba (nem stable seed).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md` futtatva.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test orbit_next_event_trace_smoke` PASS.
- [x] `cd rust/nesting_engine && cargo test -q nfp_regression` PASS.
