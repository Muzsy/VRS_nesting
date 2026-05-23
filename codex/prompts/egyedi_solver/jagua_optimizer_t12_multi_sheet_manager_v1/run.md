# Runner prompt — JG-12 `jagua_optimizer_t12_multi_sheet_manager_v1`

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-12 taskot:

```text
JG-12 — jagua_optimizer_t12_multi_sheet_manager_v1
```

Ez a task a JG-11 ScoreModel V1 után bevezeti a Phase 1 rectangular / outer-only MultiSheetManager V1 koordinációs réteget. Ne készíts általános tervet. Olvasd el a megadott repo fájlokat, ellenőrizd a dependency-t, implementáld a scope-ot, futtasd a teszteket, frissítsd a checklistet és reportot.

---

## Kötelező dependency preflight

Mielőtt bármilyen implementációs kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
```

JG-11 feltételek:

- report létezik;
- első sora `PASS`;
- tartalmazza: `JG-12_STATUS: READY`;
- létezik `rust/vrs_solver/src/optimizer/score.rs`;
- létezik `scripts/smoke_jagua_score_model_v1.py`;
- a report bizonyítja, hogy score smoke és repo gate PASS.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-11
```

Ilyenkor ne implementálj JG-12 kódot, csak frissítsd a JG-12 reportot dependency evidence-szel.

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
canvases/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t12_multi_sheet_manager_v1.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md
```

A `run.md` és a canvas az irányadó. Ha a régi fejlesztési terv JG-12-t cavity extractionként említi, dokumentáld `DISCOVERED_MISMATCH` blokkal, és az aktuális task-bontást kövesd: JG-12 = MultiSheetManager V1.

---

## Valós kód audit

Vizsgáld meg az aktuális kódot:

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/stopping.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/main.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/Cargo.toml
vrs_nesting/runner/vrs_solver_runner.py
scripts/smoke_jagua_initial_construction.py
scripts/smoke_jagua_repair_search_v1.py
scripts/smoke_jagua_score_model_v1.py
scripts/smoke_jagua_exact_validation_bridge.py
scripts/check.sh
scripts/verify.sh
```

Külön ellenőrizd:

- `adapter::solve()` Phase 1 pathját;
- `build_initial_layout()` több sheet candidate kezelését;
- `run_repair()` több sheet repair candidate kezelését;
- `ScoreModel` sheet_count penalty és `ObjectiveBreakdown.sheet_count_used` mezőit;
- `Metrics.sheet_count_used` jelenlegi contractját;
- `Placement.sheet_index` contractot;
- `expand_sheets()` stabil stock quantity expansionját;
- exact validation bridge elérhetőségét a meglévő smoke script alapján.

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

Tilos az exact validator gyengítése, kikapcsolása vagy megkerülése. Tilos sheet_indexet újraszámozni úgy, hogy a downstream output contract törjön.

---

## Implementációs scope

### 1. MultiSheetManager modul

Hozd létre:

```text
rust/vrs_solver/src/optimizer/multisheet.rs
```

Minimum elvárt elemek:

- `MultiSheetManager` vagy repo-konform ekvivalens;
- `MultiSheetDiagnostics` vagy repo-konform ekvivalens;
- used sheet számító helper;
- sheetenkénti summary helper;
- Phase 1 construction + repair orchestration;
- determinisztikus ordering és no-random döntések;
- unit tesztek.

Ne implementálj sheet eliminációt. Ne próbáld a legrosszabb sheetet kiüríteni. JG-12 csak stabil több sheet alap.

### 2. Optimizer export

Frissítsd:

```text
rust/vrs_solver/src/optimizer/mod.rs
```

Elvárt:

```text
pub mod multisheet;
```

A meglévő modul exportokat ne törd.

### 3. Adapter wiring

Frissítsd a Phase 1 pathot:

```text
rust/vrs_solver/src/adapter.rs
```

A jelenlegi közvetlen flow:

```text
build_initial_layout(...)
run_repair(...)
```

legyen MultiSheetManageren keresztül koordinálva. Az output contract maradjon kompatibilis:

```text
SolverOutput.contract_version
SolverOutput.status
SolverOutput.unsupported_reason
SolverOutput.placements
SolverOutput.unplaced
SolverOutput.metrics.placed_count
SolverOutput.metrics.unplaced_count
SolverOutput.metrics.sheet_count_used
SolverOutput.metrics.seed
SolverOutput.metrics.time_limit_s
SolverOutput.metrics.project_name
```

`main.rs` csak akkor módosítható, ha a valós CLI boundary tényleg igényli. Ha nem kell, dokumentáld a reportban, hogy `main.rs` változatlan maradt.

