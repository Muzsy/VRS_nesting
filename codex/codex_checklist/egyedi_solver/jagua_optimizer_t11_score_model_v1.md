# Codex checklist — JG-11 `jagua_optimizer_t11_score_model_v1`

## Task meta

- **Task ID:** JG-11
- **Slug:** `jagua_optimizer_t11_score_model_v1`
- **Phase:** Phase 1 / objective
- **Dependency:** JG-10 — `jagua_optimizer_t10_repair_search_loop_v1`
- **Runner:** `codex/prompts/egyedi_solver/jagua_optimizer_t11_score_model_v1/run.md`
- **Canvas:** `canvases/egyedi_solver/jagua_optimizer_t11_score_model_v1.md`
- **Goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t11_score_model_v1.yaml`
- **Report:** `codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md`

## Dependency gate

- [x] JG-10 report létezik.
- [x] JG-10 report első sora `PASS`.
- [x] JG-10 report tartalmazza: `JG-11_STATUS: READY`.
- [x] `rust/vrs_solver/src/optimizer/repair.rs` létezik.
- [x] `rust/vrs_solver/src/optimizer/stopping.rs` létezik.
- [x] `scripts/smoke_jagua_repair_search_v1.py` létezik.

## Valós kód audit

- [x] `optimizer/score.rs` meglévő skeletonja auditálva.
- [x] `LayoutState` / `PlacedItem` / `UnplacedItem` mezők auditálva.
- [x] `bbox_from_placement()` és `PlacedBbox::overlaps()` auditálva.
- [x] `rect_inside_sheet_shape()` boundary helper auditálva.
- [x] `Part` / `ItemGeometryStore` area és rotation cache auditálva.
- [x] Publikus `SolverOutput` v1 contract auditálva, nincs törő módosítás.

## Implementációs checklist

- [x] `ScoreModel V1` vagy repo-konform ekvivalens implementálva.
- [x] `ScoreWeights` vagy repo-konform ekvivalens implementálva.
- [x] Score iránya explicit dokumentált: magasabb jobb vagy alacsonyabb jobb.
- [x] `ObjectiveBreakdown` auditálható score komponensekkel bővítve.
- [x] Placed area komponens működik.
- [x] Unplaced penalty érdemben büntet.
- [x] Sheet count penalty működik.
- [x] Boundary penalty nagy súlyú.
- [x] Overlap penalty nagy súlyú.
- [x] Compactness proxy működik, de nem írja felül a validitást.
- [x] Invalid layout score-ja rosszabb valid alternatívánál.
- [x] Score determinisztikus azonos állapotra.
- [x] Nincs szétszórt, dokumentálatlan magic number súlyrendszer.
- [x] `docs/egyedi_solver/jagua_optimizer_score_model_v1.md` elkészült.
- [x] `scripts/smoke_jagua_score_model_v1.py` elkészült.

## Teszt / verify

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score` PASS.
- [x] `python3 scripts/smoke_jagua_repair_search_v1.py` PASS vagy dokumentált környezeti blocker.
- [x] `python3 scripts/smoke_jagua_score_model_v1.py` PASS.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md` PASS.
- [x] Verify log mentve: `codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.verify.log`.

## Report / progress

- [x] Report tartalmaz dependency evidence-t.
- [x] Report tartalmaz real code auditot.
- [x] Report tartalmaz score API döntést.
- [x] Report tartalmaz score weight default táblázatot.
- [x] Report tartalmaz objective breakdown példát.
- [x] Report tartalmaz invalid vs valid score evidence-t.
- [x] Report tartalmaz unit/smoke/verify eredményeket.
- [x] Globális progress checklist JG-11 szakasza frissítve.
- [x] Reportban szerepel a végső státusz: PASS / REVISE / STOP / BLOCKED.
- [x] Ha volt eltérés a tervtől, az explicit módon dokumentálva van.
- [x] Következő task indíthatósága egyértelmű: `JG-12_STATUS: READY` csak PASS esetén.
