# DXF Nesting Platform Codex Task - Cavity T3 worker cavity prepack v1
TASK_SLUG: cavity_t3_worker_cavity_prepack_v1

## Szerep
Senior coding agent vagy. Pure worker-side algorithm modult implementalsz,
runtime bekotes nelkul.

## Cel
Hozd letre a `worker/cavity_prepack.py` modult, amely snapshot + base
`nesting_engine_v2` inputbol deterministic prepackelt engine inputot es
`cavity_plan_v1` payloadot ad vissza.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `worker/engine_adapter_input.py`
- `worker/result_normalizer.py`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `tests/test_dxf_preflight_geometry_import_gate.py` es mas geometry teszt mintak
- `canvases/nesting_engine/cavity_t3_worker_cavity_prepack_v1.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t3_worker_cavity_prepack_v1.yaml`

## Engedelyezett modositas
Csak a YAML `outputs` listaja. Ne integrald a modult `worker/main.py`-ba ebben
a taskban.

## Szigoru tiltasok
- Nincs DB/API/file write a prepack modulban.
- Nincs filename/part_code hardcode.
- Child holes prepack v1-ben unsupported diagnostic, nem implementacio.
- Nincs random sorrend.
- Nincs globalis hole deletion export/gyartasi szemantikabol.

## Elvart parancsok
- `python3 -m pytest -q tests/worker/test_cavity_prepack.py`
- `python3 scripts/smoke_cavity_t3_worker_cavity_prepack_v1.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t3_worker_cavity_prepack_v1.md`

## Stop conditions
Allj meg, ha a snapshot manifest valos mezoi nem elegendoek a contractban vart
mappinghez, vagy ha exact containment csak uj dependencyvel oldhato meg.

## Report nyelve es formatuma
A report magyarul keszuljon. Kulon bizonyitsd a disabled behavior, virtual
parent holes removal, child quantity reservation, instance base es no-hardcode
invariantokat.
