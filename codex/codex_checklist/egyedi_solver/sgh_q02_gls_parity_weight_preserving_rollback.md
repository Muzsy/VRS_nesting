# Checklist — SGH-Q02 `sgh_q02_gls_parity_weight_preserving_rollback`

## Dependency

- [x] SGH-Q01 report létezik.
- [x] SGH-Q01 report első sora PASS.
- [x] SGH-Q01 report tartalmazza: SGH-Q02_STATUS: READY.

## Inputs

- [x] SGH-Q01 correction plan elolvasva.
- [x] SGH-Q01 corrected roadmap elolvasva.
- [x] SGH-Q01 no-downgrade gates elolvasva.
- [x] separator.rs auditálva (additive GLS azonosítva).
- [x] working.rs, repair.rs auditálva.

## Outputs

- [x] `rust/vrs_solver/src/optimizer/separator.rs` módosítva (GLS + snapshot).
- [x] `docs/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback_contract.md` elkészült.
- [x] `codex/codex_checklist/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md` elkészült.
- [x] `codex/reports/egyedi_solver/sgh_q02_gls_parity_weight_preserving_rollback.md` elkészült.

## Implementation

- [x] Multiplicative GLS formula implementálva (Sparrow Algorithm 8).
- [x] max_loss normalizáció implementálva.
- [x] No-collision decay implementálva (weight → 1.0, nem alá).
- [x] Boundary collision ugyanolyan elvvel frissül mint pair.
- [x] Nulla-loss pairekhez nem jön létre weight entry.
- [x] `LossSnapshot` struct hozzáadva.
- [x] `snapshot_loss()` metódus hozzáadva.
- [x] `restore_but_keep_weights(LossSnapshot)` metódus hozzáadva.
- [x] Rollback pontok `restore_but_keep_weights`-et használnak.
- [x] `VrsSeparatorConfig` két új mezővel bővítve (min_inc_ratio, max_inc_ratio).
- [x] Minden új config mező defaultot kapott.
- [x] Meglévő publikus config mezők nem törtek el.
- [x] AdditiveGlsProxy QUALITY_RISK annotáció eltávolítva (már nem proxy).
- [x] `pair_weight` pub; `boundary_weight` pub accessor hozzáadva.

## Scope tiltás

- [x] multi-worker / rayon nem nyílt meg.
- [x] stochastic ordering nem nyílt meg.
- [x] phase orchestration nem nyílt meg.
- [x] IO contract nem változott.
- [x] Python runner nem változott.
- [x] Külső backend/vendor nem adódott hozzá.

## Tesztek

- [x] Test 11: larger loss → larger weight (req #1).
- [x] Test 12: max-loss pair → max_inc_ratio (req #2).
- [x] Test 13: no-collision decay, floor 1.0 (req #3).
- [x] Test 14: boundary weight same principle (req #4).
- [x] Test 15: restore_but_keep_weights (req #5).
- [x] Test 16: no spurious weight entries.
- [x] separator_fixes_simple_overlap: best_loss == 0.0 (req #6).
- [x] separator_is_deterministic (req #7).

## Verify

- [x] `cargo test separator` 20/20 pass.
- [x] `cargo test --lib` 146/146 pass.
- [x] `verify.sh` exit 0.
- [x] Report első sora PASS.
- [x] SGH-Q03_STATUS: READY.
