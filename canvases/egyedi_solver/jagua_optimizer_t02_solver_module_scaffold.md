# JG-02 — jagua_optimizer_t02_solver_module_scaffold

## Funkció

A JG-02 feladat célja a jelenlegi monolitikus `rust/vrs_solver/src/main.rs` moduláris előkészítése **viselkedésváltozás nélkül**.

Ez architektúra/refaktor task, nem új optimizer. A kimenet célja, hogy a későbbi JG-03…JG-14 lépésekhez legyen tiszta Rust modulhatár: IO, geometria, sheet, item, adapter és optimizer/baseline placement. A jelenlegi solver output contractja, determinisztikája és validation-kompatibilitása nem változhat.

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
- `docs/egyedi_solver/jagua_optimizer_source_audit.md`
- a task szempontjából releváns valós Rust/Python/shell kód.

Ha bármely kötelező tervdokumentum hiányzik, a task `BLOCKED`.

## Dependency státusz

**Közvetlen dependency:** JG-01.

JG-01 kimenete alapján JG-02 indítható:

- `docs/egyedi_solver/jagua_optimizer_source_audit.md`
- JG-01 report státusza: `PASS`
- JG-01 audit vége: `JG-02_STATUS: READY`

Ha a helyi repóban ez nem igazolható, JG-02 nem kezdhető el.

## Stratégiai háttér

A master plan szerint a projekt nem kész Sparrow/SparrowGH solver-core-ra áll át, hanem egy `jagua-rs` collision / geometry backend + saját, ipari célú optimizer architektúrára. A JG-02 ennek a Rust oldali előkészítése: a jelenlegi row/cursor baseline solver marad, de a kódot modulhatárok közé kell rendezni, hogy később adapter, rectangular multi-sheet, exact validation, majd irregular/remnant és cavity-prepack fázisok bővíthetők legyenek.

## Jelenlegi kódállapot

A JG-01 source audit alapján:

- `rust/vrs_solver/src/main.rs` egyetlen monolit binary crate.
- `jagua-rs = "0.6.4"` dependency már van.
- A jelenlegi solver nem optimizer, hanem row/cursor alapú greedy baseline.
- Jelenlegi fő típusok:
  - `SolverInput`
  - `Stock`
  - `Part`
  - `PointInput`
  - `Point`
  - `SheetShape`
  - `SolverOutput`
  - `Placement`
  - `Unplaced`
  - `Metrics`
  - `Instance`
  - `SheetCursor`
  - `Rect`
- Jelenlegi fő függvények:
  - CLI/input: `parse_args()`
  - IO/DTO parsing: serde DTO-k, JSON read/write a `main()`-ben
  - geometry: `point_from_input()`, `polygon_bbox()`, `to_jag_point()`, `to_jag_polygon()`, `rect_corners()`, `rect_edges()`, `jag_edge_from_points()`
  - sheet: `stock_to_shape()`, `expand_sheets()`, `rect_inside_sheet_shape()`
  - item: `normalize_allowed_rotations()`, `dims_for_rotation()`, `rotated_bbox_min_offset()`, `placement_anchor_from_rect_min()`, `can_fit_any_stock()`, `expand_instances()`
  - placement baseline: `try_place_on_sheet()`
  - orchestration: `main()`
- `scripts/check.sh` tartalmazza a vrs_solver build + validator + determinism smoke belépési pontot.
- `vrs_nesting/runner/vrs_solver_runner.py` és `vrs_nesting/nesting/instances.py` a Python oldali runner + exact validation anchor.

## Task scope

### Benne van

- Repo-szabályok és JG tervdokumentáció újraolvasása.
- JG-02 task pontos kinyerése a task bontásból és checklistből.
- A jelenlegi `rust/vrs_solver/src/main.rs` viselkedésének baseline dokumentálása.
- Modulstruktúra kialakítása viselkedésváltozás nélkül:
  - `rust/vrs_solver/src/io.rs`
  - `rust/vrs_solver/src/geometry.rs`
  - `rust/vrs_solver/src/sheet.rs`
  - `rust/vrs_solver/src/item.rs`
  - `rust/vrs_solver/src/adapter.rs`
  - `rust/vrs_solver/src/optimizer/mod.rs`
