# JG-00 Checklist — jagua_optimizer_t00_task_scaffold_and_master_runner

Pipálható DoD lista a canvas alapján:

- `canvases/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`

Bizonyítékforrás:

- `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`

## Szabályfájlok és tervforrások

- [x] `AGENTS.md` beolvasva.
- [x] `docs/codex/overview.md` beolvasva.
- [x] `docs/codex/yaml_schema.md` beolvasva.
- [x] `docs/codex/report_standard.md` beolvasva.
- [x] `docs/qa/testing_guidelines.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` beolvasva.
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md` beolvasva.

## JG-00 kimenetek

- [x] Létrejött: `canvases/egyedi_solver/jagua_optimizer_task_index.md`.
- [x] A task index tartalmazza JG-00…JG-27 teljes listát.
- [x] A task index tartalmazza: `Source of truth`, `Global invariants`, `Dependency graph`, `Critical path`, `Phase gates`, `Parallelization notes`, `First package batch`, `Stop conditions`.
- [x] Létrejött: `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md`.
- [x] A master runner tartalmazza: `Baseline preflight`, `Execution order`, `Phase gates`, `Benchmark and validation policy`, `Rollback rules`, `Reporting rules`.
- [x] A master runner JG-01…JG-27 runner fájlokat csak expected pathként jelöli.

## Sanity check és guard

- [x] Goal YAML parse OK és `steps` root séma érvényes.
- [x] Nincs abszolút/sandbox-specifikus path a goal YAML-ben.
- [x] Kötelező token sanity check a task-index és master-runner fájlokra PASS.
- [x] Production diff guard: nincs módosítás `rust/**`, `worker/**`, `api/**`, `vrs_nesting/config/nesting_quality_profiles.py` alatt.

## Verify

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`.
- [x] Létrejött/frissült: `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.verify.log`.
- [x] Repo gate eredmény: PASS.

## DEVIATION NOTE

- [x] Rögzítve a tervdokumentációs eltérés: a régebbi fejlesztési terv JG-00 audit fókusza eltér a hivatalos task_bontas/checklist/master_plan scaffold fókusztól.
- [x] A `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` nem lett módosítva, mert nem szerepel a JG-00 goal YAML `outputs` listájában.
