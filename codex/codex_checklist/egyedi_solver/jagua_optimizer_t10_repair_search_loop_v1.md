# Checklist — JG-10 jagua_optimizer_t10_repair_search_loop_v1

## Feladat

Sparrow-elvű Repair Search V1 a Phase 1 rectangular / outer-only solverhez. Cél: overlap/boundary hibák javítása move/reinsert/rotate próbákkal, determinisztikusan, időlimit mellett, exact validatorral zárva.

## Dependency

- [x] JG-09 report létezik.
- [x] JG-09 report első sora `PASS`.
- [x] JG-09 report tartalmazza: `JG-10_STATUS: READY`.
- [x] JG-09 exact validation bridge artifactok léteznek: `vrs_nesting/runner/vrs_solver_runner.py`, `scripts/smoke_jagua_exact_validation_bridge.py`.
- [x] Repo szabályfájlok elolvasva: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`.
- [x] Projektterv dokumentumok elolvasva.

## Valós kód audit

- [x] `optimizer/moves.rs` jelenlegi `CandidateMove` skeletonja auditálva.
- [x] `optimizer/state.rs` `LayoutState` / `PlacementTransform` modellje auditálva.
- [x] `optimizer/initializer.rs` `build_initial_layout()` és `bbox_from_placement()` auditálva.
- [x] `optimizer/candidates.rs` `generate_candidates()` és `PlacedBbox::overlaps()` auditálva.
- [x] `adapter.rs` Phase 1 branch auditálva.
- [x] JG-09 runner exact validation útvonal auditálva.

## StoppingPolicy

- [x] `rust/vrs_solver/src/optimizer/stopping.rs` létrejött vagy repo-konform alternatíva dokumentálva.
- [x] StoppingPolicy tartalmaz time limitet.
- [x] StoppingPolicy tartalmaz iterációs vagy stagnálási limitet.
- [x] Stop reason determinisztikus és reportolható.
- [x] StoppingPolicy unit tesztek PASS.

## MoveGenerator / CandidateMove

- [x] MoveGenerator V1 elkészült vagy világosan behatárolt.
- [x] Translate/move candidate támogatott.
- [x] Reinsert candidate támogatott.
- [x] Rotate candidate támogatott allowed rotations alapján.
- [x] Candidate sorrend determinisztikus.
- [x] Azonos seed azonos move sorrendet vagy eredményt ad.

## RepairEngine

- [x] `rust/vrs_solver/src/optimizer/repair.rs` létrejött vagy repo-konform alternatíva dokumentálva.
- [x] RepairEngine V1 Phase 1 rectangular / outer-only scope-ban működik.
- [x] Boundary hibák külön diagnosztikában látszanak.
- [x] Overlap hibák külön diagnosztikában látszanak.
- [x] Mesterségesen hibás kezdőállapotból legalább egy repair scenario valid állapotot ad.
- [x] Ha repair sikertelen, rollback vagy explicit fail/unplaced reason történik.
- [x] Silent geometry loss nincs: minden instance placed vagy unplaced indokkal.
- [x] Repair attempt/success/fail metrika reportolva.

## Integráció / contract

- [x] `optimizer/mod.rs` exportok frissítve.
- [x] Phase 1 adapter branch repairrel integrálva vagy dokumentáltan behatárolva.
- [x] `SolverOutput` v1 contract nem sérült.
- [x] Rust Metrics bővítés csak backward-compatible módon történt, ha történt.
- [x] jagua-rs típus nem szivárog publikus VRS output/runner contractba.
- [x] Invalid layout nem mehet át successként.
- [x] Exact validation továbbra is végső igazság.

## Smoke / tests

- [x] `scripts/smoke_jagua_repair_search_v1.py` létrejött.
- [x] Repair smoke PASS.
- [x] Valid/repair scenario exact validator PASS.
- [x] Overlap/boundary negative evidence szerepel.
- [x] Determinism check PASS.
- [x] Time limit check PASS.
- [x] `python3 scripts/smoke_jagua_initial_construction.py` regression PASS.
- [x] `python3 scripts/smoke_jagua_exact_validation_bridge.py` regression PASS.
- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md` PASS.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.verify.log`.

## Report / checklist

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz valós kód auditot.
- [x] Report tartalmaz repair design döntést.
- [x] Report tartalmaz repair attempt/success/fail metrikát.
- [x] Report tartalmaz smoke/test kimenet-részleteket.
- [x] Globális progress checklist JG-10 szakasza frissítve.
- [x] Ha eltérés volt a tervtől, `DISCOVERED_MISMATCH`, `DEVIATION` vagy `REQUIRES_DECISION` blokk dokumentálja.
- [x] Report végső státusza: PASS / REVISE / BLOCKED.
- [x] Következő task indíthatósága jelölve: `JG-11_STATUS: READY` vagy `NOT_READY`.
