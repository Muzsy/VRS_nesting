# Checklist — JG-19 `jagua_optimizer_t19_remnant_score_model_v1`

## Dependency and preflight

- [x] JG-18 report létezik.
- [x] JG-18 report első sora `PASS` vagy `PASS_WITH_NOTES`.
- [x] JG-18 report tartalmazza: `JG-19_STATUS: READY`.
- [x] JG-18 irregular-aware candidate útvonal létezik.
- [x] Repo szabályfájlok elolvasva (`AGENTS.md`, `docs/codex/*`, `docs/qa/testing_guidelines.md`).
- [x] JG tervdokumentumok elolvasva.

## Current code audit

- [x] `rust/vrs_solver/src/optimizer/score.rs` auditálva.
- [x] `rust/vrs_solver/src/sheet.rs` sheet metadata auditálva.
- [x] `rust/vrs_solver/src/optimizer/multisheet.rs` per-sheet diagnostics auditálva.
- [x] `rust/vrs_solver/src/adapter.rs` diagnostics/output boundary auditálva.
- [x] `rust/vrs_solver/src/io.rs` metrics/output contract auditálva.
- [x] `rust/vrs_solver/src/optimizer/boundary.rs` validity-score kapcsolat auditálva.
- [x] Jelenlegi ScoreWeights és ObjectiveBreakdown dokumentálva.
- [x] Explicit remnant/inventory-cost input hiánya vagy megléte dokumentálva.

## Score model implementation

- [x] Sheet cost metadata modell dokumentálva.
- [x] Ha nincs explicit inventory schema, V1 proxy/inference policy dokumentálva.
- [x] Remnant preferencia súly dokumentálva.
- [x] Új teljes tábla nyitási büntetés dokumentálva.
- [x] Usable-area utilization számítás működik.
- [x] `ObjectiveBreakdown` tartalmaz sheet-cost/utilization breakdown-t.
- [x] Score weight defaultok reportolva.
- [x] Invalid boundary/overlap nem lehet jó score-ral sikeres.
- [x] Remnant preference nem írja felül a boundary/overlap penaltyt.
- [x] Rectangular-only score regresszió nincs.

## Fixtures and smoke

- [x] `tests/fixtures/egyedi_solver/jagua_remnant_score_model_v1.json` létrejött.
- [x] Fixture vegyes rectangular + remnant stockot tartalmaz.
- [x] Fixture hole-free, Phase 2 scope-on belül marad.
- [x] `scripts/smoke_jagua_remnant_score_model_v1.py` létrejött.
- [x] Smoke reportolja a sheet cost breakdown-t.
- [x] Smoke reportolja usable-area utilizationt.
- [x] Smoke magyarázható sheet választást ad.
- [x] Smoke bizonyítja invalid-vs-valid score dominanciát.
- [x] Smoke/benchmark PASS.
- [x] `python3 scripts/smoke_jagua_score_model_v1.py` PASS.
- [x] `python3 scripts/smoke_jagua_irregular_candidate_generation.py` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score` PASS.
- [x] Repo verify PASS és log mentve.

## Documentation and report

- [x] `docs/egyedi_solver/jagua_remnant_score_model_v1.md` létrejött.
- [x] `docs/solver_io_contract.md` frissítve: JG-19 remnant score contract.
- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz sheet metadata/proxy döntést.
- [x] Report tartalmaz default weight profile-t.
- [x] Report tartalmaz döntési példákat.
- [x] Report tartalmaz rectangular regression evidence-t.
- [x] Report tartalmaz JG-18 regression evidence-t.
- [x] Globális progress checklist JG-19 szakasza frissítve.
- [x] Csak valódi PASS esetén szerepel: `JG-20_STATUS: READY`.

## Closing fields

- [x] Report első sora `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [x] Következő task (JG-20) indíthatósága jelölve vagy explicit nem-ready.
