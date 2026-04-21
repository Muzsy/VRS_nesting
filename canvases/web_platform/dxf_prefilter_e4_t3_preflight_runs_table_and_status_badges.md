# DXF Prefilter E4-T3 — Preflight runs table es status badges

## Cel
Az E4-T1 ota letezik kulon `DXF Intake / Project Preparation` oldal, az E4-T2 ota
pedig ezen az oldalon mar van valodi preflight settings panel es upload-session
rules-profile bridge. A jobb oldali kartyan ma mar latszik a file-szintu latest
preflight status, de ez meg mindig tul vekony V1 nezet:
- csak 4 oszlop van (`Filename`, `Type`, `Latest preflight`, `Finished`);
- a badge egyetlen, osszemosott allapotot mutat;
- nincs kulon runtime-status vs acceptance-outcome vizualizacio;
- nincs issue/repair darabszam;
- nincs user-facing kovetkezo lepes / action recommendation oszlop.

Az E4-T3 celja egy **minimal, repo-grounded latest preflight runs table**
bevezetese a jelenlegi intake oldalon ugy, hogy a user egy listaban lassa,
hogy az egyes source DXF file-ok legutobbi preflight futasa hol tart, mennyi
hibat/javitast eredmenyezett, es hogy tovabbmehet-e vagy sem.

Ez a task most **nem** teljes historical preflight runs endpoint, nem diagnostics
drawer, nem review modal, nem replace/rerun flow es nem accepted->parts flow.
A helyes V1 current-code truth most: **file list endpoint optional latest-preflight
summary projection + intake oldali runs table + status badges + recommended action
cell**.

## Miért most?
A jelenlegi, kodbol igazolt helyzet:
- `frontend/src/pages/DxfIntakePage.tsx` mar ma is a `/projects/{projectId}/files`
  endpointot hasznalja `include_preflight_summary=true` queryvel, es a jobb oldali
  kartyan file-onkent a legutobbi preflight osszefoglalot jeleniti meg;
- `api/routes/files.py` current-code truth szerint csak ezt a minimal summaryt
  vetiti ki a `preflight_runs` tablából:
  - `preflight_run_id`
  - `run_seq`
  - `run_status`
  - `acceptance_outcome`
  - `finished_at`
- az E3-T1 ota a `preflight_runs` sorban mar van `summary_jsonb`, amely az E2-T7
  renderer unified issue/repair/acceptance summaryjat tartalmazza;
- az E2-T7 summaryban mar bent vannak a T3-hoz szukseges, kodszinten igazolt
  signalok:
  - `issue_summary.counts_by_severity.*`
  - `repair_summary.counts.applied_gap_repair_count`
  - `repair_summary.counts.applied_duplicate_dedupe_count`
  - `repair_summary.counts.skipped_source_entity_count`
  - `acceptance_summary.acceptance_outcome`
- nincs dedikalt preflight-runs list route vagy diagnostics detail route,
  ezert anti-pattern lenne most teljesen uj historical API-t vagy drawer scopet
  kitalalni.

Ez azt jelenti, hogy az E4-T3 legkisebb ertelmes lepese nem uj backend domain,
hanem a **meglevo latest-preflight projection gazdagitasa** es ennek az intake
oldalon valo emberi, badge-es tablazatos megjelenitese.

## Scope boundary

### In-scope
- A `latest_preflight_summary` backend projection minimal bovitese a T3 tablazathoz
  szukseges mezokkel.
- A `summary_jsonb`-bol determinisztikusan kinyert issue/repair counts kiegeszitese
  a file list endpointen.
- A frontend tipusok/API normalizacio bovitese az uj mezokre.
- A `DxfIntakePage` jobb oldali kartyan a jelenlegi egyszeru status table lecserelese
  T3-hoz illo **latest preflight runs table** nezetre.
- Kulon runtime status badge es acceptance outcome badge bevezetese.
- Issue count es repair count badge/summary oszlopok bevezetese.
- Minimal `recommended action` / `next step` oszlop bevezetese current-code truth
  alapjan.
- Determinisztikus backend unit teszt es smoke bizonyitek a projection + UI
  szerzodesre.
- Opcionális frontend build evidence.

### Out-of-scope
- Uj `GET /projects/{project_id}/preflight-runs` historical list endpoint.
- Diagnostics drawer / modal (E4-T4).
- Review modal / decision UI (E4-T5).
- Accepted->parts flow (E4-T6).
- Replace/rerun flow vagy row-level mutating actionok.
- Project-level settings persistence, rules-profile CRUD vagy named profiles.
- `NewRunPage.tsx` tovabbi bovítese.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `frontend/src/pages/DxfIntakePage.tsx`
  - current-code truth: mar van latest status table, de tul vekony T3 szinthez.
