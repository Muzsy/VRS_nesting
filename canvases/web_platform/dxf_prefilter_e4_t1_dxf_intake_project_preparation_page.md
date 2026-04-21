# DXF Prefilter E4-T1 — Uj DXF Intake / Project Preparation oldal

## Cel
A DXF prefilter lane-ben az E3-T3 utan a backend upload -> preflight ->
geometry-import gate lanc mar tenylegesen mukodik, de a frontend oldalon ma
meg mindig ket legacy belepesi pont van:
- `ProjectDetailPage.tsx` kezeli az uploadot es a file listat,
- `NewRunPage.tsx` egy regi run wizard,
- es egyik sem preflight/intake szemleletu felulet.

Az E4-T1 celja egy **kulon, dedikalt DXF Intake / Project Preparation oldal**
bevezetese, amely az uj prefilter lane frontend belepesi pontja lesz.
A task celja most **nem** teljes diagnostics UX, nem review modal, nem rules
profile editor, hanem a helyes oldal, route es minimalis read-model megteremtese
ugy, hogy a user mar ne a ProjectDetail upload blokk + legacy wizard
kombinaciobol probalja osszerakni a preflight folyamatot.

## Miert most?
A jelenlegi, kodbol igazolt helyzet:
- `api/routes/files.py` source DXF finalize utan automatikusan inditja a
  `run_preflight_for_upload(...)` runtime-ot;
- az E3-T3 ota a geometry import mar csak gate-pass utan indul;
- a preflight truth perzisztalva van `app.preflight_runs` /
  `app.preflight_artifacts` tablaban;
- ugyanakkor a frontend oldalon ma nincs olyan oldal, amely ezt a folyamatot
  nevezi meg es rendezi ossze;
- a `NewRunPage.tsx` tovabbra is legacy run-config wizard, amit az E1 docs mar
  explicit anti-iranykent rogzitett;
- a `ProjectDetailPage.tsx` uploadot tud, de nincs rajta dedikalt preflight
  statusz- vagy project-preparation allapotgep.

Az E4-T1 helyes szerepe ezert:
1. legyen uj, dedikalt belepesi pont az intake/preparation vilagnak;
2. a user itt tolthessen fel **source DXF** fajlokat a canonical nyelvezettel;
3. a user lassa legalabb a legfrissebb preflight allapotot file-szinten;
4. legyen helye a kovetkezo UI taskoknak (settings panel, runs table,
   diagnostics drawer), de azokat ez a task meg ne nyissa meg.

## Scope boundary

### In-scope
- Uj frontend oldal bevezetese a DXF intake / project preparation feladatra.
- Uj frontend route bekotese az App routerben.
- A `ProjectDetailPage`-rol egyertelmu navigacios belepesi pont az uj oldalra.
- Minimalis, repo-grounded read-model, hogy a page a source DXF fajlokhoz a
  **legfrissebb preflight statuszt** is meg tudja jeleniteni.
- A frontend API/types boundary bovitese az uj oldalhoz szukseges minimumra.
- Canonical UX nyelvezet az intake oldalon: `source DXF`, nem `stock_dxf` /
  `part_dxf` mint belso truth.
- Determinisztikus backend teszt a file-list summary projectionre.
- Minimalis smoke az uj intake route + summary read-model szerzodesre.

### Out-of-scope
- Rules profile editor vagy tenyleges settings panel (E4-T2).
- Reszletes preflight runs table/badge rendszer (E4-T3).
- Diagnostics drawer / modal (E4-T4).
- Review decision workflow (E4-T5).
- Accepted -> parts flow (E4-T6).
- Replace file, rerun, feature flag vagy rollout gate.
- Kulon explicit preflight-runs API family teljes implementacioja.
- Legacy `NewRunPage.tsx` ujabb prefilter funkciokkal valo foltozasa.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `frontend/src/App.tsx`
  - current-code truth: nincs DXF intake route.
- `frontend/src/pages/ProjectDetailPage.tsx`
  - current-code truth: upload + file lista + runs lista ugyanazon az oldalon.
