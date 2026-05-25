# Checklist — SGH-Q03R `sgh_q03r_gls_pair_weight_double_update_fix`

## Dependency

- [x] SGH-Q03 report létezik.
- [x] SGH-Q03 report első sora PASS/PASS_WITH_NOTES.
- [x] SGH-Q03 report tartalmazza: `SGH-Q04_STATUS: READY`.

## Inputs

- [x] AGENTS + Codex workflow és report/yaml szabvány átolvasva.
- [x] SGH-Q01/Q02/Q03 dokumentumok átolvasva.
- [x] `rust/vrs_solver/src/optimizer/separator.rs` auditálva.
- [x] Dependency preflight: SGH-Q03 report ellenőrizve.

## Outputs

- [x] Ellenőrző script: duplicate pair update kizárása.
- [x] `rust/vrs_solver/src/optimizer/separator.rs` nem módosult (nincs dupla update).
- [x] `codex/codex_checklist/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md` elkészült.
- [x] `codex/reports/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md` elkészült.

## Scope tiltás

- [x] exploration/compression phase orchestration nem nyílt meg.
- [x] solution pool/disruption/BPP phase loop nem nyílt meg.
- [x] continuous rotation / smooth loss nem nyílt meg.
- [x] collision backend (CDE) nem nyílt meg.
- [x] IO contract / Python runner nem változott.
- [x] Production fájl nem módosult (nincs mit javítani).
- [x] SGH-Q04 nem lett implementálva.

## Tests

- [x] `multiplicative_gls_max_loss_pair_gets_max_ratio` PASS.
- [x] `cargo test ... separator --lib` PASS (27/27).
- [x] `cargo test ... --lib` PASS (153/153).

## Verify

- [x] Ellenőrző script: no duplicate consecutive pair GLS multiplier update PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q03r_gls_pair_weight_double_update_fix.md` zöld.
- [x] Report első sora PASS.
- [x] `SGH-Q04_STATUS: READY` marker a report végén.