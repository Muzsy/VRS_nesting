# Checklist — SGH-05 `sgh_05_transfer_swap_reinsert_move_operators`

## Dependency gate

- [x] SGH-04 report létezik: `codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md`.
- [x] SGH-04 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] SGH-04 report tartalmazza: `SGH-05_STATUS: READY`.
- [x] Dependency evidence dokumentálva a SGH-05 reportban.

## Repo rules and local code audit

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva (prior sessions).
- [x] `docs/codex/yaml_schema.md` elolvasva (prior sessions).
- [x] `docs/codex/report_standard.md` elolvasva (prior sessions).
- [x] `docs/qa/testing_guidelines.md` elolvasva (prior sessions).
- [x] `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md` elolvasva (prior sessions).
- [x] `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md` elolvasva (prior sessions).
- [x] `docs/egyedi_solver/sgh_01_working_layout_state_contract.md` elolvasva (prior sessions).
- [x] `docs/egyedi_solver/sgh_02_vrs_separator_contract.md` elolvasva (prior sessions).
- [x] `docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md` elolvasva.
- [x] `docs/egyedi_solver/sgh_04_separator_backed_sheet_elimination_contract.md` elolvasva.
- [x] `rust/vrs_solver/src/optimizer/moves.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/working.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/separator.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/sheet_elimination.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/candidates.rs` auditálva (prior sessions).
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` auditálva (prior sessions).
- [x] `rust/vrs_solver/src/optimizer/initializer.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/repair.rs` auditálva (prior sessions).
- [x] `rust/vrs_solver/src/optimizer/multisheet.rs` auditálva (prior sessions).
- [x] `rust/vrs_solver/src/optimizer/stopping.rs` auditálva (prior sessions).
- [x] `rust/vrs_solver/src/optimizer/state.rs` auditálva (prior sessions).
- [x] `rust/vrs_solver/src/io.rs`, `item.rs`, `sheet.rs` auditálva.

## Implementation

- [x] `CandidateMove` skeleton megmaradt, serialization tesztek változatlanok.
- [x] `MoveFailureReason` enum elkészült.
- [x] `MoveDiagnostics` struct elkészült: attempted, committed, rolled_back, separator_attempts, separator_successes, commit_gate_rejections, last_reason.
- [x] `MoveDiagnostics::summary()` elkészült.
- [x] `MoveExecutor<'a>` struct elkészült (parts, sheets referenciákkal).
- [x] `try_reinsert` rollback-safe, commit gate-et használ.
- [x] `try_transfer` rollback-safe: LBF clear → separator fallback prioritással.
- [x] `try_swap` rollback-safe: same-sheet no-op, cross-sheet separator scoped.
- [x] `resolve_by_transfers` budget-aware, determinisztikus sorrend, rollback-safe.
- [x] `commit_gate_ok` helper: count, instance set, sheet bounds, find_violations.
- [x] `run_separator_fix` helper: WorkingLayout → VrsSeparator → validate_for_commit gate.
- [x] `lbf_clear_on_sheet` helper: LBF clear candidate keresés adott sheeten.
- [x] `seed_at_origin` helper: origin seed placement adott sheeten.
- [x] Minden operator: accepted output find_violations szerint valid.
- [x] Placement count invariant minden operatornál megmarad.
- [x] Instance set invariant minden operatornál megmarad.

## Tests

- [x] Meglévő `CandidateMove` serialization tesztek zöldek (3 db).
- [x] `try_reinsert` sikeres commit + find_violations üres.
- [x] `try_reinsert` unknown instance_id → None.
- [x] `try_reinsert` invalid sheet_index → None.
- [x] `try_transfer` success: item másik sheetre kerül, valid layout.
- [x] `try_transfer` invalid destination → None.
- [x] `try_transfer` unsupported rotation → None.
- [x] `try_swap` cross-sheet success + valid layout.
- [x] `try_swap` same-sheet no-op success.
- [x] `try_swap` unknown instance → None.
- [x] `resolve_by_transfers` budget=0 → no changes, no attempts.
- [x] `resolve_by_transfers` all failures → layout violation-free.
- [x] `resolve_by_transfers` valóban átvisz itemet.
- [x] Diagnostics summary tartalmaz minden elvárt mezőt.
- [x] Placement count + instance set invariant tesztelve.
- [x] Determinisztikus smoke: azonos input + move → azonos output.
- [x] Committed output find_violations szerint valid.
- [x] Valós VRS típusokat használnak (Part, Stock, WorkingLayout, VrsSeparator, find_violations).

## Documentation

- [x] Elkészült `docs/egyedi_solver/sgh_05_move_operators_contract.md`.
- [x] Doksi leírja a current moves.rs gapet.
- [x] Doksi leírja a SparrowGH bp_moves.rs mappinget.
- [x] Doksi leírja a move execution API-t.
- [x] Doksi leírja a reinsert operátort.
- [x] Doksi leírja a transfer operátort.
- [x] Doksi leírja a swap operátort (same-sheet no-op dokumentálva).
- [x] Doksi leírja a resolve-by-transfers helpert.
- [x] Doksi leírja a commit/rollback gate-eket.
- [x] Doksi leírja a diagnostics mezőket.
- [x] Doksi leírja a determinism szabályokat.
- [x] Doksi leírja, hogyan készíti elő SGH-06-ot.

## Scope safety

- [x] Nem történt Sparrow/SparrowGH vendorolás.
- [x] Nem készült külső backend adapter.
- [x] Nem lett módosítva `rust/vrs_solver/src/io.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/adapter.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/sheet_elimination.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/initializer.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/multisheet.rs`.
- [x] Nem lett átírva `rust/vrs_solver/src/optimizer/score.rs` objective modellje.
- [x] Nem változott a Python runner / exact validator.
- [x] Nem lett continuous rotation bevezetve.
- [x] Nem lett solution pool / perturbáció bevezetve.
- [x] Nem lett cavity-prepack bevezetve.
- [x] Pipeline-integráció (initializer / sheet_elimination bekötés) nem történt.

## Verification and report

- [x] Focused Rust teszt lefutott: `cargo test -p vrs_solver moves` — 19/19 PASS; full suite 140/140.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md` lefutott.
- [x] Verify log létrejött: `codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.verify.log`.
- [x] Report tartalmaz DoD → Evidence Matrixot.
- [x] Report első sora `PASS`.
- [x] Report végén szerepel: `SGH-06_STATUS: READY`.
