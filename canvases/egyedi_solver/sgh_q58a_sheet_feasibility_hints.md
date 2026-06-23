# Q58A — SheetFeasibilityHints

## Goal / Funkció

Hozz létre egy preprocessing-szintű `SheetFeasibilityHints` modellt egy teljes job/run-ra. Ez a task
stratégiai feasibility-t és sheet-eloszlást becsül a placement **előtt**. Nem váltja ki az exact
nestinget; hinteket ad a sheet-builder döntésekhez, különösen kritikus part-kvótákhoz és lehetséges
2-sheet / 3-sheet stratégiákhoz.

## Context / Háttér

A repo diagnosztikája ma tartalmaz `bpp_area_lower_bound`, `bpp_gap_to_area_lower_bound`,
`bpp_max_critical_per_sheet` jellegű értékeket, de ezek nem alkotnak koherens tervezési réteget. A
solvernek tudnia kell: mely partok hajtják a sheet-számot, mely kritikus típusok mennek először, hány
kritikus part próbálkozzon sheet-enként, hihető-e a 3/tábla, mely ismételt családok sugallnak
grid/band stratégiát, és mi a legjobb partial fallback.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q58A_SheetFeasibilityHints.md`

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `bpp_area_lower_bound` jellegű
  diagnosztika, kritikus admission.
- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` — `criticality_tier()`, quantity, area
  arányok.
- `rust/vrs_solver/src/optimizer/sparrow/model.rs` — sheet dimenziók, margin/spacing kontextus.
- `rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs` (Q56A),
  `rust/vrs_solver/src/optimizer/sparrow/part_analysis.rs` (Q56B),
  `rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs` (Q57A) — ha léteznek, reuse.

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/io.rs
```

Megjegyzés: `rust/vrs_solver/src/optimizer/sparrow/sheet_feasibility.rs` még **nem létezik** — ez a
task deliverable-je (új fájl).

## Scope

- Új `sheet_feasibility.rs` modul: `SheetFeasibilityHints`, `CriticalPartTypeSheetHint`,
  `RepeatedFamilySheetHint`, `DangerPartHint`, `TargetSheetStrategyHint`,
  `SheetFeasibilityDiagnostics`.
- Area lower bound, kritikus kapacitás-becslés, target distribution, danger parts.
- JSON diagnosztikai artifact.
- Fókuszált unit tesztek.

## Out of scope

- BPP/sheet-builder viselkedés megváltoztatása (Q58B).
- Placement mutáció.
- Exact nesting kiváltása / final sheet-count proof.

## Required implementation

Inputok: PartAnalysis/ShapeProfileV2, OrientationCatalog, PairCompatibilityIndex (ha elérhető), sheet
dimenziók, margin/spacing, quantity/demand, area lower bound. Ha Q57A nincs, a pair-alapú mezők
hiányozhatnak vagy `unknown`.

Becslések:
1. **Area lower bound:** `ceil(total_part_area / usable_sheet_area)`; explicit, hogy a
   `usable_sheet_area` margin-shrunk-e.
2. **Kritikus kapacitás:** `estimated_max_per_sheet` típusonként, konzervatív kombináció (area bound,
   OrientationCatalog span/min-width, sheet span ratio, pair compat ha van, current-run proof artifact
   ha van). Státusz: `unknown` / `plausible` / `unlikely` / `proven_by_focused_test` /
   `rejected_by_focused_test`. **Ne** állíts exact feasibility-t.
3. **Target distribution:** ismételt kritikus típusra (pl. quantity 6, max 3 → `[3,3]`; max 2 →
   `[2,2,2]`). Hint, nem proof.
4. **Danger parts:** nagy sheet span, magas fit difficulty, kevés hasznos orientáció, magas kontúr
   komplexitás, kevés interlock candidate, nagy ismételt mennyiség.

## Required diagnostics

```text
artifacts/benchmarks/sgh_q58a/sheet_feasibility_hints.json
```

Top-level mezők: `sheet_width`, `sheet_height`, `margin`, `spacing`, `usable_sheet_area_basis`,
`total_part_area`, `area_lower_bound`, `critical_part_type_count`, `repeated_family_count`,
`danger_part_count`, `target_sheet_strategy`, `critical_hints[]`, `repeated_family_hints[]`,
`danger_parts[]`.

## Required tests / runners

Teszt: `rust/vrs_solver/tests/sparrow_sheet_feasibility_hints.rs`. Ellenőrzések:

1. Hints épül reprezentatív valós inputra.
2. Area lower bound determinisztikus.
3. Ismételt kritikus típus distribution hintet kap.
4. Danger parts lista tartalmazza a magas-criticality large anchorokat.
5. A modell hint/probability-ként jelöli a becsléseket, nem proofként.
6. Az output artifact szerializálható és stabil.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
```

## Acceptance criteria

```text
- SheetFeasibilityHints létezik.
- Area lower bound, kritikus kapacitás-hint, ismételt család-hint, danger parts kiszámolva.
- Tiszta artifactot ad.
- Még nem használják placement döntés kényszerítésére.
- A becslések confidence/basis címkével ellátottak.
```

## Hard restrictions

```text
- area lower bound nem final sheet-count proof
- nincs LV8-only target distribution hardcode
- nem feltételez 2 sheetet csak mert area engedi
- spacing/margin basis nem hagyható figyelmen kívül
- nincs placement mutáció ebben a taskban
- nincs NFP, nincs bbox collision shortcut, nincs part-id hack
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
```

## Rollback

- A hints réteg read-only (nem mutál placementet), így no-regression-kockázat alacsony; ha az IO
  export regressziót okoz, additív/opcionális mezőként exportáld.

## Deliverables

```text
canvases/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58a_sheet_feasibility_hints.yaml
codex/prompts/egyedi_solver/sgh_q58a_sheet_feasibility_hints/run.md
codex/codex_checklist/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
codex/reports/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
codex/reports/egyedi_solver/sgh_q58a_sheet_feasibility_hints.verify.log
```
