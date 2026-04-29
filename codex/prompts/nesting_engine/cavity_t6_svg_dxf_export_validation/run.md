# DXF Nesting Platform Codex Task - Cavity T6 SVG/DXF export validation
TASK_SLUG: cavity_t6_svg_dxf_export_validation

## Szerep
Senior coding agent vagy. Export validaciot vegzel T5 projection truth utan.

## Cel
Bizonyitsd, hogy parent + internal child projection placementek SVG/DXF
artifactokban helyesen megjelennek. Csak akkor modosits exportert, ha a smoke
konkretan hibazik.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
- `worker/result_normalizer.py`
- `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`
- `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`
- `canvases/nesting_engine/cavity_t6_svg_dxf_export_validation.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t6_svg_dxf_export_validation.yaml`

## Engedelyezett modositas
Csak a YAML `outputs` listaja. Exporter kodhoz csak minimalis, smoke-altal
bizonyitott fixet adj.

## Szigoru tiltasok
- Ne implementalj manufacturing cut-ordert.
- Ne hasznalj virtual part ID-t export geometriakent.
- Ne modosits normalizer core logicot.

## Elvart parancsok
- `python3 scripts/smoke_cavity_t6_svg_dxf_export_validation.py`
- `python3 scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`
- `python3 scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t6_svg_dxf_export_validation.md`

## Stop conditions
Allj meg, ha az exporthoz cut-order vagy postprocessor schema dontes kellene.
Ebben a taskban csak geometriai artifact validacio es minimal fix megengedett.

## Report nyelve es formatuma
A report magyarul keszuljon. Ha exporter kod nem valtozott, a report ezt is
evidence-szel mondja ki. Ha valtozott, adj path/line bizonyitekot.
