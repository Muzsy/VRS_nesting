# Runner — JG-07 jagua_optimizer_t07_layout_state_and_candidate_model

## Feladat

A VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-07 feladatot: optimizer `LayoutState`, `PlacementTransform`, `CandidateMove` és `ObjectiveBreakdown` skeleton bevezetése.

Ez **implementation/audit task**, nem package-generation task. A cél az optimizer állapotmodell stabilizálása. Ne implementálj construction placer-t, candidate generationt, jagua collision próbálgatást, score optimalizálást, repair loopot vagy sheet eliminationt.

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
codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md
canvases/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t07_layout_state_and_candidate_model.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
```

Ha bármelyik kötelező tervdokumentum vagy task artifact hiányzik, állj meg `STATUS: BLOCKED` státusszal. Kivétel nincs a JG-06 report esetén: JG-07 nem indulhat JG-06 PASS nélkül.

## Dependency preflight

Mielőtt bármilyen implementációs fájlt módosítasz:

1. Ellenőrizd, hogy a JG-06 report létezik.
2. Ellenőrizd, hogy a JG-06 report első sora `PASS`.
3. Ellenőrizd, hogy a JG-06 report tartalmazza: `JG-07_STATUS: READY`.
4. Ellenőrizd, hogy a JG-06 report szerint az item geometry store, instance determinism és rotation cache ellenőrzések PASS állapotúak.

Ha ezek közül bármelyik nem igaz, ne implementálj. Frissítsd a JG-07 reportot `BLOCKED` státusszal, és írd le pontosan a hiányzó dependency evidence-t.

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

- `rust/vrs_solver/src/optimizer/state.rs`;
- `rust/vrs_solver/src/optimizer/moves.rs`;
- `rust/vrs_solver/src/optimizer/score.rs`;
- `rust/vrs_solver/src/optimizer/mod.rs` minimális export/modul bővítése;
- placed/unplaced state modell;
- `PlacementTransform` translation + rotation adattal;
- `CandidateMove` skeleton place/move/reinsert/rotate alapokkal;
- `ObjectiveBreakdown` skeleton;
- serde diagnosztikai szerializálhatóság, ha a repo függőségei alapján elérhető;
- Rust unit tesztek;
- report és checklist frissítése.

Tilos:

- JG-08 construction placer;
- candidate-point generálás;
- jagua collision check beépítése candidate próbákhoz;
- score optimalizálás vagy sheet elimination;
- repair-search loop;
- irregular/remnant/cavity nesting;
- hole-os item Phase 1 elfogadása;
- validator lazítása;
- v1 output contract törése;
- production UI/API módosítás.

## Valós kód audit kiindulópont

Olvasd el és dokumentáld a reportban:

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/sheet.rs
docs/solver_io_contract.md
scripts/verify.sh
```

Különösen ellenőrizd:

- hogyan működik most `SheetCursor` és `try_place_on_sheet()`;
- hol használja a baseline a `Placement` és `Unplaced` output DTO-kat;
- milyen JG-06 item model és rotation cache már létezik;
- van-e már `state.rs`, `moves.rs`, `score.rs`; ha nincs, hozd létre;
- hogyan lehet úgy exportálni az új modulokat, hogy a meglévő baseline továbbra is forduljon.

## Végrehajtási lépések

### 1. Goal YAML sanity

Validáld a goal YAML-t, ellenőrizd a nem üres `steps` listát és hogy nincs sandbox-specifikus útvonal.

### 2. Optimizer module design döntés

A valós kód alapján hozz döntést:

- maradjon-e a meglévő row/cursor baseline `optimizer/mod.rs`-ben;
- új state/moves/score modulok hogyan legyenek exportálva;
- kell-e `pub use` az új típusokhoz;
- kell-e bármilyen adapter oldali minimális konverziós helper.

A döntést a reportban külön blokkban rögzítsd.

### 3. Implementáció

Implementáld minimum:

- `PlacementTransform { x, y, rotation_deg }`;
- `PlacedItem` vagy ekvivalens placed state record;
- `UnplacedItem` vagy ekvivalens unplaced state record;
- `LayoutState` placed/unplaced listával, seed/determinism metadata előkészítéssel;
- `CandidateMove` enum vagy struct-alapú skeleton legalább place/move/reinsert/rotate alapokkal;
- `ObjectiveBreakdown` skeleton count/sheet/penalty mezőkkel;
- diagnosztikai serializációt, ha a repo `serde` függőségeivel kompatibilis.

Ne törj backward compatibilityt: a meglévő solver input/output JSON contract maradjon v1 kompatibilis.

### 4. Tests

Adj Rust unit teszteket ott, ahol a logika él.

A tesztek legalább ezt fedjék:

- state placed/unplaced szeparáció;
- transform translation + rotation megőrzése;
- candidate move variantok létrehozhatók és diagnosztikai formában stabilak;
- objective breakdown count mezők stabilak;
- state JSON serialization működik;
- azonos inputból épített state ordering determinisztikus;
- baseline v1 output contract nem sérült.

### 5. Kötelező parancsok

Futtasd és dokumentáld:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_item_geometry_store.py
python3 scripts/smoke_jagua_rectangular_sheet_provider.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
```

Ha környezeti dependency miatt valami nem fut, dokumentáld pontosan, és ne adj tiszta PASS-t.

### 6. Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
```

A report első sora csak akkor legyen `PASS`, ha az implementation kész, JG-06 dependency bizonyított, state unit tesztek PASS, repo verify PASS, checklist frissítve.

Ha minden rendben, a report végén szerepeljen:

```text
JG-08_STATUS: READY
```

## Végső válasz formátuma

```text
JG07_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- ...
VERIFY:
- cargo build ...: PASS/FAIL/NOT_RUN
- cargo test ...: PASS/FAIL/NOT_RUN
- python3 scripts/smoke_jagua_item_geometry_store.py: PASS/FAIL/NOT_RUN
- python3 scripts/smoke_jagua_rectangular_sheet_provider.py: PASS/FAIL/NOT_RUN
- ./scripts/verify.sh --report ...: PASS/FAIL/NOT_RUN
STATE_MODEL_DECISION:
- ...
CANDIDATE_MOVE_MODEL:
- ...
NEXT:
- JG-08_STATUS: READY | NOT_READY
BLOCKERS:
- ...
```
