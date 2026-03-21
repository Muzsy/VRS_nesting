# DXF Nesting Platform Codex Task - H2-E1-T2 Project manufacturing selection
TASK_SLUG: h2_e1_t2_project_manufacturing_selection

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `api/routes/projects.py`
- `api/services/run_snapshot_builder.py`
- `api/main.py`
- `canvases/web_platform/h2_e1_t2_project_manufacturing_selection.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e1_t2_project_manufacturing_selection.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A jelenlegi repoban a manufacturing profile domain meg nincs tenylegesen
  implementalva a migraciokban. Ez a task a H2-E1-T1 utan ertelmezett.
  A T2 feladata nem a teljes manufacturing profile CRUD ujraepitese, hanem a
  projekt-szintu selection truth leszallitasa.
- Ha a H2-E1-T1 implementacio mar tartalmazza az
  `app.project_manufacturing_selection` tablat, ne duplikald; csak a
  minimalisan szukseges hardeninget vagy bekotest vegezd el.
- Ha a tabla meg nincs meg, ez a task hozza letre a minimalis selection truth-ot.
- Ne talalj ki nem letezo gepkatalogus / anyagkatalogus vagy schema mezoket.
  A technology/manufacturing konzisztencia ellenorzes csak a valos, tenylegesen
  elerheto schema alapjan tortenhet.
- A task ne modositja a manufacturing snapshot / manufacturing manifest /
  run plan / preview / postprocess reteget.
- A `api/services/run_snapshot_builder.py` itt boundary-fajl: ezt a taskot nem
  szabad snapshot-integracios iranyba bovitett scope-pal elvinni.

Implementacios elvarasok:
- Vezess be minimalis project-level selection truth-ot.
- Keszits explicit `api/services/project_manufacturing_selection.py` service-t.
- Keszits minimalis `api/routes/project_manufacturing_selection.py` route-okat,
  es kotd be az `api/main.py`-ba.
- A selection viselkedese legyen egyertelmu create-or-replace projekt-szinten.
- A validacio ellenorizze:
  - projekt owner scope,
  - manufacturing profile version owner scope,
  - ha a valos schema tartalmaz ilyet, akkor aktiv statusz,
  - ha a valos schema tenylegesen lehetove teszi, minimalis technology /
    manufacturing konzisztencia.
- A smoke script bizonyitsa a fo sikeres es hibas agakat.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H2-E1-T2 selection flowhoz;
- hogy mit NEM szallit le meg:
  - manufacturing profile CRUD kibovitese,
  - snapshot manufacturing bővites,
  - manufacturing resolver,
  - manufacturing plan builder,
  - preview / postprocess / export;
- ha a valos T1 schema mellett valamilyen konzisztencia-ellenorzes nem volt
  megbizhatoan implementalhato, azt explicit korlatkent dokumentald.

A vegén futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
