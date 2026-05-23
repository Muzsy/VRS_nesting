# JG-07 — jagua_optimizer_t07_layout_state_and_candidate_model

## Funkció

A JG-07 feladat célja a Phase 1 `jagua-rs` + saját optimizer láncban egy stabil, szerializálható optimizer **állapotmodell** és **candidate move skeleton** létrehozása.

Ez nem minőségi kereső, nem construction placer és nem repair loop. A feladat az optimizer belső modelljét készíti elő, hogy a későbbi JG-08 construction placer, JG-10 score model és JG-11/JG-12 search/repair lépések ne ad-hoc DTO-kon, hanem egy determinisztikus `LayoutState` modellen dolgozzanak.

A fő célok:

- `LayoutState` modell létrehozása vagy repo-konform definiálása;
- placed/unplaced állapot külön, veszteségmentes kezelése;
- `PlacementTransform` modell translation + rotation adattal;
- `CandidateMove` skeleton legalább place/move/reinsert/rotate alapokkal;
- `ObjectiveBreakdown` skeleton létrehozása;
- state diagnosztikai szerializálhatóság előkészítése;
- seed/determinism mezők előkészítése;
- output contract v1 kompatibilitás megtartása;
- state unit tesztek hozzáadása;
- invalid/partial state ne jelenhessen meg sikeres final layoutként.

## Source of truth

A feladat kizárólag repo-beli, ellenőrizhető forrásokra épülhet:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`
- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md`
- `docs/solver_io_contract.md`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/sheet.rs`
- `scripts/verify.sh`

Ha bármely kötelező tervdokumentum vagy a JG-06 dependency report hiányzik, a task `BLOCKED`. JG-07 implementációt csak JG-06 PASS után szabad indítani.

## Dependency státusz és gate

**Közvetlen dependency:** JG-06.

JG-06 akkor tekinthető teljesültnek, ha:

- `codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md` létezik;
- első sora `PASS`;
- tartalmazza: `JG-07_STATUS: READY`;
- a report szerint az item geometry store, instance determinism és rotation cache ellenőrzések PASS státuszúak;
- a repo verify PASS és log mentve van.

Ha ezek közül bármelyik nem igaz, a végrehajtó agent nem módosíthat production kódot, hanem `BLOCKED` riportot ír.

## Stratégiai háttér

A JG lánc Phase 1 célja egy kontrollált, outer-only rectangular multi-sheet alap létrehozása. JG-06 stabilizálta az item oldali modellt. JG-07 a következő réteg: olyan layout state és move representation kell, amely később alkalmas lesz candidate generálásra, score bontásra, keresésre, repair-re és diagnosztikára.

A jelenlegi solver még row/cursor baseline útvonalon dolgozik:

- `adapter::solve()` expandálja a sheets + instances listát;
- `optimizer::try_place_on_sheet()` közvetlenül `Instance` + `SheetCursor` alapján próbál elhelyezni;
- a final output továbbra is `io::SolverOutput` / `Placement` / `Unplaced` v1 JSON contract;
- nincs még külön layout state, move skeleton vagy objective breakdown.

JG-07-nek ezért úgy kell új belső modellt adnia, hogy a meglévő v1 output contract és a JG-05/JG-06 regressziók ne törjenek.

## Valós kód audit megfigyelések

A friss snapshotban:

- `rust/vrs_solver/src/optimizer/mod.rs`
  - létező modul, benne `SheetCursor` és `try_place_on_sheet()`.
  - nincs `state.rs`, `moves.rs`, `score.rs`.
  - JG-07-nek itt kell repo-konform módon bővítenie a modulstruktúrát.
- `rust/vrs_solver/src/item.rs`
  - JG-06 után létezik `ItemGeometryStore`, `ItemGeometryRecord`, `RotationCacheEntry` és deterministic `expand_instances()`.
  - `Instance` továbbra is a legacy v1 placer bemenete.
- `rust/vrs_solver/src/io.rs`
  - `Placement` és `Unplaced` a v1 output contract részei; ezeket nem szabad törni.
- `rust/vrs_solver/src/adapter.rs`
  - a solver fő útvonala még közvetlenül legacy baseline; JG-07 csak akkor nyúljon hozzá, ha a state modell diagnosztikai/konverziós helperét minimálisan be kell kötni.
- `rust/vrs_solver/src/sheet.rs`
  - `SheetShape` és sheet expansion létezik; a state sheet referenciái maradjanak stabil `sheet_index` alapúak.

## Scope

Benne van:

- `rust/vrs_solver/src/optimizer/state.rs` létrehozása;
- `rust/vrs_solver/src/optimizer/moves.rs` létrehozása;
- `rust/vrs_solver/src/optimizer/score.rs` létrehozása;
- `rust/vrs_solver/src/optimizer/mod.rs` repo-konform bővítése `pub mod ...` / `pub use ...` exportokkal, a meglévő baseline megtartásával;
- `LayoutState` modell placed/unplaced listákkal, sheet/seed/meta mezőkkel;
- `PlacementTransform { x, y, rotation_deg }` vagy ezzel ekvivalens modell;
- `CandidateMove` skeleton legalább `Place`, `Move`, `Reinsert`, `Rotate` változatokkal vagy explicit ekvivalenssel;
- `ObjectiveBreakdown` skeleton legalább count/sheet/penalty mezők előkészítésével;
- serde `Serialize` support a diagnosztikai state-hez, ha a repo dependency ezt lehetővé teszi;
- unit tesztek determinismre, szerializálhatóságra, placed/unplaced szeparációra, candidate move skeletonra;
- report és checklist frissítése.

Tilos:

- JG-08 construction placer implementálása;
- collision alapú candidate próbálgatás;
- score optimalizáló logika vagy sheet elimination;
- repair-search loop;
- irregular/remnant/cavity nesting;
- hole-os part Phase 1 elfogadása;
- final layout validator lazítása;
- v1 output JSON contract törése;
- invalid layout PASS-ként elfogadása;
- production UI/API módosítás.

## Kötelező hard rules

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

## Végrehajtási terv

### 1. Dependency preflight

- Olvasd el JG-06 reportját.
- Ha JG-06 report nincs, nem PASS, vagy nem jelöli `JG-07_STATUS: READY` állapotot, állj meg `BLOCKED` státusszal.
- A reportban dokumentáld a dependency evidence-t.

### 2. Optimizer boundary audit

- Vizsgáld meg `rust/vrs_solver/src/optimizer/mod.rs`, `item.rs`, `io.rs`, `adapter.rs`, `sheet.rs`, `geometry.rs` fájlokat.
- Dokumentáld, hogy a meglévő row/cursor baseline hogyan használja az `Instance`, `Placement`, `Unplaced`, `SheetShape` típusokat.
- Döntsd el, hogy a state model csak új modulokban él-e, vagy kell-e minimális adapter/mod.rs export igazítás.

### 3. Modulstruktúra

- Hozd létre a `state.rs`, `moves.rs`, `score.rs` modulokat az `optimizer` alatt.
- Frissítsd `optimizer/mod.rs`-t úgy, hogy a meglévő `SheetCursor` és `try_place_on_sheet()` továbbra is működjön.
- Ne mozgasd át nagy refaktorral a meglévő baseline-t, ha nem szükséges.

### 4. State modell

Minimum modellek:

- `PlacementTransform`: `x`, `y`, `rotation_deg`.
- `PlacedItem`: `instance_id`, `part_id`, `sheet_index`, `transform`.
- `UnplacedItem`: `instance_id`, `part_id`, `reason`.
- `LayoutState`: placed, unplaced, sheet_count vagy sheet index metadata, seed/determinism mező, optional objective breakdown.

Elvárás: placed/unplaced ne keveredjen, és sem item identity, sem transform adat ne vesszen el.

### 5. CandidateMove skeleton

Minimum skeleton:

- place új instance-t sheetre/transzformmal;
- move meglévő placed itemet új transzformra/sheetre;
- reinsert unplaced/placed instance-t;
- rotate meglévő vagy candidate item rotációját.

Ez csak modell/skeleton. Ne implementálj candidate generationt vagy collision próbálgatást.

### 6. ObjectiveBreakdown skeleton

Minimum:

- placed_count;
- unplaced_count;
- sheet_count_used;
- optional/placeholder penalty mezők;
- determinisztikusan serializálható diagnosztikai forma.

Ez még nem score optimalizáció.

### 7. Tesztek

Adj Rust unit teszteket a logika mellett:

- `PlacementTransform` serialization / roundtrip vagy JSON sanity;
- `LayoutState` placed/unplaced szeparáció;
- `CandidateMove` változatok létrehozhatók és serializálhatók/diagnosztikába vihetők;
- `ObjectiveBreakdown` skeleton count értékek stabilak;
- v1 output `Placement`/`Unplaced` contract nem változott regresszíven;
- deterministic ordering az azonos inputból épített state-nél.

### 8. Verifikáció

Futtasd és dokumentáld:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_item_geometry_store.py
python3 scripts/smoke_jagua_rectangular_sheet_provider.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
```

