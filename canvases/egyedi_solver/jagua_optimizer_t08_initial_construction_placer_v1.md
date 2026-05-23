# JG-08 — jagua_optimizer_t08_initial_construction_placer_v1

## Funkció

A JG-08 feladat célja az első saját, determinisztikus **initial construction placer V1** bevezetése a `jagua-rs` alapú saját optimizer Phase 1 láncba.

Ez a task nem teljes minőségi optimizer, nem repair loop és nem score-search. A cél egy valid, rectangular, outer-only kiinduló layout létrehozása:

- item ordering: area/bbox alapú, determinisztikus tie-breakerekkel;
- candidate-point generálás rectangular sheetre;
- minden candidate ellenőrzése a `JaguaAdapter` collision/boundary rétegen keresztül;
- explicit `unplaced` kezelés, silent drop nélkül;
- exact validatorral ellenőrzött small/medium smoke fixture;
- candidate count és rejection reason alapdiagnosztika.

A JG-08 akkor sikeres, ha a small fixture minden partot validan elhelyez, a medium fixture legalább részleges, de **mindig valid** layoutot ad, és invalid layout nem kaphat successful státuszt.

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
- `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md` *(dependency gate; ha hiányzik, a végrehajtó agent BLOCKED státusszal álljon meg)*
- `docs/solver_io_contract.md`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/lib.rs`
- `rust/vrs_solver/src/main.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `rust/vrs_solver/src/sheet.rs`
- `vrs_nesting/nesting/instances.py`
- `scripts/smoke_jagua_adapter_contract.py`
- `scripts/smoke_jagua_rectangular_sheet_provider.py`
- `scripts/smoke_jagua_item_geometry_store.py`
- `scripts/verify.sh`

Ha bármely kötelező tervdokumentum vagy dependency report hiányzik, a task `BLOCKED`. JG-08 implementációt csak JG-04 és JG-07 PASS után szabad indítani.

## Dependency státusz és gate

**Közvetlen dependency:** JG-07 és JG-04.

JG-04 akkor tekinthető teljesültnek, ha:

- `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md` létezik;
- első sora `PASS`;
- a report tartalmazza `JG-05_STATUS: READY` vagy bizonyítja a JaguaAdapter contract PoC lezárását;
- `JaguaAdapter::check_rect_in_sheet` és `JaguaAdapter::check_polygon_collision` vagy ezek ekvivalense létezik.

JG-07 akkor tekinthető teljesültnek, ha:

- `codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md` létezik;
- első sora `PASS`;
- tartalmazza: `JG-08_STATUS: READY`;
- a layout state / placement transform / candidate move / objective breakdown skeleton ténylegesen létezik vagy a report pontosan dokumentálja az ekvivalens megoldást;
- state unit tesztek PASS.

**Jelen package-generálási megfigyelés:** a feltöltött snapshotban JG-04 report PASS, de JG-07 report/artifact nem található. Ezért a runner első lépése explicit dependency preflight. A tényleges JG-08 implementation nem kezdhető el, amíg JG-07 nincs PASS állapotban.

## Stratégiai háttér

A JG lánc Phase 1 célja egy valid rectangular multi-sheet solver felépítése hole nélkül. JG-05 rendezte a rectangular sheet provider és fixture pack alapjait, JG-06 létrehozta az item geometry store / rotation cache alapot, JG-07 pedig a layout state és candidate model előfeltételét adja. JG-08 az első olyan lépés, amely ténylegesen megpróbál layoutot építeni egy saját construction placerrel.

A feladat célja nem a végső ipari minőség, hanem egy megbízható, determinisztikus, valid kezdeti layout. Később a JG-09 exact validation bridge, JG-10 repair loop és JG-11 score model épít erre.

## Valós kód audit megfigyelések a package-generáláskor

A friss snapshot alapján:

- `rust/vrs_solver/src/adapter.rs`
  - `solve(input)` jelenleg `expand_sheets`, `expand_instances`, `SheetCursor` és `try_place_on_sheet()` útvonalon dolgozik.
  - A `jagua_optimizer_phase1_outer_only` profile hole-os partokra explicit `unsupported` státuszt ad.
  - JG-04 óta létezik `JaguaAdapter` boundary, benne `check_polygon_collision()` és `check_rect_in_sheet()`.
