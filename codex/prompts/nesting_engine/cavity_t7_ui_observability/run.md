# DXF Nesting Platform Codex Task - Cavity T7 UI observability
TASK_SLUG: cavity_t7_ui_observability

## Szerep
Senior full-stack coding agent vagy. UI/API observability taskot vegzel, nem
core nesting implementaciot.

## Cel
DXF Intake es Run Detail feluleten jelenjen meg cavity diagnosztika es prepack
summary, ha a backend metadata ezt bizonyitja.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `api/routes/files.py`
- `api/routes/runs.py`
- `api/services/dxf_preflight_runtime.py`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_acceptance_gate.py`
- `api/services/dxf_geometry_import.py`
- `api/services/part_creation.py`
- `frontend/src/pages/DxfIntakePage.tsx`
- `frontend/src/lib/dxfIntakePresentation.ts`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `canvases/nesting_engine/cavity_t7_ui_observability.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t7_ui_observability.yaml`

## Engedelyezett modositas
Csak a YAML `outputs` listaja. Ne modosits New Run Wizard filteringet es ne
implementalj core cavity logicot.

## Szigoru tiltasok
- Ne allits full hole-aware engine kepesseget.
- Ne mutass cavity summaryt adat nelkul.
- Ne keverd a rejected/review/pending file filteringgel.
- Ne hasznalj in-app magyarazokartyakat a funkcio mukodeserol; csak tenyleges
  status/diagnosztika jelenjen meg.

## Elvart parancsok
- `cd frontend && npm run build`
- Celzott Playwright vagy smoke: `frontend/e2e/cavity_prepack_observability.spec.ts`
  vagy `python3 scripts/smoke_cavity_t7_ui_observability.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t7_ui_observability.md`

## Stop conditions
Allj meg, ha a backend nem ad megbizhato cavity metadata-t, vagy ha a UI csak
talalgatassal tudna summaryt mutatni. Ilyenkor T4/T5 contract fixet javasolj.

## Report nyelve es formatuma
A report magyarul keszuljon. Tartalmazzon API/TS/UI evidence-et, build/test
eredmenyt es explicit kijelentest, hogy New Run Wizard filtering nem valtozott.
