# Runner prompt — JG-14 `jagua_optimizer_t14_phase1_benchmark_matrix`

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-14 taskot:

```text
JG-14 — jagua_optimizer_t14_phase1_benchmark_matrix
```

Ez a task a Phase 1 rectangular / outer-only Jagua optimizer benchmark gate. Ne készíts általános tervet és ne implementálj új solver algoritmust. Olvasd el a megadott repo fájlokat, ellenőrizd a dependency-t, készítsd el a benchmark scriptet, futtasd a benchmarkot és regressziókat, frissítsd a checklistet és reportot.

---

## Kötelező dependency preflight

Mielőtt bármilyen benchmarkot vagy Phase 1 gate döntést készítesz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
```

JG-13 feltételek:

- report létezik;
- első sora `PASS`;
- tartalmazza: `JG-14_STATUS: READY`;
- létezik `rust/vrs_solver/src/optimizer/sheet_elimination.rs`;
- létezik `scripts/smoke_jagua_sheet_elimination_v1.py`;
- a report bizonyítja, hogy sheet elimination smoke és repo gate PASS.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-13
```

Ilyenkor ne gyárts benchmark eredményt és ne jelöld Phase 2-t indíthatónak; csak frissítsd a JG-14 reportot dependency evidence-szel.

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
canvases/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t14_phase1_benchmark_matrix.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md
```

A `run.md` és a canvas az irányadó.

---

## Valós kód audit

Vizsgáld meg az aktuális kódot:

```text
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/Cargo.toml
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/smoke_jagua_exact_validation_bridge.py
scripts/smoke_jagua_sheet_elimination_v1.py
scripts/smoke_jagua_multisheet_manager_v1.py
scripts/check.sh
scripts/verify.sh
```

Külön ellenőrizd:

- `adapter.rs` Phase 1 profile stringjét: `jagua_optimizer_phase1_outer_only`;
- `SolverInput` / `SolverOutput` v1 mezőket;
- `runner_meta.json` mezőket: `placements_count`, `unplaced_count`, `sheet_count_used`, `utilization`, `validation_status`, `duration_sec`, `solver_bin`;
- `validate_multi_sheet_output` exact validation bridge-t;
- `compute_sheet_count_used` max+1 contractot;
- a meglévő smoke scriptek fixture- és runner-mintáit;
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
- Do not drop holes, contours, item identities, quantities, transforms, or validation data silently.
- Phase 1 benchmark fixtures must be rectangular/no-hole.
- Do not convert hole-containing inputs into outer-only fixtures silently.
```

