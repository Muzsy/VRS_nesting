# DXF Nesting Platform Codex Task - H2-E4-T2 Manufacturing plan builder
TASK_SLUG: h2_e4_t2_manufacturing_plan_builder

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
- `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
- `api/services/run_snapshot_builder.py`
- `api/services/cut_rule_matching.py`
- `api/services/geometry_contour_classification.py`
- `worker/main.py`
- `worker/result_normalizer.py`
- `canvases/web_platform/h2_e4_t2_manufacturing_plan_builder.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e4_t2_manufacturing_plan_builder.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A task snapshot-first marad: a manufacturing plan builder a runhoz tartozo
  snapshot truthra es a persisted run projection tablákra epul. Ne olvass live
  `project_manufacturing_selection` allapotot.
- A jelenlegi repoban nincs bizonyitott, stabil resolver-lanc a snapshotolt
  manufacturing profile version es a cut rule set kozott. Ezert a builder
  explicit `cut_rule_set_id` inputot kap. Ne talalj ki rejtett resolver logikat.
- A task hasznalja a meglvo `api/services/cut_rule_matching.py` service-t.
  Ne duplikald a matching logikat masik helyen.
- A task hasznalja a manufacturing derivative + contour classification truth-ot.
  Ne essen vissza `nesting_canonical` vilagra.
- A task persisted plan truthot epitsen:
  - `run_manufacturing_plans`
  - `run_manufacturing_contours`
- A task ne irjon vissza:
  - `geometry_contour_classes`
  - `cut_contour_rules`
  - `project_manufacturing_selection`
  - vagy mas korabbi truth tablaba.
- A task ne nyisson ki:
  - preview SVG scope-ot,
  - postprocessor domain aktivaciot,
  - export artifactot,
  - machine-ready emit logikat.
- `run_artifacts` iranyba ebben a taskban ne keruljon uj artifact.

Implementacios fokusz:
- Vezesd be a persisted manufacturing plan tablakat.
- Keszits dedikalt `api/services/manufacturing_plan_builder.py` service-t.
- A service owner-scope-ban validalja a run elerhetoseget.
- A service a snapshot `manufacturing_manifest_jsonb` alapjan nyerje ki a
  `manufacturing_profile_version_id`-t, de a `cut_rule_set_id` explicit input maradjon.
- A service a `run_layout_sheets` es `run_layout_placements` tablakat olvassa,
  a `part_revisions.selected_manufacturing_derivative_id` mezot hasznalja, es
  a matching eredmenybol plan/contour rekordokat general.
- A `entry_point_jsonb`, `lead_in_jsonb`, `lead_out_jsonb` csak alap,
  gepfuggetlen meta legyen. Ne generalj machine-ready geometriat.
- A persisted viselkedes legyen idempotens: ugyanazon run ujrageneralasakor
  ne maradjon duplikalt per-sheet plan reteg.

A smoke script bizonyitsa legalabb:
- valid inputbol plan keletkezik;
- contour rekordok matched rule hivatkozast kapnak;
- explicit `cut_rule_set_id` nelkul hiba jon;
- nincs write korabbi truth tablaba;
- nincs preview/export artifact;
- deterministic rebuild nem hagy duplikaciot.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H2-E4-T2 plan reteghez;
- hogy mit NEM szallit le meg:
  - manufacturing preview,
  - postprocessor adapter,
  - machine-neutral export,
  - machine-specific export;
- hogy a jelenlegi repoallapotban miert explicit `cut_rule_set_id` input a
  helyes megoldas a rejtett resolver helyett.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
