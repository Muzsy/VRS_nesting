# DXF Nesting Platform Codex Task - H2-E4-T1 Snapshot manufacturing bovites
TASK_SLUG: h2_e4_t1_snapshot_manufacturing_bovites

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
- `api/services/run_snapshot_builder.py`
- `api/services/run_creation.py`
- `api/services/project_manufacturing_selection.py`
- `canvases/web_platform/h2_e4_t1_snapshot_manufacturing_bovites.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e4_t1_snapshot_manufacturing_bovites.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A jelenlegi repoban a `manufacturing_manifest_jsonb` meg H1 placeholder.
  Ezt most valos snapshot adattá kell emelni, de a scope maradjon szuk.
- A task explicit project manufacturing selection snapshotolasa, nem resolver.
  Ne probalj manufacturing profile -> cut rule set vagy postprocessor feloldast
  kitalalni, ha arra nincs valos FK/schema lanc.
- A jelenlegi repoban nincs tenyleges postprocessor domain implementacio.
  Ezert a taskban az `includes_postprocess` explicit `false` marad, es a
  postprocess allapot csak placeholder lehet.
- A task ne nyisson ki:
  - manufacturing resolver scope-ot,
  - rule matching scope-ot,
  - manufacturing plan builder scope-ot,
  - preview/export scope-ot.
- A H1 kompatibilitas fontos: manufacturing selection hianya ne torje el a run
  snapshot epiteset. Ilyenkor tiszta, determinisztikus `selection_present=false`
  manifest kell, nem hiba.
- A snapshot hashnek tartalmaznia kell a manufacturing manifest valtozasat, hogy
  kulonbozo selection kulonbozo snapshot hash-t adjon.

Implementacios fokusz:
- Vezess be minimalis snapshot schema meta mezo(ke)t a `nesting_run_snapshots`
  tablaban.
- Frissitsd a `run_snapshot_builder.py`-t, hogy a project manufacturing selectiont
  owner-scope-ban beolvassa es snapshotolja.
- Ha kell, igazitsd a `run_creation.py` snapshot fetch/insert retegét az uj mezokhoz.
- Ne modositd a H2-E4-T2 vagy kesobbi manufacturing plan vilagot.

A smoke script bizonyitsa legalabb:
- selection absent -> snapshot epul, includes_manufacturing=false;
- selection present -> manufacturing profile version snapshotolva;
- includes_postprocess=false;
- selection change -> snapshot hash change;
- nincs manufacturing plan / persisted H2-E4-T2 iras.

A reportban kulon nevezd meg:
- mit snapshotol a task;
- mit NEM snapshotol meg:
  - postprocessor selection domain,
  - rule-set resolver,
  - manufacturing plan,
  - export;
- milyen placeholder marad tudatosan a jelenlegi repoallapot miatt.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t1_snapshot_manufacturing_bovites.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
