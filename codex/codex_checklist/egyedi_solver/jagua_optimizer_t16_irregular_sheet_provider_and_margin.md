# Checklist — JG-16 `jagua_optimizer_t16_irregular_sheet_provider_and_margin`

## Dependency preflight

- [x] `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` létezik.
- [x] JG-15 report első sora `PASS`.
- [x] JG-15 report tartalmazza: `JG-16_STATUS: READY`.
- [x] `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md` létezik.
- [x] JG-15 decision report alapján a Phase 2 irány egyértelmű: `OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION`.

## Required reads

- [x] `AGENTS.md` elolvasva.
- [x] `docs/codex/overview.md` elolvasva.
- [x] `docs/codex/yaml_schema.md` elolvasva.
- [x] `docs/codex/report_standard.md` elolvasva.
- [x] `docs/qa/testing_guidelines.md` elolvasva.
- [x] JG tervdokumentációk elolvasva.
- [x] JG-16 canvas/YAML/runner elolvasva.
- [x] JG-15 report és decision report elolvasva.

## Real code audit

- [x] `rust/vrs_solver/src/sheet.rs` Stock/SheetShape/rect_inside_sheet_shape auditálva.
- [x] `rust/vrs_solver/src/geometry.rs` polygon/bbox/jagua conversion helper auditálva.
- [x] `rust/vrs_solver/src/adapter.rs` profile és adapter boundary auditálva.
- [x] `rust/vrs_solver/src/io.rs` SolverInput/SolverOutput v1 contract auditálva.
- [x] `vrs_nesting/nesting/instances.py` stock polygon + margin validation auditálva.
- [x] `vrs_nesting/runner/vrs_solver_runner.py` validation_status/runner_meta auditálva.
- [x] `docs/solver_io_contract.md` margin/spacing JG-05 deviation auditálva.

## Provider/model implementation

- [x] SheetShape modell kibővítve: `has_irregular_outer: bool` és `area: f64` mezők hozzáadva.
- [x] Usable boundary policy implementálva: `_outer_poly`-alapú corner + edge check `has_irregular_outer=true` esetén.
- [x] Shape metadata számolva: `area` (shoelace), `has_irregular_outer`, `width`, `height`.
- [x] `Stock.outer_points` L-shape/remnant input validálva és a solver `SheetShape`-be konvertálja.
- [x] Invalid outer polygon determinisztikus hibát ad (`stock_to_shape` Err).
- [x] Non-empty `Stock.holes_points` container hole unsupported státuszt kap (`UNSUPPORTED_STOCK_HOLES_PHASE1`); nincs silent ignore.
- [x] Too-narrow remnant deterministikus PART_NEVER_FITS_STOCK állapotot kap (Phase1 pre-filter).
- [x] Rectangular provider regresszió nincs (80 unit test PASS).
- [x] Margin kezelés nem marad silent: `margin_mm` parsed; `> 0` → `UNSUPPORTED_MARGIN_MM_RUNTIME`.

## Fixtures and tests

- [x] `tests/fixtures/egyedi_solver/jagua_irregular_margin.json` létrejött.
- [x] Fixture hole-free L-shape/remnant stockot tartalmaz.
- [x] Fixture tartalmaz `margin_mm=5.0` és `_fixture_notes` metaadatot.
- [x] `scripts/smoke_jagua_irregular_sheet_provider.py` létrejött.
- [x] Smoke ellenőrzi rectangular regressziót (Check 3).
- [x] Smoke ellenőrzi L-shape/remnant provider viselkedést (Check 4).
- [x] Smoke ellenőrzi too-narrow remnant PART_NEVER_FITS_STOCK esetet (Check 7).
- [x] Smoke ellenőrzi container hole tiltását (Check 6).
- [x] Smoke exact validation gate-tel fut (Check 10).
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS — 80 tests.
- [x] `python3 scripts/smoke_jagua_irregular_sheet_provider.py` PASS — 12 PASS, 0 FAIL.
- [x] Repo verify PASS és log mentve.

## Documentation and report

- [x] `docs/solver_io_contract.md` frissítve: irregular boundary policy, margin_mm JG-16 státusz, Phase 1 unsupported okok.
- [x] Report tartalmazza a margin policy döntést.
- [x] Report tartalmazza a usable region adatokat.
- [x] Report tartalmazza a dependency evidence-t.
- [x] Report tartalmazza a futtatott parancsokat és eredményeket.
- [x] Globális progress checklist JG-16 szakasza frissítve.
- [x] `JG-17_STATUS: READY` szerepel (minden gate PASS).

## Closing fields

- [x] Report első sora `PASS`.
- [x] Eltérés a tervtől (margin_mm promoted, not silent) dokumentálva.
- [x] Következő task (JG-17) indíthatósága jelölve.
