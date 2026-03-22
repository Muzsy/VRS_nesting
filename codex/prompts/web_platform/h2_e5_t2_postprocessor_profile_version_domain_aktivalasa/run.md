# DXF Nesting Platform Codex Task - H2-E5-T2 Postprocessor profile/version domain aktiválása
TASK_SLUG: h2_e5_t2_postprocessor_profile_version_domain_aktivalasa

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `supabase/migrations/20260322020000_h2_e4_t1_snapshot_manufacturing_bovites.sql`
- `api/services/project_manufacturing_selection.py`
- `api/routes/project_manufacturing_selection.py`
- `api/services/run_snapshot_builder.py`
- `api/routes/cut_rule_sets.py`
- `api/routes/cut_contour_rules.py`
- `api/main.py`
- `canvases/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task domain-aktiválási task, nem exporter, nem adapter,
  nem machine-ready artifact es nem preview/frontend feladat.
- Ne talalj ki nem letezo `machine_catalog`, `material_catalog` vagy mas
  catalog-FK vilagot. A repo jelenlegi mintaja text-kodokkal es owner-scoped
  domain truth-tal dolgozik; ezt kovessed.
- Ne hozz letre uj project-level postprocess selection tablat.
  A postprocessor selection a `manufacturing_profile_versions` resze maradjon.
- A `manufacturing_profile_versions.active_postprocessor_profile_version_id`
  referencia legyen nullable es owner-konzisztens.
- A postprocessor domain minimalis legyen, de mar valos CRUD + version truth.
- A snapshot-first elv maradjon ervenyben: ha van aktiv, owner-valid
  postprocessor ref, azt a `run_snapshot_builder` snapshotolja; exporter meg
  tovabbra se induljon.
- Ne irj `run_artifacts` export bundle-t, ne vezess be machine-neutral exportot,
  es ne alkalmazd a postprocessor configot a toolpathra.

Implementacios elvarasok:
- Vezesd be a minimalis owner-scoped tablakat:
  - `app.postprocessor_profiles`
  - `app.postprocessor_profile_versions`
- Valassz egyetlen, kovetkezetes konfiguracios JSONB mezonevet a version
  szintre; ne hozz letre parhuzamos `config_jsonb` es `settings_jsonb` vilagot.
- A profile/version mezok legyenek repo-huek es a H2 feladathoz elegendoek:
  legalabb `adapter_key`, `output_format`, `schema_version`, `is_active`,
  `version_no`, notes/metadata jellegu mezok.
- Keszits owner-scoped CRUD service-t es route-ot a postprocessor domainhez,
  lehetőleg nested version route-tal.
- Frissitsd a `project_manufacturing_selection` read-pathot, hogy a kapcsolt
  `active_postprocessor_profile_version_id` lathato legyen.
- Frissitsd a `run_snapshot_builder`-t:
  - ref nelkul maradjon `postprocess_selection_present=false` es
    `includes_postprocess=false`;
  - aktiv refnel legyen `postprocess_selection_present=true` es
    `includes_postprocess=true`;
  - a snapshot tartalmazza legalabb az aktiv postprocessor version alap meta-it.

A smoke script bizonyitsa legalabb:
- postprocessor profile es version owner-scoped CRUD mukodik;
- version csak a sajat profile alatt kezelheto;
- manufacturing profile version csak ugyanazon owner postprocessor versionjere
  mutathat;
- idegen owner ref elutasitodik;
- a selection read-path visszaadja a postprocessor refet;
- a snapshot builder helyesen allitja a postprocess flag-eket;
- nincs export/adaptor scope;
- nincs nem letezo catalog-FK vilag.

A reportban kulon nevezd meg:
- hogyan lett a postprocessor domain minimalisan, de valosan aktiválva;
- miert nem kellett uj project-level postprocess selection tabla;
- hogyan van vedve az owner-konzisztencia a manufacturing -> postprocessor refnel;
- hogyan valt at a snapshot placeholder valos selectionre;
- hogy mit NEM szallit le meg a task:
  - machine-neutral exporter,
  - machine-specific adapter,
  - machine-ready artifact,
  - postprocessor-config alkalmazas a toolpathra.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
