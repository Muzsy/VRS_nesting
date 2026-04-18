# DXF Prefilter E1-T6 API contract specifikacio

## Funkcio
Ez a task a DXF prefilter lane hatodik, **docs-only API contract freeze** lepese.
A cel most nem FastAPI route implementacio, nem request/response model kod, nem OpenAPI export,
nem auth/RLS kidolgozas es nem frontend fetch layer, hanem annak rogzitese, hogy a jovobeli
DXF prefilter V1 milyen **HTTP API feluleten** fog bekapcsolodni a meglevo project -> files ->
geometry import -> parts -> runs platformba.

A task kozvetlenul az E1-T1 / E1-T2 / E1-T3 / E1-T4 / E1-T5 utan jon:
- a T1 rogzitette a V1 scope es integration boundary keretet;
- a T2 lefagyasztotta a glossaryt es role-szinteket;
- a T3 rogzitette a policy matrix es rules profile schema fogalmi szerzodeset;
- a T4 kulonvalasztotta a lifecycle retegeket;
- a T5 lefagyasztotta a future canonical data model es migration slicing iranyat;
- ez a T6 ezekre epitve lefagyasztja a **future canonical API contractot**.

A tasknak a jelenlegi repora kell raulnie:
- ma letezik `POST /projects/{project_id}/files/upload-url`, `POST /projects/{project_id}/files`,
  `GET /projects/{project_id}/files`, `DELETE /projects/{project_id}/files/{file_id}` a file ingesthez;
- ma leteznek top-level, owner-scoped profile/version route mintak
  (`/run-strategy-profiles`, `/scoring-profiles`, `/postprocessor-profiles`);
- ma leteznek project-scoped selection route mintak
  (`PUT /projects/{project_id}/run-strategy-selection`, `PUT /projects/{project_id}/scoring-selection`,
  `PUT /projects/{project_id}/manufacturing-selection`);
- ma letezik run artifact list/url/download minta a `/projects/{project_id}/runs/{run_id}/artifacts...` alatt;
- ma nincs dedikalt DXF prefilter route, nincs rules profile API, nincs preflight run API es nincs review decision API.

Ez a task azert kell, hogy a kovetkezo E2/E3 taskok ne ad hoc modon talaljak ki:
- milyen route-prefix alatt kell elerni a prefilter domaint;
- mi legyen top-level owner-scoped profile/version, es mi legyen project/file scoped resource;
- milyen action endpointok szuksegesek, es melyik maradjon kulon taskban;
- hogyan kell a preflight artifacts feluletet a meglevo runs-artifact mintakhoz igazitani;
- hol kell explicit current-code truth / future canonical contract kulonvalasztas.

## Scope
- Benne van:
  - a future canonical DXF prefilter HTTP API docs-level definicioja;
  - a route-prefix es resource-hatarkijeloles rogzitese;
  - a rules profile/version API irany rogzitese;
  - a project/file scoped preflight run API irany rogzitese;
  - a preflight artifact es review decision API irany rogzitese;
  - a replace/rerun jellegu action endpointok docs-szintu rogzitese;
  - a minimalis request/response shape elvek docs-szintu rogzitese;
  - anti-scope lista, hogy mi nem tartozik ebbe a taskba.
