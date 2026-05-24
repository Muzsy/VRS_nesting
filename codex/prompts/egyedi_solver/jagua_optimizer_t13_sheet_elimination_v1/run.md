# Runner prompt — JG-13 `jagua_optimizer_t13_sheet_elimination_v1`

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-13 taskot:

```text
JG-13 — jagua_optimizer_t13_sheet_elimination_v1
```

Ez a task a JG-12 MultiSheetManager V1 után bevezeti a Phase 1 rectangular / outer-only Sheet Elimination V1 pass-t. Ne készíts általános tervet. Olvasd el a megadott repo fájlokat, ellenőrizd a dependency-t, implementáld a scope-ot, futtasd a teszteket, frissítsd a checklistet és reportot.

---

## Kötelező dependency preflight

Mielőtt bármilyen implementációs kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md
```

JG-12 feltételek:

- report létezik;
- első sora `PASS`;
- tartalmazza: `JG-13_STATUS: READY`;
- létezik `rust/vrs_solver/src/optimizer/multisheet.rs`;
- létezik `scripts/smoke_jagua_multisheet_manager_v1.py`;
- a report bizonyítja, hogy multi-sheet smoke és repo gate PASS.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-12
```

Ilyenkor ne implementálj JG-13 kódot, csak frissítsd a JG-13 reportot dependency evidence-szel.

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
canvases/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t13_sheet_elimination_v1.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
```

A `run.md` és a canvas az irányadó. Ha a régi fejlesztési terv JG-13-at cavity-prepackként említi, dokumentáld `DISCOVERED_MISMATCH` blokkal, és az aktuális task-bontást kövesd: JG-13 = Sheet Elimination V1.

---

## Valós kód audit

Vizsgáld meg az aktuális kódot:

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/score.rs
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
scripts/smoke_jagua_multisheet_manager_v1.py
scripts/smoke_jagua_initial_construction.py
scripts/smoke_jagua_repair_search_v1.py
scripts/smoke_jagua_score_model_v1.py
scripts/smoke_jagua_exact_validation_bridge.py
scripts/check.sh
scripts/verify.sh
```

Külön ellenőrizd:

- `MultiSheetManager::run()` construction + repair flowját;
- `compute_sheet_count_used()` max+1 contractját;
- `repair::run_repair()` reinsert queue és deterministic order mintáját;
- `repair::find_violations()` overlap/boundary gate-jét;
- `candidates::generate_candidates()` ordering és dedup szabályait;
- `ScoreModel` sheet-count penalty és `ObjectiveBreakdown.sheet_count_used` mezőit;
- `LayoutState` / placement vector clone-olhatóságát rollback snapshothoz;
- `adapter::solve()` Phase 1 pathját;
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

Tilos az exact validator gyengítése, kikapcsolása vagy megkerülése. Tilos invalid layoutot eliminációs sikerként elfogadni. Tilos sikertelen attempt után részleges layoutot kint hagyni.

---

## Implementációs scope

### 1. Sheet elimination modul

Hozd létre:

```text
rust/vrs_solver/src/optimizer/sheet_elimination.rs
```

Minimum elvárt elemek:

- `SheetEliminationEngine` vagy repo-konform ekvivalens;
- `SheetEliminationDiagnostics` vagy repo-konform ekvivalens;
- deterministic weakest sheet selection;
- rollback snapshot;
- deterministic reinsert order;
- attempt/success/fail/rollback metrics;
- exact/violation gate;
- stopping policy támogatás;
- unit tests.

### 2. Weakest sheet rule

A szabály legyen egyszerű és auditálható. Javasolt V1:

1. Csak használt sheet választható.
2. Ne válassz olyan sheetet, amelynek ürítése nyilván nem csökkentheti a `sheet_count_used` értéket a jelenlegi max+1 contract mellett, kivéve ha a reindex/compaction explicit és validált döntés.
3. Elsődleges preferencia: legmagasabb használt sheet index, ha több gyenge sheet hasonlóan alkalmas.
4. Másodlagos metrika: alacsonyabb placed area vagy placed count.
5. Tie-break: sheet_index descending vagy dokumentált stabil order.

A végső szabályt írd le a kódban és reportban. Ha eltérsz a javaslattól, indokold.

### 3. Rollback és commit policy

Minden attempt előtt vegyél snapshotot:

```text
placements_before
unplaced_before
sheet_count_used_before
score_before vagy diagnostics_before
```

Commit csak akkor:

- minden eltávolított item visszakerült;
- nincs overlap/boundary/sheet violation;
- exact validation smoke szerint valid a layout, ha az adott szinten elérhető;
- `sheet_count_used_after < sheet_count_used_before`;
- `placed_count` nem csökken;
- `unplaced_count` nem nő;
- stopping policy nem jelzett félbeszakítást siker előtt.

Minden más eset rollback.

### 4. Reinsert order

A kiválasztott sheet itemjeit determinisztikusan rendezd:

```text
area desc -> instance_id asc
```

A visszahelyezés csak nem eliminált sheetekre történhet. Candidate generationhez a meglévő `generate_candidates()` logikát használd vagy ahhoz igazodj. Ne írj külön, eltérő collision modelt.

### 5. Wiring

Exportáld:

```text
pub mod sheet_elimination;
```

A JG-13 pass a JG-12 MultiSheetManager után fusson. Elfogadható:

- `MultiSheetManager::run()` construction+repair után meghívja a sheet elimination pass-t; vagy
- az adapter Phase 1 flow hívja meg a manager után.

A döntést dokumentáld. Az output contract ne törjön.

---

## Tesztelési elvárások

Futtasd, ha elérhetők:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
python3 scripts/smoke_jagua_multisheet_manager_v1.py
python3 scripts/smoke_jagua_sheet_elimination_v1.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
```

Ha bármelyik parancs környezeti okból elakad, írd le pontosan. Környezeti hiba nem lehet rejtett PASS.

---

## Report és checklist

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
```

A report első sora legyen `PASS`, `REVISE`, `FAIL` vagy `BLOCKED` a tényleges eredmény alapján. Csak akkor írd a report végére:

```text
JG-14_STATUS: READY
```

ha minden JG-13 acceptance gate PASS.

---

## Kötelező output összefoglaló

A válaszod végén ezt add:

```text
STATUS: PASS | REVISE | FAIL | BLOCKED
SUMMARY:
- ...
CHANGED_FILES:
- ...
TESTS:
- command: ... -> result
REPORT:
- codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
NEXT:
- JG-14_STATUS: READY | NOT_READY
```
