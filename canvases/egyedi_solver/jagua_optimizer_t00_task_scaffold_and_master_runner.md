# JG-00 — jagua_optimizer_t00_task_scaffold_and_master_runner

## Funkció

A JG-00 feladat célja a teljes `jagua-rs` + saját optimizer fejlesztési lánc repo-kompatibilis task-indexének és master runnerének létrehozása. Ez a task még **nem implementál solver-kódot**. A kimenete egy olyan belső index és master runner, amelyből a későbbi JG-01…JG-27 `canvas + YAML + runner` csomagok következetesen elkészíthetők és futtathatók.

A JG-00 kimenete a későbbi munka forrása:

- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.verify.log`

## Source of truth

A feladat kizárólag ezekből a repo-beli forrásokból dolgozhat:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`
- meglévő canvas/YAML/runner/checklist/report minták, különösen:
  - `canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
  - `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml`
  - `codex/prompts/nesting_engine/lv8_density_master_runner.md`
  - `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
  - `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`

## Stratégiai háttér

A JG munkalánc alapdöntése: a `jagua-rs` a VRS_nesting projektben gyors collision / geometry backend szerepet kaphat, de nem kezelendő kész ipari optimizerként. A saját optimizer feladata a fixed-sheet, multi-sheet, remnant és későbbi cavity-prepack logika. A Sparrow-ból csak a keresési/repair szemlélet és minták vehetők át szelektíven; az eredeti strip-packing outer-loop nem kerülhet vakon átemelésre.

A munkalánc képességi lépcsői:

1. Rectangular multi-sheet nesting, item hole nélkül.
2. Irregular/remnant sheet nesting, item hole nélkül.
3. Hole / part-in-hole kezelés cavity-prepack rétegen keresztül.

Minden fázisban kötelező az exact final validation. Invalid layout nem lehet sikeres eredmény.

## Feladat scope

### JG-00 feladata

- Hozd létre a teljes JG-00…JG-27 task-indexet.
- Hozd létre a `jagua_optimizer_master_runner.md` futtatási dokumentumot.
- Hozd létre/frissítsd a JG-00 checklistet és reportot.
- A task-indexben és master runnerben rögzítsd a dependency graphot, critical pathot, phase gate-eket, stop conditionöket és per-task expected runner pathokat.
- A kimenetek legyenek alkalmasak arra, hogy később külön package-generáló taskok készítsék el a JG-01…JG-27 konkrét canvas/YAML/runner csomagjait.

### Out of scope

- Nem implementál Rust solver-logikát.
- Nem köt be új `jagua-rs` dependency-t.
- Nem módosít `rust/vrs_solver/**`, `rust/nesting_engine/**`, `worker/**`, `api/**` production runtime kódot.
- Nem módosít quality profile-t.
- Nem készít el JG-01…JG-27 canvas/YAML/runner csomagokat.
- Nem futtat hosszú benchmarkot.
- Nem dönt újra a stratégiai terv tartalmáról.

## Kötelező globális invariánsok

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
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md when the actual task is executed.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

További invariánsok:

- Phase 1–2 alatt item hole kezelése tilos; explicit unsupported/warning szükséges.
- Új jagua optimizer útvonal feature gate nélkül nem törheti a meglévő `vrs_solver` / Sparrow / nesting_engine útvonalakat.
- Minden hosszabb keresésnek explicit seed, time limit és stopping policy kell.
- Minden DoD ponthoz report evidence szükséges.

## Valós repo anchorok

A JG-00-ban nem kell módosítani ezeket, de a task-indexben és master runnerben valós kiindulópontként ellenőrizni/rögzíteni kell őket, ha léteznek:

- `rust/vrs_solver/Cargo.toml`
- `rust/vrs_solver/src/main.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/search/sa.rs`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `worker/cavity_prepack.py`
- `worker/cavity_validation.py`
- `scripts/validate_nesting_solution.py`
- `scripts/validate_sparrow_io.py`
- `scripts/run_sparrow_smoketest.sh`
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `docs/nesting_engine/cavity_prepack_contract_v2.md`
- `docs/solver_io_contract.md`

Ha bármelyik anchor hiányzik, ne találj ki pótlást. A task-indexben jelöld `DISCOVERED_MISMATCH` vagy `REQUIRES_DECISION` státusszal.

## Kötelező task-index tartalom

A `canvases/egyedi_solver/jagua_optimizer_task_index.md` legalább ezeket a szekciókat tartalmazza:

1. `# Jagua optimizer — task index`
2. `## Source of truth`
3. `## Strategic decision`
4. `## Global invariants`
5. `## Real repo anchors`
6. `## Task list`
7. `## Dependency graph`
8. `## Critical path`
9. `## Phase gates`
10. `## Parallelization notes`
11. `## First package batch`
12. `## Stop conditions`

A task listának tartalmaznia kell JG-00…JG-27 teljes felsorolását a task bontásból. Minden tasknál legyen:

- task id;
- slug;
- phase;
- cél;
- függőség;
- expected canvas path;
- expected goal YAML path;
- expected runner path;
- expected checklist path;
- expected report path;
- acceptance gate röviden.

A task-indexben rögzítendő dependency graph a task bontás alapján:

