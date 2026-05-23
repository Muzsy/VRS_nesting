# Canvas — JG-11 `jagua_optimizer_t11_score_model_v1`

## Meta

- **Task ID:** JG-11
- **Slug:** `jagua_optimizer_t11_score_model_v1`
- **Phase:** Phase 1 / objective
- **Dependency:** JG-10 — `jagua_optimizer_t10_repair_search_loop_v1`
- **Primary output:** ScoreModel V1 a Phase 1 rectangular / outer-only optimizerhez.
- **Package status:** ez a dokumentum a futtatható task-csomag része; nem maga az implementáció.

## Dependency preflight

A JG-11 task csak akkor indítható, ha a repo aktuális állapotában:

```text
codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
```

- létezik;
- első sora `PASS`;
- tartalmazza: `JG-11_STATUS: READY`;
- bizonyítja, hogy JG-10 repair-search smoke és exact validation regression PASS;
- a Phase 1 branchben invalid layout nem mehet át successként.

Ha ez nem teljesül, az implementáló agent álljon meg `BLOCKED` státusszal, és ne módosítson optimizer kódot.

## Stratégiai háttér

A master plan szerint a projekt `jagua-rs` collision / geometry backendre épített, saját optimizer irányba megy. A JG-08 initial construction és JG-10 repair-search mechanika után a következő kritikus elem az objektív függvény: egy auditálható, determinisztikus ScoreModel, amely nem keveri össze a validitást és a tömörségi/minőségi célokat.

A JG-11 célja nem teljes metaheurisztika vagy multi-sheet manager bevezetése, hanem az első, dokumentált scoring réteg:

- placed area reward;
- unplaced penalty;
- sheet count penalty;
- overlap/boundary penalty;
- compactness proxy;
- diagnosztikus `ObjectiveBreakdown` output;
- dokumentált default weight profile.

Ez a ScoreModel később JG-12 multi-sheet, JG-13 benchmark és JG-14 phase-gate döntések alapja lesz.

## Valós repo audit — JG-11 kiindulóállapot

A csomag készítésekor ellenőrzött aktuális kódállapot:

| Fájl | Megfigyelés |
|---|---|
| `rust/vrs_solver/src/optimizer/score.rs` | Már létezik skeletonként. `ObjectiveBreakdown` csak countokat és `penalty_placeholder` mezőt tartalmaz. Ez JG-11-ben továbbfejlesztendő, nem duplikálandó. |
| `rust/vrs_solver/src/optimizer/state.rs` | `LayoutState`, `PlacedItem`, `UnplacedItem`, `PlacementTransform` létezik és serializálható. |
| `rust/vrs_solver/src/optimizer/repair.rs` | JG-10 után létezik `RepairDiagnostics`, `find_violations()` és `run_repair()`; overlap/boundary diagnosztika elérhető. |
| `rust/vrs_solver/src/optimizer/initializer.rs` | `bbox_from_placement()` létezik, Phase 1 rectangular bbox recoveryre használható. |
| `rust/vrs_solver/src/optimizer/candidates.rs` | `PlacedBbox::overlaps()` létezik, score overlap auditnál újrahasználható. |
| `rust/vrs_solver/src/item.rs` | `Part`, `ItemGeometryStore`, `build_item_geometry_store()`, `dims_for_rotation()` és area proxy elérhető. |
| `rust/vrs_solver/src/sheet.rs` | `SheetShape` és `rect_inside_sheet_shape()` létezik; boundary penalty számításhoz használható. |
| `rust/vrs_solver/src/adapter.rs` | Phase 1 branch jelenleg `build_initial_layout()` → `run_repair()` pipeline-t használ, a repair diagnostics még nincs score-hoz kötve. |
| `rust/vrs_solver/src/io.rs` | Publikus `SolverOutput` v1 contract szűk: `contract_version`, `status`, `unsupported_reason`, `placements`, `unplaced`, `metrics`. JG-11 nem törheti ezt. |

## Cél

A JG-11 végére legyen repo-konform ScoreModel V1, amely:

1. auditálható `ObjectiveBreakdown` struktúrával bontja le a score-t;
2. dokumentált, nem szétszórt magic number alapú `ScoreWeights` / profile default rendszert használ;
3. determinisztikusan értékel azonos layoutot;
4. explicit módon rosszabbnak értékeli az invalid layoutot, mint egy valid alternatívát;
5. érdemben bünteti az unplaced itemeket;
6. bünteti a több használt sheetet;
7. nagy súllyal bünteti az overlap és boundary hibákat;
8. tartalmaz compactness proxyt, de az nem írhatja felül a validitást;
9. dokumentálja a Phase 1 default weight profilt;
10. smoke teszttel bizonyítja a fenti invariánsokat.

