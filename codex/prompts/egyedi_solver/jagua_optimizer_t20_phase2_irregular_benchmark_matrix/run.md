# Runner prompt — JG-20 `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-20 taskot:

```text
JG-20 — jagua_optimizer_t20_phase2_irregular_benchmark_matrix
```

Ez a task a Phase 2 irregular/remnant benchmark gate. Ne implementálj új solver algoritmust, ne vezess be cavity-prepackot, és ne támogass hole-os inputot. Olvasd el a megadott repo fájlokat, ellenőrizd a dependency-t, készítsd el a benchmark scriptet, futtasd a benchmarkot és regressziókat, frissítsd a checklistet és reportot.

---

## Kötelező dependency preflight

Mielőtt bármilyen benchmarkot vagy Phase 2 gate döntést készítesz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
```

JG-19 feltételek:

- report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `JG-20_STATUS: READY`;
- létezik `scripts/smoke_jagua_remnant_score_model_v1.py`;
- létezik `rust/vrs_solver/src/optimizer/score.rs`;
- a JG-19 report bizonyítja, hogy remnant score smoke és repo gate PASS.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-19
```

Ilyenkor ne gyárts benchmark eredményt és ne jelöld JG-21-et indíthatónak; csak frissítsd a JG-20 reportot dependency evidence-szel.

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
canvases/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t20_phase2_irregular_benchmark_matrix.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
```

A `run.md` és a canvas az irányadó.

---

## Valós kód audit

Vizsgáld meg az aktuális kódot:

```text
scripts/bench_jagua_optimizer_phase1_rectangular.py
scripts/smoke_jagua_irregular_sheet_provider.py
scripts/smoke_jagua_irregular_boundary_validation.py
scripts/smoke_jagua_irregular_candidate_generation.py
scripts/smoke_jagua_remnant_score_model_v1.py
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/multisheet.rs
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/check.sh
scripts/verify.sh
```

Külön ellenőrizd:

- Phase 1/Jagua solver profile stringet: `jagua_optimizer_phase1_outer_only`;
- `SolverInput` / `SolverOutput` v1 mezőket;
- `runner_meta.json` mezőket: `placements_count`, `unplaced_count`, `sheet_count_used`, `utilization`, `validation_status`, `duration_sec`, `solver_bin`;
- exact validator bridge-t a runnerben;
- `SheetShape.has_irregular_outer`, `outer_vertices`, `area`, `cost_per_use` elérhetőségét;
- `generate_candidates_with_sheets` candidate source stats elérhetőségét;
- `score_breakdown` mezőket és remnant cost defaultokat;
- a meglévő benchmark/smoke scriptek fixture- és report-mintáit;
- `scripts/verify.sh --report ...` standard gate-et.

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
- Do not drop holes, contours, item identities, quantities, transforms, margin data, stock identities, sheet metadata, or validation data silently.
- Phase 2 benchmark fixtures must be outer-only and hole-free.
- Do not strip holes from a fixture to make it pass; reject or mark BLOCKED/UNSUPPORTED with evidence.
```