- `rust/vrs_solver/src/optimizer/mod.rs`
  - Jelenleg row/cursor jellegű `SheetCursor` és `try_place_on_sheet()` baseline van.
  - Nincs még `initializer.rs` vagy `candidates.rs` modul.
  - A jelenlegi placer csak bbox/row alapú, nem explicit candidate listát vizsgál.
- `rust/vrs_solver/src/item.rs`
  - JG-06 után létezik `ItemGeometryStore`, `ItemGeometryRecord`, `RotationCacheEntry` és `build_item_geometry_store()`.
  - `expand_instances()` stabil instance id formátuma: `part_id__0001`.
  - `normalize_allowed_rotations()` csak 0/90/180/270 fokot enged.
- `rust/vrs_solver/src/sheet.rs`
  - `SheetShape` és `rect_inside_sheet_shape()` létezik.
  - Rectangular és polygonal stock parse alapok készen vannak, de JG-08 scope rectangular Phase 1.
- `rust/vrs_solver/src/io.rs`
  - Output contract v1: `placements`, `unplaced`, `metrics`.
  - Nincs még candidate diagnostics mező a JSON outputban; ha ilyet JG-08 hozzáad, backward-compatible módon tegye, vagy csak report/smoke logban rögzítse.
- `vrs_nesting/nesting/instances.py`
  - `validate_multi_sheet_output(input_payload, output_payload)` exact validator ellenőrzi sheet-indexet, boundary-t, overlapot és spacinget.

## Scope

Benne van:

- construction placer V1 bevezetése feature flag/profile mögött vagy a Phase 1 profile útvonalon;
- determinisztikus item ordering: descending area, bbox méret, majd stable id tie-breaker;
- candidate point generálás rectangular sheetre;
- candidate dedupe és determinisztikus rendezés;
- minden candidate ellenőrzése sheet boundary és collision szempontból a `JaguaAdapter` contracton át;
- placement/unplaced állapot frissítése a JG-07 layout-state modell szerint;
- elhelyezhetetlen item explicit `unplaced` reasonnel;
- candidate count / rejection reason diagnosztika reportban vagy non-breaking output mezőben;
- `scripts/smoke_jagua_initial_construction.py` létrehozása;
- Rust unit tesztek és/vagy smoke tesztek small/medium fixture-re;
- exact validator PASS minden elfogadott placement listára;
- report és task checklist frissítése.

Tilos:

- JG-09 validation bridge teljes újratervezése;
- JG-10 repair-search loop;
- JG-11 score model;
- sheet elimination;
- irregular/remnant nesting;
- cavity-prepack vagy part-in-hole nesting;
- hole-os part Phase 1 elfogadása;
- invalid layout PASS-ként elfogadása;
- silent geometry loss: holes, contours, item identity, quantity, transform vagy validation adat eltűntetése;
- jagua-rs típusok kiszivárogtatása a publikus VRS output contractba;
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

- Olvasd el JG-04 és JG-07 reportját.
- Ha JG-04 vagy JG-07 report nincs, nem PASS, vagy JG-07 nem jelöli `JG-08_STATUS: READY` állapotot, állj meg `BLOCKED` státusszal.
- Dokumentáld a dependency evidence-t a reportban.

### 2. Layout-state és adapter audit

- Vizsgáld meg a JG-07-ben létrehozott `optimizer` state/move/score modulokat vagy dokumentált ekvivalenseket.
- Vizsgáld meg `adapter.rs`, `optimizer/mod.rs`, `item.rs`, `sheet.rs`, `geometry.rs`, `io.rs` aktuális állapotát.
- Döntsd el, hogy az initializer/candidate logika új modulokba kerül-e:
  - `rust/vrs_solver/src/optimizer/initializer.rs`
  - `rust/vrs_solver/src/optimizer/candidates.rs`
- Ha a JG-07 state modell nem létezik, ne kerülje meg a dependency-t; állj meg `BLOCKED` státusszal.

### 3. Candidate model és generation V1

Implementálj vagy dokumentálj olyan candidate-generátort, amely legalább:

- induló pontként használja a sheet origin pontját;
- meglévő placementek jobb és felső bbox sarkait candidate pointként hozzáadja;
- sheetenként és rotációnként determinisztikusan dedupe-ol;
- x/y/sheet/rotation alapján stabil sorrendet ad;
- limitálható vagy diagnosztizálható candidate countot ad;
- rejection reasonöket külön kezeli: `OUT_OF_SHEET`, `COLLISION`, `UNSUPPORTED_ROTATION`, `NO_CANDIDATE`.