- `frontend/src/pages/NewRunPage.tsx`
  - current-code truth: legacy run wizard, nem intake page.
- `frontend/src/lib/api.ts`
  - current-code truth: `listProjectFiles(...)` tud file listat kerni, de nincs
    benne preflight summary projection.
- `frontend/src/lib/types.ts`
  - current-code truth: a `ProjectFile` modellben nincs latest preflight summary.
- `api/routes/files.py`
  - current-code truth: upload finalize utan auto-preflight fut, de a GET files
    lista nem ad preflight summaryt.
- `api/services/dxf_preflight_runtime.py`
  - current-code truth: a preflight runtime perzisztal `acceptance_outcome` es
    artifact truth adatokat.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - docs truth: kulon `DXF Intake / Project Preparation` oldal a helyes irany.

## Jelenlegi repo-grounded helyzetkep

### 1. A frontendben nincs kulon intake belepesi pont
Ma a user a `ProjectDetailPage` upload blokkjat es a `NewRunPage` legacy wizardot
latja. Ettol a preflight lane frontend szinten nehezen ertelmezheto.

### 2. A backend mar auto-preflight alapon mukodik
Az E3-T2 ota a preflight upload utan automatikusan indul. Ez azt jelenti, hogy
az E4-T1 **nem** manualis "Start preflight" gombbal kell induljon, hanem olyan
oldallal, amely ezt a viselkedest megmutatja es keretet ad neki.

### 3. Nincs meg dedikalt rules-profile domain
Az E3 current-code truth szerint nincs implementalt rules-profile owner/version
API domain. Emiatt az E4-T1-ben nem szabad teljes settings szerkesztot kitalalni.
Legfeljebb read-only placeholder / info blokk lehet, a valodi settings panel az
E4-T2 feladata.

### 4. A file-list endpoint nem ad preflight statuszt
A page-nek minimalisan latnia kell, hogy egy source DXF legutobbi preflight
futasa milyen allapotban van. Mivel ma nincs explicit preflight-runs frontend
API, az E4-T1 helyes minimal bridge-je egy **optional file-list summary
projection** a meglvo `GET /projects/{project_id}/files` endpointban.

### 5. A canonical frontend nyelvezet mar atallhat `source DXF`-re
A backend a `stock_dxf` / `part_dxf` legacy ertekeket ugyis `source_dxf`-re
normalizalja. Az uj intake oldal mar ne erositse vissza a legacy terminologiat.
Itt a helyes upload nyelvezet: **Source DXF files**.

## Konkret elvarasok

### 1. Legyen uj dedikalt oldal es route
Az App router kapjon uj route-ot, javasolt utvonallal:
- `/projects/:projectId/dxf-intake`

Az uj oldal neve es celja legyen egyertelmu:
- `DXF Intake / Project Preparation`

Az oldal minimum szekcioi:
- header + vissza a projekthez link,
- upload panel,
- read-only/current-defaults info blokk,
- source DXF statuszlista.

### 2. A page az uploadot canonical `source_dxf` modban kezelje
Az intake oldalon ne legyen legacy `stock_dxf` / `part_dxf` toggle.
A page upload flow-ja a backendnek egyertelmuen `source_dxf`-et kuldjon.

Ez current-code kompatibilis, mert a backend mar ma is ezt kezeli belso truth-kent.

### 3. A page mondja ki, hogy a preflight automatikusan indul
Mivel az E3-T2 ota upload utan automatikusan fut a runtime, az oldalon legyen
explicit UX magyarazo szoveg, pl. hogy a preflight a feltoltes finalizalasa utan
magatol elindul.

Anti-scope:
- ne vezess be kulon manualis "Start preflight" gombot;
- ne talalj ki fake workflow-t, ami nincs a backendben.

### 4. Legyen minimalis read-model a file listahoz
A `GET /projects/{project_id}/files` endpoint current-code kompatibilis, minimalis
bovitessel tudja kiszolgalni az intake oldalt.

