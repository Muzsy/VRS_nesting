# Checklist — JG-18 `jagua_optimizer_t18_irregular_candidate_generation`

## Dependency and preflight

- [x] JG-17 report létezik.
- [x] JG-17 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] JG-17 report tartalmazza: `JG-18_STATUS: READY`.
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` létezik és használható boundary façade.
- [x] Repo szabályfájlok elolvasva (`AGENTS.md`, `docs/codex/*`, `docs/qa/testing_guidelines.md`).
- [x] JG tervdokumentumok elolvasva.

## Current code audit

- [x] `rust/vrs_solver/src/optimizer/candidates.rs` auditálva.
- [x] `rust/vrs_solver/src/optimizer/initializer.rs` candidate call site auditálva.
- [x] `rust/vrs_solver/src/optimizer/repair.rs` candidate call site auditálva.
- [x] `rust/vrs_solver/src/optimizer/sheet_elimination.rs` candidate call site auditálva.
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` boundary filter kapcsolat auditálva.
- [x] `rust/vrs_solver/src/sheet.rs` irregular sheet metadata auditálva.
- [x] Current legacy candidate behavior dokumentálva.

## Candidate generation implementation

- [x] Irregular-aware candidate generator API vagy wrapper implementálva.
- [x] Legacy rectangular candidate behavior regresszió-kompatibilisen megmaradt.
- [x] Candidate source/reason modell bevezetve vagy dokumentáltan elérhető.
- [x] Interior sampling determinisztikus seed/input alapján.
- [x] Edge-near candidate generálás implementálva.
- [x] Vertex-near candidate generálás implementálva.
- [x] Neighbor-near candidate generálás implementálva vagy dokumentált fallbackkel jelölve.
- [x] Candidate dedup policy determinisztikus.
- [x] Candidate sorrend determinisztikus.
- [x] Candidate rejection reason reportolva.
- [x] Candidate count metrika szerepel.

## Integration

- [x] `build_initial_layout()` az irregular-aware candidate útvonalat használja vagy kompatibilisen wrapperel.
- [x] Repair reinsertion az irregular-aware candidate útvonalat használja vagy kompatibilisen wrapperel.
- [x] Sheet-elimination reinsertion call site regresszió-kompatibilis.
- [x] Minden új candidate boundary::rect_within_boundary szűrésen megy át.
- [x] Collision check továbbra is kiszűri az átfedő placementeket.
- [x] Invalid candidate nem kerül final layoutba.
- [x] Exact validation gate nem lett lazítva.

## Fixtures and tests

- [x] `tests/fixtures/egyedi_solver/jagua_irregular_candidate_generation.json` létrejött.
- [x] Fixture hole-free irregular/remnant stockot tartalmaz.
- [x] Fixture legalább részleges valid irregular elhelyezést bizonyít.
- [x] `scripts/smoke_jagua_irregular_candidate_generation.py` létrejött.
- [x] Smoke riportolja candidate countot.
- [x] Smoke riportolja candidate source breakdown-t.
- [x] Smoke riportolja rejection reasonöket.
- [x] Azonos seed/input determinisztikus candidate sorrendet ad.
- [x] Rectangular candidate generation regresszió nincs.
- [x] `python3 scripts/smoke_jagua_irregular_candidate_generation.py` PASS.
- [x] `python3 scripts/smoke_jagua_irregular_boundary_validation.py` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] Repo verify PASS és log mentve.

## Documentation and report

- [x] `docs/solver_io_contract.md` frissítve: JG-18 candidate generation contract.
- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz candidate source összefoglalót.
- [x] Report tartalmaz irregular elhelyezési példát.
- [x] Report tartalmaz determinism evidence-t.
- [x] Report tartalmaz rectangular regression evidence-t.
- [x] Report tartalmaz futtatott parancsokat és eredményeket.
- [x] Globális progress checklist JG-18 szakasza frissítve.
- [x] Csak valódi PASS esetén szerepel: `JG-19_STATUS: READY`.

## Closing fields

- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [x] Következő task (JG-19) indíthatósága jelölve vagy explicit nem-ready.
