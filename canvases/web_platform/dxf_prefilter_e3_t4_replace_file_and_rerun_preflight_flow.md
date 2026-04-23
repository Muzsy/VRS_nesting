# DXF Prefilter E3-T4 — Replace file es re-run preflight flow

## Cel
Az E3-T2 ota a source DXF upload finalize automatikusan elinditja a preflight runtime-ot,
az E3-T3 ota pedig a geometry import mar csak gate-pass utan indul. A jelenlegi rendszerben
viszont nincs explicit **replace file** flow: ha egy fajl `preflight_rejected` vagy
`preflight_review_required`, a user jelenleg csak uj feltoltessel tud tovabblepni, explicit
API-level replacement lineage nelkul.

A DXF-E3-T4 celja egy minimalis, repo-grounded **replace file + implicit re-run preflight**
backend flow bevezetese ugy, hogy:
- a replace actionnak legyen explicit API route-ja;
- az uj replacement upload a jelenlegi signed-upload + `complete_upload` flow-hoz igazodjon;
- az elozo filehoz tartozo preflight runok auditkent megmaradjanak;
- az uj replacement file finalize utan a meglevo E3-T2 runtime automatikusan ujrainditsa a preflightot;
- ne kelljen uj manualis `rerun` endpointot kitalalni.

## Miert most?
A jelenlegi repo-grounded helyzet:
- az E4-T1..T4 intake UI mar megmutatja a preflight statuszt, a diagnostics drawert es a
  `Fix source DXF and re-upload` ajanlott lepest;
- az API contract docs mar korabban rogzitette a future canonical replace action endpointot:
  `POST /projects/{project_id}/files/{file_id}/replace`;
- az E3-T2 auto-preflight trigger es az E3-T3 geometry import gate mar kesz;
- a hianyzo darab most egy explicit backend replacement flow, amely a jelenlegi upload finalize
  pipeline-hoz illeszkedik.

Ez a task a legkisebb helyes lepest vezeti be: **replace route + persistence lineage bridge +
automatikus preflight ujrafutas a meglevo finalize/runtime lancban**.

## Scope boundary

### In-scope
- Uj replacement upload-action route a `files.py` alatt:
  - `POST /projects/{project_id}/files/{file_id}/replace`
- Minimalis replacement lineage persistence a `file_objects` truth-ban.
- A `complete_upload` V1 bridge bovitese, hogy replacement finalize-kor a rendszer el tudja
  tarolni, melyik elozo file-t valtja le az uj file.
- Annak bizonyitasa, hogy replacement finalize utan a meglevo source-DXF finalize flow
  automatikusan ujrainditja a preflight runtime-ot az uj file-ra.
- Determinisztikus unit teszt es smoke coverage.