```text
EXACT_VALIDATION_REQUIRED:
- Every benchmark run must go through the existing runner/validator path where possible.
- Every accepted layout must have validation_status=pass.
- Invalid boundary layout cannot be accepted as success.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md.
- Update the global JG-20 and Gate 2 entries in canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

---

## Implementációs scope

Hozd létre:

```text
scripts/bench_jagua_optimizer_phase2_irregular.py
```

A script célja:

- Phase 2 irregular/remnant/no-hole benchmark matrix futtatása;
- summary JSON és MD generálása;
- exact validation gate érvényesítése;
- rectangular Phase 1 regresszió ellenőrzése;
- invalid boundary layout fail policy bizonyítása;
- Phase 2 gate döntés előkészítése.

Kimenetek:

```text
codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json
codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md
```

### Benchmark matrix minimum

Legalább ezek legyenek:

1. `l_shape` — konkáv L-alakú sheet, hole nélkül.
2. `concave_remnant` — konkáv remnant sheet, `cost_per_use` vagy JG-19 score metaadatokkal.
3. `mixed_rectangular_remnant` — normál rectangular + remnant sheet együtt.
4. `rectangular_phase1_regression` — JG-14 Phase 1 rectangular regresszió vagy a Phase 1 benchmark script újrafuttatása.

Minden fixture legyen outer-only/no-hole. A fixture-ök ne használjanak DXF-importot.

### Kötelező metrikák

Minden case-nél rögzítsd:

```text
case_id
status
seed
time_limit_s
solver_profile
placed
unplaced
used_sheets
utilization
runtime_sec
validation_status
boundary_rejects vagy boundary_rejects_status/unavailable_reason
score_breakdown, ha elérhető
stock_summary: rectangular/irregular/remnant/cost_per_use
backend/solver_bin
```

### Invalid boundary case

Legyen legalább egy negatív/invalid boundary bizonyíték. Ez lehet:

- olyan explicit case, amelyet a script futtat és `validation_status != pass` miatt `fail` státuszra tesz; vagy
- meglévő JG-17 smoke/regresszió eredményének explicit futtatása és reportolása.

A lényeg: invalid boundary layout automatikusan nem lehet successful benchmark result.

### Gate 2 döntés

A benchmark MD-ben és JG-20 reportban szerepeljen:

```text
PHASE2_GATE_DECISION: PASS | REVISE | STOP
```

Javasolt döntési logika:

- `PASS`: minden kötelező Phase 2 case lefutott, minden accepted layout exact validator PASS, rectangular regresszió PASS, invalid boundary fail evidence megvan.
- `REVISE`: részleges eredmény, hiányzó vagy instabil metrika, environment issue, vagy nem kritikus benchmark hiány.
- `STOP`: boundary/validation contract sérül, invalid layout sikeresnek látszik, vagy rectangular regresszió törik.

Csak `PASS` esetén írd a JG-20 reportba:

```text
JG-21_STATUS: READY
```

---

## Explicit out of scope

Ne implementáld ezeket:

- JG-21 cavity-prepack integration audit;
- cavity extraction / usability filter;
- item-hole vagy stock-hole support;
- macro-part expansion;
- új solver backend profil API/worker integráció;
- új exact validator;
- JG-19 score modell újratervezése;
- production runtime viselkedés módosítása benchmarkon kívül.

---

## Kötelező outputok

A YAML outputs szabálya szerint csak deklarált fájlokat módosíts. Várható fő outputok:

```text
scripts/bench_jagua_optimizer_phase2_irregular.py
codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json
codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md
codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Ha további fájl szükséges, előbb frissítsd a goal YAML-t, különben sérül az `AGENTS.md` outputs szabály.

---

## Kötelező ellenőrzések

Futtasd és dokumentáld:

```bash
python3 scripts/bench_jagua_optimizer_phase2_irregular.py
python3 scripts/bench_jagua_optimizer_phase1_rectangular.py
python3 scripts/smoke_jagua_irregular_sheet_provider.py
python3 scripts/smoke_jagua_irregular_boundary_validation.py
python3 scripts/smoke_jagua_irregular_candidate_generation.py
python3 scripts/smoke_jagua_remnant_score_model_v1.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
```

Ha a környezet miatt valamelyik parancs nem fut, írd le pontosan a hibát, és ne adj PASS-t pusztán feltételezésre.

---

## Report követelmények

A report első sora legyen egyértelműen:

```text
PASS
```

vagy:

```text
PASS_WITH_NOTES
```

vagy:

```text
FAIL
```

vagy:

```text
BLOCKED
```

A report tartalmazza:

- dependency evidence;
- code audit summary;
- benchmark matrix definíció;
- összes case metrikái;
- exact validation evidence;
- invalid boundary fail evidence;
- Phase 1 rectangular regression evidence;
- JG-16/JG-17/JG-18/JG-19 regression evidence;
- summary JSON/MD útvonalak;
- `PHASE2_GATE_DECISION: PASS | REVISE | STOP`;
- checklist update evidence;
- risks/blockers;
- csak valódi PASS esetén: `JG-21_STATUS: READY`.

---

## Kötelező záró válasz

A futás végén add meg:

```text
STATUS: PASS | PASS_WITH_NOTES | FAIL | BLOCKED
TASK: JG-20 — jagua_optimizer_t20_phase2_irregular_benchmark_matrix
PHASE2_GATE_DECISION: PASS | REVISE | STOP
CREATED_OR_UPDATED:
- ...
COMMANDS_RUN:
- ... -> PASS/FAIL
REPORTS:
- codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
- codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json
- codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md
NEXT:
- JG-21_STATUS: READY | not ready, reason: ...
```