- `rust/vrs_solver/src/main.rs` szerepének szűkítése CLI/orchestration rétegre.
- Unit tesztek áthelyezése vagy megtartása úgy, hogy továbbra is lefussanak.
- Baseline output és refaktor utáni output szemantikai összehasonlítása a meglévő smoke inputokon.
- `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` futtatása.
- Standard repo verify wrapper futtatása.
- Task report, verify log, task checklist és globális progress checklist frissítése.

### Nincs benne

- Nem szabad új optimizer algoritmust implementálni.
- Nem szabad `jagua-rs` magasabb szintű API-t bekötni. Ez JG-04 scope.
- Nem szabad Phase 1 outer-only hole gate-et implementálni. Ez JG-03 scope.
- Nem szabad IO contractot kompatibilitást törően módosítani.
- Nem szabad `Cargo.toml` dependencyt, feature-t vagy verziót módosítani, kivéve ha a task közben bizonyított blocker miatt explicit `REQUIRES_DECISION` keletkezik.
- Nem szabad Python runner/adapter viselkedést módosítani, kivéve ha csak report/checklist bizonyíték kell.
- Nem szabad cavity-prepack, result normalizer, DXF import/export vagy API runtime kódot módosítani.

## Kötelező globális invariánsok

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

## Tervezett modulhatárok

### `io.rs`

Javasolt tartalom:

- serde DTO-k:
  - `SolverInput`
  - `SolverOutput`
  - `Placement`
  - `Unplaced`
  - `Metrics`
- JSON-hoz kötött input/output típusok, ha szükséges.
- Contract-kompatibilis mezőnevek változatlanul.

Nem cél: IO contract bővítése vagy mezőátnevezés.

### `geometry.rs`

Javasolt tartalom:

- `PointInput`
- `Point`
- `Rect`
- `point_from_input()`
- `polygon_bbox()`
- `to_jag_point()`
- `to_jag_polygon()`
- `jag_edge_from_points()`
- `rect_corners()`
- `rect_edges()`
- geometriához kötött helper tesztek.

Nem cél: új polygon engine vagy NFP implementáció.

### `sheet.rs`

Javasolt tartalom:

- `Stock`
- `SheetShape`
- `stock_to_shape()`
- `expand_sheets()`
- `rect_inside_sheet_shape()`

A sheet expand order és `sheet_index` mapping nem változhat.

### `item.rs`

Javasolt tartalom:

- `Part`
- `Instance`
- `normalize_allowed_rotations()`
- `dims_for_rotation()`
- `rotated_bbox_min_offset()`
- `placement_anchor_from_rect_min()`
- `can_fit_any_stock()`
- `expand_instances()`

A jelenlegi allowed rotations policy nem változhat: csak `0`, `90`, `180`, `270`.

### `adapter.rs`

Javasolt tartalom:

- Baseline solver API, például `solve(input: SolverInput) -> Result<SolverOutput, String>`.
- A solver orchestration legyen main-től elkülönítve, de backend-adapter bővítésre később alkalmas.
- Jagua-specifikus magasabb szintű adapter még nem cél.

### `optimizer/mod.rs`

Javasolt tartalom:

- A jelenlegi row/cursor baseline placement mechanika.
- `SheetCursor`
- `try_place_on_sheet()`
- későbbi optimizer-loophoz minimális modulhely.

Nem cél: score model, candidate generation, SA, repair loop, Sparrow-style search.

### `main.rs`

A refaktor után a `main.rs` maradjon:

- CLI argumentum feldolgozás;
- input fájl olvasás;
- JSON parse;
- `adapter::solve()` vagy ekvivalens belső solver API hívása;
- output JSON írás;
- hibák visszaadása `Result<(), String>` formában.

## DISCOVERED_MISMATCH / REQUIRES_DECISION

A task bontás `Érintett fókusz` része említi a `validation` modult is, de a JG-02 hivatalos output listája nem tartalmazza ezt:

```text
rust/vrs_solver/src/validation.rs
```

Ezért a default megoldás:

- **Ne hozz létre `validation.rs` fájlt JG-02-ben**, hacsak a futtató agent előbb nem dokumentálja és nem frissíti explicit módon a YAML outputs listát.
- A validációs fókuszt JG-02-ben a meglévő exact validation anchorok megőrzése és a smoke/validator futtatása jelenti.
- Ha a refaktor során mégis önálló `validation.rs` szükséges, a reportban `REQUIRES_DECISION` blokkot kell nyitni, és a YAML-t előbb módosítani kell az AGENTS.md output szabálya szerint.

## Viselkedésmegőrzési követelmények

