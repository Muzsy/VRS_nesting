# DXF Nesting Platform Codex Task - H0-E2-T3 technology domain alapok
TASK_SLUG: h0_e2_t3_technology_domain_alapok

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e2_t3_technology_domain_alapok.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e2_t3_technology_domain_alapok.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql
- supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope tovabbra is kontrollalt:
  most csak a technology domain alap tablavilaga johet letre.
- Part/file/revision/run/remnant/export/manufacturing package vilag nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo H0-E2-T1/T2 migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- Kulonitsd el a reusable technology catalog/preset vilagot a projekt-szintu
  technology setup/profile vilagtol.
- A projekt technology setup elo konfiguracios truth, nem snapshot.
- A kesobbi run snapshot ezt masolja majd immutable futasi inputta.
- Ne csinalj altalanos JSON dump tablat, ha a fo technology parametereknek
  mar most van stabil domain jelentese.

Kulon figyelj:
- ne hozz letre part definition, file metadata, geometry, revision, run,
  snapshot, remnant, export vagy manufacturing package tablat;
- ne keruljon bele RLS policy;
- ne keverd a preset catalog truth-ot a project-bound truth-tal;
- ha a fo architecture/H0 doksiban a technology tablairany meg pontatlan vagy
  stale, azt minimalisan szinkronizald.

A reportban kulon nevezd meg:
- a technology preset tabla vegleges oszlopait;
- a project technology setup tabla vegleges oszlopait;
- az FK kapcsolatokat;
- az indexeket;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md

Ez frissitse:
- codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md
- codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.