- Nincs benne:
  - FastAPI route implementacio;
  - `api/request_models.py` vagy route-level Pydantic model irasa;
  - auth/RLS implementacio;
  - konkret SQL vagy migration;
  - frontend hook/service implementacio;
  - OpenAPI schema export frissitese;
  - background worker/polling mechanika implementacio.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/routes/files.py`
  - current-code truth: project-scoped file ingest router a `/projects/{project_id}/files` prefix alatt;
  - upload-url + complete-upload + list + delete mintak.
- `api/routes/run_strategy_profiles.py`
  - current-code truth: top-level owner-scoped profile/version route minta.
- `api/routes/scoring_profiles.py`
  - current-code truth: masodik profile/version route minta.
- `api/routes/postprocessor_profiles.py`
  - current-code truth: harmadik profile/version route minta, strukturailag konzisztens API stilus.
- `api/routes/project_strategy_scoring_selection.py`
  - current-code truth: project-scoped selection route minta `PUT` alapu upserttel.
- `api/routes/project_manufacturing_selection.py`
  - current-code truth: project-scoped manufacturing selection minta.
- `api/routes/runs.py`
  - current-code truth: artifact list/url/download minta es action endpoint mintak (`rerun`, `bundle`).
- `api/request_models.py`
  - current-code truth: `StrictRequestModel` mint request-body alap.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - T1 output; rogzitette, hogy a prefilter a file upload utan, de a geometry import elott lep be.
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
  - T2 output; role- es fogalmi alap.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - T3 output; rules profile fogalmi szerzodes.
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
  - T4 output; lifecycle retegek.
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
  - T5 output; future canonical persistence es migration slicing.

## Jelenlegi repo-grounded helyzetkep
A repoban ma nincs DXF prefilter API surface.
A jelenlegi API truth-kep:
- a file ingest a `files.py` route-on elerheto;
- a geometry import upload finalize utan aszinkron indul;
- profile/version domainre mar van konzisztens owner-scoped route minta;
- project-szintu aktiv version selectionre mar van `PUT` alapu upsert minta;
- artifact surfaces-re mar van list/url/download minta;
- review decisions ma geometry review action log oldalon vannak, de nem prefilter domainben.

Ezert a T6-ben nem szabad ugy tenni, mintha ma mar leteznenek pl.
`api/routes/dxf_rules_profiles.py`, `api/routes/project_dxf_rules_selection.py`
vagy `api/routes/preflight_runs.py`.
A helyes output most egy **architecture-level API contract specification**,
amelyet a kesobbi implementacios taskok route-okra, request modellekre es OpenAPI-ra bontanak.

## Konkret elvarasok

### 1. Current-code truth es future canonical API contract legyen explicit kulonvalasztva
A dokumentumnak kulon kell kezelnie:
- mely route-ok leteznek ma mar a repoban;
- mely route-szerkezeteket vesz at mintakent a future DXF prefilter API;
- mely endpointok uj canonical contractok.

### 2. A rules profile API kovesse a meglevo owner-scoped profile/version mintat
A dokumentumnak rogzitnie kell, hogy a future DXF rules profile API szerkezetileg a mar
letezo profile/version route mintakat kovesse.
Minimum future canonical route-csalad:
- `POST /dxf-rules-profiles`
- `GET /dxf-rules-profiles`
- `GET /dxf-rules-profiles/{profile_id}`
- `PATCH /dxf-rules-profiles/{profile_id}`
- `DELETE /dxf-rules-profiles/{profile_id}`
- `POST /dxf-rules-profiles/{profile_id}/versions`
- `GET /dxf-rules-profiles/{profile_id}/versions`
- `GET /dxf-rules-profiles/{profile_id}/versions/{version_id}`
- `PATCH /dxf-rules-profiles/{profile_id}/versions/{version_id}`
- `DELETE /dxf-rules-profiles/{profile_id}/versions/{version_id}`

Kulon legyen jelezve, hogy ez docs-level freeze, nem route implementation.

### 3. A project-level active rules selection kulon route-csalad legyen
A dokumentumnak rogzitenie kell, hogy a future project-bound active rules version selection
kovesse a mar letezo selection route mintat.
Minimum future canonical route-csalad:
- `PUT /projects/{project_id}/dxf-rules-selection`
- `GET /projects/{project_id}/dxf-rules-selection`
- `DELETE /projects/{project_id}/dxf-rules-selection`

Kulon legyen rogzitve, hogy ez project-level active version binding,
nem file-level override es nem upload payloadba rejtett parameter.

### 4. A preflight run API legyen project/file scoped, kulon a file ingesttol
A dokumentumnak ki kell mondania, hogy a preflight run domain kulon resource,
nem a `POST /projects/{project_id}/files` finalize payloadba zsufolt side effect.
Minimum future canonical route-csalad:
- `POST /projects/{project_id}/files/{file_id}/preflight-runs`
- `GET /projects/{project_id}/files/{file_id}/preflight-runs`
- `GET /projects/{project_id}/preflight-runs/{preflight_run_id}`
- `GET /projects/{project_id}/preflight-runs/{preflight_run_id}/artifacts`
- `GET /projects/{project_id}/preflight-runs/{preflight_run_id}/artifacts/{artifact_id}/url`
- `GET /projects/{project_id}/preflight-runs/{preflight_run_id}/artifacts/{artifact_id}/download`

Kulon legyen jelezve, hogy a list/url/download minta a `runs.py` artifact surfaces-bol jon.

### 5. A review decision es replace/rerun action endpointok legyenek kulon kezelve
A dokumentumnak rogzitnie kell, hogy a review es replacement action endpointok
kulon route-ak legyenek, ne impliciten payload-mezok.
Minimum future canonical actionok:
- `POST /projects/{project_id}/preflight-runs/{preflight_run_id}/review-decisions`
- `POST /projects/{project_id}/files/{file_id}/replace`
- opcionailag: `POST /projects/{project_id}/preflight-runs/{preflight_run_id}/rerun`

Kulon legyen rogzitve, hogy a rerun csak akkor keruljon be a canonical contractba,
ha a state machine es data-model ezt tenylegesen indokolja; egyebkent maradhat extension marker.

### 6. Legyen explicit request/response shape irany docs-szinten
A dokumentumban legyen legalabb magas szintu schema-irany:
- request body hol szukseges es hol nincs;
- `StrictRequestModel` mint request-body minta;
- response envelope vagy item/list stilus;
- status_code mintak (201 create, 200 read, 204 delete) a meglevo route-okhoz igazodva.

De ne valjon route-level Pydantic model implementaciova.

### 7. Legyen explicit anti-scope: auth, RLS, OpenAPI, frontend integracio
A dokumentum mondja ki, hogy:
- auth/RLS reszletszabalyok kesobbi taskban jonnek;
- OpenAPI schema export majd implementacio utan frissul;
- frontend hook/service contract es polling UX nem T6 scope;
- worker/background orchestration nem T6 scope.

### 8. Legyen migration/data-model/API kulonvalasztas
A dokumentum mondja ki, hogy:
- a lifecycle mar T4-ben rogzitve van;
- a data-model/migration T5-ben rogzitve van;
- ez a task csak HTTP API contract freeze;
- a request model / route implementation majd E2/E3 implementacios taskokban jon.

### 9. Legyen explicit anti-scope lista
Kulon legyen kimondva, hogy ebben a taskban nem szabad:
- `api/routes/*.py` fajlt letrehozni vagy modositani;
- `api/request_models.py`-t boviteni;
- OpenAPI-t exportalni;
- frontend oldali hookot vagy oldalt tervezni reszletesen;
- SQL migraciot, RLS policyt vagy state-machine implementaciot rogziteni.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t6_api_contract_specification.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e1_t6_api_contract_specification/run.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`

## DoD
- [ ] Letrejon a `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md` dokumentum.
- [ ] A dokumentum explicit kulonvalasztja a current-code route truthot es a future canonical DXF prefilter API contractot.
- [ ] A dokumentum a rules profile/version route-csaladot a meglevo owner-scoped profile mintakhoz igazitja.
- [ ] A dokumentum a project-level active rules selectiont kulon route-csaladkent rogziti.
- [ ] A dokumentum a preflight run / artifact / review action route-csaladot kulon resource-kent kezeli.
- [ ] A dokumentum rogzit minimalis request/response/status-code mintakat docs-szinten, implementacio nelkul.
- [ ] A dokumentum explicit anti-scope listat tartalmaz.
- [ ] Nem jon letre vagy modosul implementacios route/request-model/OpenAPI/frontend fajl.
