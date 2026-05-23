# Runner prompt — JG-08 jagua_optimizer_t08_initial_construction_placer_v1

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-08 taskot:

```text
JG-08 — jagua_optimizer_t08_initial_construction_placer_v1
```

Ez a task az első saját initial construction placer V1 implementációja a jagua-rs alapú Phase 1 rectangular, outer-only solverláncban.

Ne készíts általános tervet. Olvasd el a megadott repo fájlokat, ellenőrizd a dependency-ket, implementáld a scope-ot, futtasd a teszteket, frissítsd a checklistet és reportot.

---

## Kötelező dependency preflight

Mielőtt bármilyen kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
```

JG-04 feltételek:

- report létezik;
- első sora `PASS`;
- a JaguaAdapter contract PoC ténylegesen létezik az aktuális kódban.

JG-07 feltételek:

- report létezik;
- első sora `PASS`;
- tartalmazza: `JG-08_STATUS: READY`;
- a layout-state / placement transform / candidate move / objective breakdown skeleton ténylegesen létezik, vagy a report pontosan dokumentálja az ekvivalens megoldást;
- state unit tesztek PASS.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-04/JG-07
```

Ilyenkor ne implementálj JG-08 kódot, csak frissítsd a JG-08 reportot a dependency evidence-szel.

---

## Kötelező olvasmányok

Olvasd el:

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
canvases/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t08_initial_construction_placer_v1.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
```

A `run.md` és a canvas az irányadó. Ha a valós kód és a terv eltér, ne találgass: dokumentáld `DISCOVERED_MISMATCH` vagy `REQUIRES_DECISION` blokkban.

---

## Valós kód audit

Vizsgáld meg az aktuális kódot:

```text
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/lib.rs
rust/vrs_solver/src/main.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/sheet.rs
vrs_nesting/nesting/instances.py
scripts/smoke_jagua_adapter_contract.py
scripts/smoke_jagua_rectangular_sheet_provider.py
scripts/smoke_jagua_item_geometry_store.py
```

Külön ellenőrizd:

- hol van JG-07 után a `LayoutState` vagy ekvivalens state modell;
- hogyan reprezentálódik a `PlacementTransform`;
- van-e már `CandidateMove` vagy ekvivalens;
- hogyan használható JG-06 `ItemGeometryStore` és `RotationCacheEntry`;
- hol fut a Phase 1 hole gate;
- hol lehet bekötni a construction placer V1-et úgy, hogy a v1 output contract ne törjön.

---

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

---

## Implementációs scope

Implementáld a JG-08 initial construction placer V1-et.

Expected touched files, ha a dependency-k teljesülnek:

```text
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/main.rs
rust/vrs_solver/src/io.rs
scripts/smoke_jagua_initial_construction.py
codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
```

Csak akkor módosíts `io.rs`-t, ha backward-compatible módon szükséges. A meglévő v1 output mezőknek működniük kell:

```text
contract_version
status
placements
unplaced
metrics
```

### Candidate generation V1

Minimum stratégia:

- sheet origin candidate: `(0, 0)` minden sheetre;
- minden meglévő placement rotated bboxának jobb alsó / jobb oldali és felső pontjai candidate-ként;
- candidate dedupe EPS-toleranciával vagy deterministic key-jel;
- candidate sorting: `sheet_index`, `y`, `x`, `rotation_deg`, majd stable id;
- rejection reason gyűjtés: `OUT_OF_SHEET`, `COLLISION`, `UNSUPPORTED_ROTATION`, `NO_CANDIDATE`.

### Item ordering

Minimum determinisztikus ordering:

1. nagyobb area előre;
2. nagyobb max rotated bbox dimension előre;
3. `part_id`;
4. `instance_id`.

A policyt dokumentáld a reportban.

### Candidate validation

Minden candidate-re:

- számítsd a rotated bboxot JG-06 helper/cache alapján;
- boundary check: `JaguaAdapter::check_rect_in_sheet()` vagy dokumentált ekvivalens;
- collision check: `JaguaAdapter::check_polygon_collision()` vagy dokumentált rect-polygon adapter;
- valid candidate esetén placement létrejön;
- ha nincs valid candidate, explicit `Unplaced { reason: ... }`.

Az itemeket tilos eltűntetni. `placed_count + unplaced_count` egyezzen az instance counttal.

---

## Teszt és smoke elvárás

Hozd létre:

```text
scripts/smoke_jagua_initial_construction.py
```

A smoke script illeszkedjen a meglévő smoke mintákhoz, és használja:

```text
vrs_nesting.nesting.instances.validate_multi_sheet_output
```

Minimum ellenőrzések:

- small fixture: minden part placed, exact validator PASS;
- medium fixture: `status in (ok, partial)`, exact validator PASS;
- unplaced item nem tűnik el;
- determinism: azonos input + seed → azonos placement lista;
- negatív validator check: mesterséges overlap vagy invalid sheet_index elutasítva;
- candidate/rejection diagnosztika legalább a reportban dokumentálva.

---

## Kötelező parancsok

Futtasd:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_initial_construction.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
```

Ha bármelyik nem fut le környezeti okból, dokumentáld pontosan. Ne adj PASS-t, ha az exact validator vagy repo verify nem bizonyított.

---

## Report és checklist

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
```

A report tartalmazza:

- dependency evidence;
- valós kód audit;
- candidate model döntés;
- item ordering policy;
- boundary/collision check evidence;
- smoke/test eredmények;
- exact validator evidence;
- git diff/status;
- risks/blockers.

A report első sora csak akkor legyen `PASS`, ha minden acceptance criterion teljesült és a repo verify zöld.

Ha minden rendben, a report végén szerepeljen:

```text
JG-09_STATUS: READY
```

---

## Végső válasz formátuma

```text
JG08_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- ...
VERIFY:
- cargo build --manifest-path rust/vrs_solver/Cargo.toml: PASS/FAIL/NOT_RUN
- cargo test --manifest-path rust/vrs_solver/Cargo.toml: PASS/FAIL/NOT_RUN
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