### Out-of-scope
- Uj explicit `POST /preflight-runs/{id}/rerun` endpoint.
- UI button vagy intake-page replace UX (ez kesobbi E4 scope).
- Historical replacement timeline UI vagy file-grouping UX.
- Feature flag / rollout gate (E3-T5).
- Review decision workflow.
- Artifact download/detail API.
- Geometry import gate ujrairasa.
- Full rules-profile domain.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/routes/files.py`
  - current-code truth: upload-url + complete_upload mar letezik;
  - source DXF finalize utan legacy validation + preflight runtime indul.
- `api/services/dxf_preflight_runtime.py`
  - current-code truth: a rerunhoz nincs kulon endpoint szukseg, mert source DXF finalize utan automatikusan fut.
- `api/services/dxf_preflight_persistence.py`
  - current-code truth: a preflight runok source file object id-hoz kotve mar audit truth-kent tarolodnak.
- `frontend/src/pages/DxfIntakePage.tsx`
  - current-code truth: a user-facing recommended action mar ma is `Fix source DXF and re-upload`,
    de ez meg nem explicit replacement action route-ra epul.
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
  - docs-level truth: a replace actionnak kulon route-nak kell lennie.
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
  - docs-level truth: replacement utan uj preflight run indulhat, de ehhez nem kell kulon rerun endpoint.

## Jelenlegi repo-grounded helyzetkep

### 1. Van upload finalize flow, de nincs explicit replacement action
Ma egy uj source DXF upload teljesen kulonallo uj file flow-kent megy:
- upload-url
- signed upload
- `complete_upload`
- auto preflight

Ez mukodik, de nincs benne semmi, ami a replacementet API-levelen kimondana.

### 2. A preflight run audit mar ma is file-object scoped
A `preflight_runs.source_file_object_id` miatt az elozo runok auditkent maradnak meg.
Ez jo, viszont replacement eseten csak akkor marad tiszta lineage, ha az uj file-nak van
explicit kapcsolata az elozo file-hoz.

### 3. A rerun endpoint current-code truth szerint felesleges
Mivel az E3-T2 ota a source DXF finalize automatikusan futtatja a preflight runtime-ot,
a replacement utani "re-run" helyes V1 megvalositasa nem uj endpoint, hanem:
- replacement upload action,
- majd a replacement finalize ugyanazon auto-preflight triggerrel.

### 4. A replacement lineage-nek persisted truth-nak kell lennie
A docs-level contractban replace action van, nem puszta UI szoveg. Ezert az E3-T4-ben
nem eleg report-levelen vagy route valaszban elmondani, hogy "ez replacement".
Szukseg van minimalis persisted truth-ra is.

## Konkret elvarasok

### 1. Uj replacement upload-action route kell
A `files.py` alatt jojjon letre:
- `POST /projects/{project_id}/files/{file_id}/replace`

A route feladata:
- ellenorizze, hogy a target `file_id` letezik, a projekthez tartozik, es `source_dxf` jellegu file;
- adjon vissza signed upload URL-t es egy uj replacement `file_id`-t a meglevo upload-url mintahoz igazodva;
- a response-ben explicit jelenjen meg, hogy melyik file-t csereli az uj upload slot.

Current-code truth szerint ez a route **nem** vegzi el a finalize-t; csak replacement upload slotot nyit.
A signed upload es a finalize marad a meglevo ketlepeses modellben.

### 2. A finalize payload kapjon minimalis replacement bridge-et
A `FileCompleteRequest` kapjon egy optional replacement mezot, pl.:
- `replaces_file_object_id`

A `complete_upload` source DXF finalize flow ennek alapjan:
- validalja, hogy a replacement target ugyanabban a projektben letezo source DXF;
- perszisztalja az uj file-object lineage-et;
- az uj file-ra ugyanugy elinditja a legacy validation + auto preflight runtime taskokat.

### 3. A replacement lineage legyen persisted truth
A taskban vezess be minimalis, current-code kompatibilis persistence truth-ot a `file_objects` domainben.
A helyes irany:
- uj nullable self-FK, pl. `replaces_file_object_id uuid null references app.file_objects(id) on delete restrict`

Ennek celja:
- az elozo preflight runok az eredeti file objecthez kotve auditkent megmaradnak;
- az uj replacement file explicit jelzi, melyik elozo file-t valtja le;
- nem kell in-place atirni a regi file objectet;
- nem kell torolni a regi file storage objectet vagy geometry revision auditot.

Anti-pattern, amit kerulni kell:
- a regi file object in-place frissitese uj tartalomra;
- replacement lineage csak response payloadban, persisted truth nelkul;
- kulon replacement tabla bevezetese, ha egy self-FK eleg.

### 4. A rerun flow legyen implicit, ne kulon endpoint
A task explicit bizonyitsa, hogy replacement finalize utan:
- a meglevo `complete_upload` source DXF branch lefut;
- a meglevo `run_preflight_for_upload(...)` background task az uj replacement file-ra indul;
- nem jon letre uj manualis rerun route.

### 5. A route-list projection meg maradhat valtozatlan V1-ben
Az E3-T4-ben nem kotelezo megjeleniteni a replacement lineage-et a `GET /files` projectionben,
ha a persisted truth mar megvan es a route-action bizonyitott.

Ha viszont minimalis projection kell a deterministic tesztekhez, az csak optional mezokent johet,
de ne nyisson meg UI scope-ot.

### 6. A delete/cleanup semantics maradjanak kesobbi scope-ban
Az E3-T4 ne oldja meg most:
- a regi file automatikus torleset;
- a superseded file hide/filter UX-et;
- a replacement lineage historical listazast;
- a geometry revisionek cleanupjat.

A cel most csak az explicit replace action + replacement lineage + auto preflight rerun.

## Tesztelhetoseg es bizonyitas

### Unit teszt minimum
- replace route source_dxf targetra signed replacement upload slotot ad vissza;
- non-source_dxf vagy mas projekt target -> hiba;
- `complete_upload` replacement finalize eseten az uj file row persisted `replaces_file_object_id`-t kap;
- replacement finalize utan a route ugyanazt a ket background taskot regisztralja, mint normal source uploadnal;
- nincs uj manualis rerun endpoint-hivas.

### Smoke minimum
- replacement route -> signed upload URL + uj file_id + replacement target evidence;
- finalize replacement -> uj file row + lineage truth;
- preflight runtime task az uj replacement file_id-re indul;
- az eredeti file objecthez tartozo korabbi preflight runok nem torlodnek.

## Mi marad kesobbi scope-ban
- **E3-T5**: feature flag / rollout gate
- kesobbi explicit artifact/download/review endpointok
- E4 oldalon replace button / rerun UX
- superseded file hiding/grouping UX
- accepted->parts flow

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow/run.md`
- `supabase/migrations/<timestamp>_dxf_e3_t4_replace_file_and_rerun_preflight_flow.sql`
- `api/routes/files.py`
- `tests/test_dxf_preflight_replace_flow.py`
- `scripts/smoke_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md`

## DoD
- [ ] Letrejon az explicit `POST /projects/{project_id}/files/{file_id}/replace` route.
- [ ] A route csak letezo, projektbe tartozo `source_dxf` targetra mukodik.
- [ ] A replacement upload flow a meglevo signed-upload + `complete_upload` ketlepeses mintara epul.
- [ ] A finalize payload kap optional replacement bridge mezot.
- [ ] A `file_objects` domainben persisted replacement lineage truth jon letre.
- [ ] Replacement finalize utan a meglevo auto-preflight runtime az uj replacement file-ra indul.
- [ ] Nem jon letre kulon manualis rerun endpoint.
- [ ] Nem tortenik regi file in-place felulirasa.
- [ ] Keszul task-specifikus unit teszt es smoke.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md` PASS.
