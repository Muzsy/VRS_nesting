# Checklist — JG-17 `jagua_optimizer_t17_irregular_boundary_validation`

## Dependency preflight

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md` létezik.
- [x] JG-16 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] JG-16 report tartalmazza: `JG-17_STATUS: READY`.
- [x] `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md` létezik.
- [x] JG-15 decision továbbra is `OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION`.
- [x] `docs/solver_io_contract.md` tartalmazza a JG-16 irregular sheet boundary policy-t.

## Required reads

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] JG tervdokumentációk elolvasva.
- [x] JG-17 canvas/YAML/runner elolvasva.
- [x] JG-16 report elolvasva.
- [x] JG-15 decision report elolvasva.

## Real code audit

- [x] `rust/vrs_solver/src/sheet.rs` `SheetShape` és `rect_inside_sheet_shape()` auditálva.
- [x] `rust/vrs_solver/src/geometry.rs` corner/edge helper auditálva.
- [x] `rust/vrs_solver/src/adapter.rs` `JaguaAdapter::check_rect_in_sheet()` és unsupported policy auditálva.
- [x] `rust/vrs_solver/src/optimizer/mod.rs` boundary module hiánya / bekötése auditálva.
- [x] `rust/vrs_solver/src/optimizer/initializer.rs` construction boundary use auditálva.
- [x] `rust/vrs_solver/src/optimizer/repair.rs` `find_violations()` boundary use auditálva.
- [x] `rust/vrs_solver/src/optimizer/score.rs` boundary penalty auditálva.
- [x] `vrs_nesting/nesting/instances.py` exact stock polygon + margin validation auditálva.
- [x] `vrs_nesting/runner/vrs_solver_runner.py` `validation_status=fail` semantics auditálva.
- [x] `docs/solver_io_contract.md` JG-16/JG-17 boundary contract auditálva.

## Boundary policy implementation

- [x] Boundary validation policy dokumentálva.
- [x] Boundary-touch policy dokumentálva.
- [x] Proxy Rust boundary check és Python exact boundary check viszonya dokumentálva.
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` létrejött, vagy a report explicit indokolja, miért nem repo-konform.
- [x] `rust/vrs_solver/src/optimizer/mod.rs` frissítve, ha boundary module létrejött.
- [x] Construction placer boundary útvonala a policy-t használja vagy oda delegál.
- [x] Repair `find_violations()` boundary útvonala a policy-t használja vagy oda delegál.
- [x] ScoreModel boundary penalty továbbra is hard validity guard.
- [x] Invalid sheet_index / out-of-boundary placement `BoundaryOrSheet` violation marad.

## Fixtures and tests

- [x] `tests/fixtures/egyedi_solver/jagua_irregular_boundary_validation.json` létrejött.
- [x] Fixture hole-free L-shape/remnant stockot tartalmaz.
- [x] Fixture tartalmaz pozitív inside-L példát.
- [x] Fixture tartalmaz negatív notch/outside-L példát.
- [x] Sheeten belüli item PASS.
- [x] Konkáv sheetből kilógó vagy notch régióba eső item FAIL.
- [x] Margin-zónába lógó vagy marginos input nem silent success.
- [x] Invalid boundary layout nem lehet successful.
- [x] Rectangular boundary validation regresszió nincs.
- [x] `scripts/smoke_jagua_irregular_boundary_validation.py` létrejött.
- [x] Validator smoke lefut irregular fixture-ön.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] Repo verify PASS és log mentve.

## Documentation and report

- [x] `docs/solver_io_contract.md` frissítve: JG-17 boundary validation policy.
- [x] Report tartalmaz pozitív és negatív példát.
- [x] Report tartalmaz boundary-touch policy-t.
- [x] Report tartalmaz proxy vs exact boundary relationt.
- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz futtatott parancsokat és eredményeket.
- [x] Globális progress checklist JG-17 szakasza frissítve.
- [x] Csak valódi PASS esetén szerepel: `JG-18_STATUS: READY`.

## Closing fields

- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [x] Következő task (JG-18) indíthatósága jelölve vagy explicit nem-ready.