### 4. Metrics policy

A meglévő `io::Metrics` mezők nem törhetők és nem nevezhetők át.

Per-sheet metrics két módon fogadható el:

1. internal diagnostics a `MultiSheetDiagnostics` alatt, report/smoke evidence-szel; vagy
2. additív JSON output field az `io.rs`-ben, ha a downstream wrapper és smoke tesztek bizonyítják, hogy nem tör kompatibilitást.

Ne változtasd a `contract_version` mezőt csak azért, mert diagnosztikát adsz hozzá.

### 5. Used sheet / sheet_count_used policy

A jelenlegi solver contract szerint `sheet_count_used` a legmagasabb használt `sheet_index + 1`. JG-12-ben ezt helperbe kell emelni és tesztelni kell.

Minimum tesztesetek:

```text
[] -> 0
[sheet 0] -> 1
[sheet 0, sheet 1] -> 2
[sheet 1 only] -> 2, ha max+1 contract marad
out-of-range sheet_index -> validation/diagnostic hiba, nem silent success
```

Ha ettől el akarsz térni, az contract decision: állj meg `REQUIRES_DECISION` státusszal.

### 6. Smoke script

Hozd létre:

```text
scripts/smoke_jagua_multisheet_manager_v1.py
```

Minimum bizonyítás:

- több rectangular sheet fixture valid;
- fixture legalább két sheetet használ;
- `sheet_index` minden placementnél érvényes;
- `metrics.sheet_count_used` pontos;
- unplaced kezelés több sheet mellett helyes;
- azonos seed + azonos input azonos sheet assignmentet ad;
- single-sheet fixture nem regresszál;
- exact validation bridge továbbra is PASS, ha elérhető.

A smoke ne mockolja ki a valós solver boundary-t. A meglévő `vrs_nesting/runner/vrs_solver_runner.py` vagy a Rust CLI használható a repo mintái szerint.

---

## Kötelező tesztek / parancsok

Futtasd, ha a helyi környezetben elérhetők:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::multisheet
python3 scripts/smoke_jagua_initial_construction.py
python3 scripts/smoke_jagua_repair_search_v1.py
python3 scripts/smoke_jagua_score_model_v1.py
python3 scripts/smoke_jagua_multisheet_manager_v1.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md
```

Ha valamelyik környezeti okból elakad, a reportban legyen konkrét log és státusz. Ne adj PASS-t piros vagy nem futtatott gate-re.

---

## Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md
```

A task-specifikus checklistben és a globális progress checklist JG-12 szakaszában csak bizonyítottan teljesült pontokat pipálj ki.

Report kötelező tartalom:

- dependency evidence;
- real code audit;
- `DISCOVERED_MISMATCH` a régi JG-12 cavity extraction tervnév miatt;
- MultiSheetManager API döntés;
- adapter wiring döntés;
- metrics policy döntés;
- used sheet / `sheet_count_used` policy;
- multi-sheet fixture példa;
- deterministic seed evidence;
- exact validation evidence;
- single-sheet regression evidence;
- futtatott parancsok és eredmények;
- `git status --short` preview;
- végső státusz.

A report első sora csak akkor lehet:

```text
PASS
```

ha minden acceptance gate és verify zöld. Ha minden rendben, a report végére írd:

```text
JG-13_STATUS: READY
```

Ha nem minden bizonyított, ne írd be ezt.

---

## Elfogadási feltételek

JG-12 akkor kész, ha:

- JG-11 dependency PASS és dokumentált;
- `rust/vrs_solver/src/optimizer/multisheet.rs` létrejött;
- `optimizer/mod.rs` exportálja a modult;
- Phase 1 adapter MultiSheetManageren keresztül fut;
- több sheetes fixture valid;
- `sheet_index` contract nem törik;
- `sheet_count_used` pontos és tesztelt;
- unplaced kezelés több sheet mellett helyes;
- azonos seed azonos sheet assignmentet ad;
- sheetenkénti diagnostics/metrics reportolva van;
- construction/repair sheetenkénti működése ellenőrizve;
- single-sheet fixture regresszió nem történt;
- exact validation végső gate megmaradt;
- progress checklist frissült;
- repo verify PASS és log mentve.

---

## Végső válasz formátuma

```text
STATUS: PASS | REVISE | BLOCKED

SUMMARY:
- ...

IMPLEMENTED:
- ...

VERIFY:
- command: ...
- result: ...
- log: ...

CHANGED_FILES:
- ...

BLOCKERS_OR_DEVIATIONS:
- ...

NEXT:
- JG-13_STATUS: READY | NOT_READY
```