## Nem-cél

- Nem JG-12 multi-sheet manager implementáció.
- Nem JG-13 benchmark mátrix.
- Nem JG-14 phase gate döntés.
- Nem teljes Sparrow score/search átvétel.
- Nem irregular/remnant sheet scoring.
- Nem cavity-prepack scoring.
- Nem publikus JSON contract törő módosítás.
- Nem exact validator gyengítése vagy kiváltása.

## Érintett fájlok

### Implementációs fókusz

```text
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/mod.rs
```

### Dokumentáció és smoke

```text
docs/egyedi_solver/jagua_optimizer_score_model_v1.md
scripts/smoke_jagua_score_model_v1.py
```

### Task admin

```text
canvases/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t11_score_model_v1.yaml
codex/prompts/egyedi_solver/jagua_optimizer_t11_score_model_v1/run.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.verify.log
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

## Hard rules

```text
REAL_CODE_ONLY:
- Work only from actual repository files.
- Do not invent files, modules, APIs, functions, schemas, or test commands.
- If the expected element does not exist, report it as mismatch/blocker.
```

```text
NO_SILENT_GEOMETRY_LOSS:
- Do not drop holes, contours, item identities, quantities, transforms, or validation data silently.
```

```text
EXACT_VALIDATION_REQUIRED:
- Any task that produces or modifies nesting layout behavior must require exact final validation.
- Invalid layout cannot be accepted as success.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## ScoreModel V1 elvárt viselkedés

A konkrét API-t a valós kód alapján kell kialakítani, de a JG-11 reportban bizonyítani kell legalább ezeket:

- van egy egyértelmű `ScoreWeights` vagy ekvivalens default profile;
- van egy `ObjectiveBreakdown` vagy ekvivalens diagnosztikai struktúra;
- a breakdown tartalmazza a placed area, unplaced, sheet count, overlap/boundary és compactness komponenseket;
- van egy `total_score` vagy ekvivalens összehasonlítható érték;
- a score iránya explicit dokumentált: például magasabb jobb vagy alacsonyabb jobb;
- van helper vagy dokumentált döntés az összehasonlításhoz, például `is_better_than()` vagy ekvivalens;
- invalid layout score-ja teszttel bizonyítottan rosszabb valid alternatívánál;
- score determinisztikus azonos inputra.

## Végrehajtási terv

### 1. Dependency preflight

- Olvasd el JG-10 reportját.
- Ha nincs `PASS` + `JG-11_STATUS: READY`, állj meg `BLOCKED` státusszal.
- Ellenőrizd, hogy JG-10 után `repair.rs`, `stopping.rs` és `scripts/smoke_jagua_repair_search_v1.py` létezik.

### 2. Score skeleton audit

- Auditáld a meglévő `optimizer/score.rs` skeleton tartalmát.
- Ne hozz létre duplikált score modult.
- Döntsd el, hogy a ScoreModel `LayoutState`-et, `Vec<Placement>`-et, vagy mindkettőhöz adaptert használ-e.
- A döntést dokumentáld a reportban.

### 3. ScoreWeights / profile default

- Vezess be dokumentált default weight profilt.
- A súlyokat egy helyen tartsd, ne elszórt konstansokként.
- A boundary/overlap penalty legyen elég nagy ahhoz, hogy validitást ne írhasson felül compactness vagy placed area reward.
- Az unplaced penalty legyen érdemi.
- A sheet count penalty legyen mérhető, de ne okozzon invalid layout elfogadást.

### 4. ObjectiveBreakdown bővítése

- Bővítsd vagy cseréld kompatibilisen a jelenlegi `ObjectiveBreakdown` skeleton mezőit.
- Minimum komponensek:
  - `placed_area` vagy ekvivalens;
  - `unplaced_count` / `unplaced_penalty`;
  - `sheet_count_used` / `sheet_count_penalty`;
  - `overlap_penalty`;
  - `boundary_penalty`;
  - `compactness_penalty` vagy `compactness_proxy`;
  - `total_score` vagy `total_cost`.

