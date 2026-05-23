# Canvas — JG-10 `jagua_optimizer_t10_repair_search_loop_v1`

## Meta

- **Task ID:** JG-10
- **Slug:** `jagua_optimizer_t10_repair_search_loop_v1`
- **Phase:** Phase 1 / repair search
- **Dependency:** JG-09 — `jagua_optimizer_t09_exact_validation_bridge_and_metrics`
- **Primary output:** Sparrow-elvű, determinisztikus Repair Search V1 a Phase 1 rectangular / outer-only solverhez.
- **Package status:** ez a dokumentum a futtatható task-csomag része; nem maga az implementáció.

## Dependency gate

JG-10 csak akkor indítható, ha:

```text
codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
```

létezik, első sora `PASS`, és tartalmazza:

```text
JG-10_STATUS: READY
```

A friss package-generálási snapshotban ez teljesült. A runnernek ettől függetlenül futás elején újra ellenőriznie kell.

## Stratégiai háttér

A JG-08 létrehozta az initial construction placert, a JG-09 pedig lezárta az exact validation bridge-et. Ezután a Phase 1 solvernek már nem elég egyszerűen elhelyezési sorrendet lefuttatnia: kell egy javító mechanika, amely egy hibás vagy részben hibás állapotot determinisztikusan próbál legalizálni.

A JG-10 célja nem a végső ipari minőség vagy optimalizált kihasználtság. A cél az első működő repair-search szerkezet:

- hibák diagnosztikája: overlap vs boundary;
- hibás placementek eltávolítása vagy újrapozicionálása;
- move / reinsert / rotate jellegű próbák;
- időlimit és iterációs vagy stagnálási limit;
- determinisztikus futás azonos seed mellett;
- exact validatorral igazolt végső állapot.

## DISCOVERED_MISMATCH

A régi `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md` JG-10-et még `Irregular sheet provider` jellegű taskként említi. Az aktuális hivatalos task-bontás (`jagua_optimizer_canvas_yaml_runner_task_bontas.md`) és a progress checklist szerint:

```text
JG-10 = jagua_optimizer_t10_repair_search_loop_v1
```

**Resolution:** a JG-10 package az aktuális task-bontást és a JG-09 `JG-10_STATUS: READY` gate-et követi. Irregular/remnant sheet provider nincs JG-10 scope-ban.

## Valós kód audit megfigyelések a package-generáláskor

A friss snapshot alapján:

- `rust/vrs_solver/src/optimizer/mod.rs`
  - jelenleg exportálja: `candidates`, `initializer`, `moves`, `score`, `state`;
  - még nem exportál `repair` vagy `stopping` modult;
  - tartalmazza a régi row/cursor fallback `try_place_on_sheet()` segédet.
- `rust/vrs_solver/src/optimizer/moves.rs`
  - `CandidateMove` skeleton már létezik: `Place`, `Move`, `Reinsert`, `Rotate`;
  - jelenleg nincs move generation, legality check vagy application logic.
- `rust/vrs_solver/src/optimizer/state.rs`
  - `LayoutState`, `PlacedItem`, `UnplacedItem`, `PlacementTransform` skeleton létezik;
  - ez még belső optimizer state, nem publikus JSON contract.
- `rust/vrs_solver/src/optimizer/initializer.rs`
  - `build_initial_layout()` determinisztikus candidate-point construction placert ad;
  - `ConstructionDiagnostics` és `bbox_from_placement()` létezik;
  - `PlacedBbox` és `generate_candidates()` használható a Phase 1 rectangular repairhez.
- `rust/vrs_solver/src/optimizer/candidates.rs`
  - candidate point generálás és `PlacedBbox::overlaps()` elérhető;
  - rectangular Phase 1 esetben ez megfelelő alap a repair V1-hez.
- `rust/vrs_solver/src/adapter.rs`
  - Phase 1 profile: `jagua_optimizer_phase1_outer_only`;
  - jelenleg `build_initial_layout()` közvetlenül adja a placements/unplaced listát;
  - JG-10-ben csak Phase 1 branch bővíthető repairrel.
- `vrs_nesting/runner/vrs_solver_runner.py`
  - JG-09 után exact validator bridge ír `validation_status`, `validation_error`, `utilization` metát;
  - invalid output nem lehet successful.
