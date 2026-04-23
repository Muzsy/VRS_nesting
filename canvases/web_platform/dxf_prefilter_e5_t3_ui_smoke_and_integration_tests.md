# DXF Prefilter E5-T3 — UI smoke / integration tesztek

## Cel
A taskbontas szerint a DXF-E5-T3 celja a legfontosabb intake flow-k ellenorzese, es a DoD az,
hogy a **beallitas -> preflight -> diagnostics -> tovabbengedes** flow ne torjon. A jelenlegi
repo-grounded truth mellett ez nem jelent full backend E2E-t, mert azt az E5-T2 mar lefedi.
Az E5-T3 helyes szerepe most egy **browser-level, mock API-ra epulo UI smoke / integration pack**
a `DxfIntakePage` korul.

A mai kodban mar megvan:
- kulon `DxfIntakePage` route a project detail oldalrol;
- upload-session szintu preflight settings panel;
- upload finalize bridge a `rules_profile_snapshot_jsonb` payloadra;
- latest preflight runs table status / issue / repair / acceptance badge-ekkel;
- diagnostics drawer/modal a persisted latest diagnostics projectionra.

Az E5-T3 celja ezert nem uj product logika, hanem annak browser-szintu bizonyitasa, hogy a
**settings -> upload finalize -> latest preflight summary -> diagnostics drawer -> accepted "ready for next step" jelzes**
lanc a jelenlegi frontenden nem torik el.

## Miert most?
A jelenlegi repo-grounded helyzet:
- az E5-T2 mar route-level API E2E packban bizonyitja a `complete_upload -> BackgroundTasks -> runtime -> list_project_files` lancot;
- az E4-T1→T4 mar felépitette a `DxfIntakePage` user-facing V1 feluletet;
- viszont nincs kulon UI smoke/integration pack, amely a browserben ellenorzi:
  - a settings panel valodi payload bridge-et,
  - a latest runs table rendereleset,
  - a diagnostics drawer megnyithatosagat,
  - es az accepted/review/rejected vizualis kulonbsegeket.

A helyes E5-T3 scope ezert:
**dedikalt Playwright-alapu DXF intake UI smoke/integration pack a meglovo mock API harnessre epitve,
uj frontend framework, uj backend endpoint vagy valodi Supabase/API fuggoseg nelkul.**

## Scope boundary

### In-scope
- Uj, dedikalt Playwright spec a `DxfIntakePage` koruli legfontosabb V1 flow-kra.
- A meglovo `frontend/e2e/support/mockApi.ts` bovitese annyira, hogy a DXF intake flow current-code truthja
  browserbol tesztelheto legyen:
  - `latest_preflight_summary`
  - `latest_preflight_diagnostics`
  - `rules_profile_snapshot_jsonb` request payload capture
  - source_dxf upload finalize utani state frissites
- Minimum UI scenario-k:
  - settings panel -> upload finalize bridge
  - accepted latest run -> diagnostics drawer megnyitas
  - non-accepted latest run(ok) -> helyes badge / recommended action rendereles
- Task-specifikus structural smoke a Playwright spec + mockApi bridge jelenletere.
- Frontend build evidence.
- Checklist + report evidence frissitese.

### Out-of-scope
- Uj frontend tesztframework (Vitest, Cypress, RTL component test stack, stb.).
- Valodi backend/API/Supabase inditasa a UI tesztekhez.
- E5-T2 route-level API E2E ujrairasa.
- Uj backend endpoint vagy query parameter kitalalasa.
- Review modal / decision flow (E4-T5).
- Accepted->parts valodi tovabblepes vagy mutacio (E4-T6).
- UX copy/visual redesign task.
- `NewRunPage.tsx` vagy mas legacy oldal bovítese.

## Talalt relevans fajlok (meglevo kodhelyzet)
- Frontend page:
  - `frontend/src/pages/DxfIntakePage.tsx`
- Frontend route:
  - `frontend/src/App.tsx`
  - `frontend/src/pages/ProjectDetailPage.tsx`
