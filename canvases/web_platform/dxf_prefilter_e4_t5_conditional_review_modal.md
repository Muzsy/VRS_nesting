# DXF Prefilter E4-T5 — Conditional review modal

## Cel
Az E4-T4 ota a `DxfIntakePage` mar tudja:
- a latest preflight runs tablaban mutatni a file-onkenti statuszt;
- a persisted T7 diagnostics truthot read-only drawer/modal nezetben megjeleniteni.

A jelenlegi repo-grounded hiany viszont az, hogy a `preflight_review_required` kimenetu
file-okhoz nincs kulon, celzott **review UX**. A user ma latja, hogy review kell, de nincs
olyan iranyitott felulet, ami:
- csak review-required file-ra aktiv,
- kiemeli a review-required jeleket,
- es a jelenlegi kodban tenylegesen letezo kovetkezo lepest adja.

A current-code truth szerint ez a kovetkezo lepés **nem persisted review decision save**,
mert a repoban jelenleg nincs:
- `preflight_review_decisions` persistence implementacio,
- review-decision API route,
- rules-profile update domain,
- olyan stabil source-entity identity, amire file-szintu review dontesek biztonsaggal
  visszakothetok.

Ugyanakkor a repoban mar van:
- E4-T4 diagnostics drawer,
- E3-T4 backend replacement flow (`POST /projects/{project_id}/files/{file_id}/replace` +
  replacement finalize bridge),
- E3-T5 rollout/feature gate.

Ezert az E4-T5 helyes V1 current-code scope-ja egy **conditional review modal**, amely:
- csak review-required file-ra nyithato meg,
- a persisted diagnostics truthbol kiemeli a review-igenylo jeleket,
- es a usernek a jelenlegi rendszerben tenylegesen letezo akciot adja:
  **replacement upload ugyanebbol a modalbol**, a meglevo backend replacement flow-ra epitve.

## Miért most?
A jelenlegi repo-grounded helyzet:
- az E4-T3 tabla mar mutat acceptance/recommended-action allapotot;
- az E4-T4 diagnostics drawer mar megmutatja a teljes persisted T7 truthot;
- az E3-T4 replacement backend mar kesz, de frontendrol meg nincs bekotve;
- az E3-T5 feature flag / rollout gate mar kapuzza a DXF intake route-ot es replacement flow-t.

Ez azt jelenti, hogy a legkisebb ertelmes T5 scope most:
**review-required fila eseten iranyitott modal + replacement upload bekotese**,
nem pedig egy meg nem letezo persisted review-decision domain kitalalasa.

## Scope boundary

### In-scope
- `DxfIntakePage` row-level, **conditional** review trigger review-required file-okra.
- Page-local `Conditional review modal` UX ugyanazon az oldalon.
- A modal a persisted `latest_preflight_diagnostics` payloadbol kiemeli:
  - review-required issue-ket,
  - remaining review-required signals-t,
  - acceptance summary review state-jat,
  - es egy rovid "what to do now" osszefoglalot.
- A modalbol indithato legyen a **replacement upload flow** a meglevo E3-T4 backend route-ra epitve.
- A replacement finalize hasznalja a mar meglvo `complete_upload` route-ot es kuldje at:
  - `replaces_file_object_id`
  - `rules_profile_snapshot_jsonb` a page jelenlegi settings draftja alapjan.
- Frontend API/type boundary a replacement route-hoz.
- Task-specifikus smoke es build evidence.

### Out-of-scope
- Persisted review decision save.
- Uj `POST /projects/{project_id}/preflight-runs/{id}/review-decisions` route.
- `preflight_review_decisions` tabla vagy migration.
- Rules profile mentes / update domain.
- Source-entity szintu cut/marking/ignore dontes persistence.
- Accepted->parts flow.
- Diagnostics drawer redesign.
- Historical preflight-runs vagy detail endpoint.
- NewRunPage vagy mas legacy wizard bovitese.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `frontend/src/pages/DxfIntakePage.tsx`
  - mar van settings draft, upload helper, latest preflight table, diagnostics drawer.
- `frontend/src/lib/api.ts`
  - van create-upload + complete-upload helper, de replacement helper meg nincs.
- `frontend/src/lib/types.ts`
  - mar tartalmazza a latest summary/diagnostics tipusokat.
- `api/routes/files.py`
  - mar van `POST /projects/{project_id}/files/{file_id}/replace` route,
    es a finalize bridge `replaces_file_object_id` mezo.
- `frontend/src/lib/featureFlags.ts`
  - a route/CTA visibility mar build-time gate-elt.
- `canvases/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md`
- `canvases/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`
- `canvases/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md`

## Jelenlegi repo-grounded helyzetkep

### 1. A review-required allapot mar megjelenik, de nincs ra celzott UX
A tabla mar mutatja:
- `acceptance_outcome = preflight_review_required`
- `recommended_action = review_required_wait_for_diagnostics`

De ez jelenleg csak badge/szoveg szintjen latszik.

### 2. A diagnostics drawer nem azonos a review modal feladattal
A diagnostics drawer jelenleg egy teljes, read-only diagnostics nezet. Ez jo,
de nem eleg review UX-nek, mert:
- minden reteget mutat, nem csak a review-required reszt;
- nincs benne celzott kovetkezo lepes;
- nincs replacement upload akcio.

