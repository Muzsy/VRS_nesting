# DXF Prefilter E2-T1 Preflight inspect engine V1
TASK_SLUG: dxf_prefilter_e2_t1_preflight_inspect_engine_v1

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/dxf_validation.py`
- `api/routes/files.py`
- `tests/test_dxf_importer_json_fixture.py`
- `tests/test_dxf_importer_error_handling.py`
- `scripts/smoke_dxf_import_convention.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **inspect-only backend task**. Ne vezess be repair, role resolver, acceptance gate,
  DB persistence, API route vagy frontend valtoztatast.
- Ne talalj ki uj parhuzamos DXF parser logikat az `api/services/` alatt. A meglvo
  `vrs_nesting/dxf/importer.py` legyen a nyers source olvasas egyetlen truth-ja.
- Ha inspect helper kell, azt minimalis, visszafele kompatibilis public feluletkent
  nyisd ki az importerben.
- Ne torj vissza a jelenlegi `import_part_raw()` acceptance vilagban: a mai smoke-ok es
  importer testek szemantikaja maradjon stabil.
- Ne nyisd meg idovel elott a `api/routes/files.py` es `api/services/dxf_geometry_import.py`
  preflight bekoteset; az E3 scope feladata.
- Ne keverd ossze a nyers inspect diagnostikat a future canonical user-facing error cataloggal;
  az E1-T7 es a kesobbi E3/E4 feladatokra marad.

Modellezesi elvek:
- A T1 inspect result a nyers megfigyeles truth-ja, nem vegso dontes.
- A role assignment (`CUT_OUTER`/`CUT_INNER`/`MARKING`) a T2 feladata; itt legfeljebb
  outer-like / inner-like topology-jeloltek szulethetnek.
- A color/linetype inventory itt raw signal legyen, ne policyvel ertelmezett canonical szerep.
- Ha a source backend nem ad explicit szin/linetype erteket, az inspect kimenet ezt
  determinisztikus hianyjelzessel kezelje; ne talalj ki RGB/ACI policyt.
- A service ne csinaljon auto-javitast, gap zarast vagy deduplikacios modositast;
  csak jelolteket listazzon.

Kulon figyelj:
- a JSON fixture backend maradjon elsoosztalyu deterministic tesztforras;
- a smoke es unit teszt ne fuggjon kotelezoen a real `ezdxf` backendtol;
- a `diagnostics` objektum kulon retegen maradjon az inventory/candidate mezokhoz kepest;
- a reportban nevezd meg egyertelmuen, hogy mi oldodott meg T1-ben, es mi marad T2/T3/T4/T5/T6 scope-ban.

A reportban kulon nevezd meg:
- mely importer helper felulet nyilt ki a taskban;
- hogyan maradt visszafele kompatibilis a `import_part_raw()`;
- milyen raw signalokat visz tovabb mostantol az inspect result;
- milyen deterministic bizonyitekok vannak a unit tesztben es a smoke-ban;
- mi maradt kifejezetten a kovetkezo taskokra.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