- `scripts/smoke_jagua_exact_validation_bridge.py`
  - JG-09 regression smoke létezik;
  - JG-10-hez külön `scripts/smoke_jagua_repair_search_v1.py` szükséges.
- `rust/vrs_solver/Cargo.toml`
  - jelenleg nincs `rand` dependency; JG-10 determinisztikája lehetőleg stabil rendezéssel, ne új RNG-vel készüljön. Ha RNG kell, explicit `REQUIRES_DECISION` dokumentáció szükséges.

## Scope

Benne van:

- `rust/vrs_solver/src/optimizer/repair.rs` létrehozása;
- `rust/vrs_solver/src/optimizer/stopping.rs` létrehozása;
- `rust/vrs_solver/src/optimizer/moves.rs` bővítése MoveGenerator V1 logikával, ha a valós kód alapján ez a legjobb hely;
- `rust/vrs_solver/src/optimizer/mod.rs` frissítése az új modulok exportjához;
- Phase 1 rectangular/outer-only RepairEngine V1;
- boundary és overlap diagnosztika elkülönítése;
- hibás placement eltávolítása, reinsert/move/rotate próbák stabil sorrendben;
- time limit + iteration vagy stagnation limit;
- deterministic seed evidence;
- repair attempt/success/fail metrics a reportban vagy solver diagnosticsban;
- `scripts/smoke_jagua_repair_search_v1.py` létrehozása;
- cargo build/test + JG-08/JG-09 regression smoke + JG-10 smoke;
- task-specifikus checklist és globális progress checklist frissítése.

## Out of scope

Tilos JG-10-ben:

- JG-11 score model V1;
- simulated annealing, tabu, genetikus vagy nagy search framework;
- irregular/remnant sheet provider;
- hole nesting vagy cavity-prepack;
- új DXF intake/preflight feature;
- production UI/API módosítás;
- exact validator gyengítése vagy kikapcsolása;
- invalid layout successful státuszba engedése;
- silent geometry loss: holes, contours, item identity, quantity, transform vagy validation adat elvesztése;
- jagua-rs típusok kiszivárogtatása a publikus VRS JSON contractba.

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

- Olvasd el JG-09 reportját.
- Ha nincs `PASS` + `JG-10_STATUS: READY`, állj meg `BLOCKED` státusszal.
- Ellenőrizd, hogy JG-09 után a runner exact validation bridge és `scripts/smoke_jagua_exact_validation_bridge.py` létezik.

### 2. Repair data és diagnostics audit

- Auditáld a meglévő `LayoutState`, `CandidateMove`, `ObjectiveBreakdown`, `build_initial_layout()`, `generate_candidates()`, `bbox_from_placement()` elemeket.
- Határozd meg, hogy a RepairEngine belső állapota közvetlenül `Vec<Placement>/Vec<Unplaced>`-et kezeljen-e, vagy `LayoutState` konverziós réteget használjon.
- Dokumentáld a döntést a reportban.

### 3. StoppingPolicy V1

- Hozz létre `rust/vrs_solver/src/optimizer/stopping.rs` modult.
- Tartalmazzon legalább:
  - time limit;
  - max iteration vagy stagnation limit;
  - deterministic stop reason;
  - unit teszteket.
- A `time_limit_s` inputból származó limitet tiszteletben kell tartani. A repair belső limit lehet ennél kisebb, de nem lehet nagyobb.

### 4. MoveGenerator V1

- Bővítsd `moves.rs`-t vagy hozz létre kapcsolódó helper(eke)t a valós kódhoz illeszkedve.
- Legalább ezek legyenek kezelve:
  - translate/move meglévő placementre;
  - reinsert eltávolított/unplaced instance-re;
  - rotate allowed rotations alapján;
  - stabil, determinisztikus candidate sorrend.
- Ne adj hozzá nem dokumentált randomizálást. Azonos input + seed → azonos move sorrend és eredmény.

### 5. RepairEngine V1