### 5. Invalid-layout scoring

- Használd a meglévő Phase 1 helperöket, ahol lehet:

```text
rust/vrs_solver/src/optimizer/initializer.rs::bbox_from_placement
rust/vrs_solver/src/optimizer/candidates.rs::PlacedBbox::overlaps
rust/vrs_solver/src/sheet.rs::rect_inside_sheet_shape
rust/vrs_solver/src/item.rs::dims_for_rotation
```

- Ha `LayoutState`-ből scoringolsz, valós konverziós döntést dokumentálj.
- Az overlap és boundary penalty külön komponensben látszódjon.

### 6. Compactness proxy

- Legyen egyszerű, Phase 1-kompatibilis proxy, például bounding extent / used area jellegű mérőszám.
- Nem lehet erősebb, mint a validity penalty.
- Dokumentáld a korlátait: ez nem végső ipari nesting objective.

### 7. Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/jagua_optimizer_score_model_v1.md
```

Tartalmazza:

- score irányát;
- weight defaultokat;
- komponensek definícióját;
- validitási invariánsokat;
- ismert korlátokat;
- hogyan kapcsolódik JG-12/JG-13/JG-14-hez.

### 8. Smoke teszt

Hozd létre:

```text
scripts/smoke_jagua_score_model_v1.py
```

A smoke legalább ezeket bizonyítsa:

- Rust score unit testek PASS;
- invalid layout score-ja rosszabb, mint valid alternatíva;
- unplaced penalty működik;
- sheet count penalty működik;
- overlap/boundary penalty nagy súlyú;
- compactness proxy nem írja felül a validitást;
- score determinisztikus azonos állapotra;
- JG-10 repair smoke regresszió PASS, ha a környezet engedi.

### 9. Checklist és report

- Frissítsd a JG-11 task-specifikus checklistet.
- Frissítsd a globális progress checklist JG-11 szakaszát.
- Csak bizonyított pontot pipálj ki.
- A reportban legyen score breakdown példa és profile default evidence.

### 10. Repo gate

A futás végén futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
```

Task-specifikus minimum parancsok, ha a repo környezet engedi:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score
python3 scripts/smoke_jagua_repair_search_v1.py
python3 scripts/smoke_jagua_score_model_v1.py
```

## Acceptance criteria

- [ ] JG-10 dependency PASS + `JG-11_STATUS: READY` bizonyított.
- [ ] `ScoreModel V1` vagy ekvivalens score API implementálva a meglévő `score.rs` modulban.
- [ ] Score komponensek dokumentálva: placed area, unplaced penalty, sheet count, overlap/boundary penalty, compactness proxy.
- [ ] `ObjectiveBreakdown` outputban auditálható.
- [ ] Score weight defaultok dokumentálva.
- [ ] Invalid layout score-ja mindig rosszabb valid alternatívánál az erre készített tesztben.
- [ ] Unplaced penalty érdemben büntet.
- [ ] Sheet count penalty működik.
- [ ] Boundary/overlap penalty nagy súlyú.
- [ ] Compactness proxy nem írja felül a validitást.
- [ ] Score determinisztikus azonos állapotra.
- [ ] Profile default reportban szerepel.
- [ ] Score smoke tesztek PASS.
- [ ] Repo verify PASS és log mentve.
- [ ] A globális checklist JG-11 szakasza frissítve.
- [ ] Csak akkor szerepel a report végén `JG-12_STATUS: READY`, ha minden JG-11 gate PASS.

## Failure / rollback policy

- Ha JG-10 dependency hiányzik vagy nem PASS: `BLOCKED`, nincs optimizer kódmódosítás.
- Ha a score API a meglévő `score.rs` skeletonnal ütközik: dokumentált `REQUIRES_DECISION`, nincs duplikált modul.
- Ha invalid layout jobb score-t kap, mint valid layout: `FAIL`, nem `PASS_WITH_NOTES`.
- Ha compactness vagy sheet penalty validitást ír felül: `FAIL`.
- Ha verify környezeti okból futásképtelen: `REVISE` vagy `BLOCKED`, pontos loggal.

## Phase gate érintettség

JG-11 még nem zárja a Gate 1-et, de előfeltétele a JG-12 multi-sheet managernek és a JG-13/JG-14 mérési döntésnek. A score súlyrendszer későbbi tuningolható komponens, de az alap validitási hierarchia már JG-11-ben nem sérülhet.
