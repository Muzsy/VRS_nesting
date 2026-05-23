# JG-06 — jagua_optimizer_t06_item_geometry_store_and_rotation_cache

## Funkció

A JG-06 feladat célja a Phase 1 `jagua-rs` + saját optimizer láncban egy stabil **ItemGeometryStore**, determinisztikus **instance expansion**, és 0/90/180/270 fokos **rotation cache** bevezetése outer-only polygonokra.

Ez nem minőségi kereső, nem repair loop, és nem teljes optimizer. A feladat az item oldali adatmodellt stabilizálja, hogy a későbbi JG-07 layout-state és JG-08 construction placer ne közvetlenül nyers `Part` DTO-kon és ad-hoc bbox számításon dolgozzon.

A fő célok:

- stabil, auditálható `instance_id` szabály és quantity expansion;
- `Part` → item geometry store normalizálás;
- outer-only exact/proxy geometria külön kezelése, silent geometry loss nélkül;
- area és bbox számítás rögzítése;
- allowed rotation ordering determinisztikussá tétele;
- 0/90/180/270 fokos rotated proxy geometry cache;
- unsupported rotációk explicit hibája;
- ugyanarra az inputra azonos instance lista és rotation ordering.

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
- `codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md` *(dependency gate; ha hiányzik, a végrehajtó agent BLOCKED státusszal álljon meg)*
- `docs/solver_io_contract.md`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `rust/vrs_solver/src/sheet.rs`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/nesting/instances.py`
- `scripts/verify.sh`

Ha bármely kötelező tervdokumentum vagy dependency report hiányzik, a task `BLOCKED`. JG-06 implementációt csak JG-05 PASS után szabad indítani.

## Dependency státusz és gate

**Közvetlen dependency:** JG-05.

JG-05 akkor tekinthető teljesültnek, ha:

- `codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md` létezik;
- első sora `PASS`;
- tartalmazza: `JG-06_STATUS: READY` vagy ezzel ekvivalens következő-task jelzést;
- a rectangular sheet provider és fixture pack bizonyítottan PASS;
- a valid rectangular fixtures exact validatorral ellenőrizve vannak.

**Jelen package-generálási megfigyelés:** a feltöltött snapshotban JG-05 report/artifact nem található. Ezért a runner első lépése explicit dependency preflight. A tényleges JG-06 implementation nem kezdhető el, amíg JG-05 nincs PASS állapotban.

## Stratégiai háttér

A JG lánc Phase 1 célja egy kontrollált, outer-only rectangular multi-sheet alap kiépítése, mielőtt minőségi keresés, repair loop, score model és későbbi irregular/cavity képességek érkeznek. Ehhez az item oldali adatmodellnek reprodukálhatónak kell lennie.

A jelenlegi `item.rs` már tartalmaz néhány fontos előkészítést:

- `Part` DTO: `id`, `width`, `height`, `quantity`, `allowed_rotations_deg`, hole/outer geometry mezők;
- `part_has_holes()` Phase 1 gate-hez;
- `normalize_allowed_rotations()` csak 0/90/180/270 fokot enged;
- `dims_for_rotation()`, `rotated_bbox_min_offset()`, `placement_anchor_from_rect_min()`;
- `Instance` és `expand_instances()` determinisztikus, instance_id szerinti rendezéssel.

JG-06 ezt szervezi tovább olyan item geometry store/cache modellé, amelyet JG-07/JG-08 már stabil belső modellként használhat.

## Valós kód audit megfigyelések

A snapshotban a JG-03 utáni fő kódhelyzet:

- `rust/vrs_solver/src/item.rs`
  - `Part` már tartalmaz hole és outer mezőket `serde_json::Value` formában.
  - `expand_instances(parts)` jelenleg minden partnál `part.id__0001` formátumú `instance_id`-t készít, majd lexikografikusan rendez.
  - `normalize_allowed_rotations(raw)` jelenleg megőrzi az input sorrend első előfordulásait; JG-06-nak el kell döntenie és dokumentálnia kell, hogy a stabil ordering input-sorrend alapú vagy canonical sorted ordering.
  - `dims_for_rotation()` és anchor helper csak bbox/proxy logikát kezel, nem teljes polygon rotációt.
- `rust/vrs_solver/src/geometry.rs`
  - `Point`, `Rect`, bbox és jagua konverziós helper létezik.
  - Nincs még általános rotate polygon helper vagy area számítás.
- `rust/vrs_solver/src/adapter.rs`
  - A solver még közvetlenül `expand_instances()` + row/cursor baseline útvonalon dolgozik.
- `rust/vrs_solver/src/optimizer/mod.rs`
  - `try_place_on_sheet()` az `Instance` width/height + rotation listából számít bboxot.
  - JG-06 után a későbbi taskoknak célszerű rotation cache entryre támaszkodniuk, de JG-06-ban nem kötelező átírni a placer működését.
- `docs/solver_io_contract.md`
  - Már rögzíti az `allowed_rotations_deg` támogatott értékeit és a Phase 1 outer-only policyt.

## Scope

Benne van:

- `ItemGeometryStore` vagy ezzel ekvivalens belső modell létrehozása;
- `ItemGeometry` / item definition és `ItemInstance` / instance modell pontosítása;
- deterministic quantity expansion, instance id és ordering szabály dokumentálása;
- area és bbox számítás implementálása vagy pontosítása;
- allowed rotations normalizálás és ordering policy rögzítése;
- 0/90/180/270 fokos rotated proxy geometry cache;
- unsupported rotációk explicit hiba/státusz útja;
- exact geometry külön megőrzésének dokumentálása, még akkor is, ha a Phase 1 placer továbbra is proxy bboxot használ;
- `scripts/smoke_jagua_item_geometry_store.py` létrehozása;
- Rust unit tesztek és/vagy smoke teszt az item store/rotation cache determinisztikára;
- report és task checklist frissítése.

Tilos:

- új construction placer vagy repair-search implementáció;
- sheet elimination;
- score model;
- irregular/remnant nesting;
- cavity-prepack vagy part-in-hole nesting;
- hole-os part Phase 1 elfogadása;
- validator lazítása;
- invalid layout PASS-ként elfogadása;
- jagua-specifikus típusok kiszivárogtatása a publikus optimizer modellbe;
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

- Olvasd el JG-05 reportját.
- Ha JG-05 report nincs, nem PASS, vagy nem jelöli `JG-06_STATUS: READY` állapotot, állj meg `BLOCKED` státusszal.
- A reportban dokumentáld a dependency evidence-t.

### 2. Item model audit

- Vizsgáld meg `rust/vrs_solver/src/item.rs`, `geometry.rs`, `io.rs`, `adapter.rs`, `optimizer/mod.rs` fájlokat.
- Dokumentáld, hogy a jelenlegi `Part`, `Instance`, rotation helper és placer mely mezőkre támaszkodik.
- Döntsd el, hogy a cache új típusai `item.rs`-ben maradnak-e, vagy külön belső modul szükséges. Új fájlt csak akkor hozz létre, ha a YAML outputs listája és a repo mintái ezt engedik; ellenkező esetben `item.rs`-ben dolgozz.

### 3. ItemGeometryStore modell

Vezess be vagy dokumentálj egy belső, stabil store modellt, amely legalább ezeket kezeli:

- part id;
- quantity;
- base width/height;
- base bbox;
- area;
- allowed rotations canonical/stable listája;
- exact outer geometry, ha a bemenetből rendelkezésre áll;
- proxy geometry / bbox representation;
- per-rotation cache entry.

Ha a teljes polygon rotation még túl korai, a Phase 1 proxy cache lehet bbox-alapú, de ezt explicit dokumentálni kell. Exact geometry mező nem veszhet el.

### 4. Rotation cache policy

Rögzítsd és implementáld:

- támogatott rotációk: 0, 90, 180, 270;
- unsupported rotáció explicit `Err(...)` vagy unsupported státusz, nem silent drop;
- duplicate rotáció determinisztikus dedupe;
- ordering policy: canonical sorted `[0,90,180,270]` vagy input-order-preserving; a döntést reportban indokolni kell;
- minden rotation cache entry tartalmazza a rotated bbox dimenziót és anchor/min-offset információt, ha a jelenlegi placer ezt igényli.

### 5. Instance expansion determinism

Bizonyítsd teszttel vagy smoke-kal:

- ugyanaz az input ugyanazt az instance listát adja;
- instance id szabály stabil, például `part_id__0001`;
- quantity expansion sorrend dokumentált;
- több part esetén az ordering deterministic és tie-breaker dokumentált;
- area/bbox számítás stabil.

### 6. Smoke script

Hozd létre:

```text
scripts/smoke_jagua_item_geometry_store.py
```

A script legalább ezeket ellenőrizze:

- simple rectangle part quantity expansion;
- allowed rotation dedupe/order;
- 0/90/180/270 bbox/cache dimenziók;
- unsupported rotation explicit hiba;
- azonos inputból két build/run azonos instance és rotation summaryt ad;
- ha solver futtatást is használ, valid layout esetén exact validator PASS.

A smoke ne hagyjon hátra felesleges repo-szennyezést.

### 7. Rust/Python módosítások

Elsődleges érintett fájlok:

- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/io.rs`