Ha a meglévő smoke script útvonal változik vagy hiányzik, ne találgass: dokumentáld `DISCOVERED_MISMATCH` vagy `BLOCKED` státusszal.

## Acceptance criteria

PASS csak akkor adható, ha:

- JG-06 dependency bizonyított;
- `LayoutState` létrejött vagy részletesen repo-kódban definiált;
- placed/unplaced külön kezelve van;
- `PlacementTransform` tartalmaz translation + rotation adatot;
- `CandidateMove` tartalmaz legalább place/move/reinsert/rotate alapot;
- `ObjectiveBreakdown` skeleton létrejött;
- state diagnosztikába szerializálható;
- output contract v1 kompatibilis maradt;
- state unit tesztek PASS;
- invalid/partial state nem jelenik meg sikeres final layoutként;
- determinism mezők / seed kezelés előkészítve;
- report tartalmaz rövid állapotmodellt vagy állapotdiagramot;
- repo verify PASS és log mentve;
- task-specifikus és globális checklist frissítve.

## Failure / rollback policy

- Ha a dependency hiányzik: `BLOCKED`, production kódmódosítás nélkül.
- Ha a serde vagy modulstruktúra ütközik a repo aktuális függőségeivel: `REQUIRES_DECISION`, részleges kód nem maradhat félkész állapotban.
- Ha bármely state teszt vagy repo verify fail: `REVISE` vagy `FAIL`, nem PASS.
- Ha final solver output változik váratlanul: revert vagy dokumentált minimal fix szükséges.

## Phase gate érintettség

JG-07 Phase 1 optimizer-core előkészítő gate. Sikeres lezárása után indítható JG-08:

```text
JG-08_STATUS: READY
```

Csak akkor írható ki, ha minden acceptance gate PASS.