```text
EXACT_VALIDATION_REQUIRED:
- Every benchmark run must go through the existing runner/validator path.
- Every accepted layout must have validation_status=pass.
- Invalid layout cannot be accepted as success.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

---

## Implementációs scope

Hozd létre:

```text
scripts/bench_jagua_optimizer_phase1_rectangular.py
```

A script célja:

- Phase 1 rectangular/no-hole benchmark matrix futtatása;
- summary JSON és MD generálása;
- exact validation gate érvényesítése;
- baseline összevetés, ha a repo valós kódja alapján értelmes;
- Phase 1 gate döntés előkészítése.

Kimenetek:

```text
codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.json
codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md
```

### Benchmark matrix minimum

Legalább ezek legyenek:

1. `smoke` — nagyon kicsi fixture, gyors, minden itemnek el kell férnie.
2. `small` — több rectangular part type, legalább egy rotációs lehetőség.
3. `medium` — több quantity, multi-sheet viselkedés.
4. `realistic_no_hole` — nagyobb rectangular/no-hole synthetic fixture, vagy explicit blocker ha a repo jelenlegi állapota alapján ez nem hozható létre felelősen.

Minden fixture legyen outer-only/no-hole. A fixture-ök ne használjanak DXF-importot.

### Kötelező metrikák

Minden case-nél rögzítsd:

```text
case_id
status
seed
time_limit_s
solver_profile
allowed_rotations_summary
solver_bin
placed_count
unplaced_count
sheet_count_used
utilization
duration_sec
validation_status
validation_error
baseline_status
baseline_metrics_or_reason
```

A `placed_count` lehet a runner meta `placements_count` mezője vagy repo-konform alias, de a benchmark JSON-ban `placed_count` néven jelenjen meg.

### Baseline compare

Baseline csak valós repo-kód alapján lehet. Elfogadható baseline például a non-Phase1 solver path, ha az `adapter.rs` alapján ténylegesen elérhető.

Ha nincs értelmes baseline, a JSON/MD tartalmazza:

```text
baseline_status: unavailable
baseline_reason: <konkrét bizonyíték>
```

Ne találj ki baseline backend nevet.

### Invalid-layout fail policy

A benchmark scriptben explicit legyen:

- `validation_status == "pass"` szükséges a successful case-hez;
- `validation_status == "fail"` → case fail;
- runner exception vagy missing output → case fail/blocker;
- unsupported input → csak akkor elfogadható külön státuszként, ha a case célja unsupported ellenőrzés volt. JG-14 fő fixture-öknél ez nem siker.

---

## Futtatandó parancsok

Minimálisan:

```bash
python3 scripts/bench_jagua_optimizer_phase1_rectangular.py
python3 scripts/smoke_jagua_sheet_elimination_v1.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md
```

Ha valamelyik parancs environment dependency miatt nem fut, dokumentáld pontosan. Ne keverd össze az environment failt a solver minőségével.

---

## Report követelmény

Frissítsd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md
```

A report tartalmazza:

- első sor: `PASS`, `FAIL`, `PASS_WITH_NOTES`, `REVISE`, `STOP` vagy `BLOCKED` repo-konform módon;
- dependency evidence;
- létrehozott benchmark script;
- benchmark summary JSON/MD útvonal;
- case-level benchmark táblázat;
- exact validation evidence;
- baseline compare státusz;
- futtatott parancsok és eredmények;
- Phase 1 gate döntés;
- checklist update státusz;
- risks/blockers.

A benchmark MD tartalmazza:

```text
PHASE1_GATE_DECISION: PASS | REVISE | STOP
```

A JG-14 report csak akkor tartalmazhatja ezt:

```text
JG-15_STATUS: READY
```

ha a Phase 1 gate döntés `PASS`.

---

## Checklist update

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Csak bizonyított pontokat pipálj ki. Ha valami nem futott, maradjon üresen vagy legyen `BLOCKED/DEVIATION` megjegyzéssel dokumentálva.

---

## Acceptance criteria

- Smoke benchmark fixture fut.
- Small benchmark fixture fut.
- Medium benchmark fixture fut.
- Realistic no-hole fixture fut vagy explicit blockerrel dokumentált.
- Baseline compare lefut, ahol van értelmes baseline.
- Minden elfogadott layout exact validator PASS.
- Invalid layout automatikus FAIL.
- Metrikák rögzítve: placed, unplaced, used_sheets, utilization, runtime.
- Seed/profile/rotations/backend meta rögzítve.
- Summary JSON létrejött.
- Summary MD report létrejött.
- Phase 1 gate döntés: PASS / REVISE / STOP dokumentálva.
- Repo verify wrapper lefutott.
- Checklist frissült.

---

## Végső válasz formátum

A futás végén ezt add:

```text
STATUS: PASS | REVISE | STOP | BLOCKED

SUMMARY:
- ...

BENCHMARK:
- script: scripts/bench_jagua_optimizer_phase1_rectangular.py
- json: codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.json
- md: codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md
- phase1_gate_decision: PASS | REVISE | STOP

VERIFY:
- command: ...
- result: ...
- log: ...

CHECKLIST:
- ...

CHANGED_FILES:
- ...

BLOCKERS:
- ...
```