- `frontend/src/lib/types.ts`
  - current-code truth: `ProjectFileLatestPreflightSummary` csak 5 mezot tartalmaz.
- `frontend/src/lib/api.ts`
  - current-code truth: a normalizer csak a minimal summary mezoket emeli ki.
- `api/routes/files.py`
  - current-code truth: `_fetch_latest_preflight_summary_by_file_id(...)` es
    `_latest_preflight_summary_from_row(...)` csak minimal latest summaryt ad.
- `api/services/dxf_preflight_persistence.py`
  - current-code truth: a `preflight_runs.summary_jsonb` mar ma is tartalmazza
    a T7 unified summaryt.
- `api/services/dxf_preflight_diagnostics_renderer.py`
  - current-code truth: issue/repair/acceptance counts mar szerkezetileg ott vannak.
- `tests/test_project_files_preflight_summary.py`
  - current-code truth: mar letezik route-level coverage a latest summary projectionre.
- `canvases/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md`
- `canvases/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md`

## Jelenlegi repo-grounded helyzetkep

### 1. A “runs table” current-code truth szerint file-onkent a legutobbi run
Mivel jelenleg nincs kulon historical preflight runs route, a T3 helyes minimal
modellje: **egy file = egy sor = az adott file legutobbi preflight runja**.
Nem szabad ugy irni a taskot, mintha mar letezne teljes run-history API.

### 2. A route mar ma is jo helyen all a projectionhoz
A `list_project_files(...)` endpoint mar optional `include_preflight_summary=true`
queryvel dolgozik, es mar most is queryzza a `preflight_runs` tablát. Emiatt a T3
helyes backend valtoztatasa nem uj endpoint, hanem a meglevo summary gazdagitasa.

### 3. A T7 summary eleg adatot ad issue/repair badge-ekhez
A `summary_jsonb`-ban mar ott van a unified issue summary es repair summary, igy
nem kell a frontendben issue-family logikat ujraepiteni. A helyes irany: a backend
vetitse ki a minimal UI mezoket, a frontend csak jelenitse meg.

### 4. Valodi actions scope meg nincs
Mivel nincs diagnostics drawer vagy replace/rerun flow, a T3 actions oszlopnak
current-code truth szerint **recommended action / next step** jellegunek kell lennie,
nem mutalo route-okat vagy buttonokat kell kitalalni.

### 5. A badge-eket kulon kell valasztani
A jelenlegi egyetlen `formatPreflightStatus(...)` badge a runtime statuszt es az
acceptance outcome-ot is osszemossa. A T3-ban kulon badge-ek kellenek:
- preflight run status badge;
- acceptance outcome badge;
- issue count badge;
- repair count badge.

## Konkret elvarasok

### 1. A backend projection bovuljon a T3 tablazathoz szukseges minimal mezokkel
Az `api/routes/files.py` latest summary projectionja bovuljon ugy, hogy a
`ProjectFileResponse.latest_preflight_summary` a jelenlegi mezokon felul legalabb
az alabbiakat is tartalmazza:
- `blocking_issue_count`
- `review_required_issue_count`
- `warning_issue_count`
- `total_issue_count`
- `applied_gap_repair_count`
- `applied_duplicate_dedupe_count`
- `total_repair_count`
- `recommended_action`

A `recommended_action` current-code truth szerint backend-projected, stabil string
lehet, pl.:
- `ready_for_next_step`
- `review_required_wait_for_diagnostics`
- `rejected_fix_and_reupload`
- `preflight_in_progress`
- `preflight_not_started`

### 2. A projection a `summary_jsonb`-bol dolgozzon, ne frontend szintu issue-parsinggal
A route a `preflight_runs` queryben kerje le a `summary_jsonb`-t is, es a server oldalon
allitson elo egy lapos, UI-barát summary shape-et.

Elv:
- `total_issue_count = blocking + review_required + warning + info` vagy legalabb
  a UI-ban hasznalt relevans severityk osszege, dokumentalt modon;
- `total_repair_count = applied_gap_repair_count + applied_duplicate_dedupe_count`;
- ha a `summary_jsonb` reszben hianyzik, a projection maradjon optional / null-safe,
  ne torje el a file list route-ot.

