# Runner — JG-04 jagua_optimizer_t04_jagua_adapter_contract_poc

## Feladat

A VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-04 backend adapter PoC taskot:

```text
JG-04 — jagua_optimizer_t04_jagua_adapter_contract_poc
```

Ez **nem teljes optimizer implementáció**. A feladat célja: vékony `JaguaAdapter` contract és proof-of-contact a `jagua-rs` collision/geometry backend felé, a JG-02/JG-03 utáni `vrs_solver` modulstruktúrában.

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
codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md
codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
docs/egyedi_solver/jagua_optimizer_source_audit.md
canvases/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t04_jagua_adapter_contract_poc.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
```

Ha bármelyik hiányzik, állj meg `STATUS: BLOCKED` státusszal.

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

Benne van: VRS-owned JaguaAdapter contract/struct/trait, belső jagua conversion boundary, item-item collision smoke valid és invalid esettel, item-sheet/boundary smoke ha támogatott, explicit adapter hibakategóriák, f32/f64 kockázat dokumentálás, `rust/vrs_solver/src/bin/jagua_adapter_smoke.rs`, `scripts/smoke_jagua_adapter_contract.py`, cargo build/test, meglévő JG-03 outer-only smoke regression, repo verify, checklist és report.

Tilos: teljes jagua layout API bekötés, teljes optimizer-loop, sheet elimination, repair search, SA, cavity-prepack, part-in-hole, hole-os nesting engedélyezése, meglévő `solve(input)` rectangular baseline viselkedésének megváltoztatása, invalid layout PASS-ként elfogadása.

## Fontos valós kódhelyzet JG-03 után

- `rust/vrs_solver/Cargo.toml` tartalmazza: `jagua-rs = "0.6.4"`.
- `rust/vrs_solver/src/geometry.rs` már tartalmaz jagua conversion helperből induló kódot: `to_jag_point()`, `to_jag_polygon()`, `jag_edge_from_points()`.
- `rust/vrs_solver/src/sheet.rs` már használja a `jagua_rs::geometry::geo_traits::CollidesWith` traitet és `SPolygon`-t stock hole collision ellenőrzésre.
- `rust/vrs_solver/src/adapter.rs` jelenleg a solver orchestration (`solve(input)`) helye, nem dedikált backend adapter modul. Ne törd el.
- `rust/vrs_solver/src/main.rs` jelenleg csak bináris modul deklarációkat tartalmaz, library crate nincs.
- `rust/vrs_solver/src/bin/` jelenleg hiányozhat; a JG-04 outputként létrehozhatja.
- `docs/solver_io_contract.md` már rögzíti a JG-03 Phase 1 profile/hole unsupported contractot.

## DISCOVERED_MISMATCH kezelés

A régebbi `jagua_rs_sajat_optimizer_fejlesztesi_terv.md` JG-04 címe rectangular single-sheet baseline optimizer. Az aktuális task-bontás szerint JG-04 backend adapter PoC. A reportban dokumentáld ezt az eltérést, és a jelen taskhoz az aktuális task-bontást kövesd.

## Végrehajtási lépések

### 1. Task és dependency ellenőrzés

Keresd meg a JG-04 definíciót itt:

```text
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/egyedi_solver/jagua_optimizer_task_index.md
codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md
```

Ellenőrizd:

- task id: `JG-04`
- slug: `jagua_optimizer_t04_jagua_adapter_contract_poc`
- phase: `Phase 1 / backend adapter`
- dependencies: `JG-02`, `JG-03`
- JG-02 report első sora `PASS`
- JG-03 report első sora `PASS`
- JG-03 report tartalmazza: `JG-04_STATUS: READY`

Ha bármelyik nem igazolható, `BLOCKED`.

### 2. Goal YAML sanity

Validáld a goal YAML-t, ellenőrizd a nem üres `steps` listát, és hogy nincs sandbox-specifikus útvonal.

### 3. Valós code-boundary audit

Olvasd el és dokumentáld a reportban:

```text
rust/vrs_solver/Cargo.toml
rust/vrs_solver/src/main.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/mod.rs
docs/solver_io_contract.md
scripts/smoke_jagua_optimizer_outer_only_contract.py
```

Különösen nézd meg:

- hol vannak a jagua conversion helperek;
- hol használja a repo már a `CollidesWith` traitet;
- hogyan lehet a smoke binárist úgy felépíteni, hogy ne legyen nagy library refaktor;
- kell-e `src/lib.rs` a bináris smoke tiszta megvalósításához;
- milyen minimális outputs-bővítés szükséges, ha a valós Rust crate struktúra ezt megköveteli.

### 4. Adapter contract döntés

Döntsd el és dokumentáld, hogy a PoC hol éljen:

A) `adapter.rs` belső `JaguaAdapter` contract/struct/trait a meglévő `solve(input)` megtartásával.

B) Új belső modul, például `jagua_adapter.rs`, ha a névütközés miatt tisztább — csak akkor, ha a YAML/report explicit dokumentálja az outputs bővítést.

C) Csak smoke-bin lokális PoC, ha a crate struktúra miatt production modul érintése túl nagy refaktor lenne — ebben az esetben `REVISE`, nem teljes PASS, hacsak a task acceptance így is teljesül.

Javasolt: A vagy B, de csak valós build alapján dönts.

### 5. Rust implementáció

Implementáld a vékony contractot úgy, hogy:

- legyen VRS-owned input/output/error típus vagy legalább stabil adapter API;
- jagua típusok ne jelenjenek meg a publikus optimizer modellben;
- conversion error elkülönüljön backend error-tól;
- unsupported branch létezzen dokumentált API-hiány esetére;
- item-item collision valid/nem átfedő és invalid/overlap eset bizonyítható legyen;
- item-sheet/boundary smoke bizonyítható legyen, ha támogatott;
- a meglévő `solve(input)` rectangle-only viselkedés ne változzon.

### 6. Smoke bináris

Hozd létre:

```text
rust/vrs_solver/src/bin/jagua_adapter_smoke.rs
```

A bináris adjon stabil, géppel ellenőrizhető kimenetet. Elfogadható például JSON:

```json
{
  "status": "ok",
  "cases": {
    "item_item_non_overlap": true,
    "item_item_overlap": true,
    "item_sheet_boundary": true
  },
  "notes": ["f64_to_f32_conversion_used"]
}
```

A pontos mezők lehetnek mások, de a Python smoke scriptnek explicit assertionöket kell tennie rájuk.

### 7. Python smoke script

Hozd létre:

```text
scripts/smoke_jagua_adapter_contract.py
```

A script:

- fusson repo rootból;
- építse/futtassa a `jagua_adapter_smoke` binárist;
- parse-olja vagy stabilan ellenőrizze a kimenetet;
- valid/nem átfedő és invalid/overlap esetet explicit ellenőrizzen;
- boundary esetet explicit ellenőrizzen, ha implementált;
- ellenőrizze, hogy conversion/precision note dokumentáltan megjelenik;
- exit code 0 csak teljes PASS esetén legyen.

### 8. Kötelező parancsok

Futtasd és dokumentáld:

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_adapter_contract.py
python3 scripts/smoke_jagua_optimizer_outer_only_contract.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
```

Ha környezeti dependency miatt valami nem fut, dokumentáld pontosan, és ne adj tiszta PASS-t.

### 9. Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
```

A report első sora csak akkor legyen `PASS`, ha az adapter PoC kész, a smoke-ok bizonyítottak, cargo build/test PASS, repo verify PASS, és a checklist frissítve.

Ha minden rendben, a report végén szerepeljen:

```text
JG-05_STATUS: READY
JG-08_DEPENDENCY_JG04: READY
```

## Végső válasz formátuma

```text
JG04_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- ...
VERIFY:
- cargo build ...: PASS/FAIL
- cargo test ...: PASS/FAIL
- python3 scripts/smoke_jagua_adapter_contract.py: PASS/FAIL
- python3 scripts/smoke_jagua_optimizer_outer_only_contract.py: PASS/FAIL
- ./scripts/verify.sh --report ...: PASS/FAIL
ADAPTER_DECISION:
- adapter.rs internal | new module | smoke-only | requires decision
API_OBSERVATIONS:
- ...
NEXT:
- JG-05_STATUS: READY | NOT_READY
- JG-08_DEPENDENCY_JG04: READY | NOT_READY
BLOCKERS:
- ...
```