### 3. A persisted review-decision domain meg nincs implementalva
A docsban future contractkent szerepel a review decision route/persistence, de a jelenlegi
kodbazisban nincs ilyen implementacio. Ezert anti-pattern lenne most olyan T5-ot irni,
ami mentett review donteseket igyertne.

### 4. A replacement flow viszont mar current-code truth
A replace route, a finalize replacement bridge es a rollout gate mar bent vannak.
Ezert a T5 modal helyes V1 current-code akcioja: **replace source DXF from modal**.

## Konkret elvarasok

### 1. A tablaba keruljon felteteles review trigger
A `DxfIntakePage` latest preflight runs tablajaban review-required file eseten jelenjen meg
egy kulon trigger, peldaul:
- `Review`
- vagy `Open review`

A trigger csak akkor legyen aktiv, ha:
- `latest_preflight_summary.acceptance_outcome === "preflight_review_required"`
- es van `latest_preflight_diagnostics` payload.

Nem jo irany:
- review trigger minden sorra,
- review trigger accepted/rejected file-okra is,
- review trigger diagnostics payload nelkul.

### 2. A review modal kulonuljon el a diagnostics drawer-tol
A T5 vezessen be kulon page-local review modal state-et.
Ez lehet egyszeru overlay/modal, de legyen kulon a diagnostics drawertol.

A modal minimum tartalma:
- fejlec: file nev + acceptance badge + run seq / finished at;
- review summary blokk:
  - review-required issue count,
  - remaining review-required signal count,
  - recommended action,
  - precedence rule / acceptance outcome;
- review-required issue lista:
  - a `normalized_issues` review_required severity szelete;
- remaining review signals lista:
  - a `repair_summary.remaining_review_required_signals` listabol;
- rovid action guidance blokk:
  - miert nincs meg persisted review decision save,
  - mi a jelenlegi repo-grounded kovetkezo lepés.

### 3. A modal current-code truth szerint replacement upload entrypoint legyen
A modal tartalmazzon egy replacement file inputot/secondary upload zonet,
amellyel a user ki tud valasztani egy javitott DXF-et ugyanarra a file-ra.

A helyes technikai lepesek:
1. `POST /projects/{project_id}/files/{file_id}/replace`
2. signed upload az uj replacement storage path-ra
3. `POST /projects/{project_id}/files` finalize a mar meglevő `complete_upload` route-ra, ezzel:
   - `file_id` = replacement slot file_id
   - `replaces_file_object_id` = az eredeti file id
   - `rules_profile_snapshot_jsonb` = a page jelenlegi settings draftjabol epitve
4. `loadData()` refresh, hogy az uj latest summary / diagnostics megjelenjen

### 4. Az uj frontend API helper current-code route-ra epuljon
A `frontend/src/lib/api.ts` kapjon replacement helper(eke)t a jelenlegi backend route-hoz,
uj route kitalalasa nelkul.

Peldaszeru helper shape:
- `replaceProjectFile(...)`

A response current-code truth szerint tartalmaz:
- `upload_url`
- `file_id`
- `storage_bucket`
- `storage_path`
- `expires_at`
- `replaces_file_id`

### 5. A task ne allitson tobbet a reviewrol, mint ami ma igaz
A T5 UX-ben explicit legyen, hogy ez **guidance + replacement** V1, nem persisted review engine.

Anti-pattern:
- "Save review decision" gomb nem letezo backend nelkul;
- layer/entity szintu cut/marking/ignore dontesek mentese;
- rules profile update promise;
- file helyben history nelkuli felulirasa.

### 6. A diagnostics drawer maradjon meg
A T5 ne torolje ki es ne olvassza be a T4 diagnostics drawert.
Legyen lehetoseg a review modalbol diagnostics megnyitasra is, vagy legalabb a review modal
ugyanarra a truthra tamaszkodjon anelkul, hogy a drawer regressziot szenvedne.

### 7. A task bizonyitasa
Minimum deterministic evidence:

#### Frontend smoke
Bizonyitsa legalabb:
- a review trigger csak review-required file-ra renderelodik;
- a review modal tokenek bent vannak;
- a replacement flow a meglevo route/helper nevekre epul;
- a modal explicit current-code disclaimer-t tartalmaz a persisted review decision hianyarol.

#### Frontend build
- `npm --prefix frontend run build`

#### Ha van minimalis API/type boundary smoke
- az uj replacement helper es tipusok bent vannak.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t5_conditional_review_modal.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e4_t5_conditional_review_modal/run.md`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/DxfIntakePage.tsx`
- `scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`

## DoD
- [ ] A runs tablaban review-required file-ra megjelenik a conditional review trigger.
- [ ] A review modal csak review-required + diagnostics payloados file-ra nyithato meg.
- [ ] A modal kulon review summaryt mutat a persisted diagnostics truth review szeleteibol.
- [ ] A modal current-code truth szerint replacement upload entrypointot ad a meglevo backend route-ra epitve.
- [ ] A finalize replacement a mar meglevő `complete_upload` route-on keresztul tortenik, `replaces_file_object_id` bridge-dzsel.
- [ ] A page jelenlegi preflight settings draftja replacement finalize-kor is atmegy snapshotkent.
- [ ] A T4 diagnostics drawer nem regresszal.
- [ ] Nincs uj review-decision API, nincs persisted review decision domain, nincs rules-profile save scope.
- [ ] Keszul task-specifikus smoke.
- [ ] `npm --prefix frontend run build` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md` PASS.
