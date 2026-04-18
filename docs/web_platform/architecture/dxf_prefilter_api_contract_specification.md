# DXF Prefilter API Contract Specification (E1-T6)

## 1. Cel
Ez a dokumentum docs-only modban lefagyasztja a DXF prefilter V1 HTTP API
contractjat. A cel nem route implementacio, hanem a future canonical API surface
rogzitese a meglevo route-mintakra tamaszkodva.

## 2. Scope boundary
- Ez API contract freeze, nem FastAPI kodolas.
- Nem request model implementacio, nem OpenAPI export.
- Nem auth/RLS policy implementacio.
- Nem SQL migration vagy persistence implementacio.
- Nem frontend hook/service/polling implementacio.

## 3. Current-code API truth (repo-grounded)

### 3.1 Project files ingest route-csalad
- Prefix: `/projects/{project_id}/files`
- Letezo endpoint mintak:
  - `POST /projects/{project_id}/files/upload-url`
  - `POST /projects/{project_id}/files`
  - `GET /projects/{project_id}/files`
  - `DELETE /projects/{project_id}/files/{file_id}`
- A `complete_upload` jelenleg aszinkron geometry importot indit,
  de nincs dedikalt prefilter resource.

### 3.2 Owner-scoped profile/version route-csalad mintak
A repoban tobb top-level profile/version API minta mar letezik:
- `/run-strategy-profiles`
- `/scoring-profiles`
- `/postprocessor-profiles`

Kozos route pattern:
- profile: `POST`, `GET(list)`, `GET(id)`, `PATCH`, `DELETE`
- nested versions: `POST /{profile_id}/versions`, `GET(list)`, `GET(id)`,
  `PATCH`, `DELETE`

### 3.3 Project-level selection route-csalad mintak
Letezo project-scoped active selection route-ok:
- `PUT/GET/DELETE /projects/{project_id}/run-strategy-selection`
- `PUT/GET/DELETE /projects/{project_id}/scoring-selection`
- `PUT/GET/DELETE /projects/{project_id}/manufacturing-selection`

A minta lenyege:
- project-level active version binding kulon resource-kent,
- `PUT` alapu upsert,
- kulon `GET` es `DELETE`.

### 3.4 Runs artifact surface mintak
A repoban letezik artifact API surface a runs domainben:
- `GET /projects/{project_id}/runs/{run_id}/artifacts`
- `GET /projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/url`
- `GET /projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/download`

Action endpoint mintak is latszanak:
- `POST /projects/{project_id}/runs/{run_id}/rerun`
- `POST /projects/{project_id}/runs/{run_id}/artifacts/bundle`

### 3.5 Request body baseline
- A route request body modellek `StrictRequestModel`-re ulnek (`extra="forbid"`).
- A docs-level prefilter API contract ezt a strict body mintat kovesse,
  de T6-ban nem keszul uj model implementacio.

## 4. Future canonical DXF prefilter API contract (V1, docs-level)

### 4.1 Alapelv
A future DXF prefilter API kulon route-csalad legyen:
- elkulonitve a files ingest endpointoktol,
- de a meglevo profile/version, selection es artifact mintakhoz igazodva,
- T4 lifecycle es T5 data-model contracttal konzisztensen.

### 4.2 Rules profile/version route-csalad
Top-level owner-scoped minta szerint:
- `POST /dxf-rules-profiles` -> uj profile (201)
- `GET /dxf-rules-profiles` -> owner list (200)
- `GET /dxf-rules-profiles/{profile_id}` -> egy profile (200)
- `PATCH /dxf-rules-profiles/{profile_id}` -> profile update (200)
- `DELETE /dxf-rules-profiles/{profile_id}` -> profile torles (204)
- `POST /dxf-rules-profiles/{profile_id}/versions` -> uj version (201)
- `GET /dxf-rules-profiles/{profile_id}/versions` -> version lista (200)
- `GET /dxf-rules-profiles/{profile_id}/versions/{version_id}` -> egy version (200)
- `PATCH /dxf-rules-profiles/{profile_id}/versions/{version_id}` -> version update (200)
- `DELETE /dxf-rules-profiles/{profile_id}/versions/{version_id}` -> version torles (204)

