# DXF Nesting Platform Codex Task - H3-E1-T1 Run strategy profile modellek
TASK_SLUG: h3_e1_t1_run_strategy_profile_modellek

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql`
- `api/services/postprocessor_profiles.py`
- `api/routes/postprocessor_profiles.py`
- `api/routes/run_configs.py`
- `api/main.py`
- `canvases/web_platform/h3_e1_t1_run_strategy_profile_modellek.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_e1_t1_run_strategy_profile_modellek.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez strategy-domain task, nem scoring task, nem project-selection task,
  nem batch/ranking task, es nem snapshot-integracios task.
- Ne talalj ki nem letezo `machine_catalog`, `material_catalog`, scoring vagy
  selection tablakat. A jelen taskban csak a strategy profile + version truth
  johet letre.
- Ne tervezd ujra a legacy `run_configs` vilagot. A strategy domain kulon truth,
  a `run_configs` legfeljebb kontrollminta lehet.
- Ne modositd a `run_snapshot_builder`, `run_creation`, `runs` vagy worker
  fo folyamatot pusztan azert, hogy a strategy runtime mar most aktivalodjon.
- A T1 backlog DoD-ben szereplo "projektbol valaszthato" megfogalmazast ugy
  kezeld, hogy a domain mar listazhato/CRUD-olhato valasztasi jelolt legyen,
  de a persisted `project_run_strategy_selection` csak H3-E1-T3-ban johet.

Implementacios elvarasok:
- Vezesd be a minimalis owner-scoped tablakat:
  - `app.run_strategy_profiles`
  - `app.run_strategy_profile_versions`
- A profile szint tartalmazzon legalabb:
  - `strategy_code`, `display_name`, `description`, `lifecycle`, `is_active`,
    `metadata_jsonb`
- A version szint tartalmazzon legalabb:
  - `version_no`, `lifecycle`, `is_active`,
    `solver_config_jsonb`, `placement_config_jsonb`,
    `manufacturing_bias_jsonb`, `notes`, `metadata_jsonb`
- A schema legyen owner-konzisztens, H2-minta szerinti composite FK-val vagy
  azzal ekvivalens adatbazis-vedelemmel.
- Keszits owner-scoped CRUD service-t es route-ot a strategy domainhez,
  nested version route-tal.
- Regisztrald a route-ot az `api/main.py`-ban.

A smoke script bizonyitsa legalabb:
- strategy profile owner-scoped CRUD mukodik;
- nested version CRUD mukodik;
- version_no novekszik;
- idegen owner nem tud masik owner profile-ja alatt verziot letrehozni vagy
  adatot olvasni/modositani;
- nem jon letre scoring vagy project-selection side effect;
- nincs snapshot-builder vagy run-creation write side effect.

A reportban kulon nevezd meg:
- hogyan lett a strategy domain kulon truth reteggé emelve;
- miben kulonbozik a technology / manufacturing / scoring vilagtol;
- hogyan lett vedve az owner-konzisztencia a profile es version kozott;
- miert marad out-of-scope ebben a taskban:
  - `project_run_strategy_selection`,
  - scoring profile domain,
  - batch/orchestrator,
  - evaluation/ranking,
  - runtime strategy-alkalmazas a snapshotban vagy a workerben;
- hogyan kell ertelmezni a T1 rovid DoD-jet a T3 selection task fenyeben.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t1_run_strategy_profile_modellek.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
