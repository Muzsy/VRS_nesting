# DXF Prefilter E1-T3 Policy matrix es rules profile schema
TASK_SLUG: dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `vrs_nesting/dxf/importer.py`
- `api/routes/files.py`
- `api/config.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
- `canvases/web_platform/dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez **docs-only policy/schema freeze** task. Ne vezess be Python, TypeScript,
  SQL, migration, enum, route, service vagy UI implementacios valtoztatast.
- Ne talalj ki mar implementaltkent olyan `rules_profile` vagy `preflight_settings`
  mezot, tablát vagy endpointot, amely jelenleg meg nem letezik a repoban.
- Ne csusztasd at a taskot data model, state machine vagy API payload veglegesitesbe.
- A dokumentumnak a jelenlegi kodra kell epulnie: importer, files route, config,
  upload UI entrypointok es a repoban mar letezo profile/version mintak konkret
  figyelembevetelevel.

A dokumentacios elvarasok:
- Kulonitsd el a **policy matrix** es a **rules profile schema** szerepet.
- Rogzitsd, hogy a canonical role a truth, a szin pedig input-hint policy mezo.
- Rogzitsd a V1 minimum rules profile mezoket.
- Rogzitsd kulon, hogy mi current-code truth, mi future canonical contract,
  es mi later extension.
- Rogzitsd a default / override / review-required alapmodellt docs-szinten.
- Nevezd meg, hogy a future rules profile domain szerkezetileg igazodhat a repo
  profile/version mintaihoz, de ebben a taskban nincs migration vagy CRUD.
- Legyen explicit anti-scope lista, hogy mit nem fagyaszt le ez a task.

A reportban nevezd meg kulon:
- melyik meglevo fajlokra epul a policy/schema dokumentum;
- mely mezok tekinthetok V1 minimum contractnak;
- mely policy teruletek maradnak kesobbi extensionnek;
- miert fontos a policy matrix es a rules profile schema kulonvalasztasa a
  kovetkezo taskokhoz.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
