# Checklist — SGH-03 `sgh_03_lbf_separator_construction_integration`

## Dependency gate

- [x] SGH-02 report létezik: `codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md`.
- [x] SGH-02 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] SGH-02 report tartalmazza: `SGH-03_STATUS: READY`.
- [x] Dependency evidence dokumentálva a SGH-03 reportban.

## Repo rules and local code audit

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md` elolvasva.
- [x] `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md` elolvasva.
- [x] `docs/egyedi_solver/sgh_01_working_layout_state_contract.md` elolvasva.
- [x] `docs/egyedi_solver/sgh_02_vrs_separator_contract.md` elolvasva.
- [x] `rust/vrs_solver/src/optimizer/initializer.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/candidates.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/separator.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/working.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/repair.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/score.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/state.rs` auditálva.
- [x] `rust/vrs_solver/src/io.rs`, `item.rs`, `sheet.rs` auditálva.

## Implementation

- [x] `ConstructionDiagnostics` bővült LBF/separator fallback mezőkkel.
- [x] `ConstructionDiagnostics::summary()` tartalmazza az új mezőket.
- [x] Clear placement választás explicit LBF scoringot használ.
- [x] LBF scoring determinisztikus és used-sheet first policyt használ.
- [x] LBF selection a valós `generate_candidates_with_sheets()` forrást használja.
- [x] LBF selection a valós `rect_within_boundary()` boundary policyt használja.
- [x] LBF selection a valós rotation helpereket használja.
- [x] Separator fallback be van kötve, ha nincs clear LBF candidate.
- [x] Separator fallback `WorkingLayout`-ot és `VrsSeparator::run()`-t használ.
- [x] Fallback csak `best_loss == 0.0` vagy `converged == true` és commit-gate success után fogad el eredményt.
- [x] Sikeres fallback után a teljes `placed_bboxes` cache újraépül.
- [x] Sikertelen fallback rollback-safe, nem sérti az előző placement state-et.
- [x] `build_initial_layout()` public signature alapesetben változatlan maradt.

## Tests

- [x] Meglévő initializer tesztek zöldek.
- [x] LBF scorer used sheetet preferál unused sheet előtt.
- [x] `build_initial_layout()` determinisztikus két azonos futáson.
- [x] `placed.len() + unplaced.len() == expanded_instances.len()` továbbra is igaz.
- [x] Separator fallback helper sikeres kényszerített colliding seedből.
- [x] Separator fallback failure rollback-safe tesztelve.
- [x] Successful construction output `find_violations()` szerint valid.
- [x] Diagnostics summary tartalmazza az új LBF/separator mezőket.
- [x] A tesztek valós VRS típusokat használnak, nem mockolt commit gate-et.

## Documentation

- [x] Elkészült `docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md`.
- [x] A doksi leírja a current initializer gapet.
- [x] A doksi leírja az LBF scoring V1 szabályt.
- [x] A doksi leírja a separator fallback V1 szabályt.
- [x] A doksi leírja a commit/rollback szabályokat.
- [x] A doksi leírja a diagnostics mezőket.
- [x] A doksi leírja, hogyan készíti elő SGH-04-et.

## Scope safety

- [x] Nem történt Sparrow/SparrowGH vendorolás.
- [x] Nem készült külső backend adapter.
- [x] Nem lett módosítva `rust/vrs_solver/src/io.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/adapter.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/sheet_elimination.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/moves.rs`.
- [x] Nem lett módosítva `rust/vrs_solver/src/optimizer/multisheet.rs`.
- [x] Nem lett átírva `rust/vrs_solver/src/optimizer/score.rs` objective modellje.
- [x] Nem változott a Python runner / exact validator.
- [x] Nem lett continuous rotation bevezetve.
- [x] Nem lett solution pool / perturbáció bevezetve.

## Verification and report

- [x] Focused Rust teszt lefutott: `cargo test -p vrs_solver initializer` — 15/15 passed; full suite 121/121.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md` lefutott.
- [x] Verify log létrejött: `codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.verify.log`.
- [x] Report tartalmaz DoD → Evidence Matrixot.
- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Ha zöld, report végén szerepel: `SGH-04_STATUS: READY`.
