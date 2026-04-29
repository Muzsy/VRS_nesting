# DXF Nesting Platform Codex Task - Cavity T4 worker integration es artifacts
TASK_SLUG: cavity_t4_worker_integration_and_artifacts

## Szerep
Senior coding agent vagy. A mar letezo T3 prepack modult kotod be a workerbe
es artifact persistet adsz hozza.

## Cel
Prepack policy eseten a worker a prepackelt solver inputot futtassa, melle
`cavity_plan.json` sidecart irjon es artifactkent regisztraljon.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `worker/main.py`
- `worker/cavity_prepack.py`
- `worker/raw_output_artifacts.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `api/routes/runs.py`
- `canvases/nesting_engine/cavity_t4_worker_integration_and_artifacts.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t4_worker_integration_and_artifacts.yaml`

## Engedelyezett modositas
Csak a YAML `outputs` listaja. Ne modosits result normalizert kiveve, ha
szukseges crash guardhoz es a YAML-t elobb bovited.

## Szigoru tiltasok
- Ne valtoztasd a prepack algorithmot T3 scope-on tul.
- Ne futtasd egyszerre prepack es legacy `part_in_part=auto` engine modot.
- Ne regisztralj nem letoltheto artifact rekordot.
- Ne modosits Rust engine fallbacket.

## Elvart parancsok
- `python3 scripts/smoke_cavity_t4_worker_integration_and_artifacts.py`
- `python3 scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`
- `python3 scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t4_worker_integration_and_artifacts.md`

## Stop conditions
Allj meg, ha a worker artifact registration schema nem tudja additiv modon
kezelni a `cavity_plan` artifactot, vagy ha a solver input hash nem teheto
konzisztensse a futtatott payloadhoz.

## Report nyelve es formatuma
A report magyarul keszuljon. Evidence-ben legyen prepack call site,
solver_input write/hash, cavity_plan upload/registration es non-prepack
regresszio bizonyitek.
