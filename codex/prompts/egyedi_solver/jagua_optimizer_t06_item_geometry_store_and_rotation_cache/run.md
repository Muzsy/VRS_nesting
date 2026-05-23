# Runner — JG-06 jagua_optimizer_t06_item_geometry_store_and_rotation_cache

## Feladat

A VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-06 feladatot: ItemGeometryStore, deterministic instance expansion és rotation cache bevezetése outer-only itemekhez.

Ez **implementation/audit task**, nem package-generation task. A cél az item oldali belső modell stabilizálása. Ne implementálj repair-search loopot, layout state modellt, új construction placer-t vagy sheet eliminationt.

## Kötelező bemenetek

Először olvasd el teljes egészében:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md
canvases/egyedi_solver/jagua_optimizer_task_index.md
codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md
codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
canvases/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t06_item_geometry_store_and_rotation_cache.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
```

Ha bármelyik kötelező tervdokumentum vagy task artifact hiányzik, állj meg `STATUS: BLOCKED` státusszal. Kivétel nincs a JG-05 report esetén: JG-06 nem indulhat JG-05 PASS nélkül.

## Dependency preflight

Mielőtt bármilyen implementációs fájlt módosítasz:

1. Ellenőrizd, hogy a JG-05 report létezik.
2. Ellenőrizd, hogy a JG-05 report első sora `PASS`.
3. Ellenőrizd, hogy a JG-05 report tartalmazza: `JG-06_STATUS: READY`.
4. Ellenőrizd, hogy a JG-05 report szerint a rectangular sheet provider és fixture pack exact validatorral bizonyított.

Ha ezek közül bármelyik nem igaz, ne implementálj. Frissítsd a JG-06 reportot `BLOCKED` státusszal, és írd le pontosan a hiányzó dependency evidence-t.

## Globális hard rules

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

## Scope

Benne van:

- item geometry store / equivalent belső modell;
- deterministic quantity expansion;
- instance id szabály;
- area/bbox számítás;
- allowed rotations normalization és stable ordering;
- 0/90/180/270 rotation cache;
- unsupported rotation explicit error/unsupported;
- exact vs proxy geometry separation dokumentálása;
- item-level unit tests vagy smoke;
- `scripts/smoke_jagua_item_geometry_store.py`;
- report és checklist frissítése.

Tilos:

- JG-07 layout state modell;
- JG-08 initial construction placer;
- repair-search / score model;
- irregular/remnant/cavity nesting;
- hole-os item Phase 1 elfogadása;
- validator lazítása;
- invalid layout PASS-ként elfogadása;
- production UI/API módosítás.

## Valós kód audit kiindulópont

Olvasd el és dokumentáld a reportban:

```text
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/sheet.rs
docs/solver_io_contract.md
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/verify.sh
```

Különösen ellenőrizd:

- hogyan működik most `Part`, `Instance`, `expand_instances()`;
- mit csinál `normalize_allowed_rotations()` és milyen orderinget ad;
- hol használja a placer a width/height + rotation helper logikát;
- van-e már polygon area vagy rotate helper `geometry.rs`-ben;
- hogy a JG-03 hole gate nem sérül-e;
- milyen smoke/validator útvonal használható új scripthez.

## Végrehajtási lépések

### 1. Goal YAML sanity

Validáld a goal YAML-t, ellenőrizd a nem üres `steps` listát és hogy nincs sandbox-specifikus útvonal.

### 2. ItemGeometryStore design döntés

A valós kód alapján hozz döntést:

- maradjon-e minden `item.rs`-ben, vagy szükséges új modul;
- a store csak bbox/proxy cache-t tartson-e most, vagy outer polygon point cache is kell;
- exact geometry hogyan marad meg akkor is, ha a Phase 1 placement még proxy-bbox alapú.

A döntést a reportban külön blokkban rögzítsd.

### 3. Implementáció

Implementáld minimum:

- stabil item geometry record;
- area/bbox helper;
- per-rotation cache entry;
- deterministic store builder a `Part` listából;
- deterministic instance expansion store-ból vagy a meglévő `expand_instances()` bizonyított megtartásával;
- unsupported rotation explicit error.

Ne törj backward compatibilityt: a meglévő solver input/output JSON contract maradjon v1 kompatibilis.

### 4. Tests / smoke

Adj Rust unit teszteket ott, ahol a logika él, és/vagy hozz létre smoke scriptet:

```text
scripts/smoke_jagua_item_geometry_store.py
```

A smoke tesztelje:

- same input → same instance summary;
- same input → same rotation summary;
- 0/90/180/270 bbox/cache correctness;
- duplicate rotations deterministic dedupe;
- unsupported rotation explicit failure.

### 5. Kötelező parancsok

Futtasd és dokumentáld:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_item_geometry_store.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
```

Ha környezeti dependency miatt valami nem fut, dokumentáld pontosan, és ne adj tiszta PASS-t.

### 6. Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
```

A report első sora csak akkor legyen `PASS`, ha az implementation kész, JG-05 dependency bizonyított, smoke/unit tesztek PASS, repo verify PASS, checklist frissítve.

Ha minden rendben, a report végén szerepeljen:

```text
JG-07_STATUS: READY
```

## Végső válasz formátuma

```text
JG06_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- ...
VERIFY:
- cargo build ...: PASS/FAIL/NOT_RUN
- cargo test ...: PASS/FAIL/NOT_RUN
- python3 scripts/smoke_jagua_item_geometry_store.py: PASS/FAIL/NOT_RUN
- ./scripts/verify.sh --report ...: PASS/FAIL/NOT_RUN
ITEM_MODEL_DECISION:
- ...
ROTATION_POLICY:
- ...
NEXT:
- JG-07_STATUS: READY | NOT_READY
BLOCKERS:
- ...
```
