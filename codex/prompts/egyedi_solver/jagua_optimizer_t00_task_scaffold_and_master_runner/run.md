# VRS Nesting Codex Task — JG-00 task scaffold és master runner

TASK_SLUG: `jagua_optimizer_t00_task_scaffold_and_master_runner`
TASK_ID: `JG-00`
AREA: `egyedi_solver`

## Feladat

Hajtsd végre a JG-00 taskot: hozd létre a teljes `jagua-rs` + saját optimizer munkalánc task-indexét és master runnerét.

Ez a futás **nem solver-implementáció**. Most csak a JG fejlesztési lánc repo-konform scaffoldját készíted el.

## Olvasd el először

Kötelező repo-szabályok:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`

Kötelező JG tervdokumentáció:

- `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`

Task package:

- `canvases/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t00_task_scaffold_and_master_runner.yaml`

Minta, ha ellenőrizni kell a repo-konvenciót:

- `canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml`
- `codex/prompts/nesting_engine/lv8_density_master_runner.md`
- `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
- `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`

## Végrehajtás

Hajtsd végre sorrendben a YAML `steps` lépéseit:

```text
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t00_task_scaffold_and_master_runner.yaml
```

Szabályok:

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamelyik YAML step `outputs` listájában.
- A minőségkaput kizárólag wrapperrel futtasd.
- Ne rögtönözz új, nem dokumentált ellenőrző parancsot kötelező gate-ként.
- Ne hivatkozz nem létező fájlra, modulra, API-ra vagy parancsra.
- Ha terv és repo között eltérés van, `REQUIRES_DECISION` blokkban dokumentáld.

## Kötelező hard rules

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
- Update the task-specific checklist entries.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## JG-00 konkrét kimenetei

Hozd létre/frissítsd:

- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.verify.log` a verify wrapperrel

Ne készítsd el a JG-01…JG-27 canvas/YAML/runner fájlokat. Ezek csak expected pathként szerepeljenek a master runnerben és a task indexben.

## Sanity check

A task-indexben legyen:

- JG-00…JG-27 teljes tasklista.
- Dependency graph.
- Critical path.
- Phase gate-ek.
- Stop conditionök.
- First package batch.

A master runnerben legyen:

- baseline preflight;
- global hard rules;
- execution order;
- checkpoints;
- phase gates;
- per-task expected runner references;
- benchmark/validation policy;
- rollback rules;
- reporting rules.

## Production diff guard

JG-00 alatt tilos módosítani:

- `rust/**`
- `worker/**`
- `api/**`
- `vrs_nesting/config/nesting_quality_profiles.py`
- meglévő solver/runtime viselkedést befolyásoló fájlok

Ha ilyen módosítás történt, rollbackeld, vagy a report legyen `REVISE`.

## Kötelező verify

A végén futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md
```

Ez létrehozza/frissíti:

- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.verify.log`
- a report `AUTO_VERIFY` blokkját

## Záró output

A futás végén a reportban és az ügynöki válaszban add meg:

```text
JG00_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- <path>
VERIFY:
- <command>
- <PASS/FAIL>
NEXT:
- JG-01 package indítható / nem indítható, indokkal
```
