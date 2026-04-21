# DXF Prefilter E4-T4 — Diagnostics drawer / modal

## Cel
Az E4-T3 ota a `DxfIntakePage` mar file-onkenti latest preflight runs table-t mutat
kulon runtime-status / issue / repair / acceptance badge-ekkel, de a user tovabbra
is csak lapos statuszsummaryt lat. A persisted truth a backendben mar joval gazdagabb:
- az E2-T7 renderer a `preflight_runs.summary_jsonb` mezoben strukturalt,
  UI-barat diagnostics/repair/acceptance summaryt tarol;
- az E3-T1 ota ez a summary persistence truth;
- az E4-T3 route csak lapos counts-ot vetit ki a file listra.

Az E4-T4 celja egy **minimal, repo-grounded diagnostics drawer / modal** bevezetese
az intake oldalon ugy, hogy a user egy file legutobbi preflight futasarol reszletes,
olvashato diagnosztikai nezetet kapjon, de a task ne nyisson uj historical preflight-runs
API-t, review dontesi UI-t vagy replace/rerun/accepted->parts workflow-t.

A helyes V1 current-code truth most:
- marad a meglovo `GET /projects/{project_id}/files` route;
- ezen jelenik meg egy **optional latest diagnostics projection** a legutobbi preflight runhoz;
- a `DxfIntakePage` tabla soraihoz jelenik meg egy **View diagnostics** jellegu nem-mutalo akcio;
- ez egy drawer/modal nezetet nyit a persisted T7 summary alapjan.

## Miért most?
A jelenlegi kodbol igazolt helyzet:
- `api/routes/files.py` mar ma is optional `include_preflight_summary=true` queryvel
  a `preflight_runs` truthot kerdezi le file-onkenti latest run logikaval;
- a `preflight_runs.summary_jsonb` mar ma is tartalmazza a T7-ben eloallitott retegezett
  summaryt (`source_inventory_summary`, `role_mapping_summary`, `issue_summary`,
  `repair_summary`, `acceptance_summary`, `artifact_references`);
- az intake oldalon mar van kulon tabela, tehat a T4 termeszetes kovetkezo lepese egy
  details-nezet, nem uj page vagy uj endpointcsalad;
- nincs historical preflight-runs route, es nincs dedikalt preflight detail route,
  ezert anti-pattern lenne most teljesen uj API-csaladot kitalalni.

Ez azt jelenti, hogy a legkisebb ertelmes T4 scope nem uj backend domain, hanem:
**meglevo file-list route optional diagnostics projection + intake oldali drawer/modal UX**.

## Scope boundary

### In-scope
- A `GET /projects/{project_id}/files` route optional bovitese ugy, hogy a latest runhoz
  teljesebb, drawer-kompatibilis diagnostics payload is visszajohessen.
- Stabil backend projection helper a persisted `summary_jsonb` alapjan.
- Frontend tipus/API boundary bovitese a diagnostics payloadra.
- `DxfIntakePage` tablaban row-level non-mutating diagnostics trigger.
- Drawer/modal UX ugyanazon az oldalon:
  - source inventory summary,
  - role mapping summary,
  - issue summary,
  - repair summary,
  - acceptance summary,
  - artifact references.
- Determinisztikus route-level unit teszt es UI smoke a diagnostics projection + drawer triggerre.
- Opcionális frontend build evidence.