- Hozz létre `rust/vrs_solver/src/optimizer/repair.rs` modult.
- Phase 1 rectangular/outer-only inputra dolgozz.
- Minimum követelmény:
  - overlap és boundary hibák külön diagnosztikája;
  - hibás placement eltávolítása vagy reinsert próbája;
  - ha javítható, valid layout felé mozdul;
  - ha nem javítható, explicit fail/unplaced/rollback történik;
  - nincs silent drop: minden instance vagy placed, vagy unplaced indokkal.
- Használd a meglévő exact/boundary/candidate segédeket: `rect_inside_sheet_shape`, `generate_candidates`, `PlacedBbox::overlaps`, `bbox_from_placement`, `dims_for_rotation`, `placement_anchor_from_rect_min`.

### 6. Adapter integration

- A Phase 1 branchben a `build_initial_layout()` után futtatható repair loopot integráld, ha a valós kód ezt indokolja.
- A publikus `SolverOutput` contract maradjon v1 kompatibilis: `contract_version`, `status`, `unsupported_reason`, `placements`, `unplaced`, `metrics`.
- Ha új repair metrics kerül be, backward-compatible módon történjen vagy report/smoke szinten dokumentáld.

### 7. Smoke és regresszió

- Hozd létre `scripts/smoke_jagua_repair_search_v1.py` scriptet.
- A smoke bizonyítsa:
  - mesterségesen hibás kezdőállapotból legalább egy repair unit vagy integration scenario valid állapotot ad;
  - overlap hiba és boundary hiba külön diagnosztizálható;
  - azonos seed determinisztikus;
  - time limit betartott;
  - invalid layout nem successful;
  - JG-08/JG-09 regression smoke-ok továbbra is PASS.

### 8. Report és checklist

- Frissítsd:
  - `codex/codex_checklist/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md`;
  - `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` JG-10 szakaszát.
- A report tartalmazza:
  - dependency evidence;
  - valós kód audit;
  - repair design döntés;
  - implemented files;
  - repair attempt/success/fail metrics;
  - smoke/test parancsok és kimenet-részletek;
  - git diff/status;
  - végső státusz.
- Csak akkor írd a végére:

```text
JG-11_STATUS: READY
```

ha JG-10 PASS, exact validatorral igazolt, repair smoke PASS és repo verify zöld.

## Kötelező ellenőrzések

Legalább ezek futtatandók, ha a környezet engedi:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_initial_construction.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
python3 scripts/smoke_jagua_repair_search_v1.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
```

Ha bármelyik dependency vagy környezeti okból elakad, dokumentáld külön. Nem lehet PASS, ha a szükséges bizonyíték nincs meg.

## Acceptance criteria

- JG-09 dependency PASS és `JG-10_STATUS: READY` ellenőrizve.
- `repair.rs` és `stopping.rs` létrejött vagy ha repo-konform módon más helyen készült, az reportban indokolt.
- MoveGenerator V1 tartalmaz translate/reinsert/rotate jellegű próbákat.
- RepairEngine V1 létezik és behatárolt Phase 1 rectangular scope-ban működik.
- StoppingPolicy tartalmaz time limitet és iterációs vagy stagnálási limitet.
- Mesterségesen hibás kezdőállapotból legalább egy repair smoke valid állapotot ad.
- Sikertelen repair esetén rollback, explicit fail vagy unplaced reason történik.
- Azonos seed determinisztikus eredményt ad.
- Boundary és overlap hibák külön diagnosztikában látszanak.
- Invalid layout nem mehet át successként.
- Report tartalmaz repair attempt/success/fail metrikát.
- JG-08 és JG-09 regresszió PASS.
- Repo verify PASS és log mentve.
- Globális progress checklist JG-10 szakasza frissítve.

## Failure / rollback policy

- Exact validator FAIL esetén a task nem lehet PASS.
- Ha repair nem tud javítani, ne rejtsd el a hibát: explicit fail/unplaced reason/diagnostics kell.
- Ha a JG-10 módosítás rontja JG-08 vagy JG-09 smoke-ot, reverteld vagy állj meg `REVISE/BLOCKED` státusszal.
- Ha a valós kód szerkezete eltér a canvasban feltételezettől, ne találd ki: dokumentáld `DISCOVERED_MISMATCH` vagy `REQUIRES_DECISION` blokkban.
