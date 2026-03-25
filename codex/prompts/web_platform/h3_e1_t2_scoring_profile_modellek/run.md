# DXF Nesting Platform Codex Task - H3-E1-T2 Scoring profile modellek
TASK_SLUG: h3_e1_t2_scoring_profile_modellek

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `api/services/project_manufacturing_selection.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/main.py`
- `canvases/web_platform/h3_e1_t2_scoring_profile_modellek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_e1_t2_scoring_profile_modellek.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task csak a scoring profile domain truth-reteget vezeti be.
- A task nem evaluation engine, nem ranking engine, nem comparison projection,
  nem batch orchestration es nem project-level selection.
- A H3 doksiban javasolt minimum H3 truthot vezesd be:
  - `scoring_profiles`
  - `scoring_profile_versions`
- A version rekord minimum konfiguracios payloadjai:
  - `weights_jsonb`
  - `tie_breaker_jsonb`
  - `threshold_jsonb`
  - `is_active`
- A `weights_jsonb` a H3 doksi peldaihoz igazodjon, peldaul olyan kulcsokkal,
  mint `utilization_weight`, `unplaced_penalty`, `sheet_count_penalty`,
  `remnant_value_weight`, `process_time_penalty`,
  `priority_fulfilment_weight`, `inventory_consumption_penalty`.
- Ne talalj ki ebben a taskban vegleges scoring formulamotort, total score
  szamitast vagy batch rankinget.
- Ne vezesd be:
  - `project_scoring_selection`
  - `run_evaluations`
  - `run_ranking_results`
  - `run_batches`
  - `comparison` projection vagy objective-best queryket.
- Ne irj vissza H2 manufacturing truth tablaba (`run_manufacturing_metrics`,
  `run_manufacturing_plans`, `run_manufacturing_contours` stb.).

Implementacios elvarasok:
- Keszits uj migraciot az `app.scoring_profiles` es
  `app.scoring_profile_versions` tablakkal.
- A domain legyen owner-scoped es verziozott.
- Biztosits legalabb `(scoring_profile_id, version_no)` egyediseget.
- Keszits dedikalt `api/services/scoring_profiles.py` service-t.
- A service legalabb ezt tudja:
  - profile create/list/get/update/delete
  - version create/list/get/update/delete
- Validald, hogy idegen owner profile-ja ala ne lehessen verziot letrehozni.
- Keszits dedikalt `api/routes/scoring_profiles.py` route-ot.
- Kotsd be a route-ot az `api/main.py`-ba.
- A route es a service maradjon tisztan profile-domain, ne vegyen at project,
  batch vagy evaluation felelosseget.

A smoke script bizonyitsa legalabb:
- owner-scoped profile letrehozhato;
- version letrehozhato es `version_no` konzisztens;
- a JSON payloadok persisted modon visszaolvashatok;
- idegen owner nem fer hozza mas profile-jahoz;
- owner/profile mismatch hibara fut;
- nincs `project_scoring_selection` truth;
- nincs `run_evaluations`, ranking vagy comparison write;
- nincs H2 truth tabla write.

A reportban kulon nevezd meg:
- milyen mezokkel lett bevezetve a scoring profile truth;
- hogyan valik a scoring explicitte es verziozhatova;
- miert nem resze ennek a tasknak a project-level selection;
- miert nem resze ennek a tasknak az evaluation engine es ranking;
- hogy a H2 manufacturing metrics csak kesobbi inputja lesz a H3-E3
  evaluation enginenek, de itt meg nem hasznaljuk score-szamitasra.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