- Frontend API/types:
  - `frontend/src/lib/api.ts`
  - `frontend/src/lib/types.ts`
  - `frontend/src/lib/supabase.ts`
- Meglevo Playwright harness:
  - `frontend/playwright.config.ts`
  - `frontend/e2e/support/mockApi.ts`
  - `frontend/e2e/phase4.stable.spec.ts`
  - `frontend/e2e/phase4.async.spec.ts`
- Kapcsolodo backend/API truth dokumentacio:
  - `canvases/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`
  - `canvases/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`
  - `canvases/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`
  - `canvases/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md`

## Jelenlegi repo-grounded helyzetkep

### 1. A helyes E5-T3 nem backend E2E, hanem browser-level integration
Az E5-T2 mar route-level E2E-kent bizonyitja a finalize -> runtime -> persistence -> projection lancot.
Az E5-T3-ben ezt nem szabad ujra backend-oldalon ujrajatszani. A helyes current-code truth most az,
hogy a browserben, auth bypass + mock API mellett ellenorizzuk a `DxfIntakePage` viselkedeset.

### 2. A frontend mar Playwrightot hasznal
A repo frontendje mar tartalmaz:
- Playwright configot,
- auth bypass modot (`VITE_E2E_BYPASS_AUTH=1`),
- mock API support layert.
Ezert E5-T3-ban anti-pattern lenne uj tesztframeworkot behozni.

### 3. A "tovabbengedes" current-code truth szerint meg csak advisory allapot
A taskbontas DoD-je a "tovabbengedes" szot hasznalja, de a mai repo-ban nincs meg az E4-T6 accepted->parts flow.
Ezert az E5-T3 helyes, szukitett igazsaga most ez:
- accepted file eseten a UI **accepted badge + recommended action = ready_for_next_step** jelzest mutat;
- ezt kell browser-szinten bizonyitani,
- nem szabad kitalalni hozza uj "Create parts" gombot vagy navigationt.

### 4. A settings panel kulcsa a finalize payload bridge
A `DxfIntakePage` jelenleg upload-session draftbol epiti a `rules_profile_snapshot_jsonb` payloadot, es ezt a
`completeUpload(...)` hivaskor kuldi el. Az E5-T3 egyik fo erteke az, hogy ezt browserbol is bizonyitja,
nem csak route/unit teszt szinten.

### 5. A diagnostics drawer persisted latest diagnostics truthra ul
A drawer mar nem future idea, hanem current-code UI. A tesztnek ezt kell bizonyitania:
- a file-list row action megnyithato,
- a drawer a vart fo blokkokat megjeleniti,
- a latest diagnostics payloadot fogyasztja,
- es non-mutating marad.

## Konkret elvarasok

### 1. Szülessen uj, dedikalt Playwright spec
Javasolt uj fajl:
- `frontend/e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts`

A spec ne a phase4 fajlokba csuszzon bele, hanem kulon, neven nevezett DXF prefilter UI pack legyen.

### 2. A meglovo mock API harness bovuljon DXF intake current-code truthra
A `frontend/e2e/support/mockApi.ts` current-code truth szerint bovuljon annyira, hogy a DXF intake UI tesztekhez
determinista fake allapotot tudjon adni. Minimum:
- `MockFile` optional `latest_preflight_summary` es `latest_preflight_diagnostics` mezokkel;
- a `POST /projects/{projectId}/files` finalize body-bol a `rules_profile_snapshot_jsonb` payload capture-je;
- a testek szamara visszaolvashato request history / uploaded finalize bodies;
- source_dxf upload finalize utan a file-list state frissitese;
- lehetoseg accepted/review_required/rejected latest preflight summary payload seedelesere.

Ne talalj ki valodi backend futast vagy background runtime-ot a browser tesztbe.
A mock csak annyit tudjon, amennyi a UI flow deterministic ellenorzeshez kell.

### 3. Minimum scenario matrix