JG-02 csak akkor lehet PASS, ha a refaktor után:

- a solver binary buildel;
- a meglévő input contract változatlanul elfogadott;
- a meglévő output contract változatlan;
- a `placements`, `unplaced`, `metrics` mezők szemantikailag változatlanok a smoke inputokon;
- az instance-id képzés és rendezés stabil;
- a `sheet_index` szemantika változatlan;
- a stock quantity expand sorrend változatlan;
- a 0/90/180/270 rotáció kezelés változatlan;
- a hole-aware sheet boundary check nem gyengül;
- nincs silent geometry loss;
- az exact final validator PASS az elfogadott layoutokra;
- a determinism hash smoke stabil marad.

Byte-for-byte output azonosság előny, de ha a JSON whitespace vagy field order miatt eltérés van, akkor normalizált JSON szemantikai összehasonlítás is elfogadható. Ezt a reportban dokumentálni kell.

## Ajánlott baseline módszer

A refaktor előtt:

1. Építsd a jelenlegi binaryt:

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
```

2. Futtasd a meglévő `scripts/check.sh` vrs_solver smoke inputját vagy a `vrs_nesting.runner.vrs_solver_runner` útvonalat.
3. Mentsd a baseline `solver_output.json`-t ideiglenes munkaterületre vagy a reportban dokumentált helyre.
4. Refaktor után futtasd ugyanazt az inputot.
5. Hasonlítsd össze normalizált JSON-ként:
   - `contract_version`
   - `status`
   - `placements`
   - `unplaced`
   - `metrics`
6. Futtasd a meglévő final validátort:

```bash
python3 scripts/validate_nesting_solution.py --run-dir <run_dir>
```

7. Futtasd a teljes repo gate-et:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md
```

Ha a local környezet dependency miatt nem tudja futtatni a teljes gate-et, a blocker pontos loggal dokumentálandó. PASS ilyen esetben csak akkor adható, ha a repo saját futtatási környezetében zöld verify bizonyíték is rendelkezésre áll.

## Érintett fájlok

### Implementációs outputok

- `rust/vrs_solver/src/main.rs`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/sheet.rs`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`

### Dokumentációs / Codex outputok

- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.verify.log`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`

## Failure / rollback policy

- Ha a refaktor után bármely smoke vagy validator eltér, állítsd vissza az érintett Rust modulváltoztatásokat, és jelöld `REVISE` vagy `BLOCKED`.
- Ha a refaktor túl nagy diffé nő, bontsd kisebb rész-taskokra és jelöld `REQUIRES_DECISION`.
- Ha a main.rs viselkedésének baseline-ja nem mérhető, ne folytasd vakon a refaktort.
- Ha `cargo build` nem megy át, nincs PASS.
- Ha repo verify nem fut vagy piros, nincs tiszta PASS, kivéve ha az ok explicit környezeti blocker, és a production diff ettől függetlenül bizonyítottan buildel egy megfelelő környezetben.

## Acceptance criteria

- [ ] JG-01 dependency PASS és `JG-02_STATUS: READY` igazolt.
- [ ] Repo szabályfájlok újraolvasva.
- [ ] JG-02 taskdefiníció és checklist pontok kinyerve.
- [ ] `main.rs` baseline viselkedése dokumentálva.
- [ ] Modulstruktúra kialakítva az engedélyezett output fájlokon belül.
- [ ] `main.rs` CLI/orchestration szerepre szűkítve.
- [ ] IO contract kompatibilitás nem törött.
- [ ] Normalizált output szemantikailag változatlan a smoke inputokon.
- [ ] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [ ] Relevant Rust unit tests / cargo test PASS, ha vannak.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md` lefutott, log mentve.
- [ ] Task report tartalmaz diff összefoglalót és NO/YES viselkedésváltozás táblát.
- [ ] Task checklist és globális progress checklist frissítve bizonyíték alapján.
- [ ] JG-03 indíthatósága explicit megjelölve.

## Phase gate érintettség

JG-02 a Gate 0 része. JG-02 után a Gate 0 még nem zárható teljesen, de JG-03 előfeltételei akkor tisztának jelölhetők, ha:

- JG-02 PASS;
- nincs build/licenc/API showstopper;
- a modularizált Rust solver továbbra is valid outputot ad;
- a JG-03 outer-only contract/hole gate implementációs pontjai az új modulhatárok alapján egyértelműek.