Lehetséges, de csak szükség esetén:

- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/nesting/instances.py`

Ne írd át a placer algoritmust minőségi optimalizálás céljából. A baseline output validitását meg kell őrizni.

### 8. Tesztelés

Minimum parancsok, ha a repo és környezet támogatja:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_item_geometry_store.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
```

Ha valamelyik parancs környezeti dependency miatt nem fut, ezt különítsd el a task hibáitól. PASS csak akkor adható, ha a kötelező JG-06 funkcionális evidence megvan.

## Acceptance criteria

JG-06 akkor PASS, ha:

- JG-05 dependency PASS evidence dokumentált;
- Item instance id szabály dokumentált;
- quantity expansion determinisztikus és tesztelt;
- area/bbox számítás rögzítve;
- allowed rotations ordering stabil és dokumentált;
- 0/90/180/270 rotációk regresszió nélkül működnek;
- unsupported rotáció explicit hibát vagy unsupported státuszt ad;
- rotated proxy geometry cache működik;
- exact geometry külön megőrzése dokumentált;
- azonos input + seed azonos instance listát ad;
- unit tesztek vagy smoke tesztek PASS;
- repo verify PASS és verify log mentve;
- task-specifikus checklist és globális progress checklist JG-06 része frissítve;
- report végén egyértelmű: `JG-07_STATUS: READY` vagy `NOT_READY`.

## Failure / rollback policy

- Ha JG-05 dependency hiányzik vagy nem PASS: `BLOCKED`, implementáció nélkül.
- Ha unsupported rotation silent droppal kezelődik: `FAIL`.
- Ha instance ordering nondeterministic: `FAIL`.
- Ha exact geometry elveszik vagy nincs dokumentálva a proxy/exact különbség: `FAIL`.
- Ha a baseline rectangular smoke törik: `REVISE` vagy `FAIL` a hiba súlyától függően.
- Rollback csak a YAML outputs listájában szereplő fájlokra korlátozódhat.
