# JG-20 — `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`

## Task identity

- **Task id:** JG-20
- **Slug:** `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`
- **Phase:** Phase 2 / benchmark gate
- **Goal:** Phase 2 irregular/remnant benchmark matrix, hole nélkül, exact validator gate-tel és explicit Gate 2 döntéssel.
- **Dependency:** JG-19 — `jagua_optimizer_t19_remnant_score_model_v1`
- **Primary report:** `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.verify.log`
- **Benchmark JSON:** `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json`
- **Benchmark MD:** `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md`

## Dependency gate

JG-20 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md` létezik;
- a JG-19 report első sora `PASS` vagy repo-konform `PASS_WITH_NOTES`;
- a JG-19 report tartalmazza: `JG-20_STATUS: READY`;
- `scripts/smoke_jagua_remnant_score_model_v1.py` létezik és a JG-19 report szerint PASS volt;
- `rust/vrs_solver/src/optimizer/score.rs` tartalmazza a JG-19 sheet-cost / usable-area utilization breakdown útvonalat;
- nincs JG-19 által jelölt `STOP`, `NO-GO` vagy unresolved remnant scoring blocker.

Ha bármelyik feltétel nem teljesül, a JG-20 futás `BLOCKED`, és nem szabad Phase 2 gate döntést vagy `JG-21_STATUS: READY` sort kiadni.

## Strategic background

JG-15–JG-19 után a Phase 2 célja az, hogy az új jagua-alapú saját optimizer ne csak rectangular/no-hole stockokon működjön, hanem hole-free irregular/remnant sheeteken is. A JG-20 nem új solver-algoritmus, hanem **gate task**: reprodukálható benchmark mátrixszal kell bizonyítani, hogy az irregular/remnant útvonal használható, nem rontja el a Phase 1 rectangular regressziót, és minden elfogadott layout exact validator PASS státuszú.

A Phase 2 továbbra is outer-only. Ez azt jelenti:

- part hole nincs támogatva;
- stock/container hole nincs támogatva;
- cavity-prepack nincs támogatva;
- irregular outer boundary és remnant score támogatás van;
- invalid boundary layout nem lehet sikeres, még akkor sem, ha a placement count vagy score első ránézésre kedvező.

JG-20 a Gate 2 döntési pontja. A reportban kötelező egyértelmű döntést adni:

```text
PHASE2_GATE_DECISION: PASS | REVISE | STOP
```

Csak `PHASE2_GATE_DECISION: PASS` esetén írható a report végére:

```text
JG-21_STATUS: READY
```

## Current repo observations

A csomag a friss repo snapshot valós kódja alapján készült:

- `scripts/bench_jagua_optimizer_phase1_rectangular.py`
  - létezik;
  - JG-14 Phase 1 benchmark script mintának használható;
  - `run_solver_in_dir` runner boundary-t használ;
  - JSON+MD summary-t ír a `codex/reports/egyedi_solver` alá;
  - a `validation_status != pass` állapotot nem kezeli sikeres benchmarkként.
- `scripts/smoke_jagua_irregular_sheet_provider.py`
  - létezik;
  - JG-16 irregular/remnant sheet provider regresszióhoz használható.
- `scripts/smoke_jagua_irregular_boundary_validation.py`
  - létezik;
  - JG-17 boundary validation regresszióhoz használható.
- `scripts/smoke_jagua_irregular_candidate_generation.py`
  - létezik;
  - JG-18 candidate generation regresszióhoz használható.
- `scripts/smoke_jagua_remnant_score_model_v1.py`
  - létezik;
  - JG-19 remnant score regressionként kötelező.
- `rust/vrs_solver/src/sheet.rs`
  - `Stock.outer_points`, `SheetShape.has_irregular_outer`, `SheetShape.outer_vertices`, `SheetShape.area` és `cost_per_use` elérhető;
  - `holes_points` továbbra is explicit unsupported/tiltott Phase 2 benchmarkban.
- `rust/vrs_solver/src/optimizer/boundary.rs`
  - a canonical proxy boundary policy façade;
  - construction/repair/score útvonalaknak ezt kell tiszteletben tartaniuk.
- `rust/vrs_solver/src/optimizer/candidates.rs`
  - `generate_candidates_with_sheets` és `CandidateGenerationStats` elérhető;
  - irregular candidate source breakdown auditálható.
- `rust/vrs_solver/src/optimizer/score.rs`
  - JG-19 sheet-cost / usable-area utilization mezők elérhetőek;
  - invalid overlap/boundary dominancia fenn kell maradjon.
- `vrs_nesting/runner/vrs_solver_runner.py`
  - meglévő runner boundary, exact validation és `runner_meta.json` alap;
  - JG-20 benchmark scriptnek ezt kell használnia, nem saját process/validator duplikációt.

## Exact scope

JG-20 implementációs scope:

1. `scripts/bench_jagua_optimizer_phase2_irregular.py` létrehozása.
2. Hole-free Phase 2 benchmark matrix létrehozása legalább ezekkel:
   - `l_shape` — konkáv L-alakú sheet;
   - `concave_remnant` — konkáv remnant sheet, remnant-cost metaadatokkal;
   - `mixed_rectangular_remnant` — normál rectangular + remnant stock együtt;
   - `rectangular_phase1_regression` — Phase 1 rectangular regressziós case vagy JG-14 benchmark újrafuttatás.
3. Minden benchmark case exact validator gate-en menjen át.
4. Invalid boundary layout automatikus FAIL legyen, ne sikeres partial.
5. Kötelező metrikák rögzítése:
   - `case_id`;
   - `status`;
   - `seed`;
   - `time_limit_s`;
   - `solver_profile`;
   - `placed` / `unplaced`;
   - `used_sheets`;
   - `utilization`;
   - `runtime_sec`;
   - `validation_status`;
   - `boundary_rejects` vagy explicit `boundary_rejects_status` / `unavailable_reason`;
   - irregular/remnant meta: `has_irregular_outer`, `cost_per_use` summary, `candidate_source_summary` ha elérhető.
6. Summary JSON és MD report létrehozása:
   - `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json`;
   - `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md`.
7. Phase 1 rectangular regresszió bizonyítása.
8. JG-16/JG-17/JG-18/JG-19 smoke regressziók futtatása.
9. Gate 2 döntés dokumentálása.
10. Checklist és globális progress checklist frissítése.
11. Csak valódi PASS esetén `JG-21_STATUS: READY` a JG-20 reportban.

## Out of scope

- Nem cél JG-21 cavity-prepack audit elvégzése.
- Nem cél part-hole vagy stock/container-hole támogatás.
- Nem cél cavity extraction, usability filter, child-in-hole placement vagy macro-part expansion.
- Nem cél új geometriai kernel, új exact validator vagy boundary policy újraírás.
- Nem cél JG-19 score modell áttervezése; csak benchmarkolni és regressziózni kell.
- Nem cél Phase 1 script teljes átírása; csak regressziós futtatás vagy hivatkozás.
- Nem cél production worker/API integráció vagy új backend profil publikálása.

## Required implementation outputs

A JG task-bontás és a valós kód alapján legalább ezek érintettek vagy vizsgálandók:

```text
scripts/bench_jagua_optimizer_phase2_irregular.py
codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json
codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md
codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Kötelező input/audit fájlok:

