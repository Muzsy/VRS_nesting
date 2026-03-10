# DXF Nesting Platform Codex Task - H0-E2-T1 enumok es core schema letrehozasa
TASK_SLUG: h0_e2_t1_enumok_es_core_schema_letrehozasa

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e2_t1_enumok_es_core_schema_letrehozasa.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez mar nem docs-only task, de a scope tovabbra is szuk:
  most csak schema + extension + enum migracio johet letre.
- Domain tablakat most ne hozz letre.
- RLS, trigger, storage, worker queue, API kod most nincs scope-ban.
- A `api/sql/phase1_schema.sql` legacy bootstrap fajlt ebben a taskban ne moditsd.

Modellezesi elvek:
- A H0-E1-T1/T2/T3 dokumentumok az elsosegi forrasok.
- Ne masold vakon a korabbi egyszerusitett SQL-peldat, ha az ellentmond a
  snapshot-first run/request/attempt logikanak.
- Ha a vegleges enum-model miatt a fo architecture/H0 dokumentumban stale vagy
  leegyszerusitett SQL-resz maradna, azt minimalisan szinkronizald.
- A migracio legyen egyertelmuen bazis H0-E2-T1 migracio, es maradjon additiv,
  duplicate-safe iranyban.
- Schema-qualified neveket hasznalj (`app.xyz`).

Kulon figyelj:
- ne hozz letre meg `profiles`, `projects`, `project_settings`, `run_*` vagy mas
  domain tablat;
- a report kulon nevezze meg a vegleges enum inventoryt;
- a report kulon jelezze, hogy a task szandekosan NEM hozott letre meg tablakepet.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md

Ez frissitse:
- codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md
- codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.