Javasolt irany:
- optional query param: `include_preflight_summary=true`
- ilyenkor a response egy file-onkent legfrissebb preflight summaryt is ad.

Minimum elvart subobject:
- `latest_preflight_summary.preflight_run_id`
- `latest_preflight_summary.run_seq`
- `latest_preflight_summary.run_status`
- `latest_preflight_summary.acceptance_outcome`
- `latest_preflight_summary.finished_at`

Fontos boundary:
- ez **nem** teljes preflight-runs API;
- ez csak minimal page-enabling summary projection;
- a diagnostics reszleteket meg ne ide tomd.

### 5. A frontend API/types erre a minimal summaryra bovuljenek
A `frontend/src/lib/types.ts` kapjon uj, optional summary shape-et a file
modellhez.
A `frontend/src/lib/api.ts` `listProjectFiles(...)` helpere tudja optional
kapcsolni az `include_preflight_summary=true` queryt es normalizalni az uj mezot.

### 6. A ProjectDetailPage kapjon egyertelmu belepesi pontot az uj oldalra
A `ProjectDetailPage` maradjon mukodokepes, de legyen rajta explicit CTA, ami az
uj intake oldalra visz.

Minimal elvaras:
- ne a New Run wizard legyen az egyetlen hangsulyos kovetkezo lepes;
- legyen `DXF Intake / Preparation` jellegu gomb vagy link.

### 7. A statuszlista mar most file-szintu legyen, nem reszletes runs table
Az E4-T1 ne akarja megoldani az E4-T3-at.
Ezert a listaban eleg a legutobbi file-szintu statusz megjelenitese, pl.:
- uploaded / no preflight yet,
- preflight_running,
- preflight_failed,
- preflight_review_required,
- preflight_rejected,
- accepted_for_import.

Ne legyen meg:
- diagnostics drawer,
- review gomb,
- artifact download,
- rerun,
- accepted -> parts flow.

### 8. A task bizonyitasa
Minimum deterministic coverage:

#### Backend unit teszt
- `include_preflight_summary=false` -> a file list response valtozatlan alap shape-et ad;
- `include_preflight_summary=true` -> a route a source fileokhoz a legfrissebb preflight summaryt merge-eli;
- ha egy file-hoz nincs preflight run, a summary `null`/hianyzik;
- ha tobb run van, a legfrissebb (`run_seq`/`created_at`) kerul be.

#### Smoke
- route-level summary projection minimal scenario;
- uj intake page route bent van a frontend routerben;
- a `ProjectDetailPage`-rol van CTA az uj intake oldalra.

#### Opcionális frontend ellenorzes
- `npm --prefix frontend run build`

## DoD
- [ ] Letrejott kulon `DXF Intake / Project Preparation` oldal es route.
- [ ] Az uj oldal canonical `source_dxf` upload nyelvezetet hasznal.
- [ ] Az oldal explicit kommunikalja, hogy a preflight automatikusan indul upload utan.
- [ ] A `ProjectDetailPage`-rol van egyertelmu belepesi pont az intake oldalra.
- [ ] A file-list endpoint minimal latest preflight summary projectiont tud adni optional kapcsoloval.
- [ ] A frontend types/api boundary tamogatja az uj summary shape-et.
- [ ] A page file-szintu statuszlistat jelenit meg, de nem nyitja meg meg a diagnostics/review/settings reszletes scope-ot.
- [ ] A task-specifikus backend teszt es smoke bizonyitja a minimal UI-enabling szerzodest.

## Javasolt verify / evidence
- `python3 -m py_compile api/routes/files.py tests/test_project_files_preflight_summary.py scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py`
- `python3 -m pytest -q tests/test_project_files_preflight_summary.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`

## Erintett fajlok (tervezett)
- `frontend/src/App.tsx`
- `frontend/src/pages/DxfIntakePage.tsx`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `api/routes/files.py`
- `tests/test_project_files_preflight_summary.py`
- `scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
