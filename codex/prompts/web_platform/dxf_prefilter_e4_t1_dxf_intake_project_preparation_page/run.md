# DXF Prefilter E4-T1 Uj DXF Intake / Project Preparation oldal
TASK_SLUG: dxf_prefilter_e4_t1_dxf_intake_project_preparation_page

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `frontend/src/App.tsx`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `api/routes/files.py`
- `api/services/dxf_preflight_runtime.py`
- `canvases/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- `canvases/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **uj DXF Intake / Project Preparation oldal** task. Ne nyiss diagnostics drawer,
  review modal, replace/rerun flow, feature flag, explicit preflight-runs API csalad
  vagy accepted->parts flow scope-ot.
- A `NewRunPage.tsx` legacy run wizardot ne bovitsd prefilter funkciokkal.
- Current-code truth szerint a preflight upload utan automatikusan indul; ne vezess be
  manualis `Start preflight` gombot vagy fake allapotgepet.
- Current-code truth szerint nincs implementalt rules-profile domain; teljes settings
  editor helyett legfeljebb read-only/current defaults blokk vagy placeholder engedett.
- Az intake oldalon canonical `source_dxf` nyelvezetet hasznalj.
- A file-list route bovitese optional legyen; a meglevo file-list fogyasztok ne torjenek.
- A `ProjectDetailPage` maradjon mukodokepes; csak explicit intake CTA-t kapjon.

Modellezesi elvek:
- Az uj oldal route-ja legyen kulon es egyertelmu, javasoltan `/projects/:projectId/dxf-intake`.
- Az uj oldal minimuma:
  - header + vissza link,
  - source DXF upload panel,
  - explicit szoveg arrol, hogy a preflight upload utan automatikusan indul,
  - minimal file-szintu latest preflight statuszlista,
  - read-only/current-defaults blokk a kesobbi settings panel helyenek.
- A file listahoz ne implementalj teljes preflight-runs API-t.
  Ehelyett optional `include_preflight_summary=true` projection eleg a meglevo
  `GET /projects/{project_id}/files` route-ban.
- A minimal latest summary shape legfeljebb ezt tartalmazza:
  - `preflight_run_id`
  - `run_seq`
  - `run_status`
  - `acceptance_outcome`
  - `finished_at`
- A frontend types/api boundary ezt optional mezokent kezelje.
- Az intake oldalon a legacy `stock_dxf` / `part_dxf` toggle ne jelenjen meg;
  a backendnek `source_dxf` menjen.

Kulon figyelj:
- ne nyisd meg elore az E4-T2 settings panel teljes szerkesztoi scope-jat;
- ne nyisd meg elore az E4-T3 reszletes runs table/badges scope-jat;
- ne nyisd meg elore az E4-T4 diagnostics drawer/modal scope-jat;
- ne tamaszkodj kozvetlen Supabase frontend query-re, ha a meglevo backend API
  optional projectionnel eleg a page truth;
- a page legyen kompatibilis a jelenlegi App/Layout/UI stilussal;
- a `ProjectDetailPage` tovabbra is maradjon hasznalhato, csak az intake oldal legyen
  az uj dedikalt belepesi pont.

A reportban kulon nevezd meg:
- miert kellett kulon intake oldal es miert nem a NewRunPage tovabbi foltozasa a helyes irany;
- hogyan jelenik meg az auto-preflight truth az oldalon;
- miert csak optional file-list summary projection keszul es nem teljes preflight API;
- hogyan marad kompatibilis a ProjectDetailPage;
- mit fed le a backend unit teszt es a smoke;
- mi marad kifejezetten E4-T2 / E4-T3 / E4-T4 kesobbi scope-ban.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`

Opcionális, de erosen ajanlott ellenorzes:
- `npm --prefix frontend run build`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