### Out-of-scope
- Uj `GET /projects/{project_id}/preflight-runs` historical list endpoint.
- Uj `GET /projects/{project_id}/preflight-runs/{id}` detail endpoint.
- Review modal / decision UI (E4-T5).
- Replace/rerun flow.
- Accepted->parts flow (E4-T6).
- Project-level settings persistence vagy named rules-profile domain.
- Signed download URL vagy preflight artifact route.
- `NewRunPage.tsx` bovítese.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/routes/files.py`
  - current-code truth: latest preflight summary projection mar letezik, de csak lapos counts/advice shape-ben.
- `api/services/dxf_preflight_diagnostics_renderer.py`
  - current-code truth: a persisted `summary_jsonb` retegezett T7 summary shape-je innen jon.
- `api/services/dxf_preflight_persistence.py`
  - current-code truth: a T7 summary snapshot bekerul a `preflight_runs.summary_jsonb` mezobe.
- `frontend/src/lib/types.ts`
  - current-code truth: van `ProjectFileLatestPreflightSummary`, de nincs diagnostics-detail tipus.
- `frontend/src/lib/api.ts`
  - current-code truth: csak lapos summaryt normalizal.
- `frontend/src/pages/DxfIntakePage.tsx`
  - current-code truth: van latest runs table es status badge-ek, de nincs diagnostics drawer/modal.
- `tests/test_project_files_preflight_summary.py`
  - current-code truth: route-level coverage mar letezik a latest summary projectionre.
- `scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py`
  - current-code truth: T3 badge/table smoke mar letezik.
- `canvases/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`

## Jelenlegi repo-grounded helyzetkep

### 1. A diagnostics truth mar persisted, csak nincs UI-ba vetitve
A T7 summary mar ma is tartalmazza a drawerhez szukseges retegeket. Emiatt a T4-ben
nem kell uj diagnostics domain vagy backend renderer, csak a persisted summary vetitese.

### 2. A legutobbi run current-code truth szerint file-onkenti nezet
Mivel nincs historical endpoint, a T4 details-nezete is **file-onkenti latest run** modellre
uljon. Nem szabad ugy irni a taskot, mintha mar letezne teljes run-history browsolas.

### 3. A route bovitese jobb, mint egy uj detail endpoint kitalalasa
A meglevo file-list route mar most is a `preflight_runs` tablat kerdezi le. Emiatt a T4
helyes minimal backend lepese egy uj optional query/projection ag, peldaul:
- `include_preflight_summary=true`
- `include_preflight_diagnostics=true`

Igy a T3 fogyasztok nem tornek, a T4 intake oldal pedig ugyanazon route-bol megkapja
a drawerhez szukseges latest diagnostics truthot.

### 4. A drawer/modal nem lehet mutalo felulet
Mivel nincs review route, replace/rerun es artifact-download API, a T4 nezet most csak
**olvaso, diagnosztikai reszletezo** legyen. Ne talaljon ki meg nem letezo gombokat.

### 5. Az artifact references current-code truth szerint local backend referenciak
A T7 `artifact_references` jelenleg `path`, `exists`, `download_label` jellegu helyi referencia.
Ez a T4-ben meg read-only listakent jelenjen meg. Ne legyen ugy irva a task, mintha mar lenne
signed URL vagy letoltes route.

## Konkret elvarasok

### 1. A file-list route kapjon optional latest diagnostics projectiont
Az `api/routes/files.py` `list_project_files(...)` route-ja bovuljon egy uj optional queryvel,
peldaul `include_preflight_diagnostics: bool = False`.

Elv:
- ha `false`, a T3 viselkedes valtozatlan;
- ha `true`, a backend a latest run `summary_jsonb` alapjan egy stabil, drawer-ready
  diagnostics objektumot is vetit ki file-onkent.

Nem jo irany:
- uj historical route,
- kulon detail endpoint,
- frontend oldali nyers `summary_jsonb` parse-olas.

### 2. A backend projection legyen stabil, UI-barat alak
A route helperje ne a teljes nyers `summary_jsonb`-t tolja ki kontroll nelkul, hanem egy
stabil latest diagnostics shape-et adjon vissza, peldaul `latest_preflight_diagnostics` alatt.

A minimum tartalom:
- `source_inventory_summary`
- `role_mapping_summary`
- `issue_summary`
- `repair_summary`
- `acceptance_summary`
- `artifact_references`

A T7 persisted truth mar alkalmas erre; a T4-ben ezt kell null-safe modon kivetiteni.

### 3. A frontend type/API boundary kovesse a diagnostics shape-et
A `frontend/src/lib/types.ts` kapjon dedikalt diagnostics detail tipust, pl.:
- `ProjectFileLatestPreflightDiagnostics`

A `ProjectFile` tipus bovuljon optional mezovel:
- `latest_preflight_diagnostics?: ProjectFileLatestPreflightDiagnostics | null`

Az `api.ts` normalizer optional-safe modon kezelje ezt az uj payloadot.

### 4. A DxfIntakePage kapjon row-level diagnostics trigger-t
A T3 tablaban jelenjen meg egy nem-mutalo row action / link / secondary button,
peldaul:
- `View diagnostics`

Current-code truth szerint ez csak akkor aktiv, ha van latest preflight summary/details.
Ha nincs, a control disabled vagy hidden lehet.

### 5. A details UX legyen drawer/modal ugyanazon az oldalon
A `DxfIntakePage` oldalon jelenjen meg egy T4-hez illo diagnostics drawer vagy modal.
A megvalositas lehet egyszeru, page-local React state-es overlay/panel; nem kell uj
komponenshierarchiat kitalalni, ha a page-level implementacio eleg.

A minimum megjelenitett blokkok:
- fejlec: fajlnev, run status badge, acceptance badge, run seq / finished at;
- source inventory:
  - found layers,
  - found colors,
  - found linetypes,
  - entity/contour/open-path/duplicate counts;
- role mapping:
  - resolved role inventory,
  - layer role assignments,
  - blocking/review counts;
- issues:
  - severity szerinti counts,
  - normalized issue lista (legalabb family/code/message szinten);
- repairs:
  - applied gap repairs,
  - applied duplicate dedupes,
  - skipped source entities,
  - remaining unresolved signals;
- acceptance:
  - precedence rule,
  - importer highlight,
  - validator highlight;
- artifacts:
  - local reference lista (`download_label`, `path`, `exists`).

### 6. A T4 ne allitson tobbet az artifactokrol, mint ami ma igaz
Az artifact references blokk current-code truth szerint meg read-only informacio.
Lehet megjeleniteni:
- label,
- path,
- exists igen/nem.

De ne legyen:
- signed download link,
- browserbol letolto mutacio,
- storage URL generalas.

### 7. A task bizonyitasa
Minimum deterministic coverage:

#### Backend route-level teszt
- ha `include_preflight_diagnostics=false`, a T3 viselkedes valtozatlan marad;
- ha `include_preflight_diagnostics=true`, a latest diagnostics projection megjelenik;
- hianyos/ures `summary_jsonb` mellett a route null-safe marad;
- a latest-run selection logika nem torik el.

#### Smoke
A smoke bizonyitsa legalabb:
- a DxfIntakePage tartalmaz diagnostics trigger tokeneket;
- a diagnostics drawer/modal state es szekcioheaderek bent vannak;
- az API/types boundary uj diagnostics mezoi jelen vannak;
- a routeban bent van az optional diagnostics query/projection.

#### Frontend build
- `npm --prefix frontend run build`

## DoD
- [ ] A meglevo file-list route optional latest diagnostics projectionnel bovult, uj historical/detail endpoint nelkul.
- [ ] A backend stabil, drawer-ready `latest_preflight_diagnostics` shape-et ad vissza a persisted T7 summary alapjan.
- [ ] A frontend tipusok es API normalizer kovetik az uj diagnostics payloadot.
- [ ] A `DxfIntakePage` tablaja kapott non-mutating diagnostics trigger-t.
- [ ] Letrejott egy page-local diagnostics drawer/modal UX a persisted latest diagnostics megjelenitesere.
- [ ] A drawer a source inventory, role mapping, issue, repair, acceptance es artifact reference blokkokat kulon jeleniti meg.
- [ ] A task nem nyit review modal / replace-rerun / accepted->parts / uj detail endpoint scope-ot.
- [ ] Keszult route-level unit teszt es task-specifikus smoke.
- [ ] A standard repo gate wrapperrel fut es a report evidence alapon frissul.

## Javasolt verify / evidence
- `python3 -m py_compile api/routes/files.py tests/test_project_files_preflight_diagnostics.py scripts/smoke_dxf_prefilter_e4_t4_diagnostics_drawer_modal.py`
- `python3 -m pytest -q tests/test_project_files_preflight_diagnostics.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t4_diagnostics_drawer_modal.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`

## Erintett fajlok (tervezett)
- `api/routes/files.py`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/DxfIntakePage.tsx`
- `tests/test_project_files_preflight_diagnostics.py`
- `scripts/smoke_dxf_prefilter_e4_t4_diagnostics_drawer_modal.py`
- `canvases/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t4_diagnostics_drawer_modal.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal/run.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.verify.log`