### 3. A frontend tipusok/API normalizacio kovesse az uj summary shape-et
A `frontend/src/lib/types.ts` `ProjectFileLatestPreflightSummary` tipusa bovuljon az uj
mezokkel, az `api.ts` normalizer pedig determinisztikusan mapelje oket.

### 4. A `DxfIntakePage` jobb oldali kartya valjon T3-kompatibilis latest runs table-le
A jelenlegi `Latest file preflight status` kartya helyen jelenjen meg egy T3-hoz illo
nezet, amely minimum ezt mutatja:
- `Filename`
- `Run status`
- `Issues`
- `Repairs`
- `Acceptance`
- `Recommended action`
- opcionálisan `Finished` vagy `Run #`

A `Type` oszlop most mar nem elso rendben hasznos; ha hely kell, elhagyhato.

### 5. Kulon status badge helper-ek legyenek
A page-ben a badge rendering legyen szetbontva determinisztikus helper-ekre, pl.:
- `formatRunStatusBadge(...)`
- `formatAcceptanceOutcomeBadge(...)`
- `formatIssueCountBadge(...)`
- `formatRepairCountBadge(...)`
- `formatRecommendedActionLabel(...)`

Nem jo irany egyetlen nagy, kevert badge-re visszafoltozni a mostani helper-t.

### 6. Az actions oszlop current-code truth szerint recommendation legyen
Mivel nincs meg reszletes diagnostics route vagy replace flow, a T3-ban a
`recommended action` oszlop legyen tiszta, user-facing szoveg. Peldaelv:
- accepted -> `Ready for next step`
- review_required -> `Wait for diagnostics`
- rejected -> `Fix source DXF and re-upload`
- running/pending -> `Preflight still running`
- no summary -> `Upload complete; waiting for preflight`

### 7. A task bizonyitasa
Minimum deterministic coverage:

#### Backend unit teszt a summary projectionre
- ha a `summary_jsonb` issue/repair counts elerhetok, a projection helyesen lapositja oket;
- ha a `summary_jsonb` hianyos vagy ures, a route optional marad;
- a latest-run kivalasztasi logika nem torik el.

#### Smoke
A smoke bizonyitsa legalabb:
- az uj T3 oszlopok es badge helper tokenek jelenletet a `DxfIntakePage`-en;
- az API/types boundary uj mezoi bent vannak;
- a route summary projection uj mezoi bent vannak.

#### Frontend build
A page es type/API boundary forduljon.

## Javasolt megvalositasi irany

### Backend
- `api/routes/files.py`
  - bovitett `select` a `preflight_runs` queryhez (`summary_jsonb` is);
  - helper a `summary_jsonb` counts kinyeresere;
  - helper a `recommended_action` meghatarozasara;
  - lapos, optional-safe `latest_preflight_summary` shape.

### Frontend
- `frontend/src/lib/types.ts`
  - bovitett `ProjectFileLatestPreflightSummary`.
- `frontend/src/lib/api.ts`
  - bovitett summary normalizer.
- `frontend/src/pages/DxfIntakePage.tsx`
  - jobb oldali table T3 szerinti oszlopokra atalakítva;
  - kulon badge helper-ek;
  - user-facing recommended action label-ek.

### Tesztek
- `tests/test_project_files_preflight_summary.py`
  - bovitett coverage `summary_jsonb` counts / recommended action projectionre.
- `scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py`
  - deterministic smoke.

## Kifejezett tiltások
- Ne hozz letre uj historical preflight-runs route-ot.
- Ne nyiss diagnostics drawer/modalt.
- Ne vezess be replace/rerun buttonokat vagy uj mutating API-t.
- Ne told ra a taskra az accepted->parts flow-t.
- Ne bonyolitsd tul a frontendben a `summary_jsonb` parse-olast; a UI minimal,
  lapos projectiont fogyasszon.
- Ne nyisd meg a `NewRunPage.tsx` scope-jat.

## Kotelezo ellenorzesek a task vegen
- `python3 -m py_compile api/routes/files.py tests/test_project_files_preflight_summary.py scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py`
- `python3 -m pytest -q tests/test_project_files_preflight_summary.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`

## Elvart eredmeny
A `DXF Intake / Project Preparation` oldalon a user egyetlen tablaban latja,
hogy az egyes source DXF file-ok legutobbi preflight futasa milyen allapotban van,
hany issue-t es javitast eredmenyezett, milyen acceptance outcome lett, es mi a
kovetkezo logikus lepes. Mindez a jelenlegi repo-grounded file-list projectionre
es a mar persisted `summary_jsonb` truth-ra epuljon, uj diagnostics vagy run-history
API kitalalasa nelkul.
