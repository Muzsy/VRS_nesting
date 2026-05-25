# Checklist — SGH-Q03 `sgh_q03_multi_worker_move_items_multi`

## Dependency

- [x] SGH-Q02 report létezik.
- [x] SGH-Q02 report első sora PASS/PASS_WITH_NOTES.
- [x] SGH-Q02 report tartalmazza: `SGH-Q03_STATUS: READY`.

## Inputs

- [x] AGENTS + Codex workflow és report/yaml szabvány átolvasva.
- [x] SGH-Q00/Q01/Q02 dokumentumok átolvasva.
- [x] Sparrow source evidence auditálva (`.cache/sparrow` separator/worker).
- [x] `separator.rs`, `working.rs`, `repair.rs`, `candidates.rs`, `boundary.rs`, `moves.rs`, `item.rs`, `sheet.rs`, `io.rs` auditálva.

## Outputs

- [x] `rust/vrs_solver/src/optimizer/separator.rs` módosítva.
- [x] `docs/egyedi_solver/sgh_q03_multi_worker_move_items_multi_contract.md` elkészült.
- [x] `codex/codex_checklist/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md` elkészült.
- [x] `codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md` elkészült.

## Implementation

- [x] `VrsSeparatorConfig` bővítve `worker_count` + `seed` mezőkkel.
- [x] `worker_count=0` normalizálás implementálva (`max(1)`).
- [x] `worker_count=1` backward-compatible ág megtartva.
- [x] `SeparatorWorker` és `WorkerCandidate` worker absztrakció bevezetve.
- [x] Determinisztikus worker-seed + shuffle implementálva.
- [x] Multi-worker branch implementálva (`worker_count>1`).
- [x] Best-worker-wins kiválasztás stabil tie-break szabállyal.
- [x] Commit szabály: csak javító candidate.
- [x] Rollback + GLS weight-preserving viselkedés megtartva.

## Scope tiltás

- [x] exploration/compression phase orchestration nem nyílt meg.
- [x] solution pool/disruption/BPP phase loop nem nyílt meg.
- [x] continuous rotation / smooth loss nem nyílt meg.
- [x] collision backend (CDE) nem nyílt meg.
- [x] IO contract / Python runner nem változott.
- [x] Production scope csak `separator.rs` (Cargo.toml nem módosult).

## Tests

- [x] worker_count=1 backward compatibility.
- [x] worker_count=0 normalization.
- [x] worker_count=3 same-seed determinism.
- [x] seed/shuffle helper smoke.
- [x] dense 21-item fixture: 3-worker `best_loss <=` 1-worker.
- [x] dense 21-item fixture: zero-loss esetben no-violation.
- [x] deterministic tie-break.

## Verify

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml separator` zöld.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` zöld.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md` zöld.
- [x] Report első sora PASS/PASS_WITH_NOTES.
- [x] `SGH-Q04_STATUS: READY` marker a report végén.