```text
scripts/bench_jagua_optimizer_phase1_rectangular.py
scripts/smoke_jagua_irregular_sheet_provider.py
scripts/smoke_jagua_irregular_boundary_validation.py
scripts/smoke_jagua_irregular_candidate_generation.py
scripts/smoke_jagua_remnant_score_model_v1.py
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/score.rs
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
```

Ha a valós audit alapján további fájl szükséges, előbb frissítsd a YAML `outputs` listáját, mert az `AGENTS.md` szerint csak deklarált output módosítható.

## Detailed execution plan

1. Olvasd el a repo szabályokat és a JG tervdokumentációkat.
2. Ellenőrizd a JG-19 dependency gate-et.
3. Auditáld a meglévő Phase 1 benchmark mintát és az irregular/remnant smoke-okat.
4. Auditáld a runner boundary-t (`run_solver_in_dir`) és a `runner_meta.json` mezőket.
5. Tervezd meg a Phase 2 benchmark case-eket hole-free inputtal.
6. Implementáld `scripts/bench_jagua_optimizer_phase2_irregular.py` scriptet:
   - offline/determinisztikus;
   - saját solver process duplikáció nélkül, ahol a runner használható;
   - summary JSON+MD outputtal;
   - invalid layout fail policy-val;
   - Gate 2 döntési logikával.
7. Biztosítsd, hogy a script ne fogadjon el `validation_status != pass` layoutot successful benchmarkként.
8. Futtasd a Phase 2 benchmarkot és a regressziós smoke-okat.
9. Frissítsd a task-specifikus checklistet és a globális progress checklist JG-20/Gate 2 szakaszát.
10. Töltsd ki a JG-20 reportot konkrét eredményekkel, metrikákkal, regressziós bizonyítékokkal.
11. Csak valódi PASS és `PHASE2_GATE_DECISION: PASS` esetén írd a report végére: `JG-21_STATUS: READY`.

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
- Phase 2 benchmark inputs must be hole-free by construction.
- If a source fixture contains holes, reject it for this benchmark instead of stripping holes.
```

```text
EXACT_VALIDATION_REQUIRED:
- Every accepted benchmark layout must pass exact validation.
- Invalid boundary layout cannot be accepted as success.
- validation_status != pass must produce failed or blocked case status.
```

```text
CHECKLIST_REQUIRED:
- Update codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md.
- Update canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md JG-20 and Gate 2 sections.
- Do not mark PASS unless checked items have concrete evidence.
```

## Required checks

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

## Acceptance criteria

A JG-20 akkor PASS, ha:

- L-shape benchmark futott és minden elfogadott layout exact validator PASS;
- konkáv remnant benchmark futott és minden elfogadott layout exact validator PASS;
- vegyes rectangular + remnant benchmark futott és score/stock meta auditálható;
- rectangular Phase 1 regresszió futott és nincs regresszió;
- invalid boundary layout automatikus FAIL;
- metrikák rögzítve: placed, unplaced, used_sheets, utilization, runtime, boundary rejects;
- seed/profile/backend meta rögzítve;
- summary JSON létrejött;
- summary MD report létrejött;
- `PHASE2_GATE_DECISION: PASS | REVISE | STOP` dokumentálva;
- Gate 2 csak PASS esetén engedi JG-21-et;
- repo verify PASS és log mentve;
- JG-20 checklist és globális progress checklist frissítve.

## Failure / rollback policy

- Ha a dependency gate nem PASS: `BLOCKED`, nincs benchmark döntés.
- Ha bármely accepted layout `validation_status != pass`: `FAIL`/`REVISE`, Gate 2 nem PASS.
- Ha rectangular regresszió törik: `REVISE` vagy `STOP`, JG-21 nem ready.
- Ha irregular/remnant benchmark csak részben fut környezeti okból: `REVISE` vagy `BLOCKED`, a hiányzó case-ek és hiba pontos dokumentálásával.
- Ha a benchmark script fut, de a metrikák hiányosak: `REVISE`, ne `PASS`.
- Rollback: a JG-20 új scriptje és reportjai visszavonhatók anélkül, hogy runtime solver kódot módosítanánk.
