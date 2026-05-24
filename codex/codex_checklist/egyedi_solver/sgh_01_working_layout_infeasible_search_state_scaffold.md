# Checklist — SGH-01 `sgh_01_working_layout_infeasible_search_state_scaffold`

## Dependency gate

- [x] SGH-00 report létezik: `codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md`.
- [x] SGH-00 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] SGH-00 report tartalmazza: `SGH-01_STATUS: READY`.
- [x] Dependency evidence dokumentálva a SGH-01 reportban.

## Repo rules and local code audit

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md` elolvasva.
- [x] `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md` elolvasva.
- [x] `rust/vrs_solver/src/optimizer/state.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/repair.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/mod.rs` auditálva.
- [x] `rust/vrs_solver/src/io.rs`, `item.rs`, `sheet.rs` auditálva.

## Implementation

- [x] `WorkingLayout` külön típusként létrejött.
- [x] `WorkingLayout` képes ideiglenesen infeasible/colliding placementeket tárolni.
- [x] `WorkingLayout` Clone/snapshot célra használható.
- [x] Van explicit `validate_for_commit` vagy ekvivalens commit gate API.
- [x] Van explicit `validate_and_commit` vagy ekvivalens accepted-output API.
- [x] A commit gate a valós `repair::find_violations()` függvényt használja.
- [x] Invalid working layout nem commitolható.
- [x] Valid working layout commitolható.
- [x] Nincs validáció nélküli implicit `WorkingLayout -> LayoutState` / output konverzió.
- [x] `rust/vrs_solver/src/optimizer/mod.rs` csak a szükséges modul exporttal változott.

## Tests

- [x] Overlapes WorkingLayout tárolható, de commit hibát ad.
- [x] Boundary/sheet violation commit hibát ad.
- [x] Valid WorkingLayout commit sikeres.
- [x] Snapshot/clone/restore determinisztikus.
- [x] Commit diagnosztika külön számolja az overlap és boundary violationöket.
- [x] A tesztek valós Part/Stock/SheetShape/Placement struktúrákat használnak.

## Documentation

- [x] Elkészült `docs/egyedi_solver/sgh_01_working_layout_state_contract.md`.
- [x] A doksi leírja a WorkingLayout szerepét.
- [x] A doksi leírja a LayoutState / SolverOutput különbséget.
- [x] A doksi leírja a commit gate-et.
- [x] A doksi leírja a tiltott implicit konverziókat.
- [x] A doksi leírja, hogyan készíti elő SGH-02-t.

## Scope safety

- [x] Nem történt Sparrow/SparrowGH vendorolás.
- [x] Nem készült külső backend adapter.
- [x] Nem történt separator/GLS tracker teljes implementáció.
- [x] Nem lett átírva `repair.rs` separatorrá.
- [x] Nem lett átírva `sheet_elimination.rs`.
- [x] Nem lett átírva `initializer.rs`.
- [x] Nem változott a solver IO contract.
- [x] Nem változott a Python runner / exact validator.

## Verification and report

- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md` lefutott vagy környezeti blocker dokumentálva.
- [x] Verify log létrejött: `codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.verify.log`.
- [x] Report tartalmaz DoD → Evidence Matrixot.
- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Ha zöld, report végén szerepel: `SGH-02_STATUS: READY`.