#### a) Settings panel -> upload finalize bridge
- nyisd meg a `DxfIntakePage`-et egy seedelt projektre;
- allits be nem-default preflight settings ertekeket;
- uploadolj source DXF-et a page sajat uploaderen keresztul;
- bizonyitsd, hogy a finalize requestben a `rules_profile_snapshot_jsonb` a vart ertekekkel ment ki;
- a file-list frissuljon, es a user latja az upload completion allapotot.

#### b) Accepted latest run -> diagnostics drawer
- seedelj egy file-t accepted latest preflight summary + diagnostics payload-dal;
- a tabla mutassa az accepted badge-et es a `Ready for next step` ajanlast;
- a `View diagnostics` akcio nyissa meg a drawer/modal nezetet;
- bizonyitsd a fo blokkokat:
  - Source inventory
  - Role mapping
  - Issues
  - Repairs
  - Acceptance
  - Artifacts

#### c) Non-accepted latest run(ok) -> helyes vizualis kulonbseg
- seedelj legalabb egy review_required vagy rejected file-t;
- a tabla mutassa a megfelelo acceptance badge-et es ajanlott kovetkezo lepest;
- ne jelenjen meg teves accepted/ready-for-next-step jelzes;
- ha van diagnostics payload, a drawer megnyithato maradjon.

### 4. A spec current-code truth szerint maradjon UI-level integration
Ne hasznalj:
- valodi backendet,
- valodi Supabase sessiont,
- uj query parametert vagy endpointot,
- ad hoc `page.route` dzsungelt minden tesztben, ha a meglovo `installMockApi(...)` bridge bovitese eleg.

A preferalt minta:
- `await installMockApi(page, options?)`
- state seedeles
- browser interaction
- request capture es DOM assertion

### 5. A diagnostics es tovabbengedesi allitasok ne menjenek tul a mai kodon
A tesztek ne allitsanak tobbet a termekrol, mint ami ma igaz:
- diagnostics drawer read-only;
- artifact blokk local reference lista;
- accepted state csak advisory `Ready for next step`, nem valodi part-creation flow.

### 6. Keszuljon task-specifikus structural smoke
Javasolt uj fajl:
- `scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`

A smoke minimum bizonyitsa:
- az uj Playwright spec file letezik;
- a spec a `DxfIntakePage` flowra epul;
- a `installMockApi` harness hasznalata explicit;
- van settings/upload bridge assertion;
- van accepted diagnostics drawer scenario;
- van non-accepted status scenario;
- nincs uj backend endpoint / UI redesign / accepted->parts scope.

### 7. Verifikacio
Minimum futtasok:
- `python3 -m py_compile scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`
- `npm --prefix frontend run build`
- `cd frontend && npx playwright test e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts`
- `python3 scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md`

A report kulon terjen ki erre:
- miert browser-level mocked UI integration a helyes E5-T3 current-code truth, nem backend E2E es nem uj tesztframework;
- hogyan bizonyitja a pack a settings -> finalize payload bridge-et;
- hogyan bizonyitja a diagnostics drawer legfontosabb blokkjait;
- hogyan ertelmezi current-code truth szerint a "tovabbengedest" accepted advisory allapotkent.

## DoD
- [ ] Van uj, dedikalt Playwright spec a DXF intake/preflight V1 flowkra.
- [ ] A meglovo mock API harness current-code truth szerint tudja seedelni a latest preflight summary/diagnostics vilagot es capture-olja a finalize settings payloadot.
- [ ] Browserbol bizonyitott a settings -> upload finalize bridge.
- [ ] Browserbol bizonyitott az accepted latest run tablazat + diagnostics drawer fo blokkjai.
- [ ] Browserbol bizonyitott legalabb egy non-accepted latest run vizualis allapota.
- [ ] Nem nyilt uj endpoint, uj tesztframework vagy accepted->parts future scope.
- [ ] Van task-specifikus structural smoke.
- [ ] A frontend build es a celzott Playwright futas dokumentaltan lefutott.

## Erintett fajlok (tervezett)
- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts`
- `scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`
- `canvases/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests/run.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md`
- `codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md`
- `codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.verify.log`