### 4. Construction placer V1

- Rendezd az itemeket determinisztikusan: nagyobb area előre, majd bbox/max dimension, majd `part_id`, majd `instance_id`.
- Minden itemnél próbáld végig a candidate-eket és allowed rotationöket.
- Minden candidate-re:
  - számíts rotated bboxot;
  - ellenőrizd sheet boundaryt `JaguaAdapter::check_rect_in_sheet()` vagy ekvivalens adapter függvényen át;
  - ellenőrizd collisiont minden korábbi placementtel a `JaguaAdapter::check_polygon_collision()` vagy dokumentált rect-polygon adapteren át;
  - valid candidate esetén hozz létre placementet;
  - ha nincs valid candidate, add az itemet `unplaced` listára explicit reasonnel.
- A solver output contract maradjon v1 kompatibilis.

### 5. Exact validation és smoke

Hozd létre:

```text
scripts/smoke_jagua_initial_construction.py
```

A smoke legalább ellenőrizze:

- small fixture: minden part placed és `validate_multi_sheet_output` PASS;
- medium fixture: `status` lehet `ok` vagy `partial`, de `validate_multi_sheet_output` PASS;
- unplaced item nem tűnik el;
- invalid/overlap/out-of-sheet outputot a validator elutasít;
- determinism: azonos input + seed → azonos placement lista;
- candidate/rejection diagnosztika jelen van reportban vagy smoke outputban.

### 6. Kötelező parancsok

Futtasd és dokumentáld:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_initial_construction.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
```

Ha környezeti dependency miatt valami nem fut, dokumentáld pontosan, és ne adj tiszta PASS-t.

### 7. Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
```

A report első sora csak akkor legyen `PASS`, ha az implementation kész, JG-04/JG-07 dependency bizonyított, smoke/unit tesztek PASS, repo verify PASS, és checklist frissítve.

Ha minden rendben, a report végén szerepeljen:

```text
JG-09_STATUS: READY
```

## Acceptance criteria

- JG-04 és JG-07 dependency bizonyított.
- Initial item ordering dokumentálva és determinisztikus.
- Rectangular candidate point generation V1 implementálva.
- Jagua boundary/collision check minden candidate próbánál használva vagy bizonyított adapter-equivalent útvonalon fut.
- Elhelyezhetetlen item explicit `unplaced` státuszba kerül.
- Small fixture minden partot validan elhelyez, vagy a report bizonyítottan indokolja, miért BLOCKED.
- Medium fixture legalább részleges, de valid layoutot ad.
- Invalid layout soha nem kap successful PASS státuszt.
- Exact validator PASS az elfogadott placementekre.
- Candidate count / rejection reason legalább részben reportolva.
- Runtime/time limit nem végtelen ciklusos.
- Repo verify PASS és log mentve.

## Failure / rollback policy

- Ha JG-07 hiányzik vagy nem PASS: `BLOCKED`, implementáció nélkül.
- Ha bármely accepted placement exact validatorral invalid: `FAIL` vagy `REVISE`, nincs `JG-09_STATUS: READY`.
- Ha a candidate generation működik, de medium fixture túl gyenge: `REVISE`, metrikával és next-step javaslattal.
- Ha a meglévő row/cursor baseline sérül feature flag nélkül: rollback a JG-07 utáni állapotra.
- Ha új diagnosztikai mező törné a v1 output contractot: távolítsd el vagy tedd backward-compatible optional mezővé.

## Végső válasz formátuma

```text
JG08_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- ...
VERIFY:
- cargo build ...: PASS/FAIL/NOT_RUN
- cargo test ...: PASS/FAIL/NOT_RUN
- python3 scripts/smoke_jagua_initial_construction.py: PASS/FAIL/NOT_RUN
- ./scripts/verify.sh --report ...: PASS/FAIL/NOT_RUN
DEPENDENCIES:
- JG-04: PASS/FAIL/MISSING
- JG-07: PASS/FAIL/MISSING
CANDIDATE_MODEL:
- ...
VALIDATION:
- ...
NEXT:
- JG-09_STATUS: READY | NOT_READY
BLOCKERS:
- ...
```
