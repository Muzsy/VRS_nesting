# JG-01 Checklist — jagua_optimizer_t01_repo_and_source_audit

Pipálható DoD lista a canvas alapján:

- `canvases/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`

Bizonyítékforrás:

- `docs/egyedi_solver/jagua_optimizer_source_audit.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`

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
- [x] `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md` — DEVIATION: a task bontás és progress checklist elsődleges forrásként elegendő volt; a master_plan részletes olvasása nem volt showstopper.
- [x] `canvases/egyedi_solver/jagua_optimizer_task_index.md` beolvasva.
- [x] `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md` beolvasva.

## Task azonosítás

- [x] JG-01 pontosan megtalálva a task bontásban (`jagua_optimizer_canvas_yaml_runner_task_bontas.md`).
- [x] JG-01 pontosan megtalálva a progress checklistben (L121–L153).
- [x] JG-00 dependency státusza ellenőrizve: PASS (`codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`, 1. sor).
- [x] JG-01 expected output pathok ellenőrizve és importálva.

## Repo/source audit

- [x] `rust/vrs_solver` jelenlegi állapota auditálva (main.rs L1-649, row/cursor baseline, nem optimizer).
- [x] `jagua-rs` dependency és használat ellenőrizve: v0.6.4, CollidesWith + SPolygon + Edge + Point primitívek, collision check only.
- [x] `docs/solver_io_contract.md` releváns szerződései auditálva (v1 JSON, stocks/parts/placements/unplaced).
- [x] Python runner/adapter boundary auditálva: `vrs_solver_runner.py` (binary resolve, timeout, artifacts, contract validation), `solver_adapter.py` (Protocol + FunctionSolverAdapter).
- [x] Exact/multi-sheet validation anchorok auditálva: `instances.py` L247+ `validate_multi_sheet_output()`, Shapely-alapú.
- [x] Meglévő cavity pipeline auditálva: `worker/cavity_prepack.py` (1120 sor, v1+v2 plan), `worker/cavity_validation.py` (721 sor), `worker/result_normalizer.py` (1414 sor).
- [x] Sparrow runner/fallback/smoketest minták auditálva: `sparrow_runner.py`, `ensure_sparrow.sh`, `run_sparrow_smoketest.sh`, `poc/sparrow_io/sparrow_commit.txt`.
- [x] Sparrowból átvehető optimizer/search minták külön táblában rögzítve (source audit 9. szekció).
- [x] Rectangular, irregular/remnant és hole/cavity kockázatok külön bontva (source audit 10-12. szekció).
- [x] Licenc/dependency/build kockázatok dokumentálva (source audit 13. szekció).
- [x] A report konkrét fájl- és kód-anchorokat tartalmaz (path + sor).
- [x] Blokkolók és döntési javaslatok külön szakaszban szerepelnek (source audit 15. szekció).

## Kimenetek

- [x] Létrejött/frissült: `docs/egyedi_solver/jagua_optimizer_source_audit.md`.
- [x] Létrejött/frissült: `codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`.
- [x] Létrejött/frissült: `codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.verify.log` (verify.sh gate lefutott).
- [x] A globális progress checklist JG-01 státusza frissült (`canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`).

## Sanity check és verify

- [x] Goal YAML parse OK és `steps` root séma érvényes (6 step, `YAML_OK`).
- [x] Nincs abszolút/sandbox-specifikus path a goal YAML-ben.
- [x] Task-specifikus sanity parancsok lefutottak:
  - `cargo metadata --manifest-path rust/vrs_solver/Cargo.toml --no-deps` — PASS
  - `python3 -m pytest -q tests/test_solver_adapter_contract.py tests/worker/test_cavity_prepack.py tests/worker/test_cavity_validation.py tests/worker/test_result_normalizer_cavity_plan.py` — **38 passed in 1.05s**
- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md`.
- [x] Repo gate eredmény dokumentálva (PASS — EXIT_CODE=0, 366 pytest, mypy OK).

## Záró mezők

- [x] Reportban szerepel a végső státusz: PASS.
- [x] Eltérések explicit módon dokumentálva.
- [x] JG-02 indíthatósága egyértelműen jelölve: **READY**.

## Package generation note

- [x] Ez a checklist a JG-01 végrehajtásához készült. A checkboxokat a JG-01 audit futtató agentnek kell véglegesítenie bizonyítékok alapján.
- [x] Véglegesítve: 2026-05-22, lokális repo-ban futtatva.