```text
JG-00 -> JG-01 -> JG-02
JG-02 -> JG-03
JG-03 + JG-02 -> JG-04
JG-03 + JG-04 -> JG-05
JG-05 -> JG-06 -> JG-07
JG-07 + JG-04 -> JG-08
JG-08 -> JG-09 -> JG-10 -> JG-11 -> JG-12 -> JG-13 -> JG-14
JG-14 -> JG-15 -> JG-16 -> JG-17 -> JG-18 -> JG-19 -> JG-20
JG-20 -> JG-21 -> JG-22
JG-22 + JG-14 -> JG-23 -> JG-24
JG-24 + JG-20 -> JG-25
JG-14 vagy JG-20 -> JG-26
JG-26 -> JG-27
```

A critical path legalább ezeket az útvonalakat tartalmazza:

```text
Rectangular: JG-00 → JG-01 → JG-02 → JG-03 → JG-04 → JG-05 → JG-06 → JG-07 → JG-08 → JG-09 → JG-10 → JG-11 → JG-12 → JG-13 → JG-14
Irregular/remnant: JG-14 → JG-15 → JG-16 → JG-17 → JG-18 → JG-19 → JG-20
Cavity: JG-20 → JG-21 → JG-22 → JG-23 → JG-24 → JG-25
Release: JG-25 → JG-26 → JG-27
```

## Kötelező master runner tartalom

A `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md` legyen önállóan használható futtatási dokumentum.

Kötelező szekciók:

1. `# Jagua Optimizer Master Runner`
2. `## Cél`
3. `## Kötelező olvasnivaló`
4. `## Baseline preflight`
5. `## Global hard rules`
6. `## Files and anchors to verify before start`
7. `## Execution order`
8. `## Checkpoints`
9. `## Per-task runner references`
10. `## Phase gates`
11. `## Benchmark and validation policy`
12. `## Rollback rules`
13. `## Reporting rules`

A master runner ne állítsa, hogy a JG-01…JG-27 runner fájlok már léteznek. Helyes forma:

```text
JG-01 expected runner path: codex/prompts/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit/run.md
Status: to be created by its own package task.
```

A JG-00 saját runnerére a státusz `present` lehet.

## Futtatási lépések

1. Olvasd el a repo szabályfájlokat és a JG tervdokumentációt.
2. Nyerd ki a JG-00…JG-27 tasklistát, dependency graphot és phase gate-eket a task bontásból.
3. Ellenőrizd a valós repo anchorokat.
4. Hozd létre a task-indexet.
5. Hozd létre a master runnert.
6. Hozd létre/frissítsd a checklistet és reportot.
7. Futtass sanity checkeket:
   - YAML parse a goal YAML-ekre, ha van repo-séma/parancs.
   - Markdown path/token sanity check a task-indexre és master runnerre.
   - Production diff guard: ne legyen módosítás `rust/**`, `worker/**`, `api/**`, `vrs_nesting/config/nesting_quality_profiles.py` alatt.
8. Futtasd a standard repó kaput:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md
```

## Failure / rollback policy

- Ha bármely kötelező tervdokumentum hiányzik: `STATUS: BLOCKED`.
- Ha `TASK_TO_PACKAGE` nem található pontosan a task bontásban/checklistben: `STATUS: BLOCKED`.
- Ha a repo séma és a master plan ellentmond: `REQUIRES_DECISION` blokk szükséges.
- Ha production kód módosult: rollback vagy `STATUS: REVISE`.
- Ha a verify wrapper piros: `STATUS: REVISE` vagy `STATUS: BLOCKED`, a log taillel.

## Ismert tervdokumentációs eltérés

`canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md` régebbi `Task JG-00 — Jagua/Sparrow kódszintű audit` megnevezést is tartalmaz. A hivatalos, repo-konform task-package forrás a `jagua_optimizer_canvas_yaml_runner_task_bontas.md`, a `jagua_optimizer_task_progress_checklist.md` és a `jagua_optimizer_master_plan.md`, amelyekben a `JG-00` már scaffold/master runner feladat. A reportban ezt `REQUIRES_DECISION/DEVIATION NOTE` jelleggel rögzíteni kell, de a csomag a task bontásban szereplő exact slugot követi.

## Acceptance criteria

- [ ] A JG-00 task pontosan azonosítva lett.
- [ ] `canvases/egyedi_solver/jagua_optimizer_task_index.md` létrejött.
- [ ] A task index tartalmazza JG-00…JG-27 teljes listáját.
- [ ] A task index tartalmaz dependency graphot és critical pathot.
- [ ] A task index tartalmaz phase gate-eket.
- [ ] `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md` létrejött.
- [ ] A master runner önállóan futtatható feladatként van megírva.
- [ ] A master runner per-task expected pathokat használ JG-01…JG-27-re, nem állítja létezőnek őket.
- [ ] Nem módosult production solver/runtime kód.
- [ ] A JG-00 checklist és report létrejött/frissült.
- [ ] A `./scripts/verify.sh --report ...` wrapper lefutott.
- [ ] A verify log mentve lett.
- [ ] A report DoD → Evidence Matrix minden pontja bizonyítékkal rendelkezik.

## Következő lépés

Sikeres JG-00 után indítható a JG-01 package-generálása:

```text
TASK_TO_PACKAGE = "JG-01 — `jagua_optimizer_t01_repo_and_source_audit`"
```