### 4.3 Project-level active rules selection route-csalad
Project-scoped selection pattern szerint:
- `PUT /projects/{project_id}/dxf-rules-selection` -> active version binding upsert (200)
- `GET /projects/{project_id}/dxf-rules-selection` -> aktualis binding (200)
- `DELETE /projects/{project_id}/dxf-rules-selection` -> binding torles (204)

Kizaras:
- ez nem file-level override endpoint;
- ez nem upload payloadba rejtett parameter.

### 4.4 Preflight run route-csalad (project/file scoped)
Kulon resource a files ingesttol:
- `POST /projects/{project_id}/files/{file_id}/preflight-runs` -> run inditas (201)
- `GET /projects/{project_id}/files/{file_id}/preflight-runs` -> file run lista (200)
- `GET /projects/{project_id}/preflight-runs/{preflight_run_id}` -> run detail (200)

### 4.5 Preflight artifact route-csalad
A runs artifact surface mintajara:
- `GET /projects/{project_id}/preflight-runs/{preflight_run_id}/artifacts` (200)
- `GET /projects/{project_id}/preflight-runs/{preflight_run_id}/artifacts/{artifact_id}/url` (200)
- `GET /projects/{project_id}/preflight-runs/{preflight_run_id}/artifacts/{artifact_id}/download` (307 redirect)

### 4.6 Review / replace / rerun action endpointok
Kulon action endpoint mintaval:
- `POST /projects/{project_id}/preflight-runs/{preflight_run_id}/review-decisions` (201)
- `POST /projects/{project_id}/files/{file_id}/replace` (201 vagy 200, endpoint policy szerint)
- opcionais: `POST /projects/{project_id}/preflight-runs/{preflight_run_id}/rerun` (202/201)

Megjegyzes:
- a `rerun` endpoint V1 extension marker lehet; csak akkor keruljon be kovetkezo
  implementacios korben, ha T4 lifecycle es T5 persistence slicing ezt indokolja.

## 5. Minimalis request/response/status-code elvek (docs-level)

### 5.1 Request body elvek
- Body ott kotelezo, ahol allapotot hoz letre vagy frissit:
  `POST`/`PUT`/`PATCH` endpointok.
- Body tiltott extra mezoket (`StrictRequestModel` elv).
- `GET`/`DELETE` endpointok alapertelmezetten body nelkuliek.

### 5.2 Response stilus
- Lista endpointok: `items + total` vagy route-domainnel konzisztens lista response.
- Detail endpointok: egyetlen resource response.
- Action endpointok: domain-specifikus action response (pl. review decision id/status).

### 5.3 Status code elvek
- `201` create actionokra.
- `200` read/update/upsert valaszokra.
- `204` delete jellegu vegpontokra.
- `307` download proxy redirect patternre.
- `4xx/5xx` hibak current FastAPI/szolgaltatas hibakezelessel konzisztensen.

## 6. Kapcsolat T4/T5 contractokkal
- T4 mar rogzitette a lifecycle modell szerzodest; T6 nem irja ujra.
- T5 mar rogzitette a data-model/migration slicing iranyt; T6 nem ir SQL vagy
  migration reszleteket.
- T6 kizlag a HTTP API surface-et es route-csalad szerkezetet fagyasztja.

## 7. Explicit anti-scope lista
- Nem jon letre es nem modosul `api/routes/*.py`.
- Nem modosul `api/request_models.py`.
- Nem tortenik OpenAPI export vagy schema commit.
- Nem keszul frontend hook/service implementacio.
- Nem keszul SQL migration, enum vagy RLS policy specifikacio implementacios szinten.
- Nem keszul worker/polling orchestration implementacio.

## 8. Later extension jeloltek (nem V1 minimum)
- Preflight rerun endpoint kotelezove teese.
- Bulk replace/multi-file preflight actionok.
- Async polling/progress endpoint bovitese.
- Version compare / diff endpoint rules profile domainben.

## 9. Bizonyitek forrasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
- `api/routes/files.py`
- `api/routes/run_strategy_profiles.py`
- `api/routes/scoring_profiles.py`
- `api/routes/postprocessor_profiles.py`
- `api/routes/project_strategy_scoring_selection.py`
- `api/routes/project_manufacturing_selection.py`
- `api/routes/runs.py`
- `api/request_models.py`
