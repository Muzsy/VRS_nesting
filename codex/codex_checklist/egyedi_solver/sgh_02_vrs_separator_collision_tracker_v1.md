# Checklist — SGH-02 `sgh_02_vrs_separator_collision_tracker_v1`

## Dependency gate

- [x] SGH-01 report létezik: `codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md`.
- [x] SGH-01 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] SGH-01 report tartalmazza: `SGH-02_STATUS: READY`.
- [x] Dependency evidence dokumentálva a SGH-02 reportban.

## Repo rules and local code audit

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md` elolvasva.
- [x] `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md` elolvasva.
- [x] `docs/egyedi_solver/sgh_01_working_layout_state_contract.md` elolvasva.
- [x] `rust/vrs_solver/src/optimizer/working.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/repair.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/candidates.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/initializer.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/stopping.rs` auditálva.
- [x] `rust/vrs_solver/src/io.rs`, `item.rs`, `sheet.rs` auditálva.

## Implementation

- [x] `rust/vrs_solver/src/optimizer/separator.rs` létrejött.
- [x] `rust/vrs_solver/src/optimizer/mod.rs` exportálja a separator modult.
- [x] `VrsCollisionTracker` vagy ekvivalens tracker implementálva.
- [x] Pair loss bbox intersection area alapján működik.
- [x] Boundary loss invalid sheet / outside boundary esetén pozitív.
- [x] Weighted total loss és GLS-like `update_weights()` implementálva.
- [x] Colliding/violating placement indexek lekérhetők.
- [x] `VrsSeparator` vagy ekvivalens separator implementálva.
- [x] Separator bemenete/kimenete `WorkingLayout` alapú.
- [x] Separator nem épít `LayoutState`-et vagy `SolverOutput`-ot közvetlenül.
- [x] Separator használja a valós candidate/bbox/boundary helper függvényeket.
- [x] Snapshot/best-state/rollback minta implementálva.
- [x] A separator determinisztikus, RNG nélküli V1.

## Tests

- [x] Valid layouton tracker total loss 0.
- [x] Overlap esetén pair loss pozitív.
- [x] Boundary/sheet violation esetén boundary loss pozitív.
- [x] Javítható overlap fixture-t separator valid layouttá javít.
- [x] Javítható fixture után `WorkingLayout.validate_for_commit()` sikeres.
- [x] Item count invariant megmarad.
- [x] Separator determinisztikus: két azonos futás azonos outputot ad.
- [x] Nem javítható fixture nem panicel és nem-konvergált diagnosztikát ad.
- [x] A tesztek valós VRS típusokat használnak, nem mockolt commit gate-et.

## Documentation

- [x] Elkészült `docs/egyedi_solver/sgh_02_vrs_separator_contract.md`.
- [x] A doksi leírja a separator célját.
- [x] A doksi leírja a WorkingLayout kapcsolatot.
- [x] A doksi leírja a collision loss V1 modellt.
- [x] A doksi leírja a boundary loss V1 proxyt.
- [x] A doksi leírja a GLS-like update V1-et.
- [x] A doksi leírja a rollback/commit szabályokat.
- [x] A doksi leírja, hogyan készíti elő SGH-03/SGH-04-et.

## Scope safety

- [x] Nem történt Sparrow/SparrowGH vendorolás.
- [x] Nem készült külső backend adapter.
- [x] Nem lett módosítva `rust/vrs_solver/src/io.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/adapter.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/initializer.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/sheet_elimination.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/moves.rs`.
- [x] Nem változott a Python runner / exact validator.
- [x] Nem lett continuous rotation bevezetve.

## Verification and report

- [x] Focused Rust teszt lefutott: `cargo test separator` (8/8 ok) és `cargo test` (114/114 ok).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md` lefutott vagy környezeti blocker dokumentálva.
- [x] Verify log létrejött: `codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.verify.log`.
- [x] Report tartalmaz DoD → Evidence Matrixot.
- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Ha zöld, report végén szerepel: `SGH-03_STATUS: READY`.
