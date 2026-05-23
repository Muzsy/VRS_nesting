# Runner — JG-05 jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-05 taskot: rectangular sheet provider contract + deterministic outer-only fixture pack + smoke validation.

Ez **implementációs/audit task**, nem package-generálás. A canvas és goal YAML már a repo-ban van:

```text
canvases/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
```

## 0. Nem alkuképes szabályok

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

## 1. Kötelező olvasás

Olvasd el teljes egészében:

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
canvases/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
```

## 2. Dependency preflight

A JG-05 közvetlen dependency-je JG-03 és JG-04.

Ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
```

Követelmény:

- JG-03 report első sora `PASS`.
- JG-03 report tartalmazza: `JG-04_STATUS: READY`.
- JG-04 report létezik.
- JG-04 report első sora `PASS`.
- JG-04 report tartalmazza: `JG-05_STATUS: READY`, vagy egyértelműen jelzi, hogy JG-05 indítható.

Ha bármelyik feltétel nem igazolható, **állj meg**:

- ne módosíts production kódot;
- ne hozz létre fixture-öket;
- írd meg/frissítsd a reportot `BLOCKED` státusszal;
- a blokkoló okot pontosan dokumentáld.

## 3. Goal YAML sanity

Validáld:

```text
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.yaml
```

Ellenőrizd:

- valid YAML;
- top-level `steps` lista;
- minden stepben `name`, `description`, `outputs`;
- nincs sandbox-specifikus vagy géphez kötött abszolút útvonal;
- az outputs lista lefedi minden tervezett módosított fájlt.

## 4. Valós kód audit

Olvasd el és dokumentáld a reportban:

```text
docs/solver_io_contract.md
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/main.rs
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/validate_nesting_solution.py
scripts/check.sh
```

Különösen ellenőrizd:

- hogyan működik a jelenlegi `Stock.quantity` expansion;
- milyen sorrendben keletkezik az expanded sheet lista;
- hogyan kerül a placementbe a `sheet_index`;
- a validator elkapja-e az out-of-range vagy invalid sheet indexet;
- a `docs/solver_io_contract.md` megfelelően dokumentálja-e a mappinget;
- van-e margin/gap runtime támogatás a jelenlegi v1 solver inputban.

## 5. Implementációs scope

### Engedett outputok

Csak a goal YAML `outputs` listájában szereplő fájlokat módosítsd/létrehozd.

Várható fő outputok:

```text
rust/vrs_solver/src/sheet.rs
docs/solver_io_contract.md
tests/fixtures/egyedi_solver/jagua_rect_smoke.json
tests/fixtures/egyedi_solver/jagua_rect_medium.json
scripts/smoke_jagua_rectangular_sheet_provider.py
codex/codex_checklist/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.verify.log
```

Ha más fájl módosítása szükséges, előbb frissítsd a YAML-t és dokumentáld a reportban, miért kellett.

### Tilos

- Ne implementálj JG-06 ItemGeometryStore-t vagy rotation cache-t.
- Ne implementálj candidate generationt, scorer-t, repair loopot, SA-t vagy density optimizationt.
- Ne implementálj irregular/remnant/cavity-prepack funkciót.
- Ne fogadj el invalid layoutot PASS-ként.
- Ne lazíts a validatoron azért, hogy egy hibás fixture átmenjen.

## 6. Rectangular sheet provider contract

A JG-05-ben a minimális cél:

- stock order determinisztikus;
- `quantity` szerinti expansion determinisztikus;
- `sheet_index` 0-alapú és az expanded listára mutat;
- több stock + több quantity esetén a mapping ellenőrizhető;
- `quantity <= 0` aktuális policy dokumentált;
- ha szükséges, adj hozzá Rust unit tesztet a `sheet.rs` fájlban.

Ne refaktorálj nagyot, ha a jelenlegi `expand_sheets()` már megfelel és elég regression teszttel lefedni.

## 7. Fixture pack

Hozd létre:

```text
tests/fixtures/egyedi_solver/jagua_rect_smoke.json
tests/fixtures/egyedi_solver/jagua_rect_medium.json
```

Elvárások:

- `contract_version: "v1"`;
- Phase 1 outer-only profil, ha a dependencyk alapján ez az aktív contract;
- csak outer-only partok;
- explicit `allowed_rotations_deg`;
- legalább egy fixture-ben több stock quantity;
- legalább egy fixture-ben olyan elrendezési helyzet, amelyből bizonyítható a második sheet használat vagy legalább a stable expanded sheet range;
- margin/gap mezők státusza dokumentált. Ha a contract nem támogatja őket, ne állítsd, hogy runtime hatásuk van.

## 8. Smoke script

Hozd létre:

```text
scripts/smoke_jagua_rectangular_sheet_provider.py
```

A script:

1. feloldja vagy megkapja a `vrs_solver` binárist;
2. futtatja a smoke fixture-t runner útvonalon;
3. futtatja a medium fixture-t runner útvonalon;
4. minden elfogadott layoutot exact validatorral validál;
5. ellenőrzi a `sheet_index` range-et és mapping evidence-t;
6. létrehoz egy ideiglenes invalid outputot vagy invalid sheet index esetet, és bizonyítja, hogy a validator elutasítja;
7. determinisztikus, gyors, nem hálózatfüggő;
8. a végén egyértelmű PASS/FAIL üzenettel tér vissza.

## 9. Kötelező parancsok

Futtasd és dokumentáld:

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_rectangular_sheet_provider.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
```

Ha dependency vagy környezeti hiba miatt nem futnak, a hiba pontos logját írd a reportba, és ne adj PASS-t.

## 10. Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
```

A report első sora csak akkor legyen `PASS`, ha:

- JG-03 és JG-04 dependency PASS;
- rectangular provider contract bizonyított;
- fixture-ök létrejöttek és validak;
- exact validator PASS az elfogadott layoutokon;
- invalid fixture/output rejected;
- cargo build/test PASS;
- smoke script PASS;
- repo verify PASS;
- checklist frissítve.

Sikeres zárásnál a report végére írd:

```text
JG-06_STATUS: READY
```

Ha nem teljes, akkor:

```text
JG-06_STATUS: NOT_READY
```

## Végső válasz formátuma

```text
JG05_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- ...
DEPENDENCIES:
- JG-03: PASS/FAIL/MISSING
- JG-04: PASS/FAIL/MISSING
VERIFY:
- cargo build ...: PASS/FAIL/SKIPPED
- cargo test ...: PASS/FAIL/SKIPPED
- python3 scripts/smoke_jagua_rectangular_sheet_provider.py: PASS/FAIL/SKIPPED
- ./scripts/verify.sh --report ...: PASS/FAIL/SKIPPED
FIXTURES:
- ...
SHEET_INDEX_CONTRACT:
- ...
NEXT:
- JG-06_STATUS: READY | NOT_READY
BLOCKERS:
- ...
```
