# DXF Nesting Platform Codex Task - Cavity T5 result normalizer expansion
TASK_SLUG: cavity_t5_result_normalizer_expansion

## Szerep
Senior coding agent vagy. Projection truth es instance accounting feladatot
vegzel.

## Cel
A normalizer opcionalis `cavity_plan.json` alapjan tuntesse el a virtual parent
ID-kat, expandalja az internal child placementeket es offsetelje a top-level
child instanceeket.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
- `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`
- `canvases/nesting_engine/cavity_t5_result_normalizer_expansion.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t5_result_normalizer_expansion.yaml`

## Engedelyezett modositas
Csak a YAML `outputs` listaja. Ne modosits worker integrationt vagy exportert.

## Szigoru tiltasok
- Virtual part ID nem kerulhet user-facing projectionbe.
- Child quantity/instance nem duplazodhat.
- Cavity plan nelkuli runok viselkedese nem valtozhat.
- Ne oldj cut-ordert ebben a taskban.

## Elvart parancsok
- `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py`
- `python3 scripts/smoke_cavity_t5_result_normalizer_expansion.py`
- `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t5_result_normalizer_expansion.md`

## Stop conditions
Allj meg, ha a `cavity_plan_v1` contract nem elegendo az abszolut transform vagy
instance offset bizonyitasahoz. Ilyenkor T1/T3 contract fixet javasolj.

## Report nyelve es formatuma
A report magyarul keszuljon. Legyen kulon DoD evidence virtual parent mappingre,
internal child transformra, top-level placement offsetre es unplaced offsetre